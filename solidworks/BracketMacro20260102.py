import win32com.client
import math

swApp = win32com.client.Dispatch("SldWorks.SldWorks")
swApp.Visible = True

def create_bracket():
    # Create new part
    swPart = swApp.NewPart()

    # Define parameters
    width = 0.0508  # 2 inches in meters
    height = 0.1016  # 4 inches in meters
    thickness = 0.00635  # 0.25 inches in meters
    hole_radius = 0.006  # 12mm bolt hole radius
    mount_hole_radius = 0.003  # 6mm mounting hole radius
    flange_reinforcement = 0.005  # 5mm flange reinforcement

    # Create base sketch
    swSketch = swPart.SketchManager
    swSketch.CreateSketchPlaneXY()

    # Draw hat channel outline
    swSketch.AddLine(0, 0, width, 0)
    swSketch.AddLine(width, 0, width, thickness)
    swSketch.AddLine(width, thickness, width - thickness, thickness)
    swSketch.AddLine(width - thickness, thickness, width - thickness, height - thickness)
    swSketch.AddLine(width - thickness, height - thickness, width, height - thickness)
    swSketch.AddLine(width, height - thickness, width, height)
    swSketch.AddLine(width, height, 0, height)
    swSketch.AddLine(0, height, 0, height - thickness)
    swSketch.AddLine(0, height - thickness, thickness, height - thickness)
    swSketch.AddLine(thickness, height - thickness, thickness, thickness)
    swSketch.AddLine(thickness, thickness, 0, thickness)
    swSketch.AddLine(0, thickness, 0, 0)

    # Sketch constraints
    swSketch.SetSketchType(1)

    # Extrude
    swPart.SketchManager.InsertSketch(True)
    swPart.SketchManager.ExitSketch()

    # Create extrusion feature
    swFeature = swPart.FeatureManager.FeatureExtrusion3(
        False, False, False, 0, 0, 0, 0.00635, 0, 0, False, False, False)

    # Add mounting holes
    swSketch = swPart.SketchManager
    swSketch.CreateSketchPlaneAtOffset(height/2, 0, 0)
    swSketch.AddCircle(width/4, 0, 0, mount_hole_radius, 0, 0)
    swSketch.AddCircle(3*width/4, 0, 0, mount_hole_radius, 0, 0)
    swPart.SketchManager.InsertSketch(True)
    swPart.SketchManager.ExitSketch()

    # Cut holes
    swFeature = swPart.FeatureManager.FeatureCut3(
        False, False, False, 0, 0, mount_hole_radius*2, 0, 0.001, False, False, False)

    # Add bolt holes with flange reinforcement
    swSketch = swPart.SketchManager
    swSketch.CreateSketchPlaneAtOffset(0, 0, 0)
    swSketch.AddCircle(width/2, height/2, 0, hole_radius, 0, 0)
    swPart.SketchManager.InsertSketch(True)
    swPart.SketchManager.ExitSketch()

    # Cut bolt hole with reinforcement
    swFeature = swPart.FeatureManager.FeatureCut3(
        False, False, False, 0, 0, hole_radius*2, 0, 0.001, False, False, False)

    # Update graphics
    swPart.ForceFeatureRebuild3(swPart.GetActiveFeature(), True)

    # Material properties
    swMaterial = swPart.MaterialPropertyValues3
    swMaterial[0] = "Carbon Steel"
    swMaterial[1] = "AISI 1080"
    swMaterial[2] = 7.85e3  # Density kg/m^3
    swMaterial[3] = 590e6   # Yield Strength MPa
    swPart.SetMaterialPropertyValues3(0, swMaterial)

    # Tolerance note according to ASCE 7-22
    swNote = swPart.CreateAnnotation()
    swNote.SetText("ASCE 7-22 Tolerances: ±0.5mm for dimensions")

    # Export as SLDPRT
    swPart.SaveAs("C:\\Temp\\Bracket.sldprt")