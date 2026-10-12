"""Gmsh case mesher; run as a separate process because Gmsh is not thread safe."""
import json
import sys
from pathlib import Path
from app_paths import VENDOR
sys.path.insert(0,str(VENDOR/"python"))


def build_mesh(geometry, settings, destination):
    import gmsh
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal",0)
        gmsh.model.add("wing")
        geo=gmsh.model.geo
        extent=max(1.,max(x for e in geometry for x,y in e)-min(x for e in geometry for x,y in e))
        size=float(settings.get("surface_size",.015))*extent
        domain=float(settings.get("domain_chords",20))*extent
        first=float(settings.get("first_layer",1e-5))
        if not 0<first<size or domain<5*extent:raise ValueError("Invalid CFD mesh spacing or domain size")
        loops=[];walls=[];tips=[]
        for element in geometry:
            points=[]
            for xy in element:
                if not points or sum((a-b)**2 for a,b in zip(xy,points[-1]))>1e-20:points.append(xy)
            if sum((a-b)**2 for a,b in zip(points[0],points[-1]))<1e-16:points.pop()
            ids=[geo.addPoint(x,y,0,size) for x,y in points]
            edges=[geo.addLine(a,b) for a,b in zip(ids,ids[1:]+ids[:1])]
            walls.extend(edges);tips.append(ids[0]);loops.append(geo.addCurveLoop(edges))
        xmin=min(x for e in geometry for x,y in e)-domain
        xmax=max(x for e in geometry for x,y in e)+domain
        ground=settings.get("ground_effect",False)
        ymin=0 if ground else min(y for e in geometry for x,y in e)-domain
        ymax=max(y for e in geometry for x,y in e)+domain
        ids=[geo.addPoint(x,y,0,extent) for x,y in [(xmin,ymin),(xmax,ymin),(xmax,ymax),(xmin,ymax)]]
        outer=[geo.addLine(a,b) for a,b in zip(ids,ids[1:]+ids[:1])]
        surface=geo.addPlaneSurface([geo.addCurveLoop(outer),*loops]);geo.synchronize()
        for name,edges in (("airfoils",walls),("farfield",outer[1:] if ground else outer)):
            tag=gmsh.model.addPhysicalGroup(1,edges);gmsh.model.setPhysicalName(1,tag,name)
        if ground:
            tag=gmsh.model.addPhysicalGroup(1,[outer[0]]);gmsh.model.setPhysicalName(1,tag,"ground")
        gmsh.model.addPhysicalGroup(2,[surface])
        field=gmsh.model.mesh.field.add("BoundaryLayer")
        gmsh.model.mesh.field.setNumbers(field,"CurvesList",walls)
        gmsh.model.mesh.field.setNumber(field,"Size",first)
        gmsh.model.mesh.field.setNumber(field,"SizeFar",size)
        gmsh.model.mesh.field.setNumber(field,"Thickness",min(.025*extent,size*2))
        gmsh.model.mesh.field.setNumber(field,"Ratio",1.15)
        gmsh.model.mesh.field.setNumber(field,"Quads",1)
        gmsh.model.mesh.field.setNumbers(field,"FanPointsList",tips)
        gmsh.model.mesh.field.setAsBoundaryLayer(field)
        gmsh.option.setNumber("Mesh.Algorithm",6)
        gmsh.model.mesh.generate(2)
        gmsh.write(str(destination))
        tags,coords,_=gmsh.model.mesh.getNodes()
        return dict(nodes=len(tags),first_layer=first,domain_chords=domain/extent)
    finally:gmsh.finalize()


if __name__=="__main__":
    data=json.loads(Path(sys.argv[1]).read_text())
    result=build_mesh(data["geometry"],data["settings"],sys.argv[2])
    Path("mesh_details.json").write_text(json.dumps(result,indent=2))
