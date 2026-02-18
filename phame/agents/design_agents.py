from pydantic_ai import Agent, RunContext
from typing import Callable, List

from phame.llm.basemodels import DesignCode, DesignPlan, DesignCodeCritic, DesignPlanCritic
from phame.llm.utils import _build_openai_model
from phame.agents.utils import SolidworksExampleDeps, CadGenAgentDeps

def build_design_plan_agent(model_name: str, api_key: str, base_url: str) -> Agent[DesignPlan]:
    model = _build_openai_model(model_name=model_name, api_key=api_key, base_url=base_url)
    agent = Agent[DesignPlan](
        model,
        output_type=DesignPlan,
        system_prompt=(
            "You are a senior mechanical engineer tasked with planning a design to be made in parametric CAD.\n"
            "Provide a step-by-step approach for developing the part.\n"
            "These steps include but are not limited to drawing shapes, intersecting shapes, extruding geometries, revovling around an axis, merging components, etc.\n"
            "Ensure that all steps are possible with SolidWorks\n"
            "Requirements:\n"
            "- Prefer simple, robust geometry.\n"
            "- Prefer easier manufacturability.\n"
            "- Keep rationale brief (<=3 bullets). No step-by-step reasoning.\n"
            "- Include holes for fasteners if needed.\n"
        ),
    )
    return agent

def build_design_critic_agent(model_name: str, api_key: str, base_url: str) -> Agent[DesignPlanCritic]:
    model = _build_openai_model(model_name=model_name, api_key=api_key, base_url=base_url)
    agent = Agent[DesignPlanCritic](
        model,
        output_type=DesignPlanCritic,
        system_prompt=(
            "You are a senior mechanical engineer tasked with evaluating a plan for designing a part in parametric CAD made by a junior engineer.\n"
            "Determine if the part achieves the intended design, and if not list all issues, rationales, and fixes.\n"
            "Consider each step individually as well as how they interact with each other.\n"
            "Implement these fixes and provide a new design plan.\n"
            "Ensure that all steps are possible with SolidWorks\n"
            "Requirements:\n"
            "- Prefer simple, robust geometry.\n"
            "- Prefer easier manufacturability.\n"
            "- Ensure fasteners are included where needed."
        ),
    )
    return agent

def build_solidworks_macro_agent(model_name: str, api_key: str, base_url: str) -> Agent[DesignCode]:
    model = _build_openai_model(model_name=model_name, api_key=api_key, base_url=base_url)
    agent = Agent[DesignCode](
        model,
        deps_type=SolidworksExampleDeps,
        output_type=DesignCode,
        system_prompt=(
            "You are a senior mechanical engineer producing SolidWorks Macro Code in Python enabled with the win32com package.\n"
            "Requirements:\n"
            "- You MUST follow the patterns from examples from the tool `get_example_macros`. Prefer their structure, naming, and error handling.\n"
            "- Never use `swPart = swApp.NewPart()` in the script.  \n"
            "     Instead Use: \n"
            "       template_path = 'C:\\\\ProgramData\\\\SOLIDWORKS\\\\SOLIDWORKS 2024\\\\templates\\\\Part.prtdot'\n"
            "       swApp.NewDocument(template_path, 0, 0, 0)\n"
            "- Prefer simple, robust geometry.\n"
            "- Prefer easier manufacturability.\n"
            "- Keep rationale brief (<=3 bullets). No step-by-step reasoning.\n"
            "- Include holes for fasteners if needed.\n"
            "- Code must include a line enabling updating graphics.\n"
            "- Code must include a line enabling exporting of design as a .SLDPRT file.\n"
            "\n\n"
            "As an independent task, you can return a printout of the reference macros in deps upon request using `get_example_macros`."
        ),
    )
    
    @agent.tool
    def get_example_macros(ctx: RunContext[SolidworksExampleDeps]) -> str:
        # You can return a combined blob, or you could return structured list.
        print(" Getting example macros...\n")
        examples = ctx.deps.load_examples_text()
        # print(examples)
        return examples
    
    return agent

def build_solidworks_macro_critic_agent(model_name: str, api_key: str, base_url: str) -> Agent[DesignCodeCritic]:
    model = _build_openai_model(model_name=model_name, api_key=api_key, base_url=base_url)
    agent = Agent[DesignCodeCritic](
        model,
        output_type=DesignCodeCritic,
        system_prompt=(
            "You are a senior mechanical engineer tasked with evaluating and fixing the CAD code of a junior engineer.\n"
            "Ensure that the code is valid SolidWorks Macro Code in Python enabled with the win32com package.\n"
            "Ensure that the intended design is achieved.\n"
            "List all issues, give a rationale, and fix the issue in the code.\n"
            "Requirements given to the junior engineer:\n"
            "- Prefer simple, robust geometry.\n"
            "- Prefer easier manufacturability.\n"
            "- Keep rationale brief (<=3 bullets). No step-by-step reasoning.\n"
            "- Include holes for fasteners if needed.\n"
            "- Code must include a line enabling updating graphics.\n"
            "- Code must include a line enabling exporting of design as a .SLDPRT file."
        ),
    )
    return agent

def build_cadquery_macro_agent(model_name: str, api_key: str, base_url: str) -> Agent[DesignCode]:
    model = _build_openai_model(model_name=model_name, api_key=api_key, base_url=base_url)
    agent = Agent[DesignCode](
        model,
        deps_type= CadGenAgentDeps,
        output_type=DesignCode,
        system_prompt=(
            "You are a senior mechanical engineer producing CADQuery code.\n"
            "Requirements:\n"
            "- Prefer simple, robust geometry.\n"
            "- Keep rationale brief (<=3 bullets). No step-by-step reasoning.\n"
            "- Include holes for fasteners if needed."
            "- Code must include a line for exporting the model to an stl file."
            "- Output must be a valid JSON"
        ),
    )
    
    # @agent.tool
    # def get_example_macros(ctx: RunContext[MacroExampleDeps]) -> str:
    #     # You can return a combined blob, or you could return structured list.
    #     print(" Getting example macros...\n")
    #     examples = ctx.deps.load_examples_text()
    #     # print(examples)
    #     return examples
    
    return agent


async def generate_design_plan(
    agent: Agent[DesignPlan],
    part_description: str,
) -> DesignPlan:

    user_prompt = (
        f"Description of part:\n{part_description}\n"
        "Return a step-by-step design plan for making this part in parametric CAD."
    )

    result = await agent.run(user_prompt)
    return result

async def generate_design_plan_critique(
    agent: Agent[DesignPlanCritic],
    part_description: str,
    design_plan: str
) -> DesignPlanCritic:

    user_prompt = (
        f"Description of part:\n{part_description}\n"
        f"Original Design Plan:\n```\n{design_plan}\n```\n"
        "Identify all issues with this design plan, give a rationale, provide an appropriate fix, and revise the design."
    )

    result = await agent.run(user_prompt)
    return result

async def generate_part_with_k_past_work_and_plan(
    agent: Agent[DesignCode],
    descriptions: List[str],
    codes: List[str],
    desired_part: str,
    plan: str
) -> DesignCode:

    assert len(descriptions) == len(codes), "Descriptions and codes must have same length"

    example_text = []
    for i, (description, code) in enumerate(zip(descriptions, codes)):
        example_text.append(
            f"Description {i+1}: {description}\nCorresponding code:\n```\n{code}\n```\n"
        )

    example_text_str = "".join(example_text)

    user_prompt = (
        "Example parts:\n"
        + example_text_str
        + f"\nTASK: Produce a CAD design for {desired_part}\n."
        + f"Here is a design plan, follow it strictly:\n{plan}\n\n"
    )

    result: DesignCode = await agent.run(user_prompt)
    return result


async def generate_cad_code_critique(
    agent: Agent[DesignCodeCritic],
    part_description: str,
    design_plan: str,
    cad_code: str
) -> DesignCodeCritic:

    user_prompt = (
        f"Description of part:\n{part_description}\n"
        f"Original Design Plan:\n```\n{design_plan}\n```\n"
        f"Original Code:\n```\n{cad_code}\n```\n"
        "Identify all issues with this code, give a rationale, provide an appropriate fix, and correct the code."
    )

    result = await agent.run(user_prompt)
    return result


async def generate_part_with_k_past_work(
    agent: Agent[DesignCode],
    descriptions: List[str],
    codes: List[str],
    desired_part: str,
) -> DesignCode:

    assert len(descriptions) == len(codes), "Descriptions and codes must have same length"

    example_text = []
    for i, (description, code) in enumerate(zip(descriptions, codes)):
        example_text.append(
            f"Description {i+1}: {description}\nCorresponding code:\n```\n{code}\n```\n"
        )

    example_text_str = "".join(example_text)

    user_prompt = (
        "Example parts:\n"
        + example_text_str
        + f"\nTASK: Produce a CAD design for {desired_part}\n."
        "Return the SolidWorks macro Python code inside a JSON matching the DesignCode schema.\n\n"
    )

    result: DesignCode = await agent.run(user_prompt)
    return result


async def generate_part_by_revisions(
    agent: Agent[DesignCode],
    issues: List[str],
    code: str,
    desired_part: str,
) -> DesignCode:

    n_issues = len(issues)
    issues_text = []
    for i, issue in enumerate(issues):
        issues_text.append(
            f"Issue {i+1}: {issue}\n"
        )

    issues_text = "".join(issues_text)

    user_prompt = (
        f"Description of part:\n{desired_part}\n"
        f"The original code provided contained {n_issues} issues.\n\n"
        "Please revise the following code in order to address these issues.\n"
        f"Original Code:\n```\n{code}\n```\n"
        f"List of Issues:\n{issues_text}"
        "Return the revised SolidWorks macro Python code inside a JSON matching the DesignCode schema.\n"
    )

    result: DesignCode = await agent.run(user_prompt)
    return result