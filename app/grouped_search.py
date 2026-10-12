"""Streaming grouped coordinate sweeps for constrained size-and-fit optimization."""
import itertools
import math
from coordinate_search import sweep_resolution,SearchCancelled,refinement_window,refinement_points

def parameter_blocks(axes,groups):
    blocks=[];covered=set()
    for group in groups:
        if not group.get("enabled",True): continue
        ids=sorted(group["elements"])
        for kind in ("chord","incidence","gap","overlap"):
            block=[f"{kind}_{i}" for i in ids if f"{kind}_{i}" in axes]
            if block and block not in blocks:
                blocks.append(block);covered.update(block)
    for name in axes:
        if name not in covered:blocks.append([name])
    return blocks

def run_grouped_search(axes,evaluate,continuous,reference=1.,settings=None,stop=None,trace=lambda e:None,evaluate_many=None):
    settings=settings or {};coarse,fine_percent=sweep_resolution(settings);windows={}
    blocks=parameter_blocks(axes,settings.get("height_constraints",[]))
    order=list(dict.fromkeys(n for block in blocks for n in block))
    passes=int(settings.get("max_passes",5));tolerance=float(settings.get("cl_tolerance",.0001))
    if passes<1 or not math.isfinite(tolerance) or tolerance<=0:raise ValueError("Sweep rounds and Cl tolerance must be positive")
    current={n:settings.get("initial_parameters",{}).get(n,(min(v)+max(v))/2 if n in continuous else v[len(v)//2]) for n,v in axes.items()}
    for name, value in current.items():
        if not min(axes[name]) <= value <= max(axes[name]):
            raise ValueError("Initial value outside range: " + name)
        if name not in continuous and value not in axes[name]:
            raise ValueError("Initial value outside discrete choices: " + name)
    cache={};calls=0;checks=[];score=-math.inf;cycle=0;converged=False;termination="pass_limit"
    def key(p):return tuple(round(p[n],14) for n in order)
    def stopped():
        if stop and stop.is_set():raise SearchCancelled()
    def scores(candidates,phase,block):
        nonlocal calls
        iterator=iter(candidates)
        width=int(settings.get("workers",1))
        while True:
            stopped()
            chunk=list(itertools.islice(iterator,width))
            if not chunk:return
            pending=[];keys=set()
            for p in chunk:
                k=key(p)
                if k not in cache and k not in keys:pending.append(p);keys.add(k)
            if pending:
                rows=evaluate_many(pending) if evaluate_many else map(evaluate,pending)
                for p,row in zip(pending,rows):
                    cache[key(p)]=row["cl"] if row is not None else -math.inf;calls+=1
            for p in chunk:
                value=cache[key(p)]
                trace(dict(phase=phase,parameter=block[0] if len(block)==1 else ",".join(block),
                           parameters=dict(p),cl=value if math.isfinite(value) else None,cycle=cycle))
                yield p,value
    def points(name,phase):
        values=axes[name];lo,hi=min(values),max(values);x=current[name]
        if len(values)==1:return [x]
        if name not in continuous:
            if phase!="verify":return sorted(set(values))
            index=sorted(values).index(x)
            return sorted(values)[max(0,index-1):index+2]
        if phase=="coarse":return [lo+(hi-lo)*i/coarse for i in range(coarse+1)]
        if phase=="verify":
            step=windows.get(name,refinement_window(x,lo,hi,fine_percent))["step"]
            return sorted({max(lo,x-step),x,min(hi,x+step)})
        windows[name]=refinement_window(x,lo,hi,fine_percent)
        return refinement_points(windows[name])
    def candidates(block,phase):
        baseline=dict(current)
        for combination in itertools.product(*(points(n,phase) for n in block)):
            yield dict(baseline,**dict(zip(block,combination)))
    def sweep(block,phase):
        nonlocal current,score
        trace(dict(phase="sweep_start",stage=phase,parameter=block[0],parameters=dict(current),block=block))
        winner=dict(current);winning=score
        for candidate,value in scores(candidates(block,phase),phase,block):
            if value>winning+tolerance:winner=dict(candidate);winning=value
        changed=winning>score+tolerance
        current=winner;score=winning
        trace(dict(phase="sweep_complete",stage=phase,parameter=block[0],block=block,parameters=dict(current),cl=score if math.isfinite(score) else None))
        return changed
    try:
        trace(dict(phase="sweep_start",stage="baseline",parameter=order[0],block=order,parameters=dict(current)))
        score=next(scores([current],"initial",order))[1]
        for cycle in range(1,passes+1):
            for phase in ("coarse","fine"):
                for block in blocks:
                    if any(len(axes[n])>1 for n in block):sweep(block,phase)
            checks=[];improved=False
            for block in blocks:
                changed=sweep(block,"verify");improved|=changed
                checks.append(dict(parameters=block,passed=not changed))
            if math.isfinite(score) and not improved:
                converged=True;termination="bounded_group_local_maximum";break
    except SearchCancelled:termination="cancelled"
    return dict(method="free",parameter_order=order,parameter_blocks=blocks,initial_divisions=coarse,fine_step_percent=fine_percent,refinement_half_width_percent=2.5,refinement_windows=windows,
        termination=termination,converged=converged,completed_passes=cycle,unique_evaluations=calls,
        parameters=current,cl=score if math.isfinite(score) else None,local_checks=checks,cl_tolerance=tolerance,fine_stage=True,
        resolution={n:dict(step=windows.get(n,refinement_window(current[n],min(v),max(v),fine_percent))["step"],unit="degrees" if n.startswith("incidence") else "reference chord") for n,v in axes.items() if n in continuous})
