# --------------------------------------------------------------
# SolidWorks Python macro –  Wall‑Mounted Bracket
# --------------------------------------------------------------
#  • 4" × 4" back plate
#  • 3" leg height, 1.5" leg width
#  • 0.25" overall thickness (cold‑formed 1018 steel)
#  • 3 wall‑mounting holes (Ø0.25", 5/16‑16) – spaced 2" apart,
#    offset 0.5" from each edge
#  • 2 shelf‑support holes (Ø0.25", 5/16‑13) on top of leg
#  • 0.125" fillets on all outer edges
#  • Material tag: “Cold‑formed 1018 steel, 0.25 in thickness”
# --------------------------------------------------------------

import win32com.client
import pythoncom

# -----------------------------------------------------------------
# 1.  USER‑DEFINED DIMENSIONS  (all values in meters)
# -----------------------------------------------------------------
inch = 0.0254
width          = 4  * inch   # back‑plate width  (4")
height         = 4  * inch   # back‑plate height (4")
leg_height     = 3  * inch   # leg protrusion    (3")
leg_width      = 1.5* inch   # leg width
thickness      = 0.25* inch   # plate thickness
hole_dia       = 0.25* inch   # clearance hole dia.
hole_spacing   = 2   * inch   # spacing of wall‑holes
edge_offset    = 0.5 * inch   # offset of wall‑holes from edges
fillet_rad     = 0.125* inch   # fillet radius

# -----------------------------------------------------------------
# 2.  Connect to SolidWorks and create a new part document
# -----------------------------------------------------------------
swApp = win32com.client.Dispatch("SldWorks.Application")
# (adjust the template path if your installation differs)
tpl = r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\Part.prtdot"
swApp.NewDocument(tpl, 0, 0, 0)
part = swApp.ActiveDoc
view = part.ActiveView
view.EnableGraphicsUpdate = False          # speed up macro execution
part.SetUserPreferenceToggle(249, False)   # turn off snapping

# -----------------------------------------------------------------
# 3.  Helper – exit a sketch cleanly
# -----------------------------------------------------------------
def exit_sketch():
    part.SketchManager.InsertSketch(False)   # leave sketch mode
    part.ClearSelection2(True)

# -----------------------------------------------------------------
# 4.  Create the back plate (4" × 4")
# -----------------------------------------------------------------
part.Extension.SelectByID2("Front Plane", "PLANE", 0, 0, 0, False, 0, None, 0)
part.SketchManager.InsertSketch(True)
part.SketchManager.CreateCornerRectangle(0, 0, 0, width, height, 0)
exit_sketch()
# Extrude to required thickness
part.FeatureManager.FeatureExtrusion2(
    True,          # Direction 1 = true
    False,         # Direction 2 = false
    False,         # Both sides = false
    0,             # End condition = 0 (Blind)
    0,             # End condition2 (ignored)
    thickness,     # Depth1
    0,             # Depth2 (ignored)
    False, False, False, False,
    0, 0,
    False, False, False, False,
    True, True, True,   # Merge result, Auto select, Create feature
    0, 0, False)

# -----------------------------------------------------------------
# 5.  Add the leg (3" high, 1.5" wide) – same thickness
# -----------------------------------------------------------------
# Sketch on the back‑plate face (the front face of the already‑extruded plate)
part.Extension.SelectByRay(width/2, height/2, thickness*2, 0, 0, -1,
                           thickness*2, 2, False, 0, 0)
part.SketchManager.InsertSketch(True)
# Leg rectangle – placed centred on the back‑plate, extending outward
part.SketchManager.CreateCornerRectangle(0, 0, 0, width, leg_height, 0)
exit_sketch()
# Extrude the leg outward (same thickness)
part.FeatureManager.FeatureExtrusion2(
    True, False, False, 0, 0, thickness, 0,
    False, False, False, False, 0, 0,
    False, False, False, False,
    True, True, True, 0, 0, False)

# -----------------------------------------------------------------
# 6.  Create the three wall‑mounting holes (Ø0.25")
# -----------------------------------------------------------------
part.Extension.SelectByRay(width/2, height/2, thickness*2, 0, 0, -1,
                           thickness*2, 2, False, 0, 0)
part.SketchManager.InsertSketch(True)

# Left hole
part.SketchManager.CreateCircle(edge_offset, edge_offset, 0,
                                edge_offset, edge_offset + hole_dia/2, 0)
# Center hole
part.SketchManager.CreateCircle(width/2, edge_offset, 0,
                                width/2, edge_offset + hole_dia/2, 0)
# Right hole
part.SketchManager.CreateCircle(width - edge_offset, edge_offset, 0,
                                width - edge_offset, edge_offset + hole_dia/2, 0)

exit_sketch()
# Cut the holes straight through the full thickness
part.FeatureManager.FeatureCut4(
    True,          # Direction 1 = true
    False, False,  # Direction 2 & both sides
    1,             # End condition = 1 (Blind)
    0,
    thickness,     # Depth
    0,
    False, False, False, False,
    0, 0,
    False, False, False, False,
    False,
    True, True, True, True,   # Create feature, Auto select, Resolve, Keep body
    False, 0, 0, False, False)

# -----------------------------------------------------------------
# 7.  Create the two shelf‑support holes on top of the leg
# -----------------------------------------------------------------
# The Y‑coordinate of the top of the leg (back‑plate origin is at the centre of the plate)
y_top = height + leg_height   # back‑plate height + leg height

part.Extension.SelectByRay(width/2, 0, 0, 0, 1, 0,
                           thickness*2, 2, False, 0, 0)
part.SketchManager.InsertSketch(True)

# Left support hole
part.SketchManager.CreateCircle(edge_offset, y_top - edge_offset, 0,
                                edge_offset, y_top - edge_offset + hole_dia/2, 0)
# Right support hole
part.SketchManager.CreateCircle(width - edge_offset, y_top - edge_offset, 0,
                                width - edge_offset, y_top - edge_offset + hole_dia/2, 0)

exit_sketch()
# Cut through the full thickness
part.FeatureManager.FeatureCut4(
    True, False, False, 1, 0, thickness, 0,
    False, False, False, False, 0, 0,
    False, False, False, False,
    False,
    True, True, True, True, False, 0, 0, False, False)

# -----------------------------------------------------------------
# 8.  Apply a 0.125‑in fillet to all outer edges
# -----------------------------------------------------------------
part.FeatureManager.FeatureFillet2(
    fillet_rad,       # radius
    False, False,    # select edge, reverse direction, etc.
    True, True, False, True,
    [True, True, True],                # apply to all selected edges
    [fillet_rad, fillet_rad, fillet_rad],
    [])

# -----------------------------------------------------------------
# 9.  Assign material (just a tag – no database lookup needed)
# -----------------------------------------------------------------
material_name = "Cold‑formed 1018 steel, 0.25 in thickness"
part.SetMaterialPropertyName2("", "", material_name)

# -----------------------------------------------------------------
# 10.  Save the part and clean up
# -----------------------------------------------------------------
part.SaveAs("Bracket.sldprt")
view.EnableGraphicsUpdate = True      # re‑enable graphics
print("Macro finished – Bracket.sldprt created.")