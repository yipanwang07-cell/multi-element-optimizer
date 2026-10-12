"""Physical air inputs, standard sea-level defaults, and solver reference quantities."""
import math
from design_inputs import length_m
SPEED_UNITS={"m/s":1.,"km/h":1/3.6,"mph":.44704,"ft/s":.3048}

def positive(value,label):
    value=float(value)
    if not math.isfinite(value) or value<=0: raise ValueError(label+" must be finite and positive")
    return value

def air_properties(sim):
    temperature=float(sim.get("temperature_c",15.))+273.15
    temperature=positive(temperature,"Absolute air temperature")
    pressure=positive(sim.get("pressure_pa",101325.),"Air pressure")
    density=pressure/(287.05*temperature)
    viscosity=1.716e-5*(temperature/273.15)**1.5*(273.15+110.4)/(temperature+110.4)
    sound=math.sqrt(1.4*287.05*temperature)
    for key,label,default in (("density_override","Air density",density),("viscosity_override","Dynamic viscosity",viscosity),("sound_speed_override","Speed of sound",sound)):
        value=sim.get(key)
        if value is not None:
            if key=="density_override": density=positive(value,label)
            elif key=="viscosity_override": viscosity=positive(value,label)
            else: sound=positive(value,label)
    return density,viscosity,sound

def normalize_conditions(sim,reference):
    # Legacy CLI configurations retain their explicit reference Re and Mach.
    if "relative_airspeed" not in sim and "wingspan" not in sim:
        return sim
    speed=sim.get("relative_airspeed",{"value":20,"unit":"m/s"})
    if isinstance(speed,dict):
        unit=speed.get("unit","m/s"); value=speed["value"]
    else: unit="m/s"; value=speed
    if unit not in SPEED_UNITS: raise ValueError("Airspeed unit must be m/s, km/h, mph or ft/s")
    velocity=positive(value,"Relative airspeed")*SPEED_UNITS[unit]
    span=positive(length_m(sim.get("wingspan",{"value":1500,"unit":"mm"})),"Wingspan")
    rho,mu,sound=air_properties(sim)
    reynolds=positive(sim.get("reynolds_override",rho*velocity*reference/mu),"Reference Reynolds number")
    mach=float(sim.get("mach_override",velocity/sound))
    aspect=float(sim.get("aspect_ratio_override",span/reference))
    if not math.isfinite(mach) or not 0<=mach<.7: raise ValueError("Mach must be in [0,0.7)")
    if not math.isfinite(aspect) or aspect<0: raise ValueError("Aspect ratio must be finite and nonnegative; 0 means 2D")
    sim.update(reynolds=reynolds,mach=mach,aspect_ratio=aspect,
        wingspan_m=span,airspeed_m_s=velocity,air_density_kg_m3=rho,dynamic_viscosity_pa_s=mu,
        speed_of_sound_m_s=sound,reference_area_m2=span*reference)
    return sim


def reynolds_estimates(sim,reference,chords):
    """Physical reference estimate and solver-scaled per-element chord ranges."""
    reference=positive(reference,"Reference chord")
    speed=sim["relative_airspeed"]
    velocity=positive(speed["value"],"Relative airspeed")*SPEED_UNITS[speed.get("unit","m/s")]
    rho,mu,_=air_properties(sim)
    calculated=rho*velocity*reference/mu
    effective=positive(sim.get("reynolds_override",calculated),"Reference Reynolds number")
    elements=[]
    for values in chords:
        lengths=[positive(v,"Chord") for v in values]
        elements.append((effective*min(lengths)/reference,effective*max(lengths)/reference))
    return calculated,effective,elements
