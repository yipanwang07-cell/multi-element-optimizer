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
        ttk.Label(self.frame,text="Enable height ceilings (y = 0) or length boundaries (x = 0) for selected airfoils.",style="Muted.TLabel",wraplength=1000).pack(anchor="w",pady=(0,5))
        self.rows=[]; self.container=ttk.Frame(self.frame); self.container.pack(fill="x")
        ttk.Button(self.frame,text="Add geometry limit",command=self.add).pack(anchor="w",pady=6)

    def add(self,group=None):
        group=group or dict(elements=list(range(1,min(2,self.element_count)+1)),max_height=200,unit="mm")
        frame=ttk.Frame(self.container,padding=6); frame.pack(fill="x")
        selected=[tk.BooleanVar(value=i in group["elements"]) for i in range(1,self.element_count+1)]
        enabled=tk.BooleanVar(value=group.get("enabled",True))
        ttk.Checkbutton(frame,text="Enable",variable=enabled).pack(side="left")
        kind=tk.StringVar(value=constraint_kind(group).title())
        ttk.Combobox(frame,textvariable=kind,values=["Height","Length"],state="readonly",width=7).pack(side="left",padx=6)
        ttk.Label(frame,text="Airfoils").pack(side="left",padx=6)
        add_help(frame,"height_group")
        choices=ttk.Frame(frame);choices.pack(side="left")
        for i,var in enumerate(selected,1):
            ttk.Checkbutton(choices,text=str(i),variable=var).grid(row=(i-1)//6,column=(i-1)%6,sticky="w",padx=5)
        ttk.Label(frame,text="Limit").pack(side="left",padx=8)
        add_help(frame,"geometry_limit")
        unit=group.get("unit","mm")
        raw=group["max_"+constraint_kind(group)]
        maximum=tk.StringVar(value=str(raw) if not group.get("enabled",True) else f"{length_m(raw,unit)/UNIT_FACTORS[unit]:g}")
        unitvar=tk.StringVar(value=unit)
        ttk.Entry(frame,textvariable=maximum,width=12).pack(side="left")
        box=ttk.Combobox(frame,textvariable=unitvar,values=list(UNIT_FACTORS),state="readonly",width=6); box.pack(side="left",padx=6)
        row=dict(enabled=enabled,kind=kind,frame=frame,choices=choices,selected=selected,maximum=maximum,unit=unitvar,old_unit=unit)
        def convert(event):
            new=unitvar.get()
            try: maximum.set(f'{float(maximum.get())*UNIT_FACTORS[row["old_unit"]]/UNIT_FACTORS[new]:.10g}'); row["old_unit"]=new
            except ValueError: unitvar.set(row["old_unit"])
        box.bind("<<ComboboxSelected>>",convert)
        ttk.Button(frame,text="Remove",style="Quiet.TButton",command=lambda:self.remove(row)).pack(side="left",padx=8)
        self.rows.append(row)

    def remove(self,row):
        row["frame"].destroy(); self.rows.remove(row)

    def get(self):
        groups=[]
        for r in self.rows:
            kind=r["kind"].get().lower()
            raw=r["maximum"].get()
            try: value=float(raw)
            except ValueError:
                if r["enabled"].get(): raise
                value=raw
            groups.append(dict(elements=[i for i,v in enumerate(r["selected"],1) if v.get()],
                **{"max_"+kind:value},unit=r["unit"].get(),enabled=r["enabled"].get(),
                measurement="right_x" if kind=="length" else "top_y"))
        return groups

    def set(self,groups):
        for row in list(self.rows): self.remove(row)
        for group in groups: self.add(group)

    def set_element_count(self,count):
        self.element_count=count
        for row in self.rows:
            previous=[v.get() for v in row["selected"]]
            for widget in row["choices"].winfo_children():widget.destroy()
            row["selected"]=[tk.BooleanVar(value=previous[i] if i<len(previous) else False) for i in range(count)]
            for i,var in enumerate(row["selected"],1):
                ttk.Checkbutton(row["choices"],text=str(i),variable=var).grid(row=(i-1)//6,column=(i-1)%6,sticky="w",padx=5)
