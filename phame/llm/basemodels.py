from pydantic import BaseModel, Field
class DesignCode(BaseModel):
    title: str = Field(..., description="Short part name")
    rationale: str = Field(..., description="1-3 bullet lines, no internal reasoning")
    cad_code: str = Field(..., description="Complete, runnable parametric code with defined parameters")

class DesignPlan(BaseModel):
    title: str = Field(..., description="Short part name")
    rationale: str = Field(..., description="1-3 bullet lines, no internal reasoning")
    plan: str = Field(..., description="A step-by-step plan for making the part in parametric CAD.")

class DesignPlanCritic(DesignPlan):
    issues: str = Field(..., description="List of issues found in original plan.")
    rationale: str = Field(..., description="Rationale for each issue listed under `issues`.")
    fix: str = Field(..., description="List of fixes for each issue.")

class DesignCodeCritic(DesignCode):
    issues: str = Field(..., description="List of issues found in original code.")
    rationale: str = Field(..., description="Rationale for each issue listed under `issues`.")
    fix: str = Field(..., description="List of fixes for each issue.")

class AnalysisCode(BaseModel):
    title: str = Field(..., description="Short part name")
    rationale: str = Field(..., description="1-3 bullet lines, no internal reasoning")
    cad_path: str = Field(..., description="Path to CAD part")
    analysis_code: str = Field(..., description="Complete, runnable PyAnsys Code for running structural/load bearing, fluids, thermal, and/or electro-magnetic analysis.")

class AnalysisPlan(BaseModel):
    title: str = Field(..., description="Short part name")
    rationale: str = Field(..., description="1-3 bullet lines, no internal reasoning")
    cad_path: str = Field(..., description="Path to CAD part")
    analysis_design: str = Field(..., description="Complete description of all boundary conditions, experiment settings, and constraints for testing the structural/load bearing, fluids, thermal, and/or electro-magnetic integrity of provided part.")
    boundary_conditions: str = Field(..., description="Bulleted list of boundary conditions.")
    constraints: str = Field(..., description="Bulleted list of constraints.")
    experiment_settings: str = Field(..., description="Bulleted list of experiment settings.")

class AnaylsisPlanCritic(AnalysisPlan):
    issues: str = Field(..., description="List of issues found in original design.")
    rationale: str = Field(..., description="Rationale for each issue listed under `issues`.")
    fix: str = Field(..., description="List of fixes for each issue.")

class AnalysisCodeCritic(AnalysisCode):
    issues: str = Field(..., description="List of issues found in original code.")
    rationale: str = Field(..., description="Rationale for each issue listed under `issues`.")
    fix: str = Field(..., description="List of fixes for each issue.")

