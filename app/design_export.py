"""Complete, portable design export using the saved winner, never the current form."""
from pathlib import Path
import csv
import json
import math
import re
import shutil
import uuid
import threading
RENDER_LOCK=threading.Lock()
import xml.etree.ElementTree as ET
from datetime import datetime
import wing_optimizer as w
from ground_effect import orient_geometry,signed_result
from air_conditions import air_properties

def parse_distribution(path,kind,geometry,with_coordinates=False):
    data=Path(path).read_bytes()
    match=re.search(br'encoding=["\']([^"\']+)',data[:100])
    encoding=match[1].decode("ascii") if match else "utf-8"
    text=data.decode(encoding)
    root=ET.fromstring(re.sub(r'encoding=["\'][^"\']+["\']',"",text))
    if root.findtext("value")!=kind:raise ValueError("Unexpected distribution type: "+str(path))
    elements=root.findall("elements/element")
    cases=root.findall("cases/case")
    if len(cases)!=1 or len(elements)!=len(geometry):raise ValueError("Incomplete distribution element/case count")
    curves=cases[0].findall("element")
    values={int(e.attrib["idx"]):[float(v.text) for v in e.findall("value")] for e in curves}
    result=[];coordinates=[]
    for index,g in enumerate(geometry):
        points=[(float(p.findtext("x")),float(p.findtext("y"))) for p in elements[index].findall("coordinates/point")]
        row=values.get(index,[])
        if len(points)<3 or len(row)!=len(points):raise ValueError("Distribution coordinate/value count mismatch")
        # JavaFoil can omit input vertices (notably the origin). Keep its
        # actual samples rather than inventing a value for a missing vertex.
        cursor=0
        for point in points:
            if not all(math.isfinite(v) for v in point):raise ValueError("Invalid distribution coordinates")
            while cursor<len(g) and math.dist(point,g[cursor])>2e-7:cursor+=1
            if cursor==len(g):raise ValueError("Distribution geometry differs from the winner")
            cursor+=1
        if not all(math.isfinite(v) for v in row):raise ValueError("Invalid distribution values")
        result.append(row);coordinates.append(points)
    return (result,coordinates) if with_coordinates else result

def flatten(value,path=""):
    if isinstance(value,dict):
        for key,item in value.items():yield from flatten(item,(path+"." if path else "")+str(key))
    elif isinstance(value,list):
        for index,item in enumerate(value,1):yield from flatten(item,f"{path}[{index}]")
    else:yield path,value

def csv_rows(path,rows,fields=None):
    with Path(path).open("w",newline="",encoding="utf-8-sig") as f:
        if fields:
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
        else:
            writer=csv.writer(f);writer.writerows(rows)

def export_design(run_directory,parent,progress=lambda s:None,stop=None):
    run=Path(run_directory).resolve();parent=Path(parent).resolve()
    if not parent.is_dir():raise ValueError("Choose an existing destination folder")
    summary=json.loads((run/"summary.json").read_text())
    best=summary.get("best")
    if not best:raise ValueError("This run has no completed winning design")
    if best.get("solver", "JavaFoil") not in ("JavaFoil", "JavaFoil (provisional)"):
        raise ValueError("This saved design uses a retired solver. Load its configuration and optimize again with JavaFoil before exporting.")
    name="Wing_design_"+datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    destination=parent/name
    stage=parent/("."+name+"_"+uuid.uuid4().hex[:8]+".building")
    stage.mkdir()
    try:
        progress("Copying saved geometry and optimization data…")
        shutil.copytree(run/"best",stage/"geometry")
        for picture in (stage/"geometry").glob("*.svg"):picture.unlink()
        if (run/"input").is_dir():shutil.copytree(run/"input",stage/"input")
        (stage/"data").mkdir()
        for name in ("config.json","summary.json","results.csv","evaluations.csv","sweep_trace.jsonl","provenance.json","input_profiles.json"):
            if (run/name).is_file():shutil.copy2(run/name,stage/"data"/name)
        config=json.loads((run/"best/best_config.json").read_text())
        profiles,chords,reference,axes,alphas,clearance=w.prepare(config,run/"best")
        params={name:points[0] for name,points in axes.items()}
        geometry=orient_geometry(w.build_geometry(profiles,chords,params,reference,[e["angle_mode"] for e in config["elements"]]),reference,config["environment"])
        w.validate_geometry(geometry,clearance,config.get("bounding_box"))
        from geometric_constraints import check_heights
        check_heights(geometry,reference,config.get("height_constraints",[]))
        progress("Calculating surface distributions for the winning geometry…")
        solver=w.JavaFoil(config["simulation"],stop)
        rows=solver.analyze(geometry,config["simulation"],alphas,stage/"analysis",surface_distributions=True)
        replay=signed_result(rows[0],config["environment"])
        if abs(replay["cl"]-best["cl"])>.0011:raise ValueError("The saved winner did not reproduce its Cl during export")
        pressure,surface_geometry=parse_distribution(stage/"analysis/pressure.xml","pressure coefficient",geometry,with_coordinates=True)
        velocity,velocity_geometry=parse_distribution(stage/"analysis/velocity.xml","velocity ratio",geometry,with_coordinates=True)
        if surface_geometry!=velocity_geometry:raise ValueError("Pressure and velocity sample coordinates differ")
        sim=config["simulation"];rho,mu,sound=air_properties(sim)
        speed=sim.get("airspeed_m_s",sim["reynolds"]*mu/(rho*reference))
        speed_source="Specified relative airspeed" if "airspeed_m_s" in sim else "Inferred from reference Reynolds number and air properties"
        samples=[]
        for i,g in enumerate(surface_geometry):
            source_index=0
            for j,(x,y) in enumerate(g):
                while math.dist((x,y),geometry[i][source_index])>2e-7:source_index+=1
                side="upper" if source_index<=len(geometry[i])//2 else "lower"
                source_index+=1
                samples.append(dict(element=i+1,point=j+1,surface=side,
                    x_ref=x,y_ref=y,x_m=x*reference,y_m=y*reference,cp=pressure[i][j],velocity_ratio=velocity[i][j],
                    velocity_m_s=velocity[i][j]*speed))
        csv_rows(stage/"data/surface_distributions.csv",samples,list(samples[0]))
        csv_rows(stage/"data/pressure_coefficient.csv",[{k:r[k] for k in ("element","point","surface","x_m","y_m","cp")} for r in samples],["element","point","surface","x_m","y_m","cp"])
        csv_rows(stage/"data/velocity_distribution.csv",[{k:r[k] for k in ("element","point","surface","x_m","y_m","velocity_ratio","velocity_m_s")} for r in samples],["element","point","surface","x_m","y_m","velocity_ratio","velocity_m_s"])
        dimensions=[]
        for i,g in enumerate(geometry,1):
            xs=[x*reference for x,y in g];ys=[y*reference for x,y in g]
            e=config["elements"][i-1]
            dimensions.append(dict(element=i,profile=e["profile"],chord_m=chords[i-1],
                entered_angle_deg=params[f"incidence_{i}"],angle_mode=e["angle_mode"],
                absolute_angle_deg=best.get(f"absolute_incidence_{i}"),gap_m=params.get(f"gap_{i}",0)*reference,
                overlap_m=params.get(f"overlap_{i}",0)*reference,reynolds=sim["reynolds"]*chords[i-1]/reference,
                x_min_m=min(xs),x_max_m=max(xs),y_min_m=min(ys),y_max_m=max(ys),width_m=max(xs)-min(xs),height_m=max(ys)-min(ys)))
        csv_rows(stage/"data/setup_dimensions.csv",dimensions,list(dimensions[0]))
        original=json.loads((run/"config.json").read_text())
        portable=json.loads(json.dumps(original))
        for e in portable["elements"]:
            if e["profile"].startswith("input/"):e["profile"]="../"+e["profile"]
        (stage/"data/config.json").write_text(json.dumps(portable,indent=2))
        csv_rows(stage/"data/all_parameters.csv",[["setup","parameter","value"],*[["winning",k,v] for k,v in flatten(config)],*[["original",k,v] for k,v in flatten(original)]])
        metadata=dict(reference_chord_m=reference,element_count=len(geometry),speed_m_s=speed,speed_source=speed_source,
            distribution_source="JavaFoil native XML exports",
            solver="JavaFoil",
            graph_quality="Two 3840 x 2160 PNG images",
            solver_panels_per_element=config["panels_per_element"],source_run=str(run),created=datetime.now().isoformat(),
            replay={k:replay[k] for k in ("cl","cd","cm","lift_cl","downforce_cl")},dimensions=dimensions,best=best,air_conditions=sim)
        (stage/"export_details.json").write_text(json.dumps(metadata,indent=2))
        progress("Creating 4K images and the PDF report…")
        from design_report import create_graphs,create_report
        with RENDER_LOCK:
            if stop and stop.is_set():raise w.Cancelled()
            create_graphs(stage,geometry,reference,samples,config)
            create_report(stage,summary,config,original,metadata,samples)
        # Exported analysis scripts should reference the completed folder, not its temporary staging name.
        for script in stage.rglob("*.jfscript"):
            text=script.read_text()
            text=text.replace(str(stage).replace("\\","/"),str(destination).replace("\\","/"))
            script.write_text(text)
        (stage/"README.txt").write_text(
            "Optimized wing design"+chr(10)+"Open design_report.pdf for results, dimensions, settings and surface data."+chr(10)+
            "graphs contains two 3840 x 2160 surface graphs."+chr(10)+
            "data contains all numerical values, original setup and optimization history."+chr(10)+
            "geometry contains CAD coordinates and a replayable best_config.json. Keep input beside geometry."+chr(10)+
            "analysis contains JavaFoil surface distributions and the reproduced winning polar."+chr(10))
        if stop and stop.is_set():raise w.Cancelled()
        stage.rename(destination)
        return destination
    except BaseException:
        # Only remove the new staging directory created by this invocation.
        if stage.resolve().parent==parent and stage.name.startswith(".Wing_design_") and stage.name.endswith(".building"):
            shutil.rmtree(stage)
        raise
