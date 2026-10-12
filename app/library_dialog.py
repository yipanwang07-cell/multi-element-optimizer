"""Searchable desktop airfoil library picker."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import webbrowser
import airfoil_library as library
import wing_optimizer as engine

class LibraryDialog:
    def __init__(self,parent,on_select):
        self.on_select=on_select
        self.window=tk.Toplevel(parent); self.window.title("Airfoil library")
        self.window.geometry("860x660")
        self.window.transient(parent)
        self.entries=library.airfoils(True)
        self.query=tk.StringVar(); self.family=tk.StringVar(value="All families")
        outer=ttk.Frame(self.window,padding=12); outer.pack(fill="both",expand=True)
        toolbar=ttk.Frame(outer); toolbar.pack(fill="x")
        ttk.Label(toolbar,text="Search").pack(side="left")
        ttk.Entry(toolbar,textvariable=self.query,width=28).pack(side="left",padx=8)
        combo=ttk.Combobox(toolbar,textvariable=self.family,
            values=["All families"]+sorted({e["family"] for e in self.entries}),state="readonly",width=18)
        combo.pack(side="left")
        self.count=ttk.Label(toolbar); self.count.pack(side="right")
        frame=ttk.Frame(outer); frame.pack(fill="both",expand=True,pady=10)
        self.tree=ttk.Treeview(frame,columns=("name","family","points","status"),show="headings",height=10)
        for key,title,width in [("name","Airfoil",180),("family","Family",130),("points","Source points",100),("status","Availability",200)]:
            self.tree.heading(key,text=title); self.tree.column(key,width=width)
        scroll=ttk.Scrollbar(frame,orient="vertical",command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left",fill="both",expand=True); scroll.pack(side="right",fill="y")
        self.canvas=tk.Canvas(outer,height=150,background="#f7f9fc",highlightthickness=0); self.canvas.pack(fill="x")
        self.details=tk.StringVar(value="Select an airfoil to preview its outline and coordinate source.")
        ttk.Label(outer,textvariable=self.details,wraplength=810).pack(fill="x",pady=8)
        buttons=ttk.Frame(outer); buttons.pack(fill="x")
        self.use=ttk.Button(buttons,text="Use selected airfoil",command=self.select,state="disabled"); self.use.pack(side="left")
        ttk.Button(buttons,text="Open coordinate source",command=self.source).pack(side="left",padx=8)
        ttk.Button(buttons,text="Import DAT for selected entry",command=self.import_file).pack(side="left")
        ttk.Button(buttons,text="Close",command=self.window.destroy).pack(side="right")
        self.query.trace_add("write",lambda *_:self.refresh())
        self.family.trace_add("write",lambda *_:self.refresh())
        self.tree.bind("<<TreeviewSelect>>",lambda e:self.preview())
        self.tree.bind("<Double-1>",lambda e:self.select())
        self.refresh()

    def current(self):
        selected=self.tree.selection()
        return next((e for e in self.entries if selected and e["id"]==selected[0]),None)

    def refresh(self):
        for id in self.tree.get_children(): self.tree.delete(id)
        q=library.key(self.query.get()); family=self.family.get()
        for e in self.entries:
            if family!="All families" and e["family"]!=family: continue
            if q and q not in library.key(e["name"]+" "+e["family"]+" "+e["id"]): continue
            status="Available" if e["status"]=="available" else "Needs coordinate file"
            self.tree.insert("", "end",iid=e["id"],values=(e["name"],e["family"],e.get("source_point_count","—"),status))
        self.count.configure(text=f"{len(library.airfoils())} available profiles")
        self.use.configure(state="disabled"); self.canvas.delete("all")

    def preview(self):
        self.canvas.delete("all")
        e=self.current()
        if not e: return
        if e["status"]!="available":
            self.use.configure(state="disabled")
            self.details.set(e.get("note","Coordinates are not installed.") )
            return
        try:
            points=engine.profile(e["id"],120,engine.ROOT)
            self.canvas.update_idletasks()
            width=max(300,self.canvas.winfo_width()); height=150
            ymin=min(y for x,y in points); ymax=max(y for x,y in points)
            scale=min(width-40,(height-30)/max(ymax-ymin,.05))
            xmin=min(x for x,y in points); xmax=max(x for x,y in points)
            cx=(xmin+xmax)/2; cy=(ymin+ymax)/2
            flat=[v for x,y in points for v in (width/2+(x-cx)*scale,height/2-(y-cy)*scale)]
            self.canvas.create_polygon(flat,fill="",outline="#2563eb",width=2)
            self.details.set(e["name"]+" · "+e["family"]+"\n"+e.get("method","")+"\nSource: "+e["source_url"])
            self.use.configure(state="normal")
        except Exception as error:
            self.details.set(str(error)); self.use.configure(state="disabled")

    def select(self):
        e=self.current()
        if e and e["status"]=="available" and str(self.use["state"])!="disabled":
            self.on_select(e["name"]); self.window.destroy()

    def source(self):
        e=self.current()
        if e and e.get("source_url","").startswith(("http://","https://")):
            webbrowser.open(e["source_url"])

    def import_file(self):
        e=self.current()
        if not e: return
        path=filedialog.askopenfilename(parent=self.window,filetypes=[("Airfoil coordinates","*.dat *.txt")])
        if not path: return
        url=simpledialog.askstring("Coordinate source","Source URL or attribution (optional):",parent=self.window)
        try:
            library.register(e["id"],path,url or "")
            self.entries=library.airfoils(True)
            self.refresh()
            self.tree.selection_set(e["id"]); self.tree.see(e["id"]); self.preview()
        except Exception as error:
            messagebox.showerror("Cannot import coordinates",str(error),parent=self.window)
