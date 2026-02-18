import win32com.client
import pythoncom

exec(open("create_bracket.py").read())

# dimensions defined in create_bracket.py
# width = 0.025
# height = 0.075
# length = 0.150
# thickness = 0.006
# hole_diameter = 0.003
# vertical_hole_spacing = height/2
# horizontal_hole_spacing = length/2

load = 100 #Newtons


errorarg = win32com.client.VARIANT(16387, 0)
swApp = win32com.client.Dispatch("SLDWORKS.Application")
Part = swApp.ActiveDoc

CWAddinCallBackObj = swApp.GetAddInObject("CosmosWorks.CosmosWorks")
COSMOSWORKSObj = CWAddinCallBackObj.COSMOSWORKS
ActiveDocObj = COSMOSWORKSObj.ActiveDoc
StudyManagerObj = ActiveDocObj.StudyManager
StudyManagerObj.ActiveStudy = 0
CWNewStudy = StudyManagerObj.CreateNewStudy3("Static 1", 0, 0, errorarg)
StudyObj = StudyManagerObj.GetStudy(0)


#apply material
solidBodyEnum = 76
boolstatus = Part.Extension.SelectByRay(width/2, height/2, -.001, 0, 0, 1, .002, solidBodyEnum, False, 0, 0)
SolidManagerObj = StudyObj.SolidManager
SolidManagerObj.SetLibraryMaterialToSelectedEntities("solidworks materials", "Alloy Steel")
Part.ClearSelection2(True)

#apply fixed constraint
Part.ClearSelection2(True)
boolstatus = Part.Extension.SelectByRay(width/2, height/2, -.001, 0, 0, 1, .002, 2, False, 0, 0)
LoadsAndRestraintsManagerObj = StudyObj.LoadsAndRestraintsManager
DispatchObj1 = Part.SelectionManager.GetSelectedObject6(1, -1)
DispArray = [DispatchObj1]
CWRestraintObj = LoadsAndRestraintsManagerObj.AddRestraint(0, DispArray, pythoncom.Nothing, errorarg)
Part.ClearSelection2(True)

#apply load
boolstatus = Part.Extension.SelectByRay(width/2, height+.001, thickness/2, 0, -1, 0, .002, 2, False, 0, 0)
LoadsAndRestraintsManagerObj = StudyObj.LoadsAndRestraintsManager
DispatchObj1 = Part.SelectionManager.GetSelectedObject6(1, -1)
DispArray = [DispatchObj1]
DistanceValues = 0
ForceValues = 0 #unused, force is the 14th argument of AddForce3
ComponentValues = [1, 1, 1, 1, 1, 1]
LoadsAndRestraintsManagerObj.AddForce3(1, 0, -1, 0, 0, 0, DistanceValues, ForceValues, 0, False, 0, 0, 0, load, ComponentValues, False, False, DispArray, pythoncom.Nothing, False, errorarg)
Part.ClearSelection2(True)

# run study
StudyObj.CreateMesh(2, 0.00802876, 0.00114805)
StudyObj.RunAnalysis

#postprocess
Results = StudyObj.Results
displacement = Results.GetMinMaxDisplacement(3, 1, pythoncom.Nothing, 0, errorarg)
print("Max displacement: " + f"{(displacement[3]*1000.0):.2f}" + " mm")
stress = Results.GetMinMaxStress(9, 0, 1, pythoncom.Nothing, 0, errorarg)
print("Max stress: " + f"{(stress[3]/1000.0):.1f}" + " kPa")