"""Desktop editor with physical lengths, chained angles and ordered sweeps."""
import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import webbrowser
import wing_optimizer as engine
import airfoil_library as library
from library_dialog import LibraryDialog
from design_inputs import UNIT_FACTORS, unit_name, map_values, ui_config, absolute_angles, length_m
from hover_help import add_help,term_label

def parse(text):
    text=text.strip()
    if ":" in text:
        parts=list(map(float,text.split(":")))
        if len(parts) not in (2,3): raise ValueError("Use min:max or min:max:step")
        value=dict(zip(("min","max","step"),parts))
    elif "," in text: value=list(map(float,text.split(",")))
    else: value=float(text)
    engine.values(value)
    return value

def display(value):
    if isinstance(value,dict):
        if "value" in value: return f"{float(value['value']):.10g}"
        return ":".join(f"{float(value[k]):.10g}" for k in ("min","max","step") if k in value)
    if isinstance(value,list): return ",".join(f"{float(x):.10g}" for x in value)
    return f"{float(value):.10g}"

class App:
    def __init__(self,root,parent=None,function=None,host=None):
        from ui_theme import apply_theme
        apply_theme(root)
        self.function=function; self.host=host
        self.root=root; root.title("Multi-element Optimizer • JavaFoil")
        if not getattr(root,"_wing_window_sized",False):
            root._wing_window_sized=True
            scale=max(1.,float(root.tk.call("tk","scaling"))/(96/72))
            width=min(round(1320*scale),root.winfo_screenwidth()-60)
            height=min(round(920*scale),root.winfo_screenheight()-90)
            root.geometry(f"{width}x{height}")
            root.minsize(min(width,1000),min(height,680))
        self.base=engine.EXAMPLES; self.rows=[]; self.messages=queue.Queue(); self.stop=threading.Event()
        self.running=False; self.saving=False; self.saved_design=None; self.output=None; self.last_config={}; self.geometry=None
        self.scene_environment={}; self.scene_reference=1.; self.scene_height_limits=[]
        self.global_unit=tk.StringVar(value="mm"); self._old_global_unit="mm"
        outer=ttk.Frame(parent if parent is not None else root,padding=(24,18)); outer.pack(fill="both",expand=True)
        outer.columnconfigure(0,weight=1);outer.rowconfigure(2,weight=1)
        self.tabs=ttk.Notebook(outer); self.tabs.grid(row=2,column=0,sticky="nsew")
        setup_shell=ttk.Frame(self.tabs); results=ttk.Frame(self.tabs,padding=10)
        setup_canvas=tk.Canvas(setup_shell,highlightthickness=0,background="#ffffff",yscrollincrement=25)
        setup_scroll=ttk.Scrollbar(setup_shell,orient="vertical",command=setup_canvas.yview)
        setup_canvas.configure(yscrollcommand=setup_scroll.set)
        setup_scroll.pack(side="right",fill="y"); setup_canvas.pack(side="left",fill="both",expand=True)
        setup=ttk.Frame(setup_canvas,padding=(12,18))
        setup_item=setup_canvas.create_window((0,0),window=setup,anchor="nw")
        setup.bind("<Configure>",lambda e:setup_canvas.configure(scrollregion=setup_canvas.bbox("all")))
        setup_canvas.bind("<Configure>",lambda e:setup_canvas.itemconfigure(setup_item,width=e.width))
        self.setup_canvas=setup_canvas
        from ui_theme import attach_scroll
        attach_scroll(setup_canvas,setup)
        self.tabs.add(setup_shell,text="Design")
        from fidelity_ui import FidelityControls
        self.fidelity=FidelityControls(self.tabs)
        self.tabs.add(self.fidelity.frame,text="Search settings")
        self.tabs.add(results,text="Preview & results")
        self.results_tab=results
        from constraints_ui import ConstraintEditor
        guide,_=term_label(setup,"Ranges and values","ranges",style="Muted.TLabel"); guide.pack(anchor="w",pady=(4,0))
        ttk.Label(setup,text="Airfoil assembly",style="Section.TLabel").pack(anchor="w",pady=(10,0))
        self.table=ttk.Frame(setup); self.table.pack(fill="x",pady=(12,4))
        buttons=ttk.Frame(setup); buttons.pack(fill="x",pady=4)
        self.add_button=ttk.Button(buttons,text="Add airfoil",command=self.add); self.add_button.pack(side="left")
        self.remove_button=ttk.Button(buttons,text="Remove last",style="Quiet.TButton",command=self.remove); self.remove_button.pack(side="left",padx=6)
        ttk.Button(buttons,text="Load setup",style="Quiet.TButton",command=self.load).pack(side="left",padx=6)
        ttk.Button(buttons,text="Save setup",style="Quiet.TButton",command=self.save).pack(side="left")
        ground=ttk.LabelFrame(setup,text="Ground & orientation",padding=16); ground.pack(fill="x",pady=8)
        self.ground_enabled=tk.BooleanVar(value=False); self.flip_downforce=tk.BooleanVar(value=False)
        self.ground_clearance=tk.StringVar(value="50"); self.ground_unit=tk.StringVar(value="mm"); self._ground_unit="mm"
        line=ttk.Frame(ground); line.pack(fill="x")
        ttk.Checkbutton(line,text="Ground effect",variable=self.ground_enabled,command=self.ground_options_changed).pack(side="left",padx=5)
        add_help(line,"ground_effect")
        ttk.Checkbutton(line,text="Flip for downforce",variable=self.flip_downforce,command=self.ground_options_changed).pack(side="left",padx=12)
        add_help(line,"flip_for_downforce")
        ttk.Label(line,text="Ground clearance").pack(side="left",padx=5)
        add_help(line,"ground_clearance")
        ttk.Entry(line,textvariable=self.ground_clearance,width=10).pack(side="left")
        ground_units=ttk.Combobox(line,textvariable=self.ground_unit,values=list(UNIT_FACTORS),state="readonly",width=6); ground_units.pack(side="left",padx=5)
        ground_units.bind("<<ComboboxSelected>>",self.change_ground_unit)
        self.constraints=ConstraintEditor(setup)
        if function=="sizing": self.constraints.frame.pack(fill="x",pady=8)
        settings=ttk.LabelFrame(setup,text="Simulation settings",padding=16)
        settings.pack(fill="x",pady=8)
        from flight_inputs import FlightInputs
        self.flight_inputs=FlightInputs(settings)
        self.advanced_button=ttk.Button(settings,text="▸ Advanced settings",style="Quiet.TButton",command=self.toggle_advanced)
        self.advanced_button.pack(anchor="w",pady=4)
        self.advanced_frame=ttk.Frame(settings)
        line=ttk.Frame(self.advanced_frame); line.grid(row=0,column=0,columnspan=4,sticky="w")
        ttk.Label(line,text="Reference length unit").pack(side="left")
        add_help(line,"reference_unit")
        unitbox=ttk.Combobox(line,textvariable=self.global_unit,values=list(UNIT_FACTORS),state="readonly",width=6)
        unitbox.pack(side="left",padx=8); unitbox.bind("<<ComboboxSelected>>",lambda e:self.change_global_unit())
        self.mode=tk.StringVar(value="sequential")
        self.settings={}; self.length_labels={}
        fields=[("reference_chord_m","Lift reference length","400",True),
            ("minimum_clearance","Minimum separation","0.8",True),
            ("alpha_deg","Whole-wing angle offset (°)","0",False),
            ("reynolds","Reynolds override (blank = auto)","",False),
            ("mach","Mach override (blank = auto)","",False),
            ("box_width","Optional box width","",True),
            ("box_height","Optional box height","",True),
            ("panels_per_element","Panels / element","120",False),
            ("max_passes","Maximum sweep rounds","5",False),
            ("seed","Random seed","42",False),
            ("temperature_c","Air temperature (°C)","15",False),
            ("pressure_pa","Air pressure (Pa)","101325",False),
            ("density_override","Density override (kg/m³)","",False),
            ("viscosity_override","Viscosity override (Pa·s)","",False),
            ("sound_speed_override","Sound speed override (m/s)","",False),
            ("aspect_ratio_override","Aspect ratio override (0 = 2D)","",False),
            ("transition_upper","Upper transition (0–1)","1",False),
            ("transition_lower","Lower transition (0–1)","1",False),
            ("roughness","Roughness (0–3)","0",False),
            ("timeout_seconds","Solver timeout (seconds)","120",False)]
        for index,(key,title,default,is_length) in enumerate(fields):
            row,column=divmod(index,4)
            frame=ttk.Frame(self.advanced_frame); frame.grid(row=row+1,column=column,padx=5,pady=4,sticky="ew")
            heading,label=term_label(frame,title,key,wraplength=145); heading.pack(anchor="w",pady=(0,3))
            if is_length: self.length_labels[key]=(label,title)
            var=tk.StringVar(value=default); self.settings[key]=var
            widget=ttk.Entry(frame,textvariable=var,width=20); widget.pack(fill="x")
            if function=="sizing" and key=="alpha_deg": widget.configure(state="disabled")
        ttk.Label(self.advanced_frame,text="No evaluation cap. Both tabs refine near the winner after the coarse sweep. Blank overrides use calculated values.",wraplength=1050).grid(row=10,column=0,columnspan=4,sticky="w",pady=4)
        results.columnconfigure(0,weight=1);results.rowconfigure(0,weight=1)
        self.canvas=tk.Canvas(results,background="#fafbfd",highlightthickness=0); self.canvas.grid(row=0,column=0,sticky="nsew")
        self.canvas.bind("<Configure>",lambda e:self.draw())
        console=ttk.Frame(results);console.grid(row=1,column=0,sticky="ew",pady=8)
        self.log=tk.Text(console,height=6,wrap="word",state="disabled",background="#142b3d",foreground="#d9e6ee",font=("Consolas",11),relief="flat",padx=12,pady=10,highlightthickness=1,highlightbackground="#e4e9f1"); self.log.pack(side="left",fill="both",expand=True)
        self.console_scrollbar=ttk.Scrollbar(console,orient="vertical",command=self.log.yview)
        self.console_scrollbar.pack(side="right",fill="y");self.log.configure(yscrollcommand=self.console_scrollbar.set)
        commands=ttk.Frame(outer,style="Action.TFrame",padding=(14,12)); commands.grid(row=3,column=0,sticky="ew",pady=(12,4))
        self.preview_button=ttk.Button(commands,text="Preview geometry",command=self.preview);self.preview_button.pack(side="left")
        self.start_button=ttk.Button(commands,text="Optimize",style="Primary.TButton",command=self.start); self.start_button.pack(side="left",padx=8)
        add_help(commands,"cl")
        self.stop_button=ttk.Button(commands,text="Stop",command=self.cancel,state="disabled"); self.stop_button.pack(side="left")
        self.report_button=ttk.Button(commands,text="Open report",style="Quiet.TButton",command=self.open_report,state="disabled"); self.report_button.pack(side="left",padx=8)
        self.save_design_button=ttk.Button(commands,text="Save results…",command=self.save_design,state="disabled");self.save_design_button.pack(side="right",padx=8)
        self.status=tk.StringVar(value="Ready")
        self.status_label=ttk.Label(outer,textvariable=self.status,style="Status.TLabel",wraplength=1100); self.status_label.grid(row=4,column=0,sticky="w",pady=6)
        outer.bind("<Configure>",lambda e:self.status_label.configure(wraplength=max(300,e.width-20)))
        initial=engine.EXAMPLES/("free_optimization_example.json" if function=="sizing" else "sequential_example.json")
        if not initial.exists(): initial=engine.EXAMPLES/"example.json"
        self.apply_config(json.loads(initial.read_text(encoding="utf-8-sig")))
        self.update_reynolds_estimate()
        self._poll_timer=root.after(150,self.poll)
        root.bind("<Destroy>",self._cancel_poll_on_destroy,add="+")
        if host is None: root.protocol("WM_DELETE_WINDOW",self.close)

    def toggle_advanced(self):
        if self.advanced_frame.winfo_manager():
            self.advanced_frame.pack_forget(); self.advanced_button.configure(text="▸ Advanced settings")
        else:
            self.advanced_frame.pack(fill="x",pady=6); self.advanced_button.configure(text="▾ Advanced settings")

    def ground_options_changed(self):
        if self.ground_enabled.get() or self.flip_downforce.get(): self.settings["alpha_deg"].set("0")
        if self.geometry is not None and not self.running: self.preview()

    def change_ground_unit(self,event=None):
        new=self.ground_unit.get()
        try:
            value=float(self.ground_clearance.get())*UNIT_FACTORS[self._ground_unit]/UNIT_FACTORS[new]
            self.ground_clearance.set(f"{value:.10g}"); self._ground_unit=new
            self.ground_options_changed()
        except ValueError:
            self.ground_unit.set(self._ground_unit)
            messagebox.showerror("Ground clearance","Enter a numeric clearance before changing units")

    def families(self):
        return ["NACA"]+sorted({e["family"] for e in library.airfoils()})+["Custom DAT"]

    def add(self,element=None):
        if self.running: return
        if not isinstance(element,dict):
            element=dict(profile="S1223",chord={"min":75,"max":225} if self.function=="sizing" else 150,length_unit=self.global_unit.get(),
                incidence_deg={"min":10,"max":30},angle_mode="relative",gap_length={"min":5,"max":20},overlap_length={"min":0,"max":15})
            # Default new element dimensions are 150 mm, independent of the active unit.
            factor=.001/UNIT_FACTORS[self.global_unit.get()]
            for key in ("chord","gap_length","overlap_length"): element[key]=map_values(element[key],factor)
        index=len(self.rows)+1; row={}
        frame=ttk.Frame(self.table,style="Card.TFrame",padding=18); frame.pack(fill="x",pady=8)
        card_title=ttk.Frame(frame);card_title.pack(fill="x",pady=(0,12))
        ttk.Label(card_title,text=f"{index:02d}",style="Index.TLabel").pack(side="left")
        ttk.Label(card_title,text=f"Airfoil {index}",style="Section.TLabel").pack(side="left",padx=12)
        row["_widgets"]=[frame]
        header=ttk.Frame(frame); header.pack(fill="x")
        source=element.get("profile","NACA 2412"); entry=library.find(source)
        family=entry["family"] if entry else ("NACA" if engine.re.fullmatch(r"(?:NACA\s*)?\d{4}",source,engine.re.I) else "Custom DAT")
        row["family"]=tk.StringVar(value=family); row["profile"]=tk.StringVar(value=entry["name"] if entry else source)
        ttk.Label(header,text="Family").pack(side="left")
        add_help(header,"family")
        combo=ttk.Combobox(header,textvariable=row["family"],values=self.families(),width=14,state="readonly"); combo.pack(side="left",padx=5)
        ttk.Label(header,text="Profile").pack(side="left")
        add_help(header,"profile")
        row["_profile_box"]=ttk.Combobox(header,textvariable=row["profile"],width=22)
        row["_profile_box"].pack(side="left",padx=5)
        combo.bind("<<ComboboxSelected>>",lambda e:self.change_family(row))
        self.change_family(row,preserve=True)
        ttk.Button(header,text="Library",style="Quiet.TButton",command=lambda:self.pick_library(row)).pack(side="left",padx=4)
        ttk.Button(header,text="Import DAT",style="Quiet.TButton",command=lambda:self.browse(row)).pack(side="left")
        inputs=ttk.Frame(frame); inputs.pack(fill="x",pady=(10,0))
        for col in range(3): inputs.columnconfigure(col,weight=1,uniform="airfoil")
        definitions=[("chord","Chord range" if self.function=="sizing" else "Chord length",element.get("chord",1),12),
            ("length_unit","Length unit",element.get("length_unit",self.global_unit.get()),7),
            ("incidence_deg","Angle (°)",element.get("incidence_deg",0),17),
            ("angle_mode","Angle mode",element.get("angle_mode","absolute"),12),
            ("gap","Gap from previous",element.get("gap_length",0),17),
            ("overlap","Overlap with previous",element.get("overlap_length",0),17)]
        for column,(key,title,value,width) in enumerate(definitions):
            part=ttk.Frame(inputs); part.grid(row=column//3,column=column%3,sticky="ew",padx=(0,14),pady=5)
            heading,_=term_label(part,title,key,style="Muted.TLabel");heading.pack(anchor="w",pady=(0,4))
            var=tk.StringVar(value=str(value) if key in ("length_unit","angle_mode") else display(value)); row[key]=var
            if key in ("length_unit","angle_mode"):
                widget=ttk.Combobox(part,textvariable=var,width=width,state="readonly",
                    values=list(UNIT_FACTORS) if key=="length_unit" else ("absolute","relative"))
                if key=="length_unit": widget.bind("<<ComboboxSelected>>",lambda e:self.change_row_unit(row))
            else: widget=ttk.Entry(part,textvariable=var,width=width)
            widget.pack(anchor="w",fill="x")
            if index==1 and key in ("gap","overlap","angle_mode"):
                widget.configure(state="disabled")
                if key=="angle_mode": var.set("absolute")
        def toggle_dimensions():
            if inputs.winfo_manager():
                inputs.pack_forget();detail_button.configure(text="Edit dimensions")
            else:
                inputs.pack(fill="x",pady=(10,0));detail_button.configure(text="Hide dimensions")
        detail_button=ttk.Button(frame,text="Hide dimensions",style="Quiet.TButton",command=toggle_dimensions)
        detail_button.pack(anchor="e",before=inputs,pady=(6,0))
        if index>1:
            inputs.pack_forget();detail_button.configure(text="Edit dimensions")
        row["_old_unit"]=row["length_unit"].get(); self.rows.append(row)
        self.constraints.set_element_count(len(self.rows))

    def change_family(self,row,preserve=False):
        family=row["family"].get()
        choices=([v for v in library.choices() if v.startswith("NACA ")] if family=="NACA"
            else [e["name"] for e in library.airfoils() if e["family"]==family])
        row["_profile_box"].configure(values=choices)
        if not preserve and choices and row["profile"].get() not in choices: row["profile"].set(choices[0])

    def choose_profile(self,row,name):
        row["profile"].set(name); entry=library.find(name)
        row["family"].set(entry["family"] if entry else "Custom DAT")
        self.change_family(row,preserve=True)

    def remove(self):
        if self.running or len(self.rows)<=1: return
        for widget in self.rows.pop()["_widgets"]: widget.destroy()
        self.constraints.set_element_count(len(self.rows))

    def pick_library(self,row):
        if self.running: return
        LibraryDialog(self.root,lambda name:self.choose_profile(row,name))

    def browse(self,row):
        if self.running: return
        path=filedialog.askopenfilename(filetypes=[("Airfoil coordinates","*.dat *.txt")])
        if path: self.choose_profile(row,path)

    def change_row_unit(self,row):
        old=row["_old_unit"]; new=row["length_unit"].get()
        try:
            factor=UNIT_FACTORS[old]/UNIT_FACTORS[new]
            converted={key:display(map_values(parse(row[key].get()),factor)) for key in ("chord","gap","overlap")}
            for key,value in converted.items(): row[key].set(value)
            row["_old_unit"]=new
        except Exception as e:
            row["length_unit"].set(old); messagebox.showerror("Cannot change units",str(e))

    def update_unit_labels(self):
        for label,title in self.length_labels.values(): label.configure(text=f"{title} ({self.global_unit.get()})")

    def change_global_unit(self):
        old=self._old_global_unit; new=self.global_unit.get()
        try:
            factor=UNIT_FACTORS[old]/UNIT_FACTORS[new]
            converted={key:display(map_values(parse(self.settings[key].get()),factor))
                for key in self.length_labels if self.settings[key].get().strip()}
            for key,value in converted.items(): self.settings[key].set(value)
            # Elements still using the old default follow the global selection.
            for row in self.rows:
                if row["length_unit"].get()==old:
                    row["length_unit"].set(new); self.change_row_unit(row)
            self._old_global_unit=new; self.update_unit_labels()
        except Exception as e:
            self.global_unit.set(old); messagebox.showerror("Cannot change units",str(e))

    def config(self):
        config=json.loads(json.dumps(self.last_config)); elements=[]
        for index,row in enumerate(self.rows):
            unit=row["length_unit"].get()
            e=dict(profile=row["profile"].get().strip(),length_unit=unit,chord=parse(row["chord"].get()),
                incidence_deg=parse(row["incidence_deg"].get()),angle_mode=row["angle_mode"].get())
            if index: e.update(gap_length=parse(row["gap"].get()),overlap_length=parse(row["overlap"].get()))
            elements.append(e)
        unit=self.global_unit.get()
        config.update(schema_version=2,length_unit=unit,elements=elements,
            reference_chord={"value":float(self.settings["reference_chord_m"].get()),"unit":unit},
            minimum_clearance_length={"value":float(self.settings["minimum_clearance"].get()),"unit":unit},
            alpha_deg=parse(self.settings["alpha_deg"].get()),
            panels_per_element=int(self.settings["panels_per_element"].get()))
        config["height_constraints"]=self.constraints.get() if self.function!="placement" else []
        if self.function:
            config["search"]["mode"]="free" if self.function=="sizing" else "sequential"
        if self.function=="sizing": config["alpha_deg"]=0
        config["environment"]=dict(ground_effect=self.ground_enabled.get(),flip_for_downforce=self.flip_downforce.get(),
            ground_clearance={"value":float(self.ground_clearance.get()),"unit":self.ground_unit.get()})
        config.pop("profile_sources",None)
        sim=config.setdefault("simulation",{}); sim.update(self.flight_inputs.get())
        for key in ("temperature_c","pressure_pa","transition_upper","transition_lower","timeout_seconds"):
            sim[key]=float(self.settings[key].get())
        for key in ("roughness",): sim[key]=int(self.settings[key].get())
        for field,key in (("reynolds","reynolds_override"),("mach","mach_override"),
                          ("density_override","density_override"),("viscosity_override","viscosity_override"),
                          ("sound_speed_override","sound_speed_override"),("aspect_ratio_override","aspect_ratio_override")):
            value=self.settings[field].get().strip()
            if value: sim[key]=float(value)
            else: sim.pop(key,None)
        from air_conditions import normalize_conditions
        from design_inputs import length_m
        normalize_conditions(sim,length_m(config["reference_chord"]))
        config.setdefault("search",{}).update(mode=self.mode.get(),
            seed=int(self.settings["seed"].get()),max_passes=int(self.settings["max_passes"].get()),
            )
        config["search"].update(self.fidelity.get())
        for key in ("fine_divisions","max_geometries","max_refinements","angle_tolerance_deg","length_tolerance_m"): config["search"].pop(key,None)
        width=self.settings["box_width"].get().strip(); height=self.settings["box_height"].get().strip()
        config.pop("bounding_box",None); config.pop("bounding_box_lengths",None)
        if width or height:
            if not width or not height: raise ValueError("Enter both box dimensions or leave both blank")
            config["bounding_box_lengths"]={key:{"value":float(value),"unit":unit} for key,value in (("width",width),("height",height))}
        return config

    def apply_config(self,config):
        config=ui_config(config)
        if not config["elements"]: raise ValueError("Specify at least one airfoil")
        self.last_config=config
        self.geometry=None
        env=config.get("environment",{})
        self.ground_enabled.set(env.get("ground_effect",False)); self.flip_downforce.set(env.get("flip_for_downforce",False))
        ground_value=env.get("ground_clearance",{"value":50,"unit":"mm"})
        from design_inputs import length_m
        ground_unit=ground_value.get("unit","mm") if isinstance(ground_value,dict) else env.get("length_unit","mm")
        self.ground_unit.set(ground_unit); self._ground_unit=ground_unit
        self.ground_clearance.set(f"{length_m(ground_value,ground_unit)/UNIT_FACTORS[ground_unit]:.10g}")
        self.global_unit.set(config["length_unit"]); self._old_global_unit=config["length_unit"]; self.update_unit_labels()
        for row in self.rows:
            for widget in row["_widgets"]: widget.destroy()
        self.rows=[]
        for e in config["elements"]: self.add(e)
        self.constraints.set(config.get("height_constraints",[]))
        self.settings["reference_chord_m"].set(display(config["reference_chord"]))
        self.settings["minimum_clearance"].set(display(config["minimum_clearance_length"]))
        self.settings["alpha_deg"].set(display(config.get("alpha_deg",0)))
        self.settings["panels_per_element"].set(str(config.get("panels_per_element",120)))
        sim=config.get("simulation",{})
        self.flight_inputs.set(sim,config["reference_chord_m"])
        for field,key in (("reynolds","reynolds_override"),("mach","mach_override"),
                          ("density_override","density_override"),("viscosity_override","viscosity_override"),
                          ("sound_speed_override","sound_speed_override"),("aspect_ratio_override","aspect_ratio_override")):
            value=sim.get(key)
            if field=="mach" and "relative_airspeed" not in sim and sim.get("mach",0)>0: value=sim["mach"]
            self.settings[field].set(str(value) if value is not None else "")
        for key,default in (("temperature_c",15),("pressure_pa",101325),("transition_upper",1),("transition_lower",1),
                            ("roughness",0),("timeout_seconds",120)):
            self.settings[key].set(str(sim.get(key,default)))
        search=config.get("search",{})
        self.fidelity.set(search)
        for key,default in (("max_passes",5),("seed",42)):
            self.settings[key].set(str(search.get(key,default)))
        self.mode.set("free" if self.function=="sizing" else "sequential" if self.function=="placement" else search.get("mode","sequential"))
        for key,dimension in (("box_width","width"),("box_height","height")):
            value=config.get("bounding_box_lengths",{}).get(dimension)
            self.settings[key].set(display(value) if value is not None else "")

    def load(self):
        if self.running: return
        path=filedialog.askopenfilename(initialdir=engine.EXAMPLES,filetypes=[("Configuration","*.json")])
        if path:
            try:
                config=json.loads(Path(path).read_text(encoding="utf-8-sig")); engine.prepare(config,Path(path).parent)
                if self.host:
                    self.host.apply_config(config,Path(path).resolve().parent)
                else:
                    self.apply_config(config); self.base=Path(path).resolve().parent; self.preview()
            except Exception as e: messagebox.showerror("Cannot load",str(e))

    def save(self):
        try:
            config=self.config(); engine.prepare(config,self.base)
            for e in config["elements"]:
                if not engine.re.fullmatch(r"(?:NACA\s*)?\d{4}",e["profile"],engine.re.I) and not library.find(e["profile"]):
                    e["profile"]=str(library.resolve_profile(e["profile"],self.base).resolve())
            path=filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("Configuration","*.json")])
            if path: Path(path).write_text(json.dumps(config,indent=2))
        except Exception as e: messagebox.showerror("Cannot save",str(e))

    def preview_interim_best(self):
        self.tabs.select(self.results_tab)
        path=self.output/"best/best.json" if self.output else None
        if path is None or not path.exists():
            self.status.set("Waiting for the first valid result — optimization is still running.")
            return
        try:
            snapshot=json.loads(path.read_text(encoding="utf-8"))
            geometry=snapshot["preview_geometry"]
            self.scene_environment=snapshot["environment"]
            self.scene_reference=snapshot["reference_chord_m"]
            self.scene_height_limits=snapshot.get("height_constraints",[])
            self.geometry=geometry
            self.draw()
            self.status.set(f"Best so far • Cl {snapshot['result']['cl']:.5f} • optimization continues")
        except (OSError,ValueError,KeyError):
            self.status.set("Best result is being saved — select Preview geometry again shortly.")

    def preview(self):
        if self.running:
            self.preview_interim_best()
            return
        try:
            config=self.config(); p,c,r,axes,alphas,clearance=engine.prepare(config,self.base)
            params={key:(min(value)+max(value))/2 for key,value in axes.items()}
            modes=[e["angle_mode"] for e in config["elements"]]
            if self.mode.get()=="free":
                from geometric_constraints import feasible_seed, check_heights
                def valid(candidate):
                    from ground_effect import orient_geometry
                    g=orient_geometry(engine.build_geometry(p,c,candidate,r,modes),r,config["environment"])
                    engine.validate_geometry(g,clearance,config.get("bounding_box"))
                    check_heights(g,r,config["height_constraints"])
                params=feasible_seed(axes,valid)
            from ground_effect import orient_geometry
            self.geometry=orient_geometry(engine.build_geometry(p,c,params,r,modes),r,config["environment"])
            self.scene_environment=dict(config["environment"]); self.scene_reference=r
            self.scene_height_limits=json.loads(json.dumps(config.get("height_constraints",[])))
            self.draw()
            engine.validate_geometry(self.geometry,clearance,config.get("bounding_box"))
            from geometric_constraints import check_heights
            check_heights(self.geometry,r,config.get("height_constraints",[]))
            angles=absolute_angles(params,modes)
            if config["environment"]["flip_for_downforce"]: angles=[-a for a in angles]
            if self.mode.get() in ("sequential","free"):
                info=f"{config['search']['coarse_divisions']} coarse intervals; {sum(len(v)>1 for v in axes.values())} variable parameters"
                info+=f"; fine window ±2.5% of full range, step {config['search']['fine_step_percent']:g}% of full range"
            else: info=f"{engine.math.prod(len(v) for v in axes.values()):,} combinations × {len(alphas)} reference offsets"
            self.status.set(f"Preview valid • absolute body angles {', '.join(f'{a:g}°' for a in angles)} • {info}")
            self.tabs.select(self.results_tab)
        except Exception as e: self.status.set("Preview: "+str(e)); messagebox.showerror("Preview",str(e))

    def draw(self):
        self.canvas.delete("all")
        if not self.geometry:
            self.canvas.create_text(max(100,self.canvas.winfo_width())/2,max(100,self.canvas.winfo_height())/2,
                text="Your wing preview appears here"+chr(10)+"Choose airfoils, then select Preview.",justify="center",
                font=("Segoe UI",12),fill="#98a2b3")
            return
        pts=[p for element in self.geometry for p in element]
        x0=min(0.,min(x for x,y in pts)); x1=max(x for x,y in pts); y0=min(y for x,y in pts); y1=max(y for x,y in pts)
        ground=self.scene_environment.get("ground_effect",False)
        from design_inputs import length_m
        from geometric_constraints import constraint_kind
        active=[g for g in self.scene_height_limits if g.get("enabled",True)]
        ceilings=[(g,length_m(g["max_height"],g.get("unit","m"))/self.scene_reference) for g in active if constraint_kind(g)=="height"]
        lengths=[(g,length_m(g["max_length"],g.get("unit","m"))/self.scene_reference) for g in active if constraint_kind(g)=="length"]

        if ground or ceilings: y0=min(0.,y0)
        if ceilings:y1=max(y1,max(value for group,value in ceilings))
        width=max(100,self.canvas.winfo_width()); height=max(100,self.canvas.winfo_height())
        scale=min((width-60)/max(x1-x0,.001),(height-85)/max(y1-y0,.001)); cx=(x0+x1)/2; cy=(y0+y1)/2
        if ground:
            floor=height/2+cy*scale
            self.canvas.create_rectangle(0,floor,width,height,fill="#e2e8f0",outline="",tags="ground")
            self.canvas.create_line(0,floor,width,floor,fill="#64748b",width=2,tags="ground")
            self.canvas.create_text(width-15,floor+14,text="Ground (y = 0)",anchor="e",fill="#475569",tags="ground")
            low=min(pts,key=lambda p:p[1])
            px=width/2+(low[0]-cx)*scale; py=height/2-(low[1]-cy)*scale
            self.canvas.create_line(px,py,px,floor,arrow="both",fill="#475569",tags="ground-clearance")
            self.canvas.create_text(px+8,(py+floor)/2,text=f"{self.scene_environment['clearance_m']*1000:g} mm",anchor="w",fill="#475569",tags="ground-clearance")
        if ceilings and not ground:
            zero=height/2+cy*scale
            self.canvas.create_line(0,zero,width,zero,fill="#64748b",dash=(3,3),tags="height-reference")
            self.canvas.create_text(width-12,zero+12,text="Reference plane (y = 0)",anchor="e",fill="#64748b",tags="height-reference")
        for group,limit in ceilings:
            line_y=height/2-(limit-cy)*scale
            unit=group.get("unit","m");value=length_m(group["max_height"],unit)/UNIT_FACTORS[unit]
            selected=", ".join(map(str,group["elements"]))
            self.canvas.create_line(0,line_y,width,line_y,fill="#d97706",dash=(7,4),width=2,tags="height-ceiling")
            self.canvas.create_text(12,line_y-9,text=f"Airfoils {selected}: must stay below {value:g} {unit}",anchor="w",fill="#b45309",tags="height-ceiling")
        origin_x=width/2-cx*scale
        self.canvas.create_line(origin_x,0,origin_x,height,fill="#64748b",dash=(3,3),tags="length-reference")
        self.canvas.create_text(origin_x+8,height-18,text="First leading edge: x = 0",anchor="sw",fill="#475569",tags="length-reference")
        for row,(group,limit) in enumerate(lengths):
            total=sum(max(x for x,y in self.geometry[i-1])-min(x for x,y in self.geometry[i-1]) for i in group["elements"])
            unit=group.get("unit","m");factor=self.scene_reference/UNIT_FACTORS[unit]
            self.canvas.create_text(width-12,38+row*22,text=f"Airfoils {group['elements']}: total width {total*factor:g} / {limit*factor:g} {unit}",
                anchor="ne",fill="#087f8c" if total<=limit+1e-12 else "#b42318",tags="length-limit")
        colors=["#2563eb","#dc2626","#059669","#9333ea","#d97706"]
        fills=["#eff5ff","#fff1f0","#ecfdf3","#f4efff","#fff7e6"]
        for index,element in enumerate(self.geometry):
            coords=[v for x,y in element for v in (width/2+(x-cx)*scale,height/2-(y-cy)*scale)]
            self.canvas.create_polygon(coords,outline=colors[index % len(colors)],fill=fills[index % len(fills)],width=2)
        self.canvas.create_text(12,12,text="Car orientation · downforce" if self.scene_environment.get("flip_for_downforce") else "Airfoil geometry",anchor="nw",fill="#475569")

    def start(self):
        if self.running or self.saving: return
        try:
            config=self.config(); prepared=engine.prepare(config,self.base)
            total=engine.math.prod(len(v) for v in prepared[3].values())
            engine.JavaFoil(config["simulation"])
        except Exception as e: messagebox.showerror("Cannot start",str(e)); return
        self.run_environment=dict(config["environment"]); self.run_reference=prepared[2]
        self.run_height_limits=json.loads(json.dumps(config.get("height_constraints",[])))
        self.running=True; self.stop.clear(); self.start_button.configure(state="disabled"); self.stop_button.configure(state="normal")
        self.saved_design=None;self.save_design_button.configure(state="disabled")
        self.report_button.configure(state="disabled"); self.tabs.select(self.results_tab)
        self.output=engine.ROOT/"runs"/datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.status.set("Running JavaFoil…"); base=self.base
        def worker():
            try: self.messages.put(("done",engine.run(config,self.output,base,lambda s:self.messages.put(("progress",s)),self.stop)))
            except Exception as e: self.messages.put(("error",str(e)))
        threading.Thread(target=worker,daemon=True).start()

    def cancel(self):
        self.stop.set(); self.status.set("Stopping; retaining completed results…")

    def update_reynolds_estimate(self):
        """Refresh lightweight estimates without validating unrelated form fields."""
        from air_conditions import reynolds_estimates
        try:
            unit=self.global_unit.get()
            reference=length_m(float(self.settings["reference_chord_m"].get()),unit)
            sim={"relative_airspeed":{"value":float(self.flight_inputs.speed.get()),"unit":self.flight_inputs.speed_unit.get()}}
            for key in ("temperature_c","pressure_pa","density_override","viscosity_override"):
                value=self.settings[key].get().strip()
                if value:sim[key]=float(value)
            override=self.settings["reynolds"].get().strip()
            if override:sim["reynolds_override"]=float(override)
            chords=[]
            for row in self.rows:
                value=parse(row["chord"].get())
                values=[value["min"],value["max"]] if isinstance(value,dict) else value if isinstance(value,list) else [value]
                chords.append([length_m(v,row["length_unit"].get()) for v in values])
            calculated,effective,elements=reynolds_estimates(sim,reference,chords)
            label=f"Estimated reference Reynolds: {calculated:,.0f}"
            if override:label+=f" | Solver override: {effective:,.0f}"
            detail="\n".join(f"Airfoil {i}: "+(f"{lo:,.0f}" if lo==hi else f"{lo:,.0f} to {hi:,.0f}") for i,(lo,hi) in enumerate(elements,1))
            if override:detail="Using solver override\n"+detail
        except (ValueError,KeyError,TypeError,OverflowError):
            label="Estimated Reynolds: enter valid positive airspeed, chord and air properties"
            detail=""
        if self.flight_inputs.reynolds_text.get()!=label:self.flight_inputs.reynolds_text.set(label)
        if self.flight_inputs.element_reynolds_text.get()!=detail:self.flight_inputs.element_reynolds_text.set(detail)

    def _cancel_poll_on_destroy(self,event):
        if event.widget is self.root and self._poll_timer is not None:
            self.root.after_cancel(self._poll_timer)
            self._poll_timer=None

    def poll(self):
        if self._poll_timer is not None:
            self.root.after_cancel(self._poll_timer)
        self._poll_timer=None
        self.update_reynolds_estimate()
        while not self.messages.empty():
            kind,data=self.messages.get()
            if kind in ("progress","save_progress"):
                self.status.set(data)
                if kind=="progress":
                    at_bottom=self.log.yview()[1]>=.999
                    self.log.configure(state="normal"); self.log.insert("end",data+"\n")
                    if at_bottom:self.log.see("end")
                    self.log.configure(state="disabled")
            elif kind in ("saved","save_error"):
                self.saving=False;self.start_button.configure(state="normal");self.stop_button.configure(state="disabled")
                self.save_design_button.configure(state="normal")
                if kind=="saved":
                    self.saved_design=Path(data);self.report_button.configure(state="normal")
                    self.status.set("Design saved to "+data)
                else:
                    self.status.set("Save failed: "+data);messagebox.showerror("Save design",data)
            else:
                self.running=False; self.start_button.configure(state="normal"); self.stop_button.configure(state="disabled")
                if kind=="error": self.status.set("Run failed: "+data); messagebox.showerror("Optimization",data)
                else:
                    best=data["best"]; coefficient="Cl"; state=data.get("search",{}).get("termination","finished").replace("_"," ")
                    self.status.set(f"{state} • best {coefficient} {best['cl']:.5f} • {data['evaluated_geometries']} evaluations • {self.output}" if best else state+" • no completed simulation")
                    if best:
                        self.save_design_button.configure(state="normal")
                        text=(self.output/"best/javafoil_geometry.txt").read_text()
                        self.geometry=[[(float(p[0]),float(p[1])) for line in block.strip().splitlines() if len(p:=line.split())==2] for block in text.split("9999.9 9999.9")]
                        self.scene_environment=self.run_environment; self.scene_reference=self.run_reference
                        self.scene_height_limits=self.run_height_limits
                        self.draw()
                    if (self.output/"report.html").exists(): self.report_button.configure(state="normal")
        self._poll_timer=self.root.after(150,self.poll)

    def save_design(self):
        if self.running or self.saving or not self.output: return
        parent=filedialog.askdirectory(title="Choose where to save the design folder",mustexist=True)
        if not parent:return
        source=self.output
        self.saving=True;self.stop.clear()
        self.save_design_button.configure(state="disabled");self.start_button.configure(state="disabled");self.stop_button.configure(state="normal")
        self.status.set("Saving the optimized design…")
        def worker():
            try:
                from design_export import export_design
                destination=export_design(source,Path(parent),lambda text:self.messages.put(("save_progress",text)),self.stop)
                self.messages.put(("saved",str(destination)))
            except engine.Cancelled:self.messages.put(("save_error","Export canceled. Your optimization results are retained."))
            except Exception as e:self.messages.put(("save_error",str(e)))
        threading.Thread(target=worker,daemon=True).start()

    def open_report(self):
        if self.saved_design and (self.saved_design/"design_report.pdf").exists():
            webbrowser.open((self.saved_design/"design_report.pdf").as_uri());return
        if self.output and (self.output/"report.html").exists(): webbrowser.open((self.output/"report.html").as_uri())

    def close(self):
        if self.running or self.saving: self.cancel(); self.root.after(200,self.close_when_stopped)
        else: self.root.destroy()

    def close_when_stopped(self):
        if self.running or self.saving: self.root.after(200,self.close_when_stopped)
        else: self.root.destroy()

class DesktopApp:
    """Two independent function tabs, each with its own configuration and results."""
    def __init__(self,root):
        from ui_theme import apply_theme
        apply_theme(root)
        self.root=root
        from ui_theme import build_masthead
        build_masthead(root)
        self.tabs=ttk.Notebook(root,style="Main.TNotebook")
        self.tabs.pack(fill="both",expand=True,padx=24,pady=(10,20))
        self.panes={}; self.frames={}
        for function,title in (("placement","Adjust positions"),("sizing","Size & fit")):
            frame=ttk.Frame(self.tabs); self.tabs.add(frame,text=title)
            self.frames[function]=frame
            self.panes[function]=App(root,parent=frame,function=function,host=self)
        root.title("Multi-element Optimizer")
        root.protocol("WM_DELETE_WINDOW",self.close)

    def apply_config(self,config,base):
        function="sizing" if config.get("search",{}).get("mode")=="free" else "placement"
        pane=self.panes[function]
        if pane.running: raise ValueError("Stop this tab's optimization before loading a configuration")
        pane.apply_config(config); pane.base=base
        pane.tabs.select(0)
        self.tabs.select(self.frames[function])

    def close(self):
        running=[pane for pane in self.panes.values() if pane.running or pane.saving]
        if running:
            for pane in running: pane.cancel()
            self.root.after(200,self.close)
        else: self.root.destroy()

if __name__=="__main__":
    from ui_theme import enable_high_dpi
    enable_high_dpi()
    window=tk.Tk(); DesktopApp(window); window.mainloop()
