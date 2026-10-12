"""Absolute height ceilings and geometry-only feasible initialization."""
import math
import random
from design_inputs import length_m

def constraint_kind(group):
    return "length" if group.get("measurement") == "right_x" or "max_length" in group else "height"


def validate_groups(config):
    groups=config.get("height_constraints",[])
    if config.get("search",{}).get("mode")=="free" and not any(g.get("enabled",True) for g in groups):
        raise ValueError("Enable at least one height or length constraint for Size & fit")
    count=len(config["elements"])
    for group in groups:
        if not group.get("enabled",True): continue
        kind=constraint_kind(group)
        group["measurement"]="right_x" if kind=="length" else "top_y"
        group.setdefault("unit",config.get("length_unit","m"))
        ids=group.get("elements",[])
        if not ids or any(type(i) is not int or not 1<=i<=count for i in ids) or len(set(ids))!=len(ids):
            raise ValueError(f"Geometry limits need distinct existing airfoil numbers (1–{count})")
        limit=length_m(group["max_"+kind],group["unit"])
        if limit<=0: raise ValueError(kind.capitalize()+" limit must be positive")


def check_heights(geometry,reference,groups):
    """Check enabled height/length boundaries; keep legacy API for saved setups."""
    measurements={f"top_y_m_{i}":max(y*reference for x,y in element) for i,element in enumerate(geometry,1)}
    for n,group in enumerate(groups,1):
        if not group.get("enabled",True): continue
        kind=constraint_kind(group)
        axis=0 if kind=="length" else 1
        values={i:max(point[axis]*reference for point in geometry[i-1]) for i in group["elements"]}
        top=max(values.values())
        limit=length_m(group["max_"+kind],group.get("unit","m"))
        if top>limit+1e-12:
            violating=[i for i,value in values.items() if value>limit+1e-12]
            description="rightmost point from x=0" if axis==0 else "highest point above y=0"
            raise ValueError(f"Airfoil(s) {violating} exceed {kind} limit {n}: {description} {top*1000:.3f} mm; limit {limit*1000:g} mm")
        measurements[f"{'limit_right_x' if axis==0 else 'ceiling_top_y'}_m_{n}"]=top
    return measurements


def free_order(count):
    return ([f"chord_{i}" for i in range(1,count+1)]+
            [f"incidence_{i}" for i in range(1,count+1)]+
            [f"gap_{i}" for i in range(2,count+1)]+
            [f"overlap_{i}" for i in range(2,count+1)])

def feasible_seed(axes,valid,stop=None,limit=1000,seed=42):
    middle={n:v[len(v)//2] for n,v in axes.items()}
    small=dict(middle)
    for n,v in axes.items():
        if n.startswith("chord_"): small[n]=min(v)
    rng=random.Random(seed)
    for attempt in range(limit):
        if stop and stop.is_set():
            from coordinate_search import SearchCancelled
            raise SearchCancelled()
        candidate=middle if attempt==0 else small if attempt==1 else {n:rng.choice(v) for n,v in axes.items()}
        try:
            valid(candidate)
            return candidate
        except ValueError:
            pass
    raise ValueError(f"No feasible starting geometry found in {limit} geometry-only trials. Adjust ranges or geometry limits; this does not prove infeasibility.")
