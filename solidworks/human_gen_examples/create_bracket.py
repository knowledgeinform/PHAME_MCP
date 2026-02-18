import win32com.client
import pythoncom

# all dimensions in meters
width = 0.025
height = 0.075
length = 0.150
thickness = 0.006
hole_diameter = 0.003
vertical_hole_spacing = height/2
horizontal_hole_spacing = length/2

swApp = win32com.client.Dispatch("SLDWORKS.Application")

template_path = "C:\\ProgramData\\SOLIDWORKS\\SOLIDWORKS 2024\\templates\\Part.prtdot"

swApp.NewDocument(template_path, 0, 0, 0)

Part = swApp.ActiveDoc
swView = swApp.ActiveDoc.ActiveView
swView.EnableGraphicsUpdate = False
Part.SetUserPreferenceToggle(249, False) #Disable snapping

# vertical plate
boolstatus = Part.Extension.SelectByID2("Front", "PLANE", 0, 0, 0, False, 0, pythoncom.Nothing, 0)
Part.SketchManager.InsertSketch(True)
Part.ClearSelection2(True)
boolstatus = Part.Extension.SetUserPreferenceToggle(584, 0, False) # 584 = swUserPreferenceToggle_e.swSketchAddConstToRectEntity
boolstatus = Part.Extension.SetUserPreferenceToggle(585, 0, True) # 585 = swUserPreferenceToggle_e.swSketchAddConstLineDiagonalType
skSegment = Part.SketchManager.CreateCornerRectangle(0, 0, 0, width, height, 0)
Part.ClearSelection2(True)
Part.FeatureManager.FeatureExtrusion2(True, False, False, 0, 0, thickness, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
Part.ClearSelection2(True)


# horizontal plate
boolstatus = Part.Extension.SelectByRay(width/2, height/2, thickness*2, 0, 0, -1, thickness*2, 2, False, 0, 0)
Part.SketchManager.InsertSketch(True)
Part.ClearSelection2(True)
boolstatus = Part.Extension.SetUserPreferenceToggle(584, 0, False) # 584 = swUserPreferenceToggle_e.swSketchAddConstToRectEntity
boolstatus = Part.Extension.SetUserPreferenceToggle(585, 0, True) # 585 = swUserPreferenceToggle_e.swSketchAddConstLineDiagonalType
# pt = Part.SketchManager.CreatePoint(0, height, 0)
# pt2 = Part.SketchManager.CreatePoint(width, height-thickness, 0)
skSegment = Part.SketchManager.CreateCornerRectangle(0, height, 0, width, height-thickness, 0)
Part.ClearSelection2(True)
Part.FeatureManager.FeatureExtrusion2(True, False, False, 0, 0, length, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
Part.ClearSelection2(True)

# angle brace
boolstatus = Part.Extension.SelectByRay(-width, height/2, thickness/2, 1, 0, 0, width*2, 2, False, 0, 0)
Part.SketchManager.InsertSketch(True)
Part.ClearSelection2(True)
skSegment = Part.SketchManager.CreateLine(thickness, 0, 0, length+thickness, height-thickness, 0)
skSegment = Part.SketchManager.CreateLine(length+thickness, height-thickness, 0, thickness, height-thickness, 0)
skSegment = Part.SketchManager.CreateLine(thickness, height-thickness, 0, thickness, 0, 0)
Part.SketchManager.ActiveSketch.MergePoints(0.001)
Part.ClearSelection2(True)
Part.FeatureManager.FeatureExtrusion2(True, False, True, 0, 0, thickness, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
Part.ClearSelection2(True)

# holes in vertical plate
boolstatus = Part.Extension.SelectByRay(width/2, height/2, thickness*2, 0, 0, -1, thickness*2, 2, False, 0, 0)
Part.SketchManager.InsertSketch(True)
Part.ClearSelection2(True)
hole_offset = (height-vertical_hole_spacing)/2
skSegment = Part.SketchManager.CreateCircle(width/2, hole_offset, 0, width/2, hole_offset+hole_diameter/2, 0)
skSegment = Part.SketchManager.CreateCircle(width/2, hole_offset+vertical_hole_spacing, 0, width/2, hole_offset+vertical_hole_spacing+hole_diameter/2, 0)
myFeature = Part.FeatureManager.FeatureCut4(True, False, False, 1, 0, 0, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
Part.ClearSelection2(True)

#holes in horizontal plate
boolstatus = Part.Extension.SelectByRay(width/2, height*2, length/2, 0, -1, 0, height*2, 2, False, 0, 0)
Part.SketchManager.InsertSketch(True)
Part.ClearSelection2(True)
hole_offset = (length-horizontal_hole_spacing)/2
skSegment = Part.SketchManager.CreateCircle(width/2, -hole_offset, 0, width/2, -(hole_offset+hole_diameter/2), 0)
skSegment = Part.SketchManager.CreateCircle(width/2, -(hole_offset+horizontal_hole_spacing), 0, width/2, -(hole_offset+horizontal_hole_spacing+hole_diameter/2), 0)
myFeature = Part.FeatureManager.FeatureCut4(True, False, False, 1, 0, 0, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
Part.ClearSelection2(True)

swView.EnableGraphicsUpdate = True
