# -------------------------------------------------------------
# SolidWorks Python macro – ¼‑in (6 mm) steel L‑bracket
# -------------------------------------------------------------
# Tested with SolidWorks 2024 + Python 3.11 + pywin32
# -------------------------------------------------------------

import win32com.client
import os

# -----------------------------------------------------------------
# 0️⃣ USER‑CONFIGURABLE PARAMETERS (all dimensions in metres)
# -----------------------------------------------------------------
base_len        = 0.0762      # 3 in – horizontal base length
vert_len        = 0.1524      # 6 in – vertical arm height
thick           = 0.00635     # 0.25 in – material thickness
rib_width       = 0.0127      # 0.5 in – rib width
rib_thick       = 0.003175    # 0.125 in – rib thickness
rib_offset      = 0.0508      # 2 in – distance up from the base where ribs start
clear_hole_diam = 0.00635     # ¼ in – clearance hole for the shelf
screw_hole_diam = 0.003175    # #10‑16 screw hole (~3.2 mm)
h_spacing       = 0.0127      # 0.5 in – horizontal spacing of the T‑pattern
v_spacing       = 0.01905     # 0.75 in – vertical spacing of the T‑pattern
screw_depth     = 0.0127      # 0.5 in – depth of wall‑mount holes

# -----------------------------------------------------------------
# 1️⃣ Launch SolidWorks and open a new part document
# -----------------------------------------------------------------
swApp = win32com.client.Dispatch("SldWorks.Application")
swApp.Visible = True

# Default part template – change if your installation uses a different path
tpl = r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\Part.prtdot"
swApp.NewDocument(tpl, 0, 0, 0)          # 0 = default configuration
part = swApp.ActiveDoc
view = part.ActiveView
view.EnableGraphicsUpdate = False       # speeds up geometry creation

# -----------------------------------------------------------------
# 2️⃣ Helper: sketch a rectangle on a plane and extrude it
# -----------------------------------------------------------------
def sketch_and_extrude(plane_name: str, length: float, height: float, thickness: float):
    """
    Sketches a rectangle on the given plane (origin at lower‑left corner)
    and extrudes it to the supplied thickness.
    """
    # Select the plane – Mark, Callout, Data, Config = 0
    part.Extension.SelectByID2(plane_name, "PLANE", 0, 0, 0,
                               0, 0, 0, 0)

    # Start sketch
    part.SketchManager.InsertSketch(True)

    # Draw rectangle
    part.SketchManager.CreateCornerRectangle(0, 0, 0,
                                             length, height, 0)

    # Finish sketch
    part.SketchManager.ActiveSketch.Deactivate()
    part.ClearSelection2(True)

    # Blind extrude to the required thickness
    part.FeatureManager.FeatureExtrusion2(
        True,       # Direction 1 = blind
        False,      # Direction 2 = none
        False,      # Draft while 1 = no
        0, 0,       # End condition type (0=blind) + direction (ignored)
        thickness,  # Depth of extrusion
        0,          # Depth of second direction (not used)
        False, False, False, False,   # Draft options
        0, 0,                       # Draft angles (0)
        False, False, False, False,  # Merge, keep bodies, etc.
        False,                       # Auto‑select
        True, True, True,            # Keep bodies, merge result, visible
        0, 0, False)                 # Configuration stuff

# -----------------------------------------------------------------
# 3️⃣ Build the L‑bracket geometry
# -----------------------------------------------------------------
# 3.1 Horizontal base (lies on the Front Plane)
sketch_and_extrude("Front Plane", base_len, thick, thick)

# 3.2 Vertical arm (extrude from the Right Plane)
part.Extension.SelectByID2("Right Plane", "PLANE", 0, 0, 0,
                           0, 0, 0, 0)
part.SketchManager.InsertSketch(True)
part.SketchManager.CreateCornerRectangle(0, 0, 0,
                                         thick, vert_len, 0)
part.SketchManager.ActiveSketch.Deactivate()
part.ClearSelection2(True)

# Extrude the vertical arm outward (+X) by the base length
part.FeatureManager.FeatureExtrusion2(
    True, False, False,
    0, 0,
    base_len, 0,
    False, False, False, False,
    0, 0,
    False, False, False,
    False, True, True,
    True, 0, 0, False)

# -----------------------------------------------------------------
# 4️⃣ Optional reinforcement ribs (both sides of the vertical arm)
# -----------------------------------------------------------------
# 4.1 Sketch a rib on the front face of the vertical arm
part.Extension.SelectByRay(0, rib_offset, 0,      # start point (X,Y,Z)
                           0, 0, -1,          # direction (toward back face)
                           thick, 0, False, 0, 0)
part.SketchManager.InsertSketch(True)

part.SketchManager.CreateCornerRectangle(0, 0, 0,
                                         rib_width, rib_thick, 0)

part.SketchManager.ActiveSketch.Deactivate()
part.ClearSelection2(True)

# Extrude the rib through the thickness of the vertical arm
part.FeatureManager.FeatureExtrusion2(
    True, False, False,
    0, 0,
    thick, 0,
    False, False, False, False,
    0, 0,
    False, False, False,
    False, True, True,
    True, 0, 0, False)

# 4.2 Mirror the rib to the opposite side of the vertical arm
# ---------------------------------------------------------
# Mirror about the Front Plane (its normal points +X)
part.Extension.SelectByID2("Front Plane", "PLANE", 0, 0, 0,
                           0, 0, 0, 0)

# Get the most‑recent feature (the rib we just extruded)
last_feat = part.FeatureManager.GetLastFeatureAdded()
if last_feat is not None:
    part.FeatureManager.InsertMirrorFeature2(
        last_feat.Name,               # feature to mirror
        (1, 0, 0),                  # normal of the mirror plane (X‑axis)
        (0, 0, 0),                  # a point on the plane (origin)
        False, False, False, False) # keep pattern options off

# -----------------------------------------------------------------
# 5️⃣ T‑pattern wall‑mount holes on the rear face of the vertical arm
# -----------------------------------------------------------------
part.Extension.SelectByID2("Rear Plane", "PLANE", 0, 0, 0,
                           0, 0, 0, 0)
part.SketchManager.InsertSketch(True)

cx = thick / 2.0    # centre X of the vertical arm
cy = 0.0            # base Y

# Bottom row – three holes (spacing = h_spacing)
for i in range(-1, 2):                 # -1, 0, +1
    x = cx + i * h_spacing
    part.SketchManager.CreateCircleByRadius(x, cy, 0,
                                            screw_hole_diam / 2.0)

# Top row – two holes, shifted upward by v_spacing and centred between bottom holes
y_top = v_spacing
for i in range(0, 2):                  # 0, 1
    x = cx + (i - 0.5) * h_spacing
    part.SketchManager.CreateCircleByRadius(x,
                                            y_top, 0,
                                            screw_hole_diam / 2.0)

part.SketchManager.ActiveSketch.Deactivate()
part.ClearSelection2(True)

# Cut the holes (through‑all)
part.Extension.SelectByID2("Sketch1", "SKETCH", 0, 0, 0,
                           0, 0, 0, 0)
part.FeatureManager.FeatureCut4(
    True,        # direction 1 = blind (through‑all)
    False,       # direction 2 = none
    False,       # reverse = false
    1,           # cut‑type = through‑all
    0,           # depth (ignored when through‑all)
    screw_depth, # depth of the first direction (safety)
    0,           # second depth
    False, False, False, False,
    0, 0,
    False, False, False,
    False, False, True,
    True, True, True,
    True, False, 0, 0,
    False, False)

# -----------------------------------------------------------------
# 6️⃣ Clearance hole on the top of the horizontal base
# -----------------------------------------------------------------
part.Extension.SelectByRay(base_len/2, thick, 0,   # start point
                           0, 0, -1,            # look downwards
                           0.001, 0, False, 0, 0)
part.SketchManager.InsertSketch(True)

part.SketchManager.CreateCircleByRadius(base_len/2,
                                        thick/2,
                                        0,
                                        clear_hole_diam/2)

part.SketchManager.ActiveSketch.Deactivate()
part.ClearSelection2(True)

# Cut the clearance hole (through‑all)
part.Extension.SelectByID2("Sketch2", "SKETCH", 0, 0, 0,
                           0, 0, 0, 0)
part.FeatureManager.FeatureCut4(
    True, False, False,
    1, 0, 0, 0,
    False, False, False, False,
    0, 0,
    False, False, False,
    False, False, True,
    True, True, True,
    True, False, 0, 0,
    False, False)

# -----------------------------------------------------------------
# 7️⃣ Material & Appearance
# -----------------------------------------------------------------
material_name    = "AISI 1018"   # cold‑rolled steel
appearance_name = "Zinc"        # built‑in zinc‑plating appearance

# Apply material
part.Extension.SelectByID2("", "COMPONENT", 0, 0, 0,
                           0, 0, 0, 0)
part.SetMaterialPropertyName2(
    "",                 # empty component name = the part itself
    material_name,
    "Default",          # property set
    0)                  # configuration index

# Apply appearance (surface colour)
part.ChangeAppearance2(appearance_name, "", 0, "", 0)

# -----------------------------------------------------------------
# 8️⃣ Save the part on the Desktop
# -----------------------------------------------------------------
save_folder = os.path.expanduser(r"~\Desktop")
save_path   = os.path.join(save_folder, "Bracket.SLDPRT")
part.SaveAs3(save_path, 0, 0)   # 0 = silent, 0 = errors only

# -----------------------------------------------------------------
# 9️⃣ Clean‑up & finish
# -----------------------------------------------------------------
view.EnableGraphicsUpdate = True
swApp.SendMsgToUser2(f"✅ Bracket created and saved to:\n{save_path}",
                     0, 0)

# End of macro