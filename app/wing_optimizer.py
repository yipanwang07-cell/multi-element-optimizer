"""Multi-element geometry generation and JavaFoil optimization."""
from __future__ import annotations
import argparse
import csv
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from design_inputs import normalize_config, absolute_angles, UNIT_FACTORS
from airfoil_library import resolve_profile, find as find_library_profile

from app_paths import ROOT,EXAMPLES,VENDOR
from stall_models import stall_model_id, stall_model_name
from transition_models import transition_model_id, transition_model_name
if (VENDOR / "python").exists():
    sys.path.insert(0, str(VENDOR / "python"))
from shapely.geometry import Polygon

class Cancelled(Exception):
    pass

def positive(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(name + " must be finite and positive")
    return value

def values(value):
    """Accept scalar, list, or {min,max,step}; preserve an inclusive uniform grid."""
    if isinstance(value, dict):
        lo, hi = float(value["min"]), float(value["max"])
        if hi==lo:
            if not math.isfinite(lo): raise ValueError("Range must be finite")
            return [lo]
        step = positive(value.get("step",(hi-lo)/10), "step")
        if not math.isfinite(lo + hi) or hi < lo:
            raise ValueError("Range must have finite min <= max")
        n = round((hi - lo) / step)
        if n > 10000 or abs(lo + n * step - hi) > 1e-7 * max(1, abs(hi)):
            raise ValueError("Range end must land on the step; at most 10001 values")
        result = [lo + i * step for i in range(n + 1)]
    else:
        result = [float(x) for x in (value if isinstance(value, list) else [value])]
    if not result or not all(math.isfinite(x) for x in result):
        raise ValueError("Sweep values must be nonempty and finite")
    return list(dict.fromkeys(result))

def naca4(code, panels=120):
    code = code.upper().replace("NACA", "").replace(" ", "")
    if not re.fullmatch(r"\d{4}", code):
        raise ValueError("Use a NACA four-digit code or an airfoil .dat/.txt file")
    m, p, t = int(code[0])/100, int(code[1])/10, int(code[2:])/100
    if t <= 0 or (m and p == 0):
        raise ValueError("Invalid NACA thickness or camber position")
    upper, lower = [], []
    for i in range(panels // 2 + 1):
        x = (1 - math.cos(math.pi * i / (panels // 2))) / 2
        yt = 5*t*(.2969*math.sqrt(x)-.1260*x-.3516*x*x+.2843*x**3-.1036*x**4)
        if not m:
            yc = slope = 0
        elif x < p:
            yc = m/p**2*(2*p*x-x*x)
            slope = 2*m/p**2*(p-x)
        else:
            yc = m/(1-p)**2*(1-2*p+2*p*x-x*x)
            slope = 2*m/(1-p)**2*(p-x)
        if i in (0, panels // 2):
            yt = 0.0
        theta = math.atan(slope)
        upper.append((x-yt*math.sin(theta), yc+yt*math.cos(theta)))
        lower.append((x+yt*math.sin(theta), yc-yt*math.cos(theta)))
    return list(reversed(upper)) + lower[1:]

def normalize(points, panels):
    points = [p for i,p in enumerate(points) if i == 0 or p != points[i-1]]
    if len(points) < 10:
        raise ValueError("Profile needs at least 10 perimeter points")
    if any(not math.isfinite(x+y) for x,y in points):
        raise ValueError("Nonfinite profile coordinates")
    le = min(points, key=lambda p:p[0])
    te = ((points[0][0]+points[-1][0])/2, (points[0][1]+points[-1][1])/2)
    dx, dy = te[0]-le[0], te[1]-le[1]
    chord = math.hypot(dx, dy)
    if chord <= 0:
        raise ValueError("Profile must run trailing edge -> leading edge -> trailing edge")
    if min(points[0][0], points[-1][0]) < max(x for x,y in points)-.02*chord:
        raise ValueError("DAT must use Selig order: TE -> LE -> TE (Lednicer unsupported)")
    c,s = dx/chord,dy/chord
    pts = [(((x-le[0])*c+(y-le[1])*s)/chord,
            (-(x-le[0])*s+(y-le[1])*c)/chord) for x,y in points]
    # Ensure upper surface comes first, as expected by JavaFoil.
    area = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(pts,pts[1:]+pts[:1]))
    if area < 0:
        pts.reverse()
    polygon = Polygon(pts)
    if not polygon.is_valid or polygon.area < 1e-6:
        raise ValueError("Profile outline is self-intersecting or degenerate")
    # Resample each surface independently; cosine spacing resolves LE and TE.
    leading = min(range(len(pts)), key=lambda i:pts[i][0])
    def resample(part, count):
        lengths = [0.]
        for a,b in zip(part,part[1:]):
            lengths.append(lengths[-1]+math.dist(a,b))
        if lengths[-1] == 0:
            raise ValueError("Empty profile surface")
        out, j = [], 0
        for i in range(count+1):
            target = lengths[-1]*(1-math.cos(math.pi*i/count))/2
            while j < len(part)-2 and lengths[j+1] < target:
                j += 1
            f = (target-lengths[j])/(lengths[j+1]-lengths[j])
            out.append(tuple(part[j][k]*(1-f)+part[j+1][k]*f for k in (0,1)))
        return out
    return resample(pts[:leading+1],panels//2) + resample(pts[leading:],panels//2)[1:]

def profile(source, panels, base):
    if re.fullmatch(r"(?:NACA\s*)?\d{4}", source, re.I):
        return naca4(source, panels)
    path = resolve_profile(source,base)
    points = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        tokens = line.split()
        if len(tokens) == 2:
            try:
                points.append(tuple(float(x) for x in tokens))
            except ValueError:
                pass
    return normalize(points, panels)

def rotate(points, degrees):
    a = math.radians(degrees)
    c,s = math.cos(a),math.sin(a)
    return [(c*x-s*y,s*x+c*y) for x,y in points]

def build_geometry(profiles, chords, params, reference, angle_modes=None):
    """Positive incidence rotates clockwise. Gap/overlap in fixed body axes."""
    result = []
    prev_te = (0.,0.)
    resolved_angles=absolute_angles(params,angle_modes)
    for i,(pts,chord) in enumerate(zip(profiles,chords)):
        chord=params.get(f"chord_{i+1}",chord/reference)*reference
        scaled = [(x*chord/reference,y*chord/reference) for x,y in pts]
        pts = rotate(scaled, -resolved_angles[i])
        if i:
            origin = (prev_te[0]-params[f"overlap_{i+1}"],
                      prev_te[1]-params[f"gap_{i+1}"])
        else:
            origin = (0.,0.)
        pts = [(x+origin[0],y+origin[1]) for x,y in pts]
        result.append(pts)
        # TE midpoint is a stable anchor even for thick imported trailing edges.
        prev_te = ((pts[0][0]+pts[-1][0])/2,(pts[0][1]+pts[-1][1])/2)
    return result

def validate_geometry(geometry, clearance, box=None):
    polygons = [Polygon(p) for p in geometry]
    if any(not p.is_valid or p.area < 1e-10 for p in polygons):
        raise ValueError("Invalid element polygon")
    for i,p in enumerate(polygons):
        for j,q in enumerate(polygons[:i]):
            if p.intersects(q):
                raise ValueError(f"Elements {j+1} and {i+1} intersect or touch")
            if p.distance(q) < clearance:
                raise ValueError(f"Elements {j+1} and {i+1} below minimum surface clearance")
    if box:
        x0=min(p.bounds[0] for p in polygons); x1=max(p.bounds[2] for p in polygons)
        y0=min(p.bounds[1] for p in polygons); y1=max(p.bounds[3] for p in polygons)
        if x1-x0 > box["width"] or y1-y0 > box["height"]:
            raise ValueError("Assembly exceeds bounding box")
    return min((p.distance(q) for i,p in enumerate(polygons) for q in polygons[:i]), default=None)

def geometry_text(geometry):
    return "\n9999.9 9999.9\n".join(
        "\n".join(f"{x:.12g} {y:.12g}" for x,y in pts) for pts in geometry)+"\n"

def svg_geometry(geometry,ground=False):
    pts = [p for element in geometry for p in element]
    x0=min(x for x,y in pts); x1=max(x for x,y in pts)
    y0=min(y for x,y in pts); y1=max(y for x,y in pts)
    if ground: y0=min(0.,y0)
    pad=max(x1-x0,y1-y0)*.06
    colors = ["#2563eb","#dc2626","#059669","#9333ea","#d97706"]
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0-pad} {-y1-pad} {x1-x0+2*pad} {y1-y0+2*pad}">']
    if ground:
        lines.append(f'<line x1="{x0-pad}" y1="0" x2="{x1+pad}" y2="0" stroke="#64748b" stroke-width="{pad/12}"/>')
        lines.append(f'<text x="{x0}" y="{pad*.7}" font-size="{pad*.5}" fill="#475569">Ground (y=0)</text>')
    for i,element in enumerate(geometry):
        coords=" ".join(f"{x},{-y}" for x,y in element)
        lines.append(f'<polygon points="{coords}" fill="{colors[i % len(colors)]}" fill-opacity=".15" stroke="{colors[i % len(colors)]}" stroke-width="{pad/20}"/>')
    return "\n".join(lines+["</svg>"])

def export_geometry(directory, geometry, reference, alpha=0,environment=None):
    import io
    from safe_files import atomic_write_text
    ground=bool((environment or {}).get("ground_effect"))
    directory.mkdir(parents=True,exist_ok=True)
    atomic_write_text(directory/"javafoil_geometry.txt",geometry_text(geometry))
    atomic_write_text(directory/"geometry.svg",svg_geometry(geometry,ground))
    # Body rotates clockwise at positive aerodynamic angle of attack.
    operating = [rotate(p,-alpha) for p in geometry]
    atomic_write_text(directory/"geometry_at_best_alpha.svg",svg_geometry(operating,ground))
    with io.StringIO(newline="") as f:
        writer=csv.writer(f); writer.writerow(["element","point","x_m","y_m","z_m"])
        for i,pts in enumerate(geometry,1):
            for j,(x,y) in enumerate(pts):
                writer.writerow([i,j,x*reference,y*reference,0])
            atomic_write_text(directory/f"element_{i}_solidworks.xyz",
                "\n".join(f"{x*reference:.12g} {y*reference:.12g} 0" for x,y in pts)+"\n")
        atomic_write_text(directory/"coordinates_m.csv", f.getvalue())
    atomic_write_text(directory/"coordinates_at_best_alpha_m.json",
        json.dumps([[(x*reference,y*reference) for x,y in p] for p in operating],indent=2))

def parse_polar(path, expected):
    """Read JavaFoil's ASCII polar, retaining alpha/Cl/Cd/Cm only."""
    rows=[]
    for line in path.read_text(encoding="utf-8",errors="replace").splitlines():
        parts=line.split()
        if len(parts)<4:
            continue
        try:
            alpha,cl,cd,cm=map(float,parts[:4])
        except ValueError:
            continue
        if not any(abs(alpha-a)<1e-5 for a in expected):
            continue
        if not all(math.isfinite(x) for x in (alpha,cl,cd,cm)) or cd < 0:
            continue
        rows.append(dict(alpha=alpha,cl=cl,cd=cd,cm=cm))
    # An incomplete polar cannot win a comparison against fully evaluated geometries.
    if len(rows)!=len(expected) or any(sum(abs(r["alpha"]-a)<1e-5 for r in rows)!=1 for a in expected):
        raise RuntimeError("JavaFoil polar missing, duplicated, or invalid angle results; see raw polar/log")
    return rows

class JavaFoil:
    parallel_safe=True
    def configure_cores(self,cpus):
        from cpu_workers import CoreSlots
        self.core_slots=CoreSlots(cpus)
    def __init__(self, settings, stop=None):
        from cpu_workers import physical_core_cpus
        self.configure_cores(physical_core_cpus()[:1])
        self.settings=settings; self.stop=stop or threading.Event()
        self.java=settings.get("java",shutil.which("java") or "java")
        if not shutil.which(self.java) and not Path(self.java).is_file():
            raise ValueError("Java was not found. Install Java 17 or set simulation.java to java.exe.")
        self.vendor=Path(settings.get("javafoil_dir",VENDOR)).resolve()
        for name in ("javafoil.jar","mhclasses.jar","javafoil-compatible-v2.jar"):
            if not (self.vendor/name).is_file():
                raise ValueError(f"Missing {name} in {self.vendor}. Restore runtime/vendor or run tools/setup.py.")

    def analyze(self, geometry, settings, alphas, directory, surface_distributions=False,flow_field=False):
        directory.mkdir(parents=True,exist_ok=True)
        geo=directory/"geometry.txt"; geo.write_text(geometry_text(geometry))
        polar=directory/"polar.txt"
        script=directory/"run.jfscript"
        q=lambda path:json.dumps(str(path.resolve()).replace("\\","/"))
        re_value=settings["reynolds"]
        step=alphas[1]-alphas[0] if len(alphas)>1 else 1
        # The official downloaded JavaFoil distribution takes percent transition locations and integer flags.
        source=f"""
Options.Country(0);
Options.MachNumber({settings.get("mach",0)});
Options.AspectRatio({settings.get("aspect_ratio",0)});
Options.SweepAngle(0);
Options.GroundEffect({int(settings.get("ground_effect",False))});
Options.StallModel({stall_model_id(settings.get("stall_model",1))});
Options.TransitionModel({transition_model_id(settings.get("transition_model",1))});
Geometry.Clear();
if (!Geometry.Open({q(geo)})) throw new Error("Geometry import failed");
Geometry.Save({q(directory/"loaded_geometry.txt")});
Modify.Select(Java.to([{",".join(str(i+1) for i in range(len(geometry)))}], "int[]"));
Polar.Analyze({re_value},{re_value},{re_value},{alphas[0]},{alphas[-1]},{step},
{100*settings.get("transition_upper",1)},{100*settings.get("transition_lower",1)},{settings.get("roughness",0)},0);
if (!Polar.Save({q(polar)})) throw new Error("Polar export failed");
JavaFoil.Exit();
"""
        if surface_distributions:
            extra=""
            for plot,name,checkbox in ((0,"velocity","theVelocityCB"),(1,"pressure","thePressureCB")):
                extra+=f'var pf=Velocity.getClass().getDeclaredField("m_PlotType"); pf.setAccessible(true); pf.setInt(Velocity,{plot});'
                extra+=f'var cb=Velocity.getClass().getDeclaredField("{checkbox}"); cb.setAccessible(true); cb.get(Velocity).setState(true);'
                extra+=f'Velocity.Analyze({alphas[0]},{alphas[0]},1,0);'
                extra+=f'if (!Velocity.Save({q(directory/(name+".xml"))})) throw new Error("{name} export failed");'
            if flow_field:
                extent=max(max(abs(x-.5),abs(y)*2) for g in geometry for x,y in g)
                field_size=max(100,int(math.ceil((extent+.3)*100)))
                extra+=f'var fc=FlowField.getClass().getDeclaredField("theViewSizeChoice"); fc.setAccessible(true); fc.get(FlowField).add("{field_size}%");'
                extra+=f'FlowField.Analyze({alphas[0]},{field_size},1,{settings.get("field_x_steps",480)},{settings.get("field_y_steps",270)},1,0,0,0,0,0,0);'
                extra+=f'if (!FlowField.Save({q(directory/"flow_field.txt")})) throw new Error("Flow field export failed");'
            source=source.replace("JavaFoil.Exit();",extra)
            source="try {"+source+"} finally {JavaFoil.Exit();}"
        script.write_text(source)
        command=[self.java,"-XX:ActiveProcessorCount=1","-cp",str(self.vendor/"javafoil-compatible-v2.jar")+os.pathsep+str(self.vendor/"*"),"MH.JavaFoil.JavaFoil","Script="+str(script.resolve())]
        start=time.monotonic()
        from cpu_workers import bind_process
        with self.core_slots.acquire() as cpu, (directory/"javafoil.log").open("w") as log:
            process=subprocess.Popen(command,cwd=self.vendor,stdout=log,stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
            try:
                affinity=bind_process(process,cpu)
                (directory/"process.json").write_text(json.dumps(dict(pid=process.pid,logical_cpu=cpu,affinity_mask=affinity)))
                while process.poll() is None:
                    if self.stop.wait(.1):
                        raise Cancelled()
                    if time.monotonic()-start > settings.get("timeout_seconds",120):
                        raise RuntimeError("JavaFoil timed out; see javafoil.log")
                if process.returncode or not polar.exists():
                    raise RuntimeError("JavaFoil failed to export a polar; see javafoil.log")
            finally:
                if process.poll() is None:
                    process.terminate()
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill(); process.wait()
        return parse_polar(polar,alphas)

def prepare(config,base):
    normalize_config(config)
    from ground_effect import normalize_environment
    env=normalize_environment(config)
    elements=config.get("elements",[])
    if not elements:
        raise ValueError("Specify at least one airfoil")
    panels=int(config.get("panels_per_element",120))
    if panels < 40 or panels > 240 or panels%2:
        raise ValueError("Panels per element must be even, between 40 and 240")
    chords=[positive(e["chord_m"],"chord_m") for e in elements]
    reference=positive(config.get("reference_chord_m",chords[0]),"reference chord")
    profiles=[profile(e["profile"],panels,base) for e in elements]
    axes={}
    for i,e in enumerate(elements,1):
        axes[f"incidence_{i}"]=values(e.get("incidence_deg",0))
        if i>1:
            axes[f"gap_{i}"]=values(e.get("gap",.03))
            axes[f"overlap_{i}"]=values(e.get("overlap",.03))
            if any(x<0 for x in axes[f"gap_{i}"]):
                raise ValueError("Vertical gap must be nonnegative")
    alphas=values(config.get("alpha_deg",{"min":0,"max":20,"step":1}))
    if alphas!=sorted(alphas) or (len(alphas)>2 and any(abs((b-a)-(alphas[1]-alphas[0]))>1e-7 for a,b in zip(alphas,alphas[1:]))):
        raise ValueError("Alpha values must form an increasing uniform grid")
    if (env["ground_effect"] or env["flip_for_downforce"]) and alphas!=[0.]:
        raise ValueError("With ground or flipped orientation, set whole-wing angle offset to 0 and use each airfoil angle range")
    sim=config.setdefault("simulation",{})
    from air_conditions import normalize_conditions
    normalize_conditions(sim,reference)
    sim["stall_model"]=stall_model_id(sim.get("stall_model",1))
    sim["reynolds"]=positive(sim.get("reynolds",1e6),"Reynolds number")
    mach=float(sim.get("mach",0))
    sim["mach"]=mach
    aspect=float(sim.get("aspect_ratio",0))
    if not math.isfinite(aspect) or aspect<0: raise ValueError("Aspect ratio must be finite and nonnegative")
    sim["aspect_ratio"]=aspect
    if not 0<=mach<.7:
        raise ValueError("Mach must be in [0,0.7)")
    for key in ("transition_upper","transition_lower"):
        sim[key]=float(sim.get(key,1))
        if not 0<sim[key]<=1:
            raise ValueError(key+" must be in (0,1]")
    if int(sim.get("roughness",0)) not in range(4):
        raise ValueError("Roughness must be 0,1,2,3")
    sim["transition_model"]=transition_model_id(sim.get("transition_model",1))
    sim["timeout_seconds"]=positive(sim.get("timeout_seconds",120),"timeout")
    clearance=float(config.get("minimum_clearance",.001))
    if not math.isfinite(clearance) or clearance<0:
        raise ValueError("Minimum clearance must be finite and nonnegative")
    box=config.get("bounding_box")
    if box:
        for k in ("width","height"):
            positive(box[k],k)
    from geometric_constraints import validate_groups
    validate_groups(config)
    if config.get("search",{}).get("mode")=="free":
        from design_inputs import length_values_m, map_values
        for i,e in enumerate(elements,1):
            axes[f"chord_{i}"]=values(map_values(length_values_m(e.get("chord",e["chord_m"]),e.get("length_unit",config.get("length_unit","m"))) if "chord" in e else e["chord_m"],1/reference))
            if min(axes[f"chord_{i}"])<=0: raise ValueError("Chord ranges must be positive")
        if alphas!=[0.]: raise ValueError("Free optimization uses each element's AoA; set reference-axis offset to 0")
    return profiles,chords,reference,axes,alphas,clearance

def run(config,output,base=ROOT,progress=print,stop=None,solver=None):
    from optimizer_run import run_design
    return run_design(config,output,base,progress,stop,solver)


def write_report(output, summary):
    import html
    escape=lambda value:html.escape(str(value))
    with (output/"results.csv").open(newline="") as f:
        all_rows=list(csv.DictReader(f))
    best=summary["best"]
    curves={}
    for row in all_rows:
        curves.setdefault(row["geometry_id"],[]).append((float(row["alpha"]),float(row["cl"])))
    sequential=summary.get("search",{}).get("method") in ("sequential","free")
    if sequential:
        values_by_case={key:max(y for x,y in curve) for key,curve in curves.items()}
        evaluated=list(values_by_case.values())
        maximum=-math.inf; cumulative=[]
        for index,value in enumerate(evaluated,1):
            maximum=max(maximum,value); cumulative.append((index,maximum))
        curves={"evaluated":[(i,y) for i,y in enumerate(evaluated,1)],"best-so-far":cumulative}
    points=[p for curve in curves.values() for p in curve]
    chart=""
    if points:
        x0=min(x for x,y in points); x1=max(x for x,y in points)
        y0=min(y for x,y in points); y1=max(y for x,y in points)
        xspan=max(x1-x0,1); yspan=max(y1-y0,.1)
        chart='<svg viewBox="0 0 720 320" xmlns="http://www.w3.org/2000/svg"><rect width="720" height="320" fill="white"/><path d="M60 20V270H690" fill="none" stroke="#94a3b8"/>'
        for i in range(6):
            x=x0+xspan*i/5; y=y0+yspan*i/5
            chart+=f'<text x="{60+620*i/5}" y="290" font-size="12" text-anchor="middle">{x:.1f}</text>'
            chart+=f'<text x="48" y="{270-240*i/5}" font-size="12" text-anchor="end">{y:.2f}</text>'
        shown=list(curves)[:200]
        if not sequential and best and best["geometry_id"] not in shown: shown.append(best["geometry_id"])
        for key in shown:
            poly=" ".join(f"{60+(x-x0)/xspan*620},{270-(y-y0)/yspan*240}" for x,y in curves[key])
            highlight=(key=="best-so-far") if sequential else (best and key==best["geometry_id"])
            chart+=f'<polyline points="{poly}" fill="none" stroke="{"#2563eb" if highlight else "#cbd5e1"}" stroke-width="{3 if highlight else 1}"/>'
        axis_label="Unique geometry evaluation" if sequential else "Reference-axis AoA offset (degrees)"
        chart+=f'<text x="375" y="315" font-size="13" text-anchor="middle">{axis_label}</text><text x="20" y="20" font-size="13">Cl</text></svg>'
        if sequential: (output/"search_history.svg").write_text(chart)
        (output/"lift_curves.svg").write_text(chart)
    heading="Stopped — partial results" if summary["cancelled"] else "Optimization results"
    text=f"""<!doctype html><html><meta charset="utf-8"><title>Wing optimization results</title>
<style>body{{font:16px system-ui;max-width:1000px;margin:40px auto;padding:0 20px;color:#172033;background:#f8fafc}}h1{{font-size:28px}}section{{background:white;padding:20px;border-radius:12px;margin:16px 0}}svg{{width:100%;max-height:320px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:8px;text-align:left;border-bottom:1px solid #ddd}}a{{color:#2563eb}}</style>
<h1>{heading}</h1><p>JavaFoil optimization • Cl</p>
<section><p>{summary["successful_geometries"]} geometries simulated; {summary["rejected_geometries"]} rejected; {summary["failed_geometries"]} failed.</p>"""
    if summary.get("search"):
        search=summary["search"]
        text+="<p>Search: "+escape(search["method"])+" · "+escape(search["termination"].replace("_"," "))+"</p>"
    if best:
        main_angle=best.get("absolute_incidence_1",best.get("incidence_1",0))+best["alpha"]
        config=json.loads((output/"config.json").read_text())
        objective="Cl"
        sim=config.get("simulation",{})
        text+="<p>Transition model: "+escape(transition_model_name(sim.get("transition_model",1)))+"</p>"
        text+="<p>Stall model: "+escape(stall_model_name(sim.get("stall_model",1)))+"</p>"
        if "airspeed_m_s" in sim:
            text+=f'<p>Wingspan: {sim["wingspan_m"]:g} m · Relative airspeed: {sim["airspeed_m_s"]:g} m/s · Reference Re: {sim["reynolds"]:.0f} · Mach: {sim["mach"]:.4f} · Aspect ratio: {sim["aspect_ratio"]:g}</p>'
        text+=f'<h2>Best predicted {objective}: {best["cl"]:.5f}</h2><p>Main-element aerodynamic AoA: {main_angle:g}° · Reference-axis offset: {best["alpha"]:g}° · Cd: {best["cd"]:.5f} · Cm: {best["cm"]:.5f}</p>'
        text+="<table><tr><th>Parameter</th><th>Value</th></tr>"
        config=json.loads((output/"config.json").read_text())
        reference=config.get("reference_chord_m",1); global_unit=config.get("length_unit","m")
        for key,value in best.items():
            label={"geometry_id":"Geometry","alpha":"Reference-axis AoA offset (degrees)","cl":"Cl","cd":"Cd","cm":"Cm"}.get(key,key)
            if key=="clearance":
                label=f"Minimum surface clearance ({global_unit})"
                if value is not None: value=value*reference/UNIT_FACTORS[global_unit]
            if key.startswith("incidence_"):
                index=int(key.split("_")[-1]); mode=config["elements"][index-1].get("angle_mode","absolute")
                label=f"Entered AoA of element {index} (degrees, {mode})"
            elif key.startswith("absolute_incidence_"):
                index=int(key.split("_")[-1]); label=f"Absolute body angle of element {index} (degrees)"
            elif key in ("lift_cl","downforce_cl"):
                label="Signed lift coefficient (upward positive)" if key=="lift_cl" else "Downforce coefficient (downward positive)"
            elif key.startswith("ceiling_top_y_m_"):
                index=int(key.split("_")[-1]); group=config["height_constraints"][index-1]; unit=group["unit"]
                label=f"Highest point of airfoils {group['elements']} above y=0 ({unit}, ceiling {group['max_height']})"
                value=value/UNIT_FACTORS[unit]
            elif key.startswith("top_y_m_"):
                index=int(key.split("_")[-1]);label=f"Highest point of airfoil {index} above y=0 ({global_unit})"
                value=value/UNIT_FACTORS[global_unit]
            elif key.startswith("chord_m_"):
                index=int(key.split("_")[-1]); unit=config["elements"][index-1].get("length_unit",global_unit)
                label=f"Chord of element {index} ({unit})"; value=value/UNIT_FACTORS[unit]
            elif key.startswith("chord_"):
                continue
            elif key.startswith(("gap_m_","overlap_m_")):
                index=int(key.split("_")[-1]); unit=config["elements"][index-1].get("length_unit",global_unit)
                label=f"Vertical gap {index-1} to {index} ({unit})" if key.startswith("gap") else f"Overlap of element {index} ({unit})"
                value=value/UNIT_FACTORS[unit]
            elif key.startswith(("gap_","overlap_")):
                continue
            text+=f"<tr><td>{escape(label)}</td><td>{escape(value)}</td></tr>"
        text+="</table></section><section><h2>Best body geometry</h2>"+(output/"best/geometry.svg").read_text()+"</section>"
    else: text+="<p>No completed valid simulation.</p></section>"
    if sequential:
        text+="<section><h2>Search history</h2><p>Blue: best Cl so far. Gray: the Cl of each evaluated geometry. Full parameter sweeps are retained in the trace file.</p>"+chart+"</section>"
    else:
        text+="<section><h2>Lift curves</h2><p>Blue: best geometry. Gray: other geometries (up to 200 shown). Complete numerical results are saved in CSV.</p>"+chart+"</section>"
    text+="<section><h2>Interpretation</h2><ul>"+"".join("<li>"+escape(w)+"</li>" for w in summary["warnings"])+"</ul></section>"
    text+='<section><a href="results.csv">All simulated coefficients</a> · <a href="evaluations.csv">Geometry outcomes</a> · <a href="config.json">Configuration</a>'
    if best: text+=' · <a href="best/coordinates_m.csv">Best physical coordinates</a> · <a href="best/javafoil_geometry.txt">JavaFoil geometry</a> · <a href="best/polar.txt">Best raw polar</a>'
    text+="</section></html>"
    (output/"report.html").write_text(text,encoding="utf-8")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",type=Path,default=EXAMPLES/"example.json")
    parser.add_argument("--output",type=Path)
    parser.add_argument("--preview",action="store_true",help="Export first geometry without running JavaFoil")
    args=parser.parse_args()
    config=json.loads(args.config.read_text(encoding="utf-8-sig"))
    output=args.output or ROOT/"runs"/datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    if args.preview:
        profiles,chords,ref,axes,alphas,clearance=prepare(config,args.config.resolve().parent)
        geometry=build_geometry(profiles,chords,{k:v[0] for k,v in axes.items()},ref,[e.get("angle_mode","absolute") for e in config["elements"]])
        from ground_effect import orient_geometry
        geometry=orient_geometry(geometry,ref,config["environment"])
        validate_geometry(geometry,clearance,config.get("bounding_box"))
        from geometric_constraints import check_heights
        check_heights(geometry,ref,config.get("height_constraints",[]))
        export_geometry(output,geometry,ref,environment=config["environment"])
        print(output)
        return
    stop=threading.Event()
    import signal
    signal.signal(signal.SIGINT,lambda *_:stop.set())
    try:
        result=run(config,output,args.config.resolve().parent,stop=stop)
        print(json.dumps(result,indent=2))
    except Exception as e:
        parser.exit(1,str(e)+"\n")

if __name__=="__main__":
    main()
