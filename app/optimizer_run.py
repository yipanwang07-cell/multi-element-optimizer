"""Shared saved-run workflow for exhaustive and ordered local sweeps."""
import csv
import json
import math
import random
import shutil
import sys
from datetime import datetime
from pathlib import Path
import threading
import os
from concurrent.futures import ThreadPoolExecutor
from design_inputs import absolute_angles, fixed_best_config, UNIT_FACTORS
from coordinate_search import run_search, SearchBudget, SearchCancelled
from ground_effect import orient_geometry, signed_result
from stall_models import stall_model_name
from transition_models import transition_model_name

def run_design(config,output,base,progress,stop,solver):
    import wing_optimizer as w
    config=json.loads(json.dumps(config))
    profiles,chords,reference,axes,alphas,clearance=w.prepare(config,base)
    modes=[e.get("angle_mode","absolute") for e in config["elements"]]
    names=list(axes); dimensions=[len(axes[n]) for n in names]; total=math.prod(dimensions)
    search=config.get("search",{}); mode=search.get("mode","sequential")
    from coordinate_search import sweep_resolution
    search["coarse_divisions"],search["fine_step_percent"]=sweep_resolution(search)
    search.pop("fine_divisions",None)
    search.pop("max_geometries",None)  # Retire limits from legacy saved configurations.
    if mode not in ("grid","random","sequential","free"): raise ValueError("Search mode must be sequential, grid or random")
    if mode not in ("sequential","free") and total>sys.maxsize:
        raise ValueError("Grid exceeds platform size; reduce the axes or choose sequential mode")
    from cpu_workers import physical_core_cpus,worker_count
    cpus=physical_core_cpus()
    workers=worker_count(search.get("workers","auto"),len(cpus))
    if solver is not None and not getattr(solver,"parallel_safe",False): workers=1
    config.pop("final_validation",None)  # Ignore retired backend settings in saved setups.
    stop=stop or threading.Event(); solver=solver or w.JavaFoil(config.get("simulation",{}),stop)
    if hasattr(solver,"configure_cores"): solver.configure_cores(cpus[:workers])
    search["workers"]=workers
    output=Path(output).resolve(); output.mkdir(parents=True,exist_ok=False)
    profile_sources=[]
    for i,e in enumerate(config["elements"]):
        entry=w.find_library_profile(e["profile"]); previous=config.get("profile_sources",[])
        profile_sources.append(entry or (previous[i] if i<len(previous) else dict(name=e["profile"],method="Generated NACA or user coordinate file")))
    config["profile_sources"]=profile_sources
    saved_config=json.loads(json.dumps(config))
    for i,e in enumerate(config["elements"],1):
        if not w.re.fullmatch(r"(?:NACA\s*)?\d{4}",e["profile"],w.re.I):
            source=w.resolve_profile(e["profile"],base)
            (output/"input").mkdir(exist_ok=True)
            shutil.copyfile(source,output/"input"/f"element_{i}.dat")
            saved_config["elements"][i-1]["profile"]=f"input/element_{i}.dat"
    (output/"config.json").write_text(json.dumps(saved_config,indent=2))
    (output/"input_profiles.json").write_text(json.dumps(profiles))
    hashes={p.name:w.hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(w.VENDOR.glob("*.jar"))}
    (output/"provenance.json").write_text(json.dumps(dict(jar_sha256=hashes,reference_chord_m=reference,
        generated=datetime.now().isoformat(),solver="JavaFoil",stall_model=stall_model_name(config["simulation"]["stall_model"]),transition_model=transition_model_name(config["simulation"]["transition_model"]),profile_sources=profile_sources,
        length_units="Physical inputs converted to metres; solver geometry divided by fixed reference chord",
        simulation_conditions=config["simulation"],environment=config["environment"],objective="Cl",force_direction="downward" if config["environment"]["flip_for_downforce"] else "upward",
        angle_modes=modes,note="2D section coefficients; sampled/local optimum, not a proven global maximum"),indent=2))
    objective_label="Cl"
    best=None; completed=0; rejected=0; failed=0; evaluated=0; cancelled=False; search_result=None
    extra=[f"chord_m_{i}" for i in range(1,len(modes)+1)] if mode=="free" else []
    extra += ["lift_cl","downforce_cl","reference_reynolds","mach","aspect_ratio"]
    extra += [f"reynolds_{i}" for i in range(1,len(modes)+1)]
    extra += [f"absolute_incidence_{i}" for i in range(1,len(modes)+1)]
    extra += [f"top_y_m_{i}" for i in range(1,len(modes)+1)]
    extra += [f"ceiling_top_y_m_{i}" for i in range(1,len(config.get("height_constraints",[]))+1)]
    extra += [f"{name}_m_{i}" for i in range(2,len(modes)+1) for name in ("gap","overlap")]
    with (output/"results.csv").open("w",newline="") as rf, (output/"evaluations.csv").open("w",newline="") as ef, (output/"sweep_trace.jsonl").open("w") as tf:
        result_fields=["geometry_id","alpha","cl","cd","cm","clearance",*names,*extra]
        rw=csv.DictWriter(rf,fieldnames=result_fields); rw.writeheader()
        ew=csv.DictWriter(ef,fieldnames=["geometry_id","status","reason",*names]); ew.writeheader()
        context={"phase":"baseline","block":[]}
        def trace(event):
            if event.get("phase")=="sweep_start":
                context.update(phase=event["stage"],block=event.get("block",[event["parameter"]]))
            tf.write(json.dumps(event)+"\n"); tf.flush()
        def iteration_message(params):
            labels=[]
            selected=context["block"] or list(params)
            for name in selected:
                value=params[name];key,index=name.split("_");index=int(index)
                if key=="incidence":
                    label="angle";unit="deg";scale=1
                else:
                    label="slot gap" if key=="gap" else key
                    unit=config["elements"][index-1].get("length_unit",config.get("length_unit","m"))
                    scale=reference/UNIT_FACTORS[unit]
                labels.append(f"{label} {index}: {value*scale:g} {unit}")
            progress(f"Iteration {evaluated}: {context['phase']} "+("; ".join(labels)))
        def evaluate(params,gid=None,prepared=None):
            nonlocal best,completed,rejected,failed,evaluated
            if stop.is_set(): raise w.Cancelled()
            evaluated+=1; gid=gid or f"g{evaluated:08d}"
            iteration_message(params)
            geometry=orient_geometry(w.build_geometry(profiles,chords,params,reference,modes),reference,config["environment"])
            try:
                distance=w.validate_geometry(geometry,clearance,config.get("bounding_box"))
                from geometric_constraints import check_heights
                heights=check_heights(geometry,reference,config.get("height_constraints",[]))
            except ValueError as e:
                rejected+=1; ew.writerow(dict(geometry_id=gid,status="rejected",reason=str(e),**params)); ef.flush()
                return None
            try:
                if prepared is not None:
                    if isinstance(prepared,Exception): raise prepared
                    rows=prepared
                else:
                    rows=solver.analyze(geometry,config["simulation"],alphas,output/"cases"/gid)
            except (w.Cancelled,SearchCancelled): raise
            except Exception as e:
                failed+=1; ew.writerow(dict(geometry_id=gid,status="failed",reason=str(e),**params)); ef.flush()
                return None
            completed+=1; ew.writerow(dict(geometry_id=gid,status="ok",reason="",**params)); ef.flush()
            derived={f"absolute_incidence_{i}":(-a if config["environment"]["flip_for_downforce"] else a) for i,a in enumerate(absolute_angles(params,modes),1)}
            derived.update(heights)
            derived.update(reference_reynolds=config["simulation"]["reynolds"],mach=config["simulation"]["mach"],aspect_ratio=config["simulation"].get("aspect_ratio",0))
            derived.update({f"reynolds_{i}":config["simulation"]["reynolds"]*params.get(f"chord_{i}",chords[i-1]/reference) for i in range(1,len(modes)+1)})
            if mode=="free": derived.update({f"chord_m_{i}":params[f"chord_{i}"]*reference for i in range(1,len(modes)+1)})
            derived.update({f"{name}_m_{i}":params[f"{name}_{i}"]*reference for i in range(2,len(modes)+1) for name in ("gap","overlap")})
            geometry_best=None
            for row in rows:
                row=signed_result(row,config["environment"])
                record=dict(geometry_id=gid,**row,clearance=distance,**params,**derived)
                rw.writerow(record)
                if geometry_best is None or row["cl"]>geometry_best["cl"]: geometry_best=record
                if best is None or row["cl"]>best["cl"]:
                    best=record
                    w.export_geometry(output/"best",geometry,reference,row["alpha"],environment=config["environment"])
                    (output/"best/best.json").write_text(json.dumps(dict(result=best,reference_chord_m=reference,
                        elements=config["elements"],angle_modes=modes,environment=config["environment"]),indent=2))
                    best_config=fixed_best_config(saved_config,params,row["alpha"],reference)
                    (output/"best/best_config.json").write_text(json.dumps(best_config,indent=2))
                    shutil.copyfile(output/"cases"/gid/"polar.txt",output/"best/polar.txt")
                    shutil.copyfile(output/"cases"/gid/"run.jfscript",output/"best/source_case.jfscript")
            rf.flush()
            return geometry_best
        def solve_candidate(params,gid):
            # Workers only write their own case directory; results are committed by the coordinator.
            try:
                geometry=orient_geometry(w.build_geometry(profiles,chords,params,reference,modes),reference,config["environment"])
                w.validate_geometry(geometry,clearance,config.get("bounding_box"))
                from geometric_constraints import check_heights
                check_heights(geometry,reference,config.get("height_constraints",[]))
                return solver.analyze(geometry,config["simulation"],alphas,output/"cases"/gid)
            except Exception as error:
                return error
        def evaluate_many(candidates,ids=None):
            iterator=iter(candidates); id_iterator=iter(ids) if ids is not None else None
            while True:
                if stop.is_set(): raise SearchCancelled()
                batch=[]
                for _ in range(workers):
                    try: params=next(iterator)
                    except StopIteration: break
                    gid=next(id_iterator) if id_iterator is not None else f"g{evaluated+len(batch)+1:08d}"
                    batch.append((params,gid))
                if not batch: return
                if workers==1:
                    for params,gid in batch: yield evaluate(params,gid)
                else:
                    futures=[pool.submit(solve_candidate,params,gid) for params,gid in batch]
                    for (params,gid),future in zip(batch,futures):
                        yield evaluate(params,gid,future.result())
        pool=ThreadPoolExecutor(max_workers=workers,thread_name_prefix="JavaFoil")
        try:
            if mode in ("sequential","free"):
                continuous=set()
                for name in axes:
                    key,index=name.split("_"); element=config["elements"][int(index)-1]
                    value=element.get("chord" if key=="chord" else "incidence_deg" if key=="incidence" else key+"_length",element.get(key))
                    if len(axes[name])>1 and isinstance(value,dict): continuous.add(name)
                if mode=="free":
                    from geometric_constraints import feasible_seed, free_order, check_heights
                    search=dict(search,parameter_order=free_order(len(modes)),height_constraints=config["height_constraints"])
                    def valid(candidate):
                        geometry=orient_geometry(w.build_geometry(profiles,chords,candidate,reference,modes),reference,config["environment"])
                        w.validate_geometry(geometry,clearance,config.get("bounding_box"))
                        check_heights(geometry,reference,config["height_constraints"])
                    search["initial_parameters"]=feasible_seed(axes,valid,stop,seed=search.get("seed",42))
                def callback(params):
                    return evaluate(params)
                # Cancellation is translated to the search engine's own stop exception.
                def safe_callback(params):
                    try: return callback(params)
                    except (w.Cancelled,SearchCancelled): raise SearchCancelled()
                if mode=="free":
                    from grouped_search import run_grouped_search
                    search_engine=run_grouped_search
                else:search_engine=run_search
                search_result=search_engine(axes,safe_callback,continuous,reference,search,stop,trace,evaluate_many=evaluate_many)
                search_result["method"]=mode
                cancelled=search_result["termination"]=="cancelled"
            else:
                context.update(phase="sweep",block=list(axes))
                count=min(int(search.get("sample_count",total)),total) if mode=="random" else total
                if count<1: raise ValueError("Random sample count must be positive")
                indices=range(total) if mode=="grid" or count==total else random.Random(search.get("seed",42)).sample(range(total),count)
                def candidates():
                    for index in indices:
                        params={}; rem=index
                        for n,d in reversed(list(zip(names,dimensions))):
                            params[n]=axes[n][rem%d]; rem//=d
                        yield params
                for _ in evaluate_many(candidates(),(f"g{index:08d}" for index in indices)): pass
                search_result=dict(method=mode,termination="grid_complete" if count==total else "sample_complete",converged=False)
        except (w.Cancelled,SearchCancelled):
            cancelled=True; search_result=dict(method=mode,termination="cancelled",converged=False)
        finally:
            pool.shutdown(wait=True,cancel_futures=True)
    warnings=[("JavaFoil stall correction is disabled (None)." if config["simulation"]["stall_model"]==2 else
               "JavaFoil uses the "+stall_model_name(config["simulation"]["stall_model"])+" empirical stall correction.")+
              " Validate high-lift maxima with CFD or experiments."]
    if config["simulation"].get("aspect_ratio",0)>0:
        warnings.append("Wingspan uses JavaFoil's approximate finite-span correction with rectangular reference area = wingspan × fixed reference chord; this is not a full 3D wing calculation.")
    if config["environment"]["ground_effect"]:
        warnings.append("JavaFoil uses a flat-ground mirror model for 2D airfoil sections; car-body and full diffuser flow are not modeled.")
    for source in profile_sources:
        if "approximation" in source.get("method","").lower(): warnings.append(source["name"]+": "+source.get("note",source["method"]))
    if best:
        if len(alphas)>1 and best["alpha"] in (alphas[0],alphas[-1]): warnings.append("Best reference-axis offset is at a range boundary.")
        if any(len(axes[n])>1 and abs(best[n]-edge)<1e-10 for n in names for edge in (min(axes[n]),max(axes[n]))):
            warnings.append("Best geometry reaches at least one parameter boundary.")
    if search_result and search_result["termination"] in ("evaluation_budget","pass_limit"):
        warnings.append("Search stopped at its "+search_result["termination"].replace("_"," ")+"; local convergence is not established.")
    summary=dict(best=best,total_grid_geometries=total,planned_geometries=None if mode in ("sequential","free") else count,
        evaluated_geometries=evaluated,successful_geometries=completed,rejected_geometries=rejected,failed_geometries=failed,
        cancelled=cancelled,parallel_workers=workers,physical_core_cpus=cpus[:workers],search=search_result,warnings=warnings,output=str(output))
    (output/"summary.json").write_text(json.dumps(summary,indent=2))
    w.write_report(output,summary)
    if best is None and not cancelled: raise RuntimeError(f"No valid simulation completed. See {output/'evaluations.csv'} and case logs.")
    return summary
