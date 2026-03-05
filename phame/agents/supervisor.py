# supervisor.py
from dataclasses import dataclass, field

from pydantic_ai import Agent, AgentRunResult, RunContext
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from phame.agents.librarian import librarian_agent, LibrarianDeps
from phame.agents.design_agents import build_design_plan_agent, build_design_critic_agent, build_solidworks_macro_agent, build_cadquery_macro_agent, build_cadquery_fixing_agent
from phame.llm.utils import _build_openai_model
from phame.agents.utils import CadGenAgentDeps, SolidworksExampleDeps, CadQueryGenDeps

from typing import Literal, Optional
from pathlib import Path

import os

import subprocess
import sys

"""
The @dataclass decorator rewrites/augments the class by auto-generating a 
common boilerplate.  
We want an instance of SupervisorDeps to be independent from every other 
instance to prevent shared memory between instances. 

field(default_factory=list)
When constructing a new SupervisorDeps, call list() to create a fresh empty
list for this instance.

Those are two separate lists inside one SupervisorDeps instance, so librarian 
and solidworks_ designer maintain separate threads.

Caveat: If you reuse the same SupervisorDeps object across multiple chats/users, 
then those histories persist and are shared across those runs. We want per-user 
isolation, so we need to create/store a SupervisorDeps per user/session.

Right now we only run this for an isolated user locally, but here's a 
consideration for future development: 
Create a new deps for each request, but persist histories separately (stateless server)

def build_deps_for_request(session_id: str) -> SupervisorDeps:
    librarian_history = load_history(session_id, "librarian")  # returns list[ModelMessage]
    design_history = load_history(session_id, "design")

    return SupervisorDeps(
        librarian_deps=make_librarian_deps(),   # build/connect resources
        librarian_history=librarian_history,
        design_deps=make_design_deps(),
        design_history=design_history,
    )

TODO: We should make a fastAPI call with a webserver to demo so we're not tied to the 
command line


TODO: Solidworks Designer does not have any dependencies yet.  Things it could have
Examples of what to put in `deps` for `agent.run_sync(..., deps=...)` (i.e., server-side
dependencies and state that should NOT be exposed as LLM-visible tool parameters):

- Service clients / handles
  - Database connections / repositories (Postgres, Mongo, Redis)
  - Vector DB clients / document stores (Chroma, Pinecone, Weaviate, Elasticsearch)
  - HTTP clients (e.g., httpx.Client), SDK clients (GitHub, Slack, Jira, Notion, S3)
  - Queue / pubsub producers

- RAG + retrieval components
  - Retriever/search objects
  - Embedder instances
  - Reranker instances
  - Retrieval settings (top_k, filters, namespaces)
  - Knowledge-base namespace / tenant routing

- Configuration
  - Model names, temperature defaults
  - Feature flags (enable_tools, enable_rag, etc.)
  - Environment settings (base URLs)
  - Timeouts / retry policies
  - Routing policy knobs (when to call which specialist)

- Security / identity (server-side only)
  - User id / tenant id (non-sensitive identifiers)
  - Auth tokens for downstream services (handle carefully; avoid accidental logging)
  - Permissions/roles (what actions/tools are allowed)

- Per-session / per-conversation state
  - Message histories (e.g., list[ModelMessage])
  - Conversation memory / scratch state (selected file, current project, open PR id)
  - Small caches (recent retrieval results, dedup sets)

- Utilities
  - Logger
  - Clock/time provider (useful for testing)
  - Metrics/tracing hooks
  - random.Random instance for reproducible tests

- Domain-specific objects
  - Current document / active workspace model
  - Parsers/validators (schemas, Pydantic models)
  - Business rules engine / calculators

What NOT to put in deps:
- Anything the LLM should choose/modify directly (make those explicit tool parameters).
- Huge raw data blobs (prefer IDs/handles and fetch on demand).
- Sensitive secrets you might accidentally print/log (keep exposure minimal and secure).

"""

VALID_CAD_GENERATION_AGENT_TYPES = Literal[
    "CADQUERY",
    "SOLIDWORKS"
]

default_agent_thinking_model_str = "@openai-enterprise-pilot/o3"
# default_agent_thinking_model_str = "@opal/Qwen/Qwen3-30B-A3B-Thinking-2507-FP8"

CAD_GENERATION_AGENT_TYPE = "CADQUERY"
match CAD_GENERATION_AGENT_TYPE:
    case "CADQUERY":
        print("CAD Query Agent selected for CAD Generation")
        cad_generation_agent = build_cadquery_macro_agent(
            model_name=default_agent_thinking_model_str
        )
    case "SOLIDWORKS":
        print("Solidworks Agent selected for CAD Generation")
        cad_generation_agent = build_solidworks_macro_agent(
            model_name=default_agent_thinking_model_str)
    case _:
         # No case matched — raise an error
        raise ValueError(f"No matching case for value: {CAD_GENERATION_AGENT_TYPE}")

# Factory for CAD Generation_Agents
def build_cad_deps(mode: VALID_CAD_GENERATION_AGENT_TYPES, **kwargs) -> CadGenAgentDeps:
    if mode == "CADQUERY":
        # return CadQueryGenDeps(**kwargs)
        return CadQueryGenDeps()
    elif mode == "SOLIDWORKS":
        return SolidworksExampleDeps(example_dirs=kwargs['example_dirs'])


        
@dataclass
class SupervisorDeps:
    librarian_deps: LibrarianDeps
    cad_generation_agent_deps: CadGenAgentDeps
    plan_designer_deps: None = None
    plan_critic_deps: None = None
    librarian_history: list[ModelMessage] = field(default_factory=list)    
    plan_designer_history: list[ModelMessage] = field(default_factory=list)
    plan_critic_history: list[ModelMessage] = field(default_factory=list)    
    cad_generation_agent_history: list[ModelMessage] = field(default_factory=list)
    project_folder: Path = "./"
    part_iteration: int = 0
    cur_part_file: Path = None

supervisor_agent_chat_model = _build_openai_model(
    model_name=default_agent_thinking_model_str
    )

"""
Sample prompt: 
Can you design me a bracket for bookshelf which I could mount on a wall. I'm looking for a material that will work in a house setting for a shelf that will hold  least 200 lbs and be about 6 ft long.  Not sure how many brackets I should use 

Make me a picnic table for a toddler.  It will be 2ft tall.  and it will have a rectangular surface that is 18 in by 40 in.  its legs will be on the narrow ends of each side of the table.  The legs will cross on each of the narrow sides.  For each legs use a 2 by 6 beam that is cut at an angle.  The table surface can be made of strong plywood.  Go!
"""
supervisor_agent = Agent(
    supervisor_agent_chat_model,
    deps_type=SupervisorDeps,
    system_prompt=(
        "You are the Supervisor.\n"
        "For sanity, you can use `create_cad_design_pyfile` to query a printout of its reference macros\n"
        "Delegate all other knowledge-base / factual questions to the Librarian using `ask_librarian`.\n"
        "\n"
        "Otherwise, for any design request from the user, you will follow a five step process in sequence.\n"
        "The steps, listed in proper sequence, are as follows:\n"
        "1) You MUST consult the librarian about relevant design considerations and best practices.\n"
        "2) Delegate design plan request to the Plan Designer using `build_design_tool`.\n"
        "3) All design plans need to be evaluated by the Design Critic using `critique_design_tool`.\n"
        "4) Create a single CAD python file for the design using `generate_validate_and_repair` for each component.\n"
        "5) Ask user for design critiques using the `generate_with_user_input` function.\n"
        # "   If the `create_cad_design_pyfile` does not produce a python file (e.g. it makes a VB/VBA file),\n"
        # "   then send the file back to `create_cad_design_pyfile` requested a python implementation. \n"
        "6) Print the design plan and the python file for the user as the final output\n"        
        "\n\n"
        
        "For writing, clarification, etc., you may answer directly\n"
                
    ),
)



@supervisor_agent.tool
def ask_librarian(ctx: RunContext[SupervisorDeps], question: str) -> str:
    """
    Delegate a question to the librarian agent and return its answer.

    Tool arguments overview:

    1) ctx: RunContext[SupervisorDeps]
    - Injected by PydanticAI at runtime (not provided by the LLM or the user).
    - Passed automatically when the tool is executed.
    - Provides access to the run context, especially:
        - ctx.deps: the SupervisorDeps instance (shared resources + per-user state)
        and potentially other run metadata depending on the framework/version.
    - Conceptually similar to `self` in that it gives access to environment/state,
        but it is not a class method parameter—it's an injected context object.

    2) question: str
    - The tool input supplied by the model (this appears in the tool/function schema).
    - The supervisor LLM chooses to call the tool and provides {"question": "..."}.
    - PydanticAI then invokes the Python function like:
        ask_librarian(ctx=<RunContext ...>, question="What is X?")
    """
    print("", flush=True)
    print("***************************************************", flush=True)
    print("Asking the librarian agent for facts on this prompt", flush=True)
    print("***************************************************", flush=True)
    print("", flush=True)
    
    result = librarian_agent.run_sync(
        question,
        deps=ctx.deps.librarian_deps,
        message_history=ctx.deps.librarian_history,
    )

    # Keep a separate conversation state for the librarian (optional but useful)
    ctx.deps.librarian_history[:] = result.all_messages()  # :contentReference[oaicite:1]{index=1}

    print("", flush=True)
    print("***************************************************", flush=True)
    print("Done w/ librarian agent for facts on this prompt", flush=True)
    print("***************************************************", flush=True)
    print("", flush=True)

    # PydanticAI uses `result.output` in the docs; fallback for older code:
    return getattr(result, "output", None) or getattr(result, "data", "")



"""
Build the pan designer agent:

"""
plan_designer_agent = build_design_plan_agent(
    model_name=default_agent_thinking_model_str
)

@supervisor_agent.tool
def build_design_plan(ctx: RunContext[SupervisorDeps], question: str) -> str:
    """Create a design plan using the plan_designer agent and return result"""
    print("", flush=True)
    print("********************************************", flush=True)
    print("Delegating design to the Plan Designer Agent", flush=True)
    print("********************************************", flush=True)
    print("", flush=True)

    result = plan_designer_agent.run_sync(
        question,
        deps=ctx.deps.plan_designer_deps, # None right now
        message_history=ctx.deps.plan_designer_history,
    )

    # Keep a separate conversation state for the plan_designer_agent (optional but useful)
    ctx.deps.plan_designer_history[:] = result.all_messages()  # :contentReference[oaicite:1]{index=1}


    print("", flush=True)
    print("*******************************************", flush=True)
    print("Done with Plan Designer Agent invocation", flush=True)
    print("*******************************************", flush=True)
    print("", flush=True)

    # PydanticAI uses `result.output` in the docs; fallback for older code:
    return getattr(result, "output", None) or getattr(result, "data", "")


"""
Critique design plan:

"""
design_critic_agent = build_design_critic_agent(
    model_name=default_agent_thinking_model_str
)

@supervisor_agent.tool
def critique_design(ctx: RunContext[SupervisorDeps], question: str) -> str:
    """Review design plan using the plan_designer agent and return result"""
    print("", flush=True)
    print("***********************************************", flush=True)
    print("Delegating plan review to the Plan Critic Agent", flush=True)
    print("***********************************************", flush=True)
    print("", flush=True)

    result = design_critic_agent.run_sync(
        question,
        deps=ctx.deps.plan_critic_deps, # None right now
        message_history=ctx.deps.plan_critic_history,
    )

    # Keep a separate conversation state for the plan_designer_agent (optional but useful)
    ctx.deps.plan_critic_history[:] = result.all_messages()  # :contentReference[oaicite:1]{index=1}


    print("", flush=True)
    print("*******************************************", flush=True)
    print("Done with Plan Critic Agent invocation", flush=True)
    print("*******************************************", flush=True)
    print("", flush=True)

    # PydanticAI uses `result.output` in the docs; fallback for older code:
    return getattr(result, "output", None) or getattr(result, "data", "")



"""
Build the solidworks macro agent:

Call the agent class factor Gary implemented.  
TODO make a big configuation file for the supervisor and all its delegates 

Config file could contain
- agent model
- system prompt
- chromaDB paths
- etc

"""

def write_code_to_disk(ctx: RunContext[SupervisorDeps], result: AgentRunResult, iter: bool=False):
    """
    this function is for writting out code written by the AI
    """
    if iter:
        ctx.deps.part_iteration += 1
    part_name = result.output.title.replace(" ","_")
    rationale = result.output.rationale
    code = result.output.cad_code
    part_file = Path(ctx.deps.project_folder / "parts" / f"{part_name}_{ctx.deps.part_iteration}.py")
    code = code.replace('./part_replace_me.step', str(part_file)[:-4]+".step")

    with open(part_file, "w", encoding="utf-8") as fp:
        title = "## " + result.output.title
        fp.write(title + '\n')

        fp.write("## Based on \n")

        rationale = "## " + rationale.replace('\n', '\n## ')
        fp.write(rationale + '\n')

        fp.write(code)

    ctx.deps.cur_part_file = part_file

    return


@supervisor_agent.tool
def create_cad_design_pyfile(ctx: RunContext[SupervisorDeps], question: str) -> str:
    """Create a design using the solidworks_design_plan agent and return result"""
    print("", flush=True)
    print("*******************************************", flush=True)
    print("CAD Generation Agent implementing design", flush=True)
    print("*******************************************", flush=True)
    print("", flush=True)

    result = cad_generation_agent.run_sync(
        question,
        deps=ctx.deps.cad_generation_agent_deps, # None right now
        message_history=ctx.deps.cad_generation_agent_history,
    )

    ctx.deps.part_iteration = 0
    write_code_to_disk(ctx, result, False)

    # Keep a separate conversation state for the solidworks_macro_agent (optional but useful)
    ctx.deps.cad_generation_agent_history[:] = result.all_messages()  # :contentReference[oaicite:1]{index=1}

    print("", flush=True)
    print("*******************************************", flush=True)
    print("CAD Generation Agent implementing design", flush=True)
    print("*******************************************", flush=True)
    print("", flush=True)

    # PydanticAI uses `result.output` in the docs; fallback for older code:
    return getattr(result, "output", None) or getattr(result, "data", "")



@supervisor_agent.tool
def run_cad_file(ctx: RunContext[SupervisorDeps], timeout_s: int = 120) -> str:
    """
    Execute the most recently generated CAD python file in an isolated subprocess.
    Returns success output or a formatted error report to feed back into the LLM.
    """
    part_file = ctx.deps.cur_part_file
    if not part_file:
        return "ERROR: No current part file is set. Generate a part first with create_cad_design_pyfile."

    if not Path(part_file).exists():
        return f"ERROR: File does not exist: {part_file}"

    # Run as a module file with same python interpreter
    cmd = [sys.executable, str(part_file)]

    try:
        proc = subprocess.run(
            cmd,
            cwd="./",  # keep relative paths stable
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired as e:
        # Return something the LLM can act on (hangs often mean missing "show()" or big render)
        return (
            "RUNTIME_ERROR: Execution timed out.\n"
            f"file: {part_file}\n"
            f"timeout_s: {timeout_s}\n"
            "stdout (partial):\n"
            f"{(e.stdout or '')[:4000]}\n"
            "stderr (partial):\n"
            f"{(e.stderr or '')[:4000]}"
        )
    except Exception as e:
        return f"RUNTIME_ERROR: Failed to execute subprocess: {type(e).__name__}: {e}"

    # Persist logs
    logs_dir = ctx.deps.project_folder / "logs"
    logs_dir.mkdir(exist_ok=True)
    (logs_dir / f"{Path(part_file).stem}.stdout.txt").write_text(proc.stdout or "", encoding="utf-8")
    (logs_dir / f"{Path(part_file).stem}.stderr.txt").write_text(proc.stderr or "", encoding="utf-8")

    if proc.returncode == 0:
        return (
            "OK: CAD file executed successfully.\n"
            f"file: {part_file}\n"
            f"stdout:\n{(proc.stdout or '')[:4000]}\n"
        )

    # Non-zero exit: return actionable error details
    return (
        "RUNTIME_ERROR: CAD file crashed.\n"
        f"file: {part_file}\n"
        f"returncode: {proc.returncode}\n"
        "stderr:\n"
        f"{(proc.stderr or '')[:8000]}\n"
        "stdout:\n"
        f"{(proc.stdout or '')[:2000]}\n"
        "INSTRUCTIONS: Fix the code to resolve the runtime error. "
        "Do not change the design intent unless necessary. "
        "Return corrected Python CAD code."
    )


def generate_validate_and_repair(ctx: RunContext[SupervisorDeps], prompt0: str, cad_func, max_attempts: int = 3) -> str:
    """
    Deterministic loop: generate -> run -> if error, feed error back -> regenerate.
    """
    # print(max_attempts)
    last_report = ""
    for attempt in range(1, max_attempts + 1):
        prompt = prompt0
        if last_report:
            prompt += "\n\nThe previous generated code failed with this runtime error:\n" + last_report + gen.cad_code

        gen = cad_func(ctx, prompt)  # calls agent + writes file
        report = run_cad_file(ctx)

        print(report)

        if report.startswith("OK:"):
            return f"SUCCESS after {attempt} attempt(s).\n{report}"

        last_report = report

    return f"FAILED after {max_attempts} attempts.\nLast error:\n{last_report}"


code_fixing_agent = build_cadquery_fixing_agent(
    model_name=default_agent_thinking_model_str
)

@supervisor_agent.tool
def generate_validate_and_repair_cad_generation(ctx: RunContext[SupervisorDeps], prompt0: str, max_attempts: int = 3) -> str:
    return generate_validate_and_repair(ctx, prompt0, create_cad_design_pyfile, max_attempts)

@supervisor_agent.tool
def generate_with_user_input(ctx: RunContext[SupervisorDeps], spec: str):
    """
     this function allows a user to provide critique of the provided design.
     This is sent back to an agent who is tasked with fixing said design.
    """
    while True:
        issues = input("\nWhat issues do you see with the design? (type 'none' to quit)\n> ").strip()

        if issues.lower() == "none":
            print("Done!\n")
            break

        current_file = ctx.deps.cur_part_file
        with open(current_file, "r", encoding="utf-8") as fp:
            code = fp.read()

        prompt = (f"The original design request: {spec}\n"
                  f"These are the list of issues to resolve:\n{issues}\n"
                  f"Here is the original code:\n```\n{code}\n```\n"
                  "Correct these issues and provide a new code.")

        ctx.deps.part_iteration += 1
        generate_validate_and_repair(ctx, prompt, fix_cad_design_pyfile, 3)



def fix_cad_design_pyfile(ctx: RunContext[SupervisorDeps], prompt: str) -> str:
    """Create a design using the solidworks_design_plan agent and return result"""

    result = code_fixing_agent.run_sync(prompt,
                                   deps=ctx.deps.cad_generation_agent_deps,
                                   message_history=ctx.deps.cad_generation_agent_history)
    # breakpoint()
    write_code_to_disk(ctx, result, False)
    ctx.deps.cad_generation_agent_history[:] = result.all_messages()

    # PydanticAI uses `result.output` in the docs; fallback for older code:
    return getattr(result, "output", None) or getattr(result, "data", "")