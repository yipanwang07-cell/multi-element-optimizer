"""Optional 2D SU2 SST RANS validation of a saved winner (no finite-span correction)."""
import csv
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from app_paths import VENDOR


def executable():
    value=os.environ.get("SU2_CFD") or shutil.which("SU2_CFD")
    path=Path(value) if value else VENDOR/"su2/bin/SU2_CFD.exe"
    if not path.is_file():raise ValueError("Install the optional CFD tools first: python tools/setup_cfd.py")
    return path.absolute()


def configuration(sim, options):
    re=float(sim["reynolds"])
    if not math.isfinite(re) or re<=0:raise ValueError("CFD requires a positive Reynolds number")
    iterations=int(options.get("iterations",3000))
    if iterations<100:raise ValueError("CFD needs at least 100 iterations")
    model=options.get("transition",False)
    return f"""SOLVER= INC_RANS
KIND_TURB_MODEL= SST
SST_OPTIONS= V2003m
KIND_TRANS_MODEL= {'LM' if model else 'NONE'}
MATH_PROBLEM= DIRECT
RESTART_SOL= NO
INC_DENSITY_INIT= 1.0
INC_VELOCITY_INIT= (1.0, 0.0, 0.0)
INC_NONDIM= INITIAL_VALUES
VISCOSITY_MODEL= CONSTANT_VISCOSITY
MU_CONSTANT= {1/re:.14g}
FREESTREAM_TURBULENCEINTENSITY= {float(options.get('turbulence_intensity',.01))}
FREESTREAM_TURB2LAMVISCRATIO= 10
REF_ORIGIN_MOMENT_X= 0.25
REF_ORIGIN_MOMENT_Y= 0.0
REF_ORIGIN_MOMENT_Z= 0.0
REF_LENGTH= 1.0
REF_AREA= 1.0
MARKER_HEATFLUX= (airfoils, 0.0)
MARKER_FAR= (farfield)
{ 'MARKER_SYM= (ground)' if sim.get('ground_effect') else '' }
MARKER_PLOTTING= (airfoils)
MARKER_MONITORING= (airfoils)
NUM_METHOD_GRAD= WEIGHTED_LEAST_SQUARES
CFL_NUMBER= 2
CFL_ADAPT= YES
CFL_ADAPT_PARAM= (0.5, 1.2, 0.5, 30)
ITER= {iterations}
LINEAR_SOLVER= FGMRES
LINEAR_SOLVER_PREC= ILU
LINEAR_SOLVER_ERROR= 1E-6
LINEAR_SOLVER_ITER= 15
MGLEVEL= 0
CONV_NUM_METHOD_FLOW= FDS
MUSCL_FLOW= YES
SLOPE_LIMITER_FLOW= VENKATAKRISHNAN
TIME_DISCRE_FLOW= EULER_IMPLICIT
CONV_NUM_METHOD_TURB= SCALAR_UPWIND
MUSCL_TURB= NO
TIME_DISCRE_TURB= EULER_IMPLICIT
CONV_FIELD= RMS_PRESSURE
CONV_RESIDUAL_MINVAL= -8
CONV_STARTITER= 100
MESH_FILENAME= mesh.su2
MESH_FORMAT= SU2
TABULAR_FORMAT= CSV
CONV_FILENAME= history
RESTART_FILENAME= restart_flow
SURFACE_FILENAME= surface_flow
VOLUME_FILENAME= flow
WRT_RESTART_COMPACT= NO
VOLUME_OUTPUT= (COORDINATES, SOLUTION, PRIMITIVE)
OUTPUT_FILES= (PARAVIEW, SURFACE_CSV)
OUTPUT_WRT_FREQ= {iterations}
HISTORY_OUTPUT= (ITER, RMS_RES, AERO_COEFF)
SCREEN_OUTPUT= (INNER_ITER, RMS_PRESSURE, RMS_VELOCITY-X, RMS_VELOCITY-Y, LIFT, DRAG)
"""


def run_process(command, folder, stop, timeout, name):
    import wing_optimizer as w
    env=dict(os.environ,OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1")
    with (folder/(name+".log")).open("w") as log:
        process=subprocess.Popen(command,cwd=folder,env=env,stdout=log,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
        start=time.monotonic()
        try:
            while process.poll() is None:
                if stop.wait(.1):raise w.Cancelled()
                if time.monotonic()-start>timeout:raise RuntimeError(name+" timed out; inspect "+name+".log")
            if process.returncode:raise RuntimeError(name+" failed; inspect "+name+".log")
        finally:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait()


def read_result(path):
    with Path(path).open() as stream:
        rows=[{k.strip().strip('"'):float(v) for k,v in row.items()} for row in csv.DictReader(stream)]
    if len(rows)<50:raise ValueError("Insufficient CFD iteration history")
    last=rows[-1]
    values={name:last[key] for name,key in (("cl","CL"),("cd","CD"),("cm","CMz"))}
    if not all(math.isfinite(v) for row in rows[-50:] for v in row.values()):raise ValueError("CFD returned nonfinite values")
    if values["cd"]<0:raise ValueError("CFD returned negative drag")
    residuals={k:v for k,v in last.items() if k.startswith("rms[")}
    stable=all(max(row[key] for row in rows[-50:])-min(row[key] for row in rows[-50:]) < max(.0001,abs(last[key])*.005) for key in ("CL","CD"))
    flow_ok=all(last.get(k,0)<-6 for k in ("rms[P]","rms[U]","rms[V]"))
    reductions={k:max(row.get(k,v) for row in rows[:20])-v for k,v in residuals.items()}
    converged=bool(residuals) and flow_ok and last.get("rms[P]",0)<-8 and all(v>=3 for v in reductions.values()) and stable
    return dict(**values,converged=converged,residuals=residuals,coefficient_stable=stable,iterations=len(rows),
                status="numerically converged — mesh verification still required" if converged else "not converged — do not rank this result")


def validate_saved_design(run, options=None, stop=None, progress=lambda text:None):
    import wing_optimizer as w
    from ground_effect import orient_geometry
    from safe_files import atomic_write_bytes,atomic_write_text
    from datetime import datetime
    options=options or {};stop=stop or threading.Event();binary=executable()
    run=Path(run);source=run/"best/best_config.json"
    config=json.loads(source.read_text());profiles,chords,reference,axes,alphas,_=w.prepare(config,source.parent)
    if len(alphas)!=1:raise ValueError("CFD validation requires a saved single-angle winner")
    modes=[e["angle_mode"] for e in config["elements"]]
    geometry=orient_geometry(w.build_geometry(profiles,chords,{n:v[0] for n,v in axes.items()},reference,modes),reference,config["environment"])
    geometry=[w.rotate(points,-alphas[0]) for points in geometry]
    destination=run/("cfd_"+datetime.now().strftime("%Y%m%d_%H%M%S_%f"));destination.mkdir()
    sim=config["simulation"];settings=dict(options,ground_effect=sim["ground_effect"])
    with tempfile.TemporaryDirectory(prefix="wing-cfd-") as temporary:
        folder=Path(temporary)
        try:
            (folder/"mesh_input.json").write_text(json.dumps(dict(geometry=geometry,settings=settings)))
            (folder/"case.cfg").write_text(configuration(sim,options))
            progress("CFD: generating a boundary-layer mesh…")
            run_process([sys.executable,str(Path(__file__).with_name("cfd_mesh.py")),"mesh_input.json","mesh.su2"],folder,stop,180,"mesh")
            progress("CFD: solving 2D SST boundary layers and flow…")
            run_process([str(binary),"case.cfg"],folder,stop,float(options.get("timeout_seconds",900)),"solver")
            result=read_result(folder/"history.csv")
            result.update(solver="SU2 8.5.0 INC_RANS SST",transition="Langtry-Menter" if options.get("transition") else "fully turbulent",
                reference_chord_m=reference,reynolds=sim["reynolds"],aspect_ratio_correction=False,
                ground="slip/symmetry floor at y=0" if sim["ground_effect"] else "none",
                limitations="Steady RANS; not a guarantee of accuracy. Check mesh/domain independence and wall y+. Ground uses a slip floor, not a resolved stationary-ground boundary layer.")
            result["lift_cl"]=result["cl"]
            if config["environment"]["flip_for_downforce"]:result["cl"]=-result["cl"]
            result["mesh_options"]=settings
            result["surface_diagnostics"]=surface_diagnostics(folder/"surface_flow.csv",geometry)
            result["wall_resolution_ok"]=result["surface_diagnostics"]["max_y_plus"]<=2
            if not result["wall_resolution_ok"]:result["status"]+="; wall y+ too high — refine mesh"
            result["eligible_for_comparison"]=result["converged"] and result["wall_resolution_ok"]
            result["mesh_independence_verified"]=False
            (folder/"result.json").write_text(json.dumps(result,indent=2))
            write_report(folder,result)
            return destination,result
        except w.Cancelled:
            raise
        except Exception as exc:
            raise RuntimeError(f"CFD check failed: {exc}. Diagnostic files: {destination}") from exc
        finally:
            for file in folder.iterdir():
                if file.is_file():atomic_write_bytes(destination/file.name,file.read_bytes())


def surface_diagnostics(path,geometry):
    """Report reversed wall shear away from the nose; an indicator, not a stall model."""
    with Path(path).open() as stream:
        rows=[{k.strip().strip('"'):float(v) for k,v in row.items()} for row in csv.DictReader(stream)]
    if not rows:raise ValueError("Missing CFD surface diagnostics")
    required=("x","y","Y_Plus","Skin_Friction_Coefficient_x","Skin_Friction_Coefficient_y","Pressure_Coefficient")
    if any(k not in rows[0] for k in required):raise ValueError("CFD output lacks wall-shear or y+ data")
    if any(not math.isfinite(row[k]) for row in rows for k in required):raise ValueError("Invalid CFD surface diagnostics")
    segments=[]
    for index,points in enumerate(geometry,1):
        middle=len(points)//2
        for j,(a,b) in enumerate(zip(points,points[1:])):
            dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
            if length<=1e-12:continue
            direction=-1 if j<middle else 1
            segments.append((index,a,dx,dy,length,direction))
    counts={i:dict(samples=0,reversed_shear_samples=0) for i in range(1,len(geometry)+1)}
    for row in rows:
        best=None
        for index,a,dx,dy,length,direction in segments:
            t=max(0.,min(1.,((row["x"]-a[0])*dx+(row["y"]-a[1])*dy)/length**2))
            distance=(row["x"]-a[0]-t*dx)**2+(row["y"]-a[1]-t*dy)**2
            if best is None or distance<best[0]:best=(distance,index,dx/length*direction,dy/length*direction)
        _,index,tx,ty=best
        points=geometry[index-1];le=points[len(points)//2];te=((points[0][0]+points[-1][0])/2,(points[0][1]+points[-1][1])/2)
        cx,cy=te[0]-le[0],te[1]-le[1]
        station=((row["x"]-le[0])*cx+(row["y"]-le[1])*cy)/(cx*cx+cy*cy)
        if .05<station<.95:
            counts[index]["samples"]+=1
            if row["Skin_Friction_Coefficient_x"]*tx+row["Skin_Friction_Coefficient_y"]*ty < -1e-6:
                counts[index]["reversed_shear_samples"]+=1
    return dict(max_y_plus=max(r["Y_Plus"] for r in rows),airfoils=counts,
        note="Reversed wall-shear sample counts exclude the first/last 5% of local chord. They indicate possible separation, not a measured separated-area fraction. Interpret only for converged, mesh-checked solutions.")


def write_report(folder,result):
    from html import escape
    rows="".join("<tr><th>"+escape(k)+"</th><td>"+escape(json.dumps(v) if isinstance(v,(dict,list)) else str(v))+"</td></tr>" for k,v in result.items())
    text="""<!doctype html><meta charset="utf-8"><title>2D viscous CFD check</title>
<style>body{font:17px system-ui;max-width:1100px;margin:40px auto;color:#182230}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left;overflow-wrap:anywhere}th{width:30%}h1{color:#087f8c}</style>
<h1>2D viscous CFD check</h1><p>Independent SU2 analysis of the saved JavaFoil winner. This check does not replace the sweep winner or establish CFD validation. Compare Standard and Fine meshes and independent benchmarks.</p>"""
    text+="<table>"+rows+"</table><p><a href='surface_flow.csv'>Surface pressure, skin friction and y+</a> · <a href='history.csv'>Convergence history</a> · <a href='flow.vtu'>Flow field (ParaView)</a> · <a href='solver.log'>Solver log</a></p>"
    (folder/"report.html").write_text(text,encoding="utf-8")
