"""Parse native JavaFoil flow-field grids and mask solid interiors."""
from pathlib import Path
import re
import numpy as np
from shapely import intersects_xy
from shapely.geometry import Polygon

def read_flow_field(path,geometry,ground=False):
    text=Path(path).read_text(encoding="utf-8",errors="replace")
    if not re.search(r"VARIABLES\s*=\s*x\s+y\s+vx\s+vy\s+v\s+Cp",text):raise ValueError("Unexpected JavaFoil flow-field columns")
    zone=re.search(r"ZONE[^\n]*I=(\d+),\s*J=(\d+)",text)
    if not zone:raise ValueError("Missing flow-field grid dimensions")
    rows=[]
    for line in text.splitlines():
        parts=line.split()
        if len(parts)!=6:continue
        try:rows.append([float(x) for x in parts])
        except ValueError:continue
    data=np.asarray(rows,dtype=float)
    expected=int(zone[1])*int(zone[2])
    if data.shape!=(expected,6) or not np.isfinite(data[:,:2]).all():raise ValueError("Incomplete flow-field grid")
    xs=np.unique(data[:,0]);ys=np.unique(data[:,1])
    if len(xs)<3 or len(ys)<3 or len(xs)*len(ys)!=expected:raise ValueError("Invalid flow-field grid")
    ix=np.searchsorted(xs,data[:,0]);iy=np.searchsorted(ys,data[:,1])
    if len(np.unique(iy*len(xs)+ix))!=expected:raise ValueError("Duplicate flow-field grid points")
    x,y=np.meshgrid(xs,ys)
    solid=np.zeros(x.shape,dtype=bool)
    for points in geometry:
        if min(a for a,b in points)<xs[0] or max(a for a,b in points)>xs[-1] or min(b for a,b in points)<ys[0] or max(b for a,b in points)>ys[-1]:
            raise ValueError("JavaFoil flow-field grid does not cover the complete winning geometry")
        solid |= intersects_xy(Polygon(points),x,y)
    if ground:solid |= y<0
    field=dict(x=x,y=y,solid=solid,x_steps=len(xs)-1,y_steps=len(ys)-1)
    for column,name in ((2,"vx"),(3,"vy"),(4,"velocity_ratio"),(5,"cp")):
        values=np.empty(x.shape);values[iy,ix]=data[:,column]
        invalid=~np.isfinite(values)
        if np.any(invalid & ~solid):raise ValueError("Non-finite flow-field values outside airfoils")
        field[name]=np.ma.array(values,mask=solid|invalid)
    return field
