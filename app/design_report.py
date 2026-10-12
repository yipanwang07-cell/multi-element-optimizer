"""Design report with surface distributions and complete numerical tables."""
from pathlib import Path
import json
from xml.sax.saxutils import escape
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"svg.fonttype":"path","pdf.fonttype":42,"path.simplify":False})
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing,Polygon,Line,String

COLORS=["#2563eb","#dc2626","#059669","#9333ea","#d97706"]

def save_figure(fig,folder,name):
    FigureCanvasAgg(fig)
    fig.set_size_inches(12.8,7.2)
    fig.savefig(folder/(name+".png"),dpi=300,facecolor="white")
    fig.clear()

def chart(ax,title,xlabel,ylabel):
    ax.set_title(title,loc="left",fontsize=15,fontweight="bold",pad=18)
    ax.set_xlabel(xlabel);ax.set_ylabel(ylabel)
    ax.grid(True,alpha=.18);ax.spines[["top","right"]].set_visible(False)

def create_graphs(folder,geometry,reference,samples,config):
    folder=Path(folder)/"graphs";folder.mkdir()
    for field,title,ylabel,name in (("cp","Pressure coefficient distribution","Pressure coefficient Cp","pressure_coefficient"),
                                   ("velocity_ratio","Surface velocity distribution","Surface speed / relative airspeed","velocity_distribution")):
        fig=Figure(figsize=(12.8,7.2),layout="constrained");ax=fig.subplots()
        for i in range(len(geometry)):
            for surface,style in (("upper","-"),("lower","--")):
                rows=[r for r in samples if r["element"]==i+1 and r["surface"]==surface]
                ax.plot([r["x_ref"] for r in rows],[r[field] for r in rows],style,color=COLORS[i],
                    label=f"Airfoil {i+1} - {surface}",linewidth=1.6)
        chart(ax,title,"x / fixed reference chord (setup frame)",ylabel)
        if field=="cp":ax.invert_yaxis()
        ax.legend(loc="best",frameon=False,ncol=2,fontsize=9)
        save_figure(fig,folder,name)

def geometry_drawing(samples,config):
    drawing=Drawing(515,230)
    x=[r["x_m"]*1000 for r in samples];y=[r["y_m"]*1000 for r in samples]
    lo=min(y) if not config["environment"].get("ground_effect") else min(0,min(y))
    scale=min(475/max(max(x)-min(x),1e-6),180/max(max(y)-lo,1e-6))
    def xy(a,b):return 20+(a-min(x))*scale,25+(b-lo)*scale
    for i in sorted({r["element"] for r in samples}):
        points=[v for r in samples if r["element"]==i for v in xy(r["x_m"]*1000,r["y_m"]*1000)]
        drawing.add(Polygon(points,strokeColor=colors.HexColor(COLORS[i-1]),fillColor=colors.HexColor("#f5f7fb"),strokeWidth=1))
    if config["environment"].get("ground_effect"):
        _,ground=xy(0,0);drawing.add(Line(15,ground,500,ground,strokeColor=colors.HexColor("#64748b")))
    drawing.add(String(20,215,"Winning geometry - setup frame",fontName="ReportBold",fontSize=11))
    return drawing


def fmt(value):
    if isinstance(value,float):return f"{value:.12g}"
    if isinstance(value,(dict,list)):return json.dumps(value,ensure_ascii=False)
    return str(value)

def create_report(folder,summary,config,original,metadata,samples):
    folder=Path(folder)
    fonts=Path(matplotlib.get_data_path())/"fonts/ttf"
    for name,file in (("Report","DejaVuSans.ttf"),("ReportBold","DejaVuSans-Bold.ttf")):
        if name not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
    styles=getSampleStyleSheet()
    for key in ("Normal","BodyText"):styles[key].fontName="Report";styles[key].fontSize=9;styles[key].leading=13
    styles["Title"].fontName="ReportBold";styles["Title"].fontSize=27;styles["Title"].leading=33
    styles["Heading1"].fontName="ReportBold";styles["Heading1"].fontSize=17;styles["Heading1"].leading=23;styles["Heading1"].spaceAfter=10
    styles["Heading2"].fontName="ReportBold";styles["Heading2"].fontSize=12;styles["Heading2"].leading=17
    small=ParagraphStyle("Small",parent=styles["BodyText"],fontSize=7.3,leading=10)
    def para(text,style="BodyText"):return Paragraph(escape(fmt(text)),styles[style])
    def table(rows,widths=None,header=False,compact=False):
        style=small if compact else styles["BodyText"]
        cells=[[Paragraph(escape(fmt(v)),style) for v in row] for row in rows]
        t=Table(cells,colWidths=widths or [170,345],repeatRows=1 if header else 0,hAlign="LEFT")
        commands=[("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
            ("TOPPADDING",(0,0),(-1,-1),2 if compact else 5),("BOTTOMPADDING",(0,0),(-1,-1),2 if compact else 5),
            ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white,colors.HexColor("#f5f7fb")]),
            ("LINEBELOW",(0,0),(-1,-1),.3,colors.HexColor("#e3e8f0"))]
        if header:commands += [("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e7efff"))]
        t.setStyle(TableStyle(commands));return t
    def figure(name):
        return Image(str(folder/"graphs"/(name+".png")),width=515,height=515*2160/3840)
    def footer(canvas,doc):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor("#dce3ee"))
        canvas.line(40,37,A4[0]-40,37);canvas.setFont("Report",7)
        canvas.setFillColor(colors.HexColor("#667085"))
        canvas.drawString(40,24,"Multi-element Optimizer | "+fmt(metadata.get("solver","JavaFoil"))+" | Saved design")
        canvas.drawRightString(A4[0]-40,24,f"Page {doc.page}");canvas.restoreState()
    story=[para("Optimized wing design","Title"),para("Complete design record | "+metadata["created"]),
           Spacer(1,12),para("Best Cl: "+fmt(summary["best"]["cl"]),"Heading1")]
    best=summary["best"];search=summary.get("search") or {}
    story += [table([[k,best.get(k)] for k in ("cl","cd","cm","lift_cl","downforce_cl")]),
        Spacer(1,10),para("Search outcome: "+str(search.get("termination","saved")).replace("_"," ")),
        para("The report uses the saved design and its original surface points. Images are saved at 3840 x 2160 pixels."),
        Spacer(1,12),geometry_drawing(samples,config),para("Coordinates and dimensions use the same setup frame as the saved CAD geometry.")]
    story += [PageBreak(),para("Setup dimensions","Heading1")]
    allpts=[(r["x_m"],r["y_m"]) for r in samples]
    story += [table([["Assembly width (mm)",(max(x for x,y in allpts)-min(x for x,y in allpts))*1000],
                     ["Assembly height (mm)",(max(y for x,y in allpts)-min(y for x,y in allpts))*1000],
                     ["Lift reference length (mm)",metadata["reference_chord_m"]*1000],
                     ["Relative airspeed (m/s)",metadata["speed_m_s"]],
                     ["Airspeed source",metadata["speed_source"]],
                     ["Ground effect",config["environment"].get("ground_effect",False)],
                     ["Flipped orientation",config["environment"].get("flip_for_downforce",False)],
                     ["Ground clearance (mm)",config["environment"].get("clearance_m",0)*1000 if config["environment"].get("ground_effect") else "Not applied"]])]
    for d in metadata["dimensions"]:
        labels={"element":"Airfoil","profile":"Profile","chord_m":"Chord (mm)","entered_angle_deg":"Entered angle (deg)",
            "angle_mode":"Angle mode","absolute_angle_deg":"Absolute angle (deg)","gap_m":"Slot gap (mm)",
            "overlap_m":"Overlap (mm)","reynolds":"Element Reynolds","x_min_m":"Minimum x (mm)","x_max_m":"Maximum x (mm)",
            "y_min_m":"Minimum y (mm)","y_max_m":"Maximum y (mm)","width_m":"Width (mm)","height_m":"Height (mm)"}
        story += [Spacer(1,12),para(f"Airfoil {d['element']}","Heading2"),
            table([[labels.get(key,key),fmt(value*1000) if key.endswith("_m") else value] for key,value in d.items()],
                  [170,345])]
        story.append(para("The CSV dimension file preserves lengths in metres."))
    story += [PageBreak(),para("Pressure and velocity distributions","Heading1"),
              para("Surface distributions are JavaFoil section-flow results. Empirical stall and finite-span corrections are separate."),
              Spacer(1,10),figure("pressure_coefficient"),Spacer(1,14),figure("velocity_distribution")]
    story += [PageBreak(),para("Winning simulation numbers","Heading1"),table([["Parameter","Value"],*list(best.items())],header=True)]
    from design_export import flatten
    for title,setup in (("Winning setup and settings",config),("Original setup and sweep ranges",original)):
        story += [PageBreak(),para(title,"Heading1"),table([["Parameter","Value"],*list(flatten(setup))],header=True,compact=True)]
    story += [PageBreak(),para("Search details and model notes","Heading1"),table([["Parameter","Value"],*list(flatten(search))],header=True,compact=True)]
    for text in summary.get("warnings",[]):story += [Spacer(1,8),para(text)]
    story += [Spacer(1,12),para("The graphs folder contains 4K PNG images of every graph in this report. Surface CSV data and solver records are included in data and analysis.")]
    for index in range(1,metadata["element_count"]+1):
        rows=[r for r in samples if r["element"]==index]
        story += [PageBreak(),para(f"Airfoil {index} - complete surface data","Heading1"),
                  para("Positions are millimetres in the setup frame. Surface speed uses the recorded relative airspeed. CSV files retain the full exported values."),
                  Spacer(1,10),table([["Point","Side","x (mm)","y (mm)","Cp","V / Vinf","V (m/s)"]]+
                      [[r["point"],r["surface"],r["x_m"]*1000,r["y_m"]*1000,r["cp"],r["velocity_ratio"],r["velocity_m_s"]] for r in rows],
                      [29,47,85,85,88,89,92],header=True,compact=True)]
    doc=SimpleDocTemplate(str(folder/"design_report.pdf"),pagesize=A4,rightMargin=40,leftMargin=40,topMargin=40,bottomMargin=50,
                          title="Optimized wing design",author="Wing optimizer")
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
