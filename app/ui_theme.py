"""Consistent light desktop theme without additional dependencies."""
import sys
import tkinter as tk

def enable_high_dpi():
    """Opt out of Windows bitmap stretching before creating any Tk windows."""
    if sys.platform != "win32": return
    import ctypes
    try:
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)): return
    except (AttributeError, OSError): pass
    try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        try: ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError): pass

from tkinter import ttk
BG="#edf1f5"
SURFACE="#ffffff"
TEXT="#182230"
MUTED="#667085"
BORDER="#dce2eb"
ACCENT="#087f8c"

def apply_theme(root):
    if getattr(root,"_wing_theme_applied",False): return
    root._wing_theme_applied=True
    # Closed fields must not change on wheel input. Leave events available to
    # the surrounding panel; the open popup retains its Listbox bindings.
    for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        root.unbind_class("TCombobox", sequence)
    if root.tk.call("tk", "windowingsystem") == "aqua":
        root.unbind_class("TCombobox", "<Option-MouseWheel>")
    root.configure(background=BG)
    root.option_add("*Font",("Segoe UI",11))
    root.option_add("*TCombobox*Listbox.font",("Segoe UI",11))
    root.option_add("*TCombobox*Listbox.background",SURFACE)
    root.option_add("*TCombobox*Listbox.foreground",TEXT)
    style=ttk.Style(root);style.theme_use("clam")
    style.configure(".",font=("Segoe UI",11),background=SURFACE,foreground=TEXT)
    style.configure("TFrame",background=SURFACE)
    style.configure("App.TFrame",background=BG)
    style.configure("TLabel",background=SURFACE,foreground=TEXT)
    style.configure("Muted.TLabel",foreground=MUTED)
    style.configure("Help.TLabel",foreground="#6b7e9e",font=("Segoe UI",10,"bold"),padding=(4,1))
    style.configure("Hero.TLabel",background=BG,foreground=TEXT,font=("Segoe UI",22,"bold"))
    style.configure("HeroSub.TLabel",background=BG,foreground=MUTED,font=("Segoe UI",11))
    style.configure("Title.TLabel",font=("Segoe UI",18,"bold"))
    style.configure("Status.TLabel",foreground=MUTED,padding=(0,5))
    style.configure("TLabelframe",background=SURFACE,bordercolor=BORDER,lightcolor=SURFACE,darkcolor=SURFACE,relief="solid",borderwidth=1)
    style.configure("TLabelframe.Label",background=SURFACE,foreground=TEXT,font=("Segoe UI",11,"bold"))
    style.configure("TButton",background=SURFACE,foreground=TEXT,bordercolor=BORDER,lightcolor=SURFACE,darkcolor=SURFACE,relief="flat",padding=(13,8),focuscolor=SURFACE)
    style.map("TButton",background=[("disabled","#f5f6f8"),("active","#eef2f7")],foreground=[("disabled","#98a2b3")],bordercolor=[("focus",ACCENT)])
    style.configure("Primary.TButton",background=ACCENT,foreground="white",bordercolor=ACCENT,lightcolor=ACCENT,darkcolor=ACCENT,font=("Segoe UI",11,"bold"),padding=(20,10))
    style.map("Primary.TButton",background=[("disabled","#9dbfc3"),("active","#066773")],foreground=[("disabled","#edf2ff"),("!disabled","white")])
    style.configure("Quiet.TButton",background=SURFACE,foreground=MUTED,bordercolor=SURFACE,padding=(8,6))
    style.map("Quiet.TButton",background=[("active","#f0f4fa")],foreground=[("active",ACCENT),("disabled","#98a2b3")])
    style.configure("TEntry",fieldbackground="#fafbfd",foreground=TEXT,bordercolor=BORDER,lightcolor=BORDER,darkcolor=BORDER,padding=(10,9),insertcolor=TEXT)
    style.map("TEntry",bordercolor=[("focus",ACCENT)],fieldbackground=[("disabled","#f1f3f6")])
    style.configure("TCombobox",fieldbackground="#fafbfd",background="#fafbfd",foreground=TEXT,arrowcolor=MUTED,bordercolor=BORDER,lightcolor=BORDER,darkcolor=BORDER,padding=(8,7))
    style.map("TCombobox",fieldbackground=[("readonly","#fafbfd"),("disabled","#f1f3f6")],foreground=[("readonly",TEXT),("disabled","#98a2b3")],bordercolor=[("focus",ACCENT)])
    style.configure("TCheckbutton",background=SURFACE,foreground=TEXT,padding=(3,5),focuscolor=SURFACE)
    style.map("TCheckbutton",background=[("active",SURFACE)])
    style.configure("TNotebook",background=SURFACE,borderwidth=0,tabmargins=(0,5,0,6))
    style.configure("TNotebook.Tab",background="#f1f4f8",foreground=MUTED,padding=(20,10),borderwidth=0,font=("Segoe UI",11))
    style.map("TNotebook.Tab",background=[("selected","#e3f3f2"),("active","#edf2f8")],foreground=[("selected",ACCENT)])
    style.configure("Main.TNotebook",background=BG,tabmargins=(0,0,0,12))
    style.configure("Main.TNotebook.Tab",background=BG,foreground=MUTED,padding=(24,12),font=("Segoe UI",11,"bold"))
    style.map("Main.TNotebook.Tab",background=[("selected",ACCENT),("active","#e6ebf3")],foreground=[("selected","white")])
    style.configure("Masthead.TFrame",background="#122638")
    style.configure("Brand.TLabel",background="#122638",foreground="#ffffff",font=("Segoe UI",23,"bold"))
    style.configure("BrandSub.TLabel",background="#122638",foreground="#a9c3d1",font=("Segoe UI",10))
    style.configure("Section.TLabel",foreground="#122638",font=("Segoe UI",15,"bold"))
    style.configure("Index.TLabel",background="#e3f3f2",foreground=ACCENT,font=("Segoe UI",12,"bold"),padding=(10,5))
    style.configure("Card.TFrame",background=SURFACE,bordercolor=BORDER,relief="solid",borderwidth=1)
    style.configure("Action.TFrame",background="#f4f7fa")
    style.configure("Main.TNotebook.Tab",padding=(28,13))
    style.map("Main.TNotebook.Tab",background=[("selected","#122638"),("active","#dfe7ec")],foreground=[("selected","#ffffff")])
    style.configure("Vertical.TScrollbar",background="#cbd3df",troughcolor=SURFACE,bordercolor=SURFACE,arrowcolor=SURFACE,width=9,arrowsize=8)
    style.map("Vertical.TScrollbar",background=[("active","#9ba9bb")])

def attach_scroll(canvas,content):
    root=canvas.winfo_toplevel()
    def wheel(event):
        widget=root.winfo_containing(event.x_root,event.y_root)
        while widget is not None:
            if widget==content or widget==canvas:
                canvas.yview_scroll(-int(event.delta/120),"units")
                return "break"
            widget=getattr(widget,"master",None)
    root.bind("<MouseWheel>",wheel,add="+")


def build_masthead(parent):
    """Vector wing mark remains crisp at any desktop scale."""
    band=ttk.Frame(parent,style="Masthead.TFrame",padding=(28,20))
    band.pack(fill="x")
    scale=float(parent.tk.call("tk","scaling"))/(96/72)
    mark=tk.Canvas(band,width=round(76*scale),height=round(48*scale),
                   bg="#122638",highlightthickness=0)
    mark.pack(side="left",padx=(0,20))
    def draw(event):
        mark.delete("all");w=event.width;h=event.height
        import math
        # Inverted cambered sections: rounded noses, sharp trailing edges,
        # and a shorter flap rising behind the main element.
        for x0,y0,chord,angle,color in (
            (.04*w,.66*h,.64*w,8,"#38c6bb"),
            (.65*w,.48*h,.30*w,30,"#7de2d8")):
            points=[]
            theta=math.radians(angle)
            xs=[(1-math.cos(math.pi*i/40))/2 for i in range(41)]
            for side,stations in ((1,xs),(-1,list(reversed(xs)))):
                for x in stations:
                    thickness=5*.13*(.2969*math.sqrt(x)-.1260*x-.3516*x*x+.2843*x**3-.1036*x**4)
                    camber=-.045*4*x*(1-x)
                    y=camber+side*thickness
                    points.extend((x0+chord*(x*math.cos(theta)-y*math.sin(theta)),
                                   y0-chord*(x*math.sin(theta)+y*math.cos(theta))))
            mark.create_polygon(*points,fill=color,outline="")
    mark.bind("<Configure>",draw)
    title=ttk.Frame(band,style="Masthead.TFrame");title.pack(side="left")
    ttk.Label(title,text="Multi-element Optimizer",style="Brand.TLabel").pack(anchor="w")
    ttk.Label(title,text="MULTIELEMENT DESIGN & OPTIMIZATION",style="BrandSub.TLabel").pack(anchor="w",pady=(3,0))
    ttk.Label(band,text="Based on JavaFoil",style="BrandSub.TLabel").pack(side="right")
    tk.Frame(parent,height=3,bg=ACCENT).pack(fill="x")
    return band
