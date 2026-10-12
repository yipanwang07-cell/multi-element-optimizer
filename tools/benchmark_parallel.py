import json,time
from pathlib import Path
import wing_optimizer as w
root=w.ROOT/"tests/validation"/("parallel_"+time.strftime("%Y%m%d_%H%M%S"))
root.mkdir()
results=[]
for workers in (1,4):
    config=dict(elements=[dict(profile="2412",chord_m=.4,incidence_deg=dict(min=0,max=10,step=1))],reference_chord_m=.4,alpha_deg=0,panels_per_element=120,simulation=dict(relative_airspeed=dict(value=20,unit="m/s"),wingspan=dict(value=1.5,unit="m")),search=dict(mode="sequential",workers=workers,max_geometries=30))
    start=time.perf_counter()
    result=w.run(config,root/str(workers),progress=lambda s:None)
    result["elapsed_seconds"]=time.perf_counter()-start
    results.append(result)
    print(workers,result["elapsed_seconds"],result["best"]["cl"],result["evaluated_geometries"],flush=True)
assert results[0]["best"]==results[1]["best"]
assert (root/"1/results.csv").read_bytes()==(root/"4/results.csv").read_bytes()
record=dict(serial_seconds=results[0]["elapsed_seconds"],parallel_seconds=results[1]["elapsed_seconds"],speedup=results[0]["elapsed_seconds"]/results[1]["elapsed_seconds"],evaluations=results[0]["evaluated_geometries"],matching_results=True,parallel_workers=results[1]["parallel_workers"])
(root/"benchmark.json").write_text(json.dumps(record,indent=2))
print(root,record,flush=True)
