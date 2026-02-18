# supervisor.py
from dataclasses import dataclass, field

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from phame.agents.librarian import librarian_agent, LibrarianDeps
from phame.agents.design_agents import build_design_plan_agent, build_design_critic_agent, build_solidworks_macro_agent, build_cadquery_macro_agent
from phame.llm.utils import _build_openai_model
from phame.agents.utils import CadGenAgentDeps, SolidworksExampleDeps, CadQueryGenDeps

from typing import Literal

import os


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

# default_agent_thinking_model_str = "@openai-enterprise-pilot/o3"
default_agent_thinking_model_str = "Qwen/Qwen3-30B-A3B-Thinking-2507-FP8"

CAD_GENERATION_AGENT_TYPE = "CADQUERY"
match CAD_GENERATION_AGENT_TYPE:
    case "CADQUERY":
        print("CAD Query Agent selected for CAD Generation")
        cad_generation_agent = build_cadquery_macro_agent(
            model_name=default_agent_thinking_model_str,
            api_key=os.environ["PORTKEY_API_KEY"], 
            base_url=os.environ["PORTKEY_BASE_URL"]
        )
    case "SOLIDWORKS":
        print("Solidworks Agent selected for CAD Generation")
        cad_generation_agent = build_solidworks_macro_agent(
            model_name=default_agent_thinking_model_str,
            api_key=os.environ["PORTKEY_API_KEY"], 
            base_url=os.environ["PORTKEY_BASE_URL"]
        )
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

# agent_chat_model = OpenAIChatModel(
#     "openai/gpt-oss-120b",   # model string passed through to the endpoint
#     provider=OpenAIProvider(
#         base_url=os.environ["PORTKEY_BASE_URL"],   # e.g. "https://api.portkey.ai/v1"
#         api_key=os.environ["PORTKEY_API_KEY"],
#     ),
# )



supervisor_agent_chat_model = _build_openai_model(
    model_name=default_agent_thinking_model_str, 
    api_key=os.environ["PORTKEY_API_KEY"], 
    base_url=os.environ["PORTKEY_BASE_URL"]
    )

"""
Sample prompt: 
Can you design me a bracket for bookshelf which I could mount on a wall. I'm looking for a material that will work in a house setting for a shelf that will hold  least 200 lbs and be about 6 ft long.  Not sure how many brackets I should use 
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
        "4) Create a CAD python file for each component in a design using `create_cad_design_pyfile` for each component.\n"
        "   If the `create_cad_design_pyfile` does not produce a python file (e.g. it makes a VB/VBA file),\n"
        "   then send the file back to `create_cad_design_pyfile` requested a python implementation. \n"
        "5) Print the design plan and the python file for the user as the final output\n"        
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
    model_name=default_agent_thinking_model_str, 
    api_key=os.environ["PORTKEY_API_KEY"], 
    base_url=os.environ["PORTKEY_BASE_URL"]
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
    model_name=default_agent_thinking_model_str,
    api_key=os.environ["PORTKEY_API_KEY"],
    base_url=os.environ["PORTKEY_BASE_URL"]
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

    # Keep a separate conversation state for the solidworks_macro_agent (optional but useful)
    ctx.deps.cad_generation_agent_history[:] = result.all_messages()  # :contentReference[oaicite:1]{index=1}

    print("", flush=True)
    print("*******************************************", flush=True)
    print("CAD Generation Agent implementing design", flush=True)
    print("*******************************************", flush=True)
    print("", flush=True)

    # PydanticAI uses `result.output` in the docs; fallback for older code:
    return getattr(result, "output", None) or getattr(result, "data", "")
