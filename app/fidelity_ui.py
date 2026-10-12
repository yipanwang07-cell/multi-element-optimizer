"""Sweep fidelity controls shared by both independent optimization tabs."""
import tkinter as tk
from tkinter import ttk
from coordinate_search import sweep_resolution
from hover_help import term_label
from cpu_workers import physical_core_cpus,worker_count

class FidelityControls:
    def __init__(self,parent):
        self.frame=ttk.Frame(parent)
        self.canvas=tk.Canvas(self.frame,highlightthickness=0,background="#ffffff",yscrollincrement=25)
        self.scrollbar=ttk.Scrollbar(self.frame,orient="vertical",command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right",fill="y");self.canvas.pack(side="left",fill="both",expand=True)
        content=ttk.Frame(self.canvas,padding=20)
        item=self.canvas.create_window((0,0),window=content,anchor="nw")
        content.bind("<Configure>",lambda e:self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",lambda e:self.canvas.itemconfigure(item,width=e.width))
        from ui_theme import attach_scroll
        attach_scroll(self.canvas,content)
        self.core_count=len(physical_core_cpus())
        self.workers=tk.StringVar(value=str(min(4,self.core_count)))
        self.coarse=tk.StringVar(value="10")
        self.fine=tk.StringVar(value="0.25")
        self.description=tk.StringVar()
        ttk.Label(content,text="Search settings",style="Title.TLabel").pack(anchor="w")
        ttk.Label(content,text="Choose how closely to sample your angle and length ranges.",style="Muted.TLabel").pack(anchor="w",pady=(8,24))
        for title,key,var in (("Coarse sweep divisions","coarse_divisions",self.coarse),
                              ("Fine step (% of full parameter range)","fine_step_percent",self.fine)):
            section=ttk.Frame(content);section.pack(fill="x",pady=12)
            heading,_=term_label(section,title,key);heading.pack(anchor="w")
            ttk.Entry(section,textvariable=var,width=18).pack(anchor="w",pady=8)
        heading,_=term_label(content,"Parallel processes (physical cores)","workers");heading.pack(anchor="w",pady=(12,4))
        self.worker_box=ttk.Combobox(content,textvariable=self.workers,values=list(range(1,self.core_count+1)),state="readonly",width=16)
        self.worker_box.pack(anchor="w")
        ttk.Label(content,text=f"{self.core_count} physical cores available",style="Muted.TLabel",wraplength=800).pack(anchor="w",pady=8)
        ttk.Label(content,textvariable=self.description,wraplength=800,justify="left",style="Muted.TLabel").pack(anchor="w",pady=20)
        ttk.Label(content,text="Fine refinement: ±2.5% of the full input range around the winner.",wraplength=800,justify="left").pack(anchor="w",pady=8)
        ttk.Button(content,text="Restore defaults",command=lambda:self.set({})).pack(anchor="w",pady=16)
        for var in (self.coarse,self.fine):var.trace_add("write",lambda *_:self.update_description())
        self.update_description()
    def get(self):
        coarse,fine=sweep_resolution(dict(coarse_divisions=self.coarse.get(),fine_step_percent=self.fine.get()))
        return dict(coarse_divisions=coarse,fine_step_percent=fine,workers=worker_count(self.workers.get(),self.core_count))
    def set(self,settings):
        self.workers.set(str(worker_count(settings.get("workers","auto"),self.core_count)))
        self.coarse.set(str(settings.get("coarse_divisions",10)))
        self.fine.set(str(settings.get("fine_step_percent",.25)))
    def update_description(self):
        try:
            values=self.get();c=values["coarse_divisions"];f=values["fine_step_percent"]
            self.description.set(f"Coarse step: {100/c:g}%   ·   Fine step: {f:g}% of the full range")
        except ValueError as error:self.description.set(str(error))
