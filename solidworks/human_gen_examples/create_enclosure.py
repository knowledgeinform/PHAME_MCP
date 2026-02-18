import win32com.client
import pythoncom

# all dimensions in meters
width = 0.1
length = 0.150
height = 0.05
thickness = 0.006
hole_diameter = 0.003

swApp = win32com.client.Dispatch("SLDWORKS.Application")

template_path = "C:\\ProgramData\\SOLIDWORKS\\SOLIDWORKS 2024\\templates\\Part.prtdot"

swApp.NewDocument(template_path, 0, 0, 0)

Part = swApp.ActiveDoc
swView = swApp.ActiveDoc.ActiveView
swView.EnableGraphicsUpdate = False
Part.SetUserPreferenceToggle(249, False) #Disable snapping

# box to be shelled
boolstatus = Part.Extension.SelectByID2("Top", "PLANE", 0, 0, 0, False, 0, pythoncom.Nothing, 0)
Part.SketchManager.InsertSketch(True)
Part.ClearSelection2(True)
boolstatus = Part.Extension.SetUserPreferenceToggle(584, 0, True) # 584 = swUserPreferenceToggle_e.swSketchAddConstToRectEntity
boolstatus = Part.Extension.SetUserPreferenceToggle(585, 0, True) # 585 = swUserPreferenceToggle_e.swSketchAddConstLineDiagonalType
skSegment = Part.SketchManager.CreateCornerRectangle(-width/2, -length/2, 0, width/2, length/2, 0)
Part.ClearSelection2(True)
Part.FeatureManager.FeatureExtrusion2(True, False, False, 0, 0, height, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
Part.ClearSelection2(True)


# box corner holes
boolstatus = Part.Extension.SelectByRay(0, height*2, 0, 0, -1, 0, height*2, 2, False, 0, 0)
Part.SketchManager.InsertSketch(True)
Part.ClearSelection2(True)
skSegment = Part.SketchManager.CreateCircle(-width/2+hole_diameter, -length/2+hole_diameter, 0, -width/2+hole_diameter/2, -length/2+hole_diameter, 0)
skSegment = Part.SketchManager.CreateCircle(-width/2+hole_diameter, length/2-hole_diameter, 0, -width/2+hole_diameter/2, length/2-hole_diameter, 0)
skSegment = Part.SketchManager.CreateCircle(width/2-hole_diameter, -length/2+hole_diameter, 0, width/2-hole_diameter/2, -length/2+hole_diameter, 0)
skSegment = Part.SketchManager.CreateCircle(width/2-hole_diameter, length/2-hole_diameter, 0, width/2-hole_diameter/2, length/2-hole_diameter, 0)
Part.ClearSelection2(True)
myFeature = Part.FeatureManager.FeatureCut4(True, False, False, 1, 0, 0, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
Part.ClearSelection2(True)

#shell
boolstatus = Part.Extension.SelectByRay(0, height*2, 0, 0, -1, 0, height*2, 2, False, 0, 0)
Part.InsertFeatureShell(thickness, False)
Part.ClearSelection2(True)


#box fillets
boolstatus = Part.Extension.SelectByRay(-width/2, height/2, length+.001, 0, 0, -1, .002, 1, False, 0, 0)
boolstatus = Part.Extension.SelectByRay(-width/2, height/2, -length-.001, 0, 0, 1, .002, 1, True, 0, 0)
boolstatus = Part.Extension.SelectByRay(width/2, height/2, length+.001, 0, 0, -1, .002, 1, True, 0, 0)
boolstatus = Part.Extension.SelectByRay(width/2, height/2, -length-.001, 0, 0, 1, .002, 1, True, 0, 0)

swFeatData = Part.FeatureManager.CreateDefinition(1) #1=fillet
swFeatData.Initialize(0) #0=constant radius fillet

edgeArray=[None]*4
edgeArray[0] = Part.SelectionManager.GetSelectedObject6(1,1)
edgeArray[1] = Part.SelectionManager.GetSelectedObject6(2,1)
edgeArray[2] = Part.SelectionManager.GetSelectedObject6(3,1)
edgeArray[3] = Part.SelectionManager.GetSelectedObject6(4,1)
swFeatData.Edges = edgeArray

swFeatData.AsymmetricFillet = False
swFeatData.DefaultRadius = hole_diameter
swFeatData.ConicTypeForCrossSectionProfile = 0
swFeatData.CurvatureContinuous = False
swFeatData.ConstantWidth = hole_diameter
swFeatData.IsMultipleRadius = False
swFeatData.OverflowType = 0

Part.FeatureManager.CreateFeature(swFeatData)



# lid
boolstatus = Part.Extension.SelectByRay(0, height+.001, length/2-hole_diameter/2, 0, -1, 0, .002, 2, False, 0, 0)
Part.SketchManager.InsertSketch(True)
Part.ClearSelection2(True)
boolstatus = Part.Extension.SetUserPreferenceToggle(584, 0, True) # 584 = swUserPreferenceToggle_e.swSketchAddConstToRectEntity
boolstatus = Part.Extension.SetUserPreferenceToggle(585, 0, True) # 585 = swUserPreferenceToggle_e.swSketchAddConstLineDiagonalType
skSegment = Part.SketchManager.CreateCornerRectangle(-width/2, -length/2, 0, width/2, length/2, 0)
Part.ClearSelection2(True)
Part.FeatureManager.FeatureExtrusion2(True, False, False, 0, 0, thickness, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, 0, 0, False)
Part.ClearSelection2(True)

# lid corner holes
boolstatus = Part.Extension.SelectByRay(0, height*2, 0, 0, -1, 0, height*2, 2, False, 0, 0)
Part.SketchManager.InsertSketch(True)
Part.ClearSelection2(True)
skSegment = Part.SketchManager.CreateCircle(-width/2+hole_diameter, -length/2+hole_diameter, 0, -width/2+hole_diameter/2, -length/2+hole_diameter, 0)
skSegment = Part.SketchManager.CreateCircle(-width/2+hole_diameter, length/2-hole_diameter, 0, -width/2+hole_diameter/2, length/2-hole_diameter, 0)
skSegment = Part.SketchManager.CreateCircle(width/2-hole_diameter, -length/2+hole_diameter, 0, width/2-hole_diameter/2, -length/2+hole_diameter, 0)
skSegment = Part.SketchManager.CreateCircle(width/2-hole_diameter, length/2-hole_diameter, 0, width/2-hole_diameter/2, length/2-hole_diameter, 0)
Part.ClearSelection2(True)
myFeature = Part.FeatureManager.FeatureCut4(True, False, False, 2, 0, 0, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
Part.ClearSelection2(True)

#lid fillets
boolstatus = Part.Extension.SelectByRay(-width/2, height+thickness/2, length+.001, 0, 0, -1, .002, 1, False, 0, 0)
boolstatus = Part.Extension.SelectByRay(-width/2, height+thickness/2, -length-.001, 0, 0, 1, .002, 1, True, 0, 0)
boolstatus = Part.Extension.SelectByRay(width/2, height+thickness/2, length+.001, 0, 0, -1, .002, 1, True, 0, 0)
boolstatus = Part.Extension.SelectByRay(width/2, height+thickness/2, -length-.001, 0, 0, 1, .002, 1, True, 0, 0)

swFeatData = Part.FeatureManager.CreateDefinition(1) #1=fillet
swFeatData.Initialize(0) #0=constant radius fillet

edgeArray=[None]*4
edgeArray[0] = Part.SelectionManager.GetSelectedObject6(1,1)
edgeArray[1] = Part.SelectionManager.GetSelectedObject6(2,1)
edgeArray[2] = Part.SelectionManager.GetSelectedObject6(3,1)
edgeArray[3] = Part.SelectionManager.GetSelectedObject6(4,1)
swFeatData.Edges = edgeArray

swFeatData.AsymmetricFillet = False
swFeatData.DefaultRadius = hole_diameter
swFeatData.ConicTypeForCrossSectionProfile = 0
swFeatData.CurvatureContinuous = False
swFeatData.ConstantWidth = hole_diameter
swFeatData.IsMultipleRadius = False
swFeatData.OverflowType = 0

Part.FeatureManager.CreateFeature(swFeatData)



swView.EnableGraphicsUpdate = True