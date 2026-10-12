"""Configurable coarse sweeps followed by finer refinement around winning coordinates."""
import math

class SearchBudget(Exception): pass
class SearchCancelled(Exception): pass

def sweep_resolution(settings):
    coarse=settings.get("coarse_divisions",10)
    if isinstance(coarse,bool) or not str(coarse).strip().isdigit() or int(coarse)<1:
        raise ValueError("Coarse divisions must be a positive whole number")
    raw=settings.get("fine_step_percent",.25)
    try:percent=float(raw)
    except (TypeError,ValueError):raise ValueError("Fine step must be a percentage greater than 0 and less than 2.5")
    if isinstance(raw,bool) or not math.isfinite(percent) or not 0<percent<2.5:
        raise ValueError("Fine step must be a percentage greater than 0 and less than 2.5")
    return int(coarse),percent

def refinement_window(center,low,high,percent):
    scale=high-low
    radius=scale*.025;step=scale*percent/100
    return dict(center=center,low=max(low,center-radius),high=min(high,center+radius),
                step=step,reference="full parameter range (maximum - minimum)")

def refinement_points(window):
    center=window["center"];lo=window["low"];hi=window["high"];step=window["step"]
    if step==0:return [center]
    first=math.ceil((lo-center)/step-1e-9);last=math.floor((hi-center)/step+1e-9)
    return sorted({lo,hi,center,*[max(lo,min(hi,center+i*step)) for i in range(first,last+1)]})

def ordered_parameters(element_count):
    order=[]
    for index in range(1,element_count+1):
        order.append(f"incidence_{index}")
        if index<element_count: order.extend((f"gap_{index+1}",f"overlap_{index+1}"))
    return order

def run_search(axes,evaluate,continuous,reference=1.,settings=None,stop=None,trace=lambda e:None,evaluate_many=None):
    settings=settings or {}
    divisions,fine_percent=sweep_resolution(settings)
    windows={}
    fine=True
    passes=int(settings.get("max_passes",5))
    cl_tol=float(settings.get("cl_tolerance",.0001))
    if passes<1: raise ValueError("Search pass limit must be positive")
    if not math.isfinite(cl_tol) or cl_tol<=0: raise ValueError("Cl tolerance must be finite and positive")
    count=len([n for n in axes if n.startswith("incidence_")])
    order=settings.get("parameter_order") or ordered_parameters(count)
    if set(order)!=set(axes): raise ValueError("Search order must cover every parameter")
    current={}
    for name in order:
        points=axes[name]
        current[name]=settings.get("initial_parameters",{}).get(name,(min(points)+max(points))/2 if name in continuous else points[len(points)//2])
        if not min(points)<=current[name]<=max(points): raise ValueError("Initial value outside range: "+name)
        if name not in continuous and current[name] not in points: raise ValueError("Initial value outside discrete choices: "+name)
    cache={}; calls=0
    def score(candidate,parameter,phase,cycle=0,level=0):
        nonlocal calls
        if stop and stop.is_set(): raise SearchCancelled()
        key=tuple(round(candidate[name],14) for name in order)
        cached=key in cache
        if not cached:
            if phase not in ("coarse","fine"):
                trace(dict(phase="sweep_start",stage=phase,parameter=parameter,block=[parameter] if parameter in axes else list(axes)))
            row=evaluate(dict(candidate))
            cache[key]=row["cl"] if row is not None else -math.inf
            calls+=1
        value=cache[key]
        trace(dict(parameter=parameter,phase=phase,cycle=cycle,level=level,parameters=dict(candidate),
                   cl=value if math.isfinite(value) else None,cached=cached))
        return value
    def sample(name,points,phase,cycle,level):
        nonlocal current,calls
        best=current[name]; best_score=score(current,name,"baseline",cycle,level)
        points=sorted(set(points))
        trace(dict(phase="sweep_start",stage=phase,parameter=name,block=[name]))
        if evaluate_many:
            pending=[]; keys=[]
            for point in points:
                candidate=dict(current); candidate[name]=point
                key=tuple(round(candidate[n],14) for n in order)
                if key not in cache and key not in keys:
                    pending.append(candidate); keys.append(key)
            for key,row in zip(keys,evaluate_many(pending)):
                cache[key]=row["cl"] if row is not None else -math.inf
                calls+=1
        for point in points:
            candidate=dict(current); candidate[name]=point
            value=score(candidate,name,phase,cycle,level)
            # Keep the current point on ties; prevents drift on flat numerical polars.
            if value>best_score+cl_tol:
                best,best_score=point,value
        current[name]=best
        return best_score
    def neighbors(name,tolerance):
        low,high=min(axes[name]),max(axes[name]); x=current[name]
        if name in continuous: return sorted({max(low,x-tolerance),min(high,x+tolerance)})
        points=sorted(axes[name]); index=points.index(x)
        return points[max(0,index-1):min(len(points),index+2)]
    termination="pass_limit"; verified=False; final_score=-math.inf; completed_passes=0; checks=[]
    try:
        final_score=score(current,"initial","initial")
        for cycle in range(1,passes+1):
            completed_passes=cycle
            # Finish all coarse parameter sweeps before the single fine stage.
            for phase in (("coarse","fine") if fine else ("coarse",)):
                for name in order:
                    if len(axes[name])==1: continue
                    low,high=min(axes[name]),max(axes[name])
                    if phase=="fine":
                        if name not in continuous: continue
                        windows[name]=refinement_window(current[name],low,high,fine_percent)
                        points=refinement_points(windows[name])
                    else:
                        points=[low+(high-low)*i/divisions for i in range(divisions+1)] if name in continuous else axes[name]
                    final_score=sample(name,points,phase,cycle,1 if phase=="fine" else 0)
                    trace(dict(phase="sweep_complete",stage=phase,parameter=name,cycle=cycle,parameters=dict(current),
                               cl=final_score if math.isfinite(final_score) else None))
            # Certify neighbors with every other parameter at its FINAL value, since parameters interact.
            final_score=score(current,"all","verify_baseline",cycle)
            improvements=[]; checks=[]
            for name in order:
                tolerance=windows.get(name,refinement_window(current[name],min(axes[name]),max(axes[name]),fine_percent))["step"]
                passed=True
                for point in neighbors(name,tolerance):
                    if point==current[name]: continue
                    candidate=dict(current); candidate[name]=point
                    value=score(candidate,name,"verify_neighbor",cycle)
                    if value>final_score+cl_tol:
                        passed=False; improvements.append((value,name,point))
                checks.append(dict(parameter=name,passed=passed,value=current[name],
                    at_boundary=current[name] in (min(axes[name]),max(axes[name]))))
            verified=math.isfinite(final_score) and all(c["passed"] for c in checks)
            if verified:
                termination="bounded_coordinate_local_maximum"
                break
            if improvements:
                value,name,point=max(improvements)
                current[name]=point; final_score=value
                trace(dict(phase="verification_improvement",parameter=name,parameters=dict(current),cl=value))
    except SearchBudget:
        termination="evaluation_budget"
    except SearchCancelled:
        termination="cancelled"
    return dict(method="sequential",parameter_order=order,initial_divisions=divisions,fine_step_percent=fine_percent,refinement_half_width_percent=2.5,refinement_windows=windows,
        termination=termination,converged=verified,completed_passes=completed_passes,
        unique_evaluations=calls,parameters=current,cl=final_score if math.isfinite(final_score) else None,
        local_checks=checks,cl_tolerance=cl_tol,fine_stage=fine,
        resolution={name:dict(step=windows.get(name,refinement_window(current[name],min(points),max(points),fine_percent))["step"],
                             unit="degrees" if name.startswith("incidence_") else "reference chord")
                    for name,points in axes.items() if name in continuous})
