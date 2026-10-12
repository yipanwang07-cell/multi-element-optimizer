"""Simple wingspan and airspeed inputs with physical unit conversion."""
import tkinter as tk
from tkinter import ttk, messagebox
from design_inputs import UNIT_FACTORS, length_m
from air_conditions import SPEED_UNITS, air_properties
from hover_help import term_label
from stall_models import STALL_MODELS, stall_model_name
from transition_models import TRANSITION_MODELS, transition_model_label

class FlightInputs:
    def __init__(self,parent):
        self.frame=ttk.Frame(parent); self.frame.pack(fill="x")
        self.span=tk.StringVar(value="1500"); self.span_unit=tk.StringVar(value="mm")
        self.speed=tk.StringVar(value="20"); self.speed_unit=tk.StringVar(value="m/s")
        self.old_span="mm"; self.old_speed="m/s"
        for column,(title,value,unit,choices,kind) in enumerate((
            ("Wingspan",self.span,self.span_unit,UNIT_FACTORS,"span"),
            ("Relative airspeed",self.speed,self.speed_unit,SPEED_UNITS,"speed"))):
            frame=ttk.Frame(self.frame); frame.grid(row=0,column=column,padx=8,pady=5,sticky="w")
            heading,_=term_label(frame,title,"wingspan" if kind=="span" else "airspeed",style="Muted.TLabel");heading.pack(anchor="w",pady=(0,5))
            line=ttk.Frame(frame); line.pack()
            ttk.Entry(line,textvariable=value,width=18).pack(side="left")
            box=ttk.Combobox(line,textvariable=unit,values=list(choices),state="readonly",width=7)
            box.pack(side="left",padx=6)
            box.bind("<<ComboboxSelected>>",lambda e,k=kind:self.convert(k))
        self.stall_model=tk.StringVar(value=stall_model_name())
        model_frame=ttk.Frame(self.frame);model_frame.grid(row=1,column=0,columnspan=2,sticky="w",padx=8,pady=5)
        heading,_=term_label(model_frame,"Stall model","stall_model",style="Muted.TLabel")
        heading.pack(side="left",padx=(0,12))
        self.stall_model_box=ttk.Combobox(model_frame,textvariable=self.stall_model,values=list(STALL_MODELS.values()),state="readonly",width=20)
        self.stall_model_box.pack(side="left")
        self.transition_model=tk.StringVar(value=transition_model_label())
        transition_frame=ttk.Frame(self.frame);transition_frame.grid(row=2,column=0,columnspan=2,sticky="w",padx=8,pady=5)
        heading,_=term_label(transition_frame,"Transition model","transition_model",style="Muted.TLabel")
        heading.pack(anchor="w",pady=(0,5))
        self.transition_model_box=ttk.Combobox(transition_frame,textvariable=self.transition_model,
            values=[transition_model_label(k) for k in TRANSITION_MODELS],state="readonly",width=62)
        self.transition_model_box.pack(anchor="w")
        self.reynolds_text=tk.StringVar(value="Estimated Reynolds: enter airspeed and chord")
        self.element_reynolds_text=tk.StringVar()
        ttk.Label(self.frame,textvariable=self.reynolds_text,style="ReynoldsTotal.TLabel",wraplength=850,justify="left").grid(row=3,column=0,columnspan=2,sticky="w",padx=8,pady=(18,10))
        ttk.Label(self.frame,textvariable=self.element_reynolds_text,style="ReynoldsElement.TLabel",wraplength=850,justify="left").grid(row=4,column=0,columnspan=2,sticky="w",padx=8,pady=(0,5))


    def convert(self,kind):
        factors=UNIT_FACTORS if kind=="span" else SPEED_UNITS
        value=self.span if kind=="span" else self.speed
        unit=self.span_unit if kind=="span" else self.speed_unit
        old=self.old_span if kind=="span" else self.old_speed
        try: value.set(f"{float(value.get())*factors[old]/factors[unit.get()]:.10g}")
        except ValueError:
            unit.set(old); messagebox.showerror("Unit change","Enter a numeric value before changing its unit"); return
        if kind=="span": self.old_span=unit.get()
        else: self.old_speed=unit.get()

    def get(self):
        return dict(wingspan={"value":float(self.span.get()),"unit":self.span_unit.get()},
                    relative_airspeed={"value":float(self.speed.get()),"unit":self.speed_unit.get()},
                    stall_model=next(k for k,v in STALL_MODELS.items() if v==self.stall_model.get()),
                    transition_model=next(k for k in TRANSITION_MODELS if transition_model_label(k)==self.transition_model.get()))

    def set(self,sim,reference):
        self.stall_model.set(stall_model_name(sim.get("stall_model",1)))
        self.transition_model.set(transition_model_label(sim.get("transition_model",1)))
        span=sim.get("wingspan",{"value":1500,"unit":"mm"})
        unit=span.get("unit","mm") if isinstance(span,dict) else "m"
        self.span_unit.set(unit); self.old_span=unit
        self.span.set(f"{length_m(span,unit)/UNIT_FACTORS[unit]:.10g}")
        rho,mu,sound=air_properties(sim)
        speed=sim.get("relative_airspeed",sim.get("reynolds",300000)*mu/(rho*reference))
        unit=speed.get("unit","m/s") if isinstance(speed,dict) else "m/s"
        value=speed["value"] if isinstance(speed,dict) else speed
        self.speed.set(f"{float(value):.10g}"); self.speed_unit.set(unit); self.old_speed=unit
