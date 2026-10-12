"""Editable element groups with independent physical height limits."""
import tkinter as tk
from tkinter import ttk
from design_inputs import UNIT_FACTORS, length_m
from hover_help import add_help
from geometric_constraints import constraint_kind

class ConstraintEditor:
    def __init__(self,parent):
        self.element_count=0
        self.frame=ttk.LabelFrame(parent,text="Geometry limits",padding=16)
        self.rows=[]
        self.container=ttk.Frame(self.frame); self.container.pack(fill="x")
        self.container.columnconfigure(0,weight=1,uniform="limits")
        self.container.columnconfigure(1,weight=1,uniform="limits")
        self.enabled={kind:tk.BooleanVar(value=kind=="height") for kind in ("height","length")}
        self.boxes={};self.row_containers={}
        for column,kind in enumerate(("height","length")):
            box=ttk.LabelFrame(self.container,padding=12)
            heading=ttk.Checkbutton(box,text=kind.title(),variable=self.enabled[kind])
            box.configure(labelwidget=heading)
            box.grid(row=0,column=column,sticky="nsew",padx=(0,8) if column==0 else (8,0))
            self.boxes[kind]=box
            body=ttk.Frame(box);body.pack(fill="x")
            self.row_containers[kind]=body
            ttk.Button(box,text="Add "+kind+" limit",command=lambda k=kind:self.add(kind=k)).pack(anchor="w",pady=(10,0))

    def add(self,group=None,kind="height"):
        group=group or dict(elements=[max(1,self.element_count)] if kind=="height" else list(range(1,min(2,self.element_count)+1)),
                            **{"max_"+kind:200},unit="mm")
        kind=constraint_kind(group)
        frame=ttk.Frame(self.row_containers[kind],padding=(0,8));frame.pack(fill="x")
        choices=ttk.Frame(frame);choices.pack(fill="x",pady=(0,8))
        row=dict(frame=frame,choices=choices,kind=kind,
                 selected=[tk.BooleanVar(value=i in group["elements"]) for i in range(1,self.element_count+1)])
        if kind=="height":
            row["airfoil"]=tk.StringVar(value=f"Airfoil {max(group['elements'],default=1)}")
            row["selector"]=ttk.Combobox(choices,textvariable=row["airfoil"],state="readonly",width=15)
            row["selector"].pack(side="left")
            add_help(choices,"height_airfoil")
        else:
            add_help(choices,"length_group")
        line=ttk.Frame(frame);line.pack(fill="x")
        ttk.Label(line,text="Max height" if kind=="height" else "Max total width").pack(side="left",padx=(0,8))
        add_help(line,"geometry_limit")
        unit=group.get("unit","mm");raw=group["max_"+kind]
        row["maximum"]=tk.StringVar(value=str(raw) if not group.get("enabled",True) else f"{length_m(raw,unit)/UNIT_FACTORS[unit]:g}")
        row["unit"]=tk.StringVar(value=unit);row["old_unit"]=unit
        ttk.Entry(line,textvariable=row["maximum"],width=9).pack(side="left")
        box=ttk.Combobox(line,textvariable=row["unit"],values=list(UNIT_FACTORS),state="readonly",width=5)
        box.pack(side="left",padx=5)
        def convert(event):
            new=row["unit"].get()
            try:
                row["maximum"].set(f'{float(row["maximum"].get())*UNIT_FACTORS[row["old_unit"]]/UNIT_FACTORS[new]:.10g}')
                row["old_unit"]=new
            except ValueError:row["unit"].set(row["old_unit"])
        box.bind("<<ComboboxSelected>>",convert)
        ttk.Button(frame,text="Remove",style="Quiet.TButton",command=lambda:self.remove(row)).pack(anchor="e")
        self.rows.append(row);self._refresh_choices(row)

    def _refresh_choices(self,row):
        if row["kind"]=="height":
            values=[f"Airfoil {i}" for i in range(1,self.element_count+1)]
            row["selector"].configure(values=values)
            if row["airfoil"].get() not in values:row["airfoil"].set(values[-1] if values else "")
        else:
            for widget in row["choices"].winfo_children():widget.destroy()
            add_help(row["choices"],"length_group")
            grid=ttk.Frame(row["choices"]);grid.pack(fill="x")
            for i,var in enumerate(row["selected"],1):
                ttk.Checkbutton(grid,text=f"{i}",variable=var).grid(row=(i-1)//5,column=(i-1)%5,sticky="w",padx=4)

    def remove(self,row):
        row["frame"].destroy();self.rows.remove(row)

    def get(self):
        groups=[]
        for r in self.rows:
            kind=r["kind"];enabled=self.enabled[kind].get();raw=r["maximum"].get()
            try:value=float(raw)
            except ValueError:
                if enabled:raise ValueError("Enter a numeric "+kind+" limit")
                value=raw
            ids=([int(r["airfoil"].get().split()[-1])] if r["airfoil"].get() else []) if kind=="height" else [i for i,v in enumerate(r["selected"],1) if v.get()]
            groups.append(dict(elements=ids,**{"max_"+kind:value},unit=r["unit"].get(),enabled=enabled,
                               measurement="sum_width_x" if kind=="length" else "top_y"))
        for kind in ("height","length"):
            if self.enabled[kind].get() and not any(r["kind"]==kind for r in self.rows):
                raise ValueError("Add a "+kind+" limit or disable its box")
        return groups

    def set(self,groups):
        for row in list(self.rows):self.remove(row)
        for kind in ("height","length"):
            self.enabled[kind].set(any(constraint_kind(g)==kind and g.get("enabled",True) for g in groups))
        for group in groups:
            # A legacy height group becomes one row per selected airfoil,
            # preserving its limits rather than silently discarding constraints.
            if constraint_kind(group)=="height":
                for index in group["elements"]:self.add(dict(group,elements=[index]))
            else:self.add(group)

    def set_element_count(self,count):
        self.element_count=count
        for row in self.rows:
            previous=[v.get() for v in row["selected"]]
            row["selected"]=[tk.BooleanVar(value=previous[i] if i<len(previous) else False) for i in range(count)]
            self._refresh_choices(row)
