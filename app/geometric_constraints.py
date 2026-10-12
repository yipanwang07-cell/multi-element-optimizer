"""Absolute height ceilings and geometry-only feasible initialization."""
import math
import random
from design_inputs import length_m

def validate_groups(config):
    groups=config.get("height_constraints",[])
    if config.get("search",{}).get("mode")=="free" and not groups:
        raise ValueError("Add at least one airfoil height ceiling for Size & fit")
    count=len(config["elements"])
    for group in groups:
        group["measurement"]="top_y"
        group.setdefault("unit",config.get("length_unit","m"))
        ids=group.get("elements",[])
        if not ids or any(type(i) is not int or not 1<=i<=count for i in ids) or len(set(ids))!=len(ids):
            raise ValueError(f"Height ceilings need distinct existing airfoil numbers (1–{count})")
        limit=length_m(group["max_height"],group.get("unit",config.get("length_unit","m")))
        if limit<=0: raise ValueError("Height ceiling must be positive")

def check_heights(geometry,reference,groups):
    measurements={f"top_y_m_{i}":max(y*reference for x,y in element) for i,element in enumerate(geometry,1)}
    for n,group in enumerate(groups,1):
        top=max(measurements[f"top_y_m_{i}"] for i in group["elements"])
        limit=length_m(group["max_height"],group.get("unit","m"))
        if top>limit+1e-12:
            violating=[i for i in group["elements"] if measurements[f"top_y_m_{i}"]>limit+1e-12]
            raise ValueError(f"Airfoil(s) {violating} exceed height ceiling {n}: highest point {top*1000:.3f} mm above y=0; ceiling {limit*1000:g} mm")
        measurements[f"ceiling_top_y_m_{n}"]=top
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
    raise ValueError(f"No feasible starting geometry found in {limit} geometry-only trials. Adjust ranges or height limits; this does not prove infeasibility.")
