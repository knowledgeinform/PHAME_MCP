from pydantic import Field
from pydantic_ai import Agent
from typing import Callable, List

from phame.llm.utils import _build_openai_model
from phame.llm.basemodels import AnalysisCode, AnalysisPlan, AnaylsisPlanCritic, AnalysisCodeCritic


def build_analysis_plan_agent(model_name: str, api_key: str, base_url: str) -> Agent[AnalysisPlan]:
    model = _build_openai_model(model_name=model_name, api_key=api_key, base_url=base_url)

    agent = Agent(
        model,
        output_type=AnalysisPlan,
        system_prompt=(
            "You are a senior mechanical engineer tasked with designing an appropriate finite-element method experiment to test the integrity of a proposed design.\n"
            "You should consider the intended use of the design when designing the experiment.\n"
            "Experiments can be structural/load bearing, thermal, electro-magnetic, and/or fluids based.\n"
            "Enumerate all boundary conditions, constraints, and experiment settings.\n"
            "Requirements:\n"
            "- Experiments must be relevant for the intended real-world use of the design.\n"
            "- Ensure that any holes for fasteners are treated as boundary faces for any experiment.\n"
            "- Keep rationale brief (<=3 bullets). No step-by-step reasoning.\n"
            "- You must list all constraints, boundary conditions, and experiment settings."
        ),
    )
    return agent

def build_analysis_plan_critic_agent(model_name: str, api_key: str, base_url: str) -> Agent[AnaylsisPlanCritic]:
    model = _build_openai_model(model_name=model_name, api_key=api_key, base_url=base_url)

    agent = Agent(
        model,
        output_type=AnaylsisPlanCritic,
        system_prompt=(
            "You are a engineering supervisor tasked with evaluating, critiquing, and correcting an experiment plan for a design.\n"
            "You should consider the intended use of the design when deciding if the experiment plan makes sense.\n"
            "Experiments can be structural/load bearing, thermal, electro-magnetic, and/or fluids based.\n"
            "Ensure that all boundary conditions, constraints, and problem settings are appropriate and complete.\n"
            "Ensure that geometry and mesh are feasible and appropriate.\n"
            "Requirements:\n"
            "- Experiments must be relevant for the intended real-world use of the design.\n"
            "- Ensure that any holes for fasteners are treated as boundary faces for any experiment.\n"
            "- List all issues.\n"
            "- List a rationale corresponding to each issue.\n"
            "- You must list all constraints, boundary conditions, and experiment settings.\n"
            "- Make fixes to experiment based on the issues you find."
        ),
    )
    return agent

def build_analysis_code_agent(model_name: str, api_key: str, base_url: str) -> Agent[AnalysisCode]:
    model = _build_openai_model(model_name=model_name, api_key=api_key, base_url=base_url)

    agent = Agent(
        model,
        output_type=AnalysisCode,
        system_prompt=(
            "You are a senior mechanical engineer tasked with designing an appropriate finite-element method experiment to test the integrity of a proposed design.\n"
            "You will be provided with an experiment design and will be tasked with programming the actual experiment.\n"
            "You will also be provided with the path for the part that will be undergoing the experiment.\n"
            "All experiments must be designed with PyAnsys code.\n"
            "Requirements:\n"
            "- Code must include loading the part.\n"
            "- Code must correctly identify faces.\n"
            "- Code must include a line enabling exporting of outputs."
        ),
    )
    return agent


def build_analysis_code_critic_agent(model_name: str, api_key: str, base_url: str) -> Agent[AnalysisCodeCritic]:
    model = _build_openai_model(model_name=model_name, api_key=api_key, base_url=base_url)

    agent = Agent(
        model,
        output_type=AnalysisCodeCritic,
        system_prompt=(
            "You are a senior mechanical engineer tasked with reviewing, critiquing, and fixing the PyAnsys code of a junior engineer.\n"
            "The PyAnsys code corresponds to a FEM experiment designed to test the integrity of a designed object.\n"
            "You must ensure that the code has no syntactical errors nor no logical errors.\n"
            "You must ensure that all referenced faces are correct.\n"
            "You must ensure that the intended experiment is properly performed by the code.\n"
            "List each issue, list a rationale for the issue, and list a fix for the issue.\n"
            "Implement the fix and provide a corrected code.\n"
            "Additional Requirements:\n"
            "- Code must include loading the part.\n"
            "- Code must correctly identify faces.\n"
            "- Code must include a line enabling exporting of outputs."
        ),
    )
    return agent


async def generate_analysis_plan(
    agent: Agent[AnalysisPlan],
    part_cad_code: str,
    part_description: str,
) -> AnalysisPlan:

    user_prompt = (
        f"Description of part:\n{part_description}\n"
        f"Original Code:\n```\n{part_cad_code}\n```\n"
        "Return a description of an experiment based on realistic use-cases."
    )

    result = await agent.run(user_prompt)
    return result

async def generate_analysis_plan_critique(
    agent: Agent[AnaylsisPlanCritic],
    part_cad_code: str,
    part_description: str,
    experiment_plan: str
) -> AnaylsisPlanCritic:

    user_prompt = (
        f"Description of part:\n{part_description}\n"
        f"Original Code:\n```\n{part_cad_code}\n```\n"
        f"Original Experiment Plan:\n```\n{experiment_plan}\n```\n"
        "Identify all issues with this experiment plan, give a rationale, provide an appropriate fix, and revise the experiment."
    )

    result = await agent.run(user_prompt)
    return result


async def generate_analysis_code(
    agent: Agent[AnalysisCode],
    part_cad_code: str,
    part_description: str,
    part_path: str,
    experiment_plan: str
) -> AnalysisCode:

    user_prompt = (
        f"Description of part:\n{part_description}\n"
        f"Original Code:\n```\n{part_cad_code}\n```\n"
        f"Path to Part: \n{part_path}\n"
        f"Experiment Description:\n```\n{experiment_plan}\n```\n"
        "Return PyAnsys code for performing the experiment."
    )

    result = await agent.run(user_prompt)
    return result


async def generate_analysis_code_critique(
    agent: Agent[AnalysisCodeCritic],
    part_cad_code: str,
    part_description: str,
    part_path: str,
    experiment_plan: str,
    experiment_code: str
) -> AnalysisCodeCritic:

    user_prompt = (
        f"Description of part:\n{part_description}\n"
        f"Original Part Code:\n```\n{part_cad_code}\n```\n"
        f"Path to Part: \n{part_path}\n"
        f"Experiment Description:\n```\n{experiment_plan}\n```\n"
        f"Original Experiment Code:\n```\n{experiment_code}\n```\n"
        "Find all issues and propose a solution.\n"
        "Return PyAnsys code for performing the experiment with the fixes you identified."
    )

    result = await agent.run(user_prompt)
    return result