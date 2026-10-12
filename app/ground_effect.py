"""Optional inverted car geometry above JavaFoil's y=0 ground plane."""
from design_inputs import length_m
def normalize_environment(config):
    env=config.setdefault("environment",{})
    for key in ("ground_effect","flip_for_downforce"):
        if type(env.get(key,False)) is not bool: raise ValueError(key+" must be true or false")
        env.setdefault(key,False)
    if env["ground_effect"]:
        env["clearance_m"]=length_m(env.get("ground_clearance",50),env.get("length_unit","mm"))
        if env["clearance_m"]<=0: raise ValueError("Ground clearance must be greater than zero")
    config.setdefault("simulation",{})["ground_effect"]=env["ground_effect"]
    return env

def orient_geometry(geometry,reference,environment):
    if environment.get("flip_for_downforce"):
        # Restore contour traversal after reflection so the upper surface still comes first.
        geometry=[[(x,-y) for x,y in reversed(element)] for element in geometry]
    else: geometry=[list(element) for element in geometry]
    if environment.get("ground_effect"):
        shift=environment["clearance_m"]/reference-min(y for e in geometry for x,y in e)
        geometry=[[(x,y+shift) for x,y in element] for element in geometry]
        if min(y for e in geometry for x,y in e)<=0:
            raise ValueError("Airfoil touches or crosses the ground")
    return geometry

def signed_result(row,environment):
    lift=row.get("lift_cl",row["cl"])
    return dict(row,lift_cl=lift,downforce_cl=-lift,
                cl=-lift if environment.get("flip_for_downforce") else lift)
