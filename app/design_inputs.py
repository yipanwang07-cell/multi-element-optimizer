"""Physical unit conversion and backward-compatible design inputs."""
import copy
import math
import re
UNIT_FACTORS={"m":1., "cm":.01, "mm":.001, "in":.0254, "ft":.3048}
ALIASES={"meter":"m","metre":"m","meters":"m","metres":"m","inch":"in","inches":"in",
         "feet":"ft","foot":"ft"}

def unit_name(unit):
    unit=ALIASES.get(str(unit).lower(),str(unit).lower())
    if unit not in UNIT_FACTORS: raise ValueError("Length unit must be m, cm, mm, in or ft")
    return unit

def length_m(value,unit="m"):
    if isinstance(value,dict):
        unit=value.get("unit",unit); value=value["value"]
    if isinstance(value,str):
        match=re.fullmatch(r"\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*([a-zA-Z]*)\s*",value)
        if not match: raise ValueError("Length must be a number, optionally followed by a unit")
        value=float(match[1])
        if match[2]: unit=match[2]
    value=float(value)*UNIT_FACTORS[unit_name(unit)]
    if not math.isfinite(value): raise ValueError("Length must be finite")
    return value

def map_values(value,factor):
    if isinstance(value,dict):
        return {key:float(item)*factor if key in ("min","max","step","initial") else item
                for key,item in value.items() if key!="unit"}
    if isinstance(value,list): return [float(item)*factor for item in value]
    return float(value)*factor

def length_values_m(value,unit="m"):
    if isinstance(value,dict) and "value" in value:
        return length_m(value,unit)
    selected=value.get("unit",unit) if isinstance(value,dict) else unit
    if isinstance(value,str): return length_m(value,selected)
    return map_values(value,UNIT_FACTORS[unit_name(selected)])

def normalize_config(config):
    """Populate legacy metre/fraction keys while preserving the user's unit inputs."""
    default=unit_name(config.get("length_unit","m"))
    elements=config.get("elements",[])
    for element in elements:
        unit=unit_name(element.get("length_unit",default))
        if "chord" in element:
            chord=length_values_m(element["chord"],unit)
            if isinstance(chord,(dict,list)):
                if config.get("search",{}).get("mode")!="free":
                    raise ValueError("Chord ranges require free optimization mode")
                points=([float(chord["min"]),float(chord["max"])] if isinstance(chord,dict) else chord)
                if not points or min(points)<=0: raise ValueError("Chord range must be positive")
                element["chord_m"]=(min(points)+max(points))/2
            else: element["chord_m"]=chord
        mode=element.get("angle_mode","absolute").lower()
        if mode not in ("absolute","relative"): raise ValueError("Angle mode must be absolute or relative")
        element["angle_mode"]=mode
    if elements and elements[0].get("angle_mode")=="relative":
        raise ValueError("The first element has no previous element; use absolute angle")
    if "reference_chord" in config:
        config["reference_chord_m"]=length_m(config["reference_chord"],default)
    if elements:
        reference=float(config.get("reference_chord_m",elements[0].get("chord_m",0)))
        if not math.isfinite(reference) or reference<=0: raise ValueError("Reference chord must be positive")
        for element in elements[1:]:
            unit=element.get("length_unit",default)
            for key in ("gap","overlap"):
                if key+"_length" in element:
                    element[key]=map_values(length_values_m(element[key+"_length"],unit),1/reference)
        if "minimum_clearance_length" in config:
            config["minimum_clearance"]=length_m(config["minimum_clearance_length"],default)/reference
        if "bounding_box_lengths" in config:
            config["bounding_box"]={key:length_m(value,default)/reference
                                    for key,value in config["bounding_box_lengths"].items()}
    return config

def absolute_angles(params,modes=None):
    modes=modes or ["absolute"]*len([k for k in params if k.startswith("incidence_")])
    result=[]; previous=0.
    for index,mode in enumerate(modes,1):
        entered=params[f"incidence_{index}"]
        angle=previous+entered if mode=="relative" else entered
        result.append(angle); previous=angle
    return result

def fixed_best_config(saved,params,alpha,reference):
    result=copy.deepcopy(saved)
    for index,element in enumerate(result["elements"],1):
        if element["profile"].startswith("input/"): element["profile"]="../"+element["profile"]
        element["incidence_deg"]=params[f"incidence_{index}"]
        if f"chord_{index}" in params:
            element["chord_m"]=params[f"chord_{index}"]*reference
            element["chord"]={"value":element["chord_m"]/UNIT_FACTORS[element.get("length_unit",result.get("length_unit","m"))],"unit":element.get("length_unit",result.get("length_unit","m"))}
        if index>1:
            for key in ("gap","overlap"):
                element[key]=params[f"{key}_{index}"]
                if key+"_length" in element:
                    original=element[key+"_length"]
                    unit=original.get("unit",element.get("length_unit",result.get("length_unit","m"))) if isinstance(original,dict) else element.get("length_unit",result.get("length_unit","m"))
                    element[key+"_length"]={"value":element[key]*reference/UNIT_FACTORS[unit_name(unit)],"unit":unit}
    result["reference_chord"]={"value":reference,"unit":"m"}
    result["reference_chord_m"]=reference
    result["alpha_deg"]=alpha
    result["search"]={"mode":"grid"}
    return result

def ui_config(config,default_unit="mm"):
    """Migrate legacy configs to editable physical lengths, retaining angle semantics."""
    result=copy.deepcopy(config)
    normalize_config(result)
    result["schema_version"]=2
    result["length_unit"]=unit_name(result.get("length_unit",default_unit))
    factor=UNIT_FACTORS[result["length_unit"]]
    reference=result.get("reference_chord_m",result["elements"][0]["chord_m"])
    result["reference_chord"]={"value":reference/factor,"unit":result["length_unit"]}
    result["minimum_clearance_length"]={"value":result.get("minimum_clearance",.001)*reference/factor,"unit":result["length_unit"]}
    if result.get("bounding_box"):
        result["bounding_box_lengths"]={k:{"value":v*reference/factor,"unit":result["length_unit"]} for k,v in result["bounding_box"].items()}
    for index,e in enumerate(result["elements"]):
        e["length_unit"]=unit_name(e.get("length_unit",result["length_unit"]))
        local=UNIT_FACTORS[e["length_unit"]]
        e["chord"]=map_values(length_values_m(e["chord"],e["length_unit"]),1/local) if "chord" in e else e["chord_m"]/local
        if index:
            for key in ("gap","overlap"):
                e[key+"_length"]=map_values(e.get(key,.03),reference/local)
    return result
