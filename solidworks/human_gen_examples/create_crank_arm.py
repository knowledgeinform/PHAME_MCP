import win32com.client
import pythoncom

# all dimensions in meters
post_diameter = 0.025
post_height = 0.050
center_to_center_distance = 0.1
arm_thickness = 0.01
hole_diameter = 0.006


swApp = win32com.client.Dispatch("SLDWORKS.Application")

template_path = "C:\\ProgramData\\SOLIDWORKS\\SOLIDWORKS 2024\\templates\\Part.prtdot"

swApp.NewDocument(template_path, 0, 0, 0)

Part = swApp.ActiveDoc
swView = swApp.ActiveDoc.ActiveView
swView.EnableGraphicsUpdate = False
Part.SetUserPreferenceToggle(249, False) #Disable snapping

# arm
boolstatus = Part.Extension.SelectByID2("Top", "PLANE", 0, 0, 0, False, 0, pythoncom.Nothing, 0)
Part.SketchManager.InsertSketch(True)
Part.ClearSelection2(True)
boolstatus = Part.SketchManager.CreateSketchSlot(0, 1, post_diameter, 0, 0, 0, 0, center_to_center_distance, 0, 0, 0, 0, 1, False)
Part.ClearSelection2(True)
Part.FeatureManager.FeatureExtrusion2(True, False, False, 0, 0, arm_thickness, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
Part.ClearSelection2(True)

# post 1
boolstatus = Part.Extension.SelectByRay(0, arm_thickness*2, 0, 0, -1, 0, arm_thickness*2, 2, False, 0, 0)
Part.SketchManager.InsertSketch(True)
Part.ClearSelection2(True)
skSegment = Part.SketchManager.CreateCircle(0, 0, 0, 0, post_diameter/2, 0)
Part.ClearSelection2(True)
Part.FeatureManager.FeatureExtrusion2(True, False, False, 0, 0, post_height, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
Part.ClearSelection2(True)

# post 1 hole
boolstatus = Part.Extension.SelectByRay(0, post_height+arm_thickness+.001, 0, 0, -1, 0, .002, 2, False, 0, 0)
Part.SketchManager.InsertSketch(True)
Part.ClearSelection2(True)
skSegment = Part.SketchManager.CreateCircle(0, 0, 0, 0, hole_diameter/2, 0)
Part.ClearSelection2(True)
myFeature = Part.FeatureManager.FeatureCut4(True, False, False, 1, 0, 0, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
Part.ClearSelection2(True)


# post 2
boolstatus = Part.Extension.SelectByRay((hole_diameter+post_diameter)/4, -.001, 0, 0, 1, 0, .002, 2, False, 0, 0)
Part.SketchManager.InsertSketch(True)
Part.ClearSelection2(True)
skSegment = Part.SketchManager.CreateCircle(0, -center_to_center_distance, 0, 0, -center_to_center_distance+post_diameter/2, 0)
Part.ClearSelection2(True)
Part.FeatureManager.FeatureExtrusion2(True, False, False, 0, 0, post_height, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
Part.ClearSelection2(True)

# post 2 hole
boolstatus = Part.Extension.SelectByRay(0, -post_height-.001, -center_to_center_distance, 0, 1, 0, .002, 2, False, 0, 0)
Part.SketchManager.InsertSketch(True)
Part.ClearSelection2(True)
skSegment = Part.SketchManager.CreateCircle(0, -center_to_center_distance, 0, 0, -center_to_center_distance+hole_diameter/2, 0)
Part.ClearSelection2(True)
myFeature = Part.FeatureManager.FeatureCut4(True, False, False, 1, 0, 0, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
Part.ClearSelection2(True)


swView.EnableGraphicsUpdate = True
