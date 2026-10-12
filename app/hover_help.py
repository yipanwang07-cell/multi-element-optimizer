"""Small focusable help icons and delayed, screen-clamped hover explanations."""
import tkinter as tk
from tkinter import ttk

HELP={
"coarse_divisions":"Number of intervals across the full input range. Step = (maximum - minimum) / divisions. For a 20-degree range, 10 divisions gives 2-degree steps. Larger values take more simulations.",
"stall_model":"JavaFoil stall correction: Calcfoil, Eppler, or None (correction disabled). Eppler is the default and is generally preferred by JavaFoil for multi-element airfoils. These are empirical corrections, not resolved separated-flow simulations. The chosen model is used throughout the sweep and saved-design export.",
"fine_step_percent":"Both the fine window and step use the full parameter range: maximum minus minimum. Search winner ±2.5% of that range, clipped to the input bounds. Default step is 0.25% of the range. For 100–300 mm and a 200 mm winner, search 195–205 mm in 0.5 mm steps. Zero and negative winners follow the same rule.",

"workers":"Choose how many separate JavaFoil processes to run. Each is bound to one distinct physical core, without using both hyperthreads of a core. The selected number runs when the sweep has enough independent candidates; baseline and short batches use fewer.",
"family":"A group of related airfoil designs, such as Selig or Eppler. Choose a family to narrow the profile list.",
"profile":"The cross-section shape of the airfoil. The profile is scaled to the chord length you enter.",
"chord":"Distance from the leading edge to the trailing edge. Use one length to keep the size fixed, or a range such as 100:300 in Size & fit.",
"length_unit":"Unit for this airfoil's chord, gap and overlap. Changing the unit converts the numbers while preserving their physical sizes.",
"incidence_deg":"Airfoil angle in degrees. Enter one angle or a range such as 5:15. Positive angles follow the selected frame; flipping the wing mirrors those angles.",
"angle_mode":"Absolute: measured from horizontal in the entered frame. Relative: added to the previous airfoil's angle. For example, 5° absolute followed by 10° relative gives 15° for the second airfoil.",
"gap":"Vertical offset from the previous airfoil's trailing edge to this airfoil's leading edge. This is a placement offset, not the shortest distance between surfaces. The first airfoil has no previous element.",
"overlap":"Horizontal distance the next airfoil's leading edge sits ahead of the previous trailing edge. Positive means overlap; zero aligns those points horizontally; negative leaves a horizontal gap.",
"ranges":"Enter min:max, for example 10:30, to sweep a range. One value holds a parameter fixed. Comma-separated values are specific choices. Set coarse divisions and the fine-step percentage in Simulation fidelity. Default coarse steps are range/10. Fine refinement covers winner ±2.5% of the full range, with a user-set step percentage of that range.",
"wingspan":"Wing width from tip to tip. Used for JavaFoil's approximate finite-span correction. The reference area is wingspan × lift reference length. Span is not the length used for chord Reynolds number.",
"airspeed":"Speed of the surrounding air relative to the wing, including vehicle motion and wind. Used to calculate Reynolds number and Mach number. This is not simply vehicle speed if wind is present.",
"ground_effect":"Include JavaFoil's flat ground plane at y = 0. Each candidate is shifted so its lowest point has the selected clearance. This is a 2D ground model, not a complete car or diffuser simulation.",
"flip_for_downforce":"Mirror the complete wing vertically to resemble a car wing. The optimization metric stays Cl; positive Cl represents force in the selected orientation. Signed upward-positive lift is also saved.",
"ground_clearance":"Shortest vertical distance between the lowest airfoil point and the ground. The optimizer holds this clearance for each candidate as size and placement change.",
"height_group":"Choose the existing airfoils that must remain below this ceiling. Every selected airfoil is checked. Multiple selections also define joint sweep groups in Size & fit.",
"height_airfoil":"Select the airfoil whose highest point must stay below the height line measured from y = 0. Airfoils physically below it also remain below that line; numbering does not determine vertical position.",
"length_group":"Select any combination of airfoils. Their individual horizontal widths after rotation are added together, including overlapping portions. Gaps are not added.",
"geometry_limit":"Height limits the selected airfoil's highest point above y = 0. Length limits the sum of selected airfoils' horizontal widths after rotation. Enable Height, Length, or both using the box headers.",
"max_height":"Absolute height of a horizontal ceiling above y = 0. The highest point of every selected airfoil must not exceed it, after rotation, placement, flipping, and ground clearance. With ground effect, y = 0 is the ground; otherwise it is the geometry reference plane. This is not airfoil thickness or combined vertical span.",
"reference_chord_m":"Fixed length used to normalize geometry, calculate reference Reynolds number and compare Cl between designs. Each element's Reynolds number also scales with its own chord.",
"reference_unit":"Unit for the lift reference length, minimum separation and overall box dimensions in Advanced settings.",
"minimum_clearance":"Minimum permitted distance between any two airfoil surfaces. Touching, intersecting or too-close candidates are rejected before simulation.",
"alpha_deg":"Angle offset applied to the whole wing, in addition to each airfoil's angle. Normally 0°. Ground, flipped orientation and Size & fit use zero to preserve their geometric frame.",
"reynolds":"Dimensionless measure comparing inertial and viscous effects. Calculated as air density × airspeed × chord / dynamic viscosity. Leave blank to calculate automatically; an override sets reference Re.",
"mach":"Relative airspeed divided by the speed of sound. Leave blank to calculate automatically. An override of 0 requests incompressible analysis. This solver requires Mach below 0.7.",
"box_width":"Maximum horizontal span of the complete assembly, not the wing's tip-to-tip wingspan. Enter both box width and height to enforce an overall envelope.",
"box_height":"Maximum vertical span of the complete assembly. Enter both box width and height, or leave both blank. Airfoil height ceilings are separate.",
"panels_per_element":"Number of segments used to approximate each airfoil outline. More panels increase detail and cost. Use an even number between 40 and 240; default 120.",
"max_passes":"Maximum number of complete sweep rounds. Later rounds revisit parameters because they interact. Both tabs have one coarse and one fine stage per round.",
"seed":"Seed for reproducible random choices, including finding a feasible initial geometry. The same seed and settings produce the same choices.",
"temperature_c":"Ambient air temperature in degrees Celsius. Default 15°C for standard sea-level air. Changes calculated density, viscosity and speed of sound.",
"pressure_pa":"Ambient absolute air pressure in pascals. Default 101,325 Pa. Used with temperature to calculate air density.",
"density_override":"Air mass per volume in kg/m³. Leave blank to calculate from temperature and pressure. Changes calculated Reynolds number.",
"viscosity_override":"Dynamic viscosity in Pa·s: resistance to shear in the air. Leave blank for the temperature-based calculation. Lower viscosity increases Reynolds number at the same speed and chord.",
"sound_speed_override":"Speed at which sound travels through the air, in m/s. Leave blank to calculate from temperature. Used to calculate Mach number.",
"aspect_ratio_override":"JavaFoil's approximate finite-span correction parameter. Automatically wingspan / fixed reference chord. Leave blank for automatic calculation; 0 gives a 2D section result.",
"transition_upper":"Requested upper-surface laminar-to-turbulent transition location, as a fraction of chord. 0.5 is halfway; 1 is the trailing edge. Must be greater than 0 and at most 1.",
"transition_lower":"Requested lower-surface laminar-to-turbulent transition location, as a fraction of chord. 0.5 is halfway; 1 is the trailing edge. Must be greater than 0 and at most 1.",
"transition_model":"Select any of JavaFoil's nine laminar-to-turbulent transition criteria. Dropdown Reynolds guidance comes from its documentation; a lower bound is not a guaranteed validity range. Models without a published recommendation are marked accordingly. Default: Eppler 1. This is separate from the stall correction.",
"roughness":"JavaFoil surface-roughness class, from 0 to 3. Default 0. Changes the boundary-layer assumptions.",
"timeout_seconds":"Maximum time allowed for one JavaFoil simulation, in seconds. A timed-out case is recorded as failed and cannot become the best design.",
"cl":"Dimensionless lift coefficient used to compare candidates. In flipped orientation, positive Cl represents downforce. Saved lift_cl remains upward-positive. Cl depends on the fixed lift reference length.",
}

class HoverHelp:
    def __init__(self,widget,text,delay=400):
        self.widget=widget;self.text=text;self.delay=delay
        self.timer=None;self.window=None
        for event in ("<Enter>","<FocusIn>"): widget.bind(event,self.schedule,add="+")
        for event in ("<Leave>","<FocusOut>","<Escape>","<ButtonPress>","<Unmap>"): widget.bind(event,self.hide,add="+")
        widget.bind("<Destroy>",self.destroy,add="+")
    def schedule(self,event=None):
        self.hide()
        self.timer=self.widget.after(self.delay,self.show)
    def show(self):
        self.timer=None
        if self.window or not self.widget.winfo_exists() or not self.widget.winfo_ismapped(): return
        tip=tk.Toplevel(self.widget)
        self.window=tip
        tip.withdraw();tip.wm_overrideredirect(True)
        tip.transient(self.widget.winfo_toplevel())
        panel=tk.Frame(tip,bg="#1e293b",padx=14,pady=10)
        panel.pack()
        tk.Label(panel,text=self.text,bg="#1e293b",fg="#f8fafc",font=("Segoe UI",11),
                 justify="left",wraplength=340).pack()
        tip.update_idletasks()
        x=self.widget.winfo_rootx()+10;y=self.widget.winfo_rooty()+self.widget.winfo_height()+8
        width=tip.winfo_reqwidth();height=tip.winfo_reqheight()
        # Keep the explanation on the screen containing the app's virtual desktop.
        left=self.widget.winfo_vrootx();top=self.widget.winfo_vrooty()
        right=left+self.widget.winfo_vrootwidth();bottom=top+self.widget.winfo_vrootheight()
        x=max(left+6,min(x,right-width-6))
        if y+height>bottom-6:y=self.widget.winfo_rooty()-height-8
        y=max(top+6,min(y,bottom-height-6))
        tip.geometry(f"+{x}+{y}");tip.deiconify()
    def hide(self,event=None):
        if self.timer is not None:
            try:self.widget.after_cancel(self.timer)
            except tk.TclError:pass
            self.timer=None
        if self.window is not None:
            try:self.window.destroy()
            except tk.TclError:pass
            self.window=None
    def destroy(self,event):
        if event.widget==self.widget:self.hide()

def help_icon(parent,key):
    icon=ttk.Label(parent,text="?",style="Help.TLabel",cursor="hand2",takefocus=True)
    icon.help_key=key
    icon.tooltip=HoverHelp(icon,HELP[key])
    return icon

def add_help(parent,key,**pack_options):
    icon=help_icon(parent,key)
    icon.pack(side="left",padx=(4,6),**pack_options)
    return icon

def term_label(parent,text,key,**options):
    frame=ttk.Frame(parent)
    label=ttk.Label(frame,text=text,**options);label.pack(side="left")
    add_help(frame,key)
    return frame,label
