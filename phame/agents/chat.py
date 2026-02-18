# chat.py
from pydantic_ai.messages import ModelMessage
from phame.agents.supervisor import supervisor_agent, SupervisorDeps, CAD_GENERATION_AGENT_TYPE, build_cad_deps
from phame.agents.librarian import LibrarianDeps
from phame.agents.utils import SolidworksExampleDeps

# from phame.haystack.agent_calls_rag import build_rag_pipeline
from phame.haystack.trusted_references_rag import make_chroma_document_store, build_rag_pipeline
from phame.llm.utils import pretty_print_ctx_messages


from pathlib import Path

import sys
if sys.platform.startswith("win"):
    """
    Symptom (Windows)                Likely cause                                                                Why it shows up only on Windows
    -------------------------------- -------------------------------------------------------------------------   --------------------------------------------------------------
    5-10 min pause after each        The blocking run_sync call is executed on the default Windows Proactor      Windows → asyncio uses the Proactor policy by default, which does not 
    tool call (i.e. after            event loop. When a blocking HTTP request (Portkey/OpenAI) is made from      automatically run blocking code in a thread. The request sits on the
    librarian_agent.run_sync,        inside an async handler (on_events), the loop cannot process the next       main thread and the stream handler blocks, so everything downstream 
    plan_designer_agent.run_sync,    I/O event until the request finishes. On Linux the default selector loop    (printing, next tool call) appears frozen.
    solidworks_macro_agent.run_sync) can hand-off the blocking call to a thread pool more gracefully,
    so you don't see the stall.

    No stall on Linux                Linux's default selector loop (asyncio.SelectorEventLoop) automatically      Different default loop implementation.
                                     runs blocking calls in a thread pool when they are awaited inside an async
                                     coroutine.

    Same code, same network          The delay is not network latency but the event-loop thread-blocking.        -
    """
    import asyncio
    # Switch to the selector loop which can off‑load blocking calls to a thread pool
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
from collections.abc import AsyncIterable
from pydantic_ai import (
    AgentStreamEvent,
    PartStartEvent,
    PartEndEvent,
    PartDeltaEvent,
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ThinkingPart,
    TextPartDelta,
    ThinkingPartDelta,
    ToolCallPart,
    ToolCallPartDelta,
)


# textbook_rag = build_rag_pipeline()
CHROMA_PERSIST = "./chroma_db/trusted_ref_subset"
EMBED_MODEL = "intfloat/e5-large-v2"
SOLIDWORKS_MACRO_EXAMPLES = [Path("./solidworks/human_gen_examples")]
# textbook_rag = build_rag_pipeline()
document_store = make_chroma_document_store(persist_path=CHROMA_PERSIST)
textbook_rag = build_rag_pipeline(document_store, EMBED_MODEL)

   

deps = SupervisorDeps(
    librarian_deps=LibrarianDeps(textbook_rag=textbook_rag),
    cad_generation_agent_deps=build_cad_deps(mode=CAD_GENERATION_AGENT_TYPE, example_dirs=SOLIDWORKS_MACRO_EXAMPLES)
    )
supervisor_history: list[ModelMessage] = []

"""
###############################################################################
Event Handler for Logging
###############################################################################

TODO - consider adding a log to file mechanism

"""

async def on_events(ctx, event_stream: AsyncIterable[AgentStreamEvent]):
    async for e in event_stream:
        if isinstance(e, FunctionToolCallEvent):
            print(f"\n[tool-call] {e.part.tool_name} args={e.part.args}", flush=True)
            pretty_print_ctx_messages(ctx)
            
        elif isinstance(e, FunctionToolResultEvent):
            print(f"\n[tool-result] {e.tool_call_id}", flush=True)
            pretty_print_ctx_messages(ctx)
            
        elif isinstance(e, PartDeltaEvent):        
            if isinstance(e.delta, TextPartDelta):
                sys.stdout.write(e.delta.content_delta)
                sys.stdout.flush()
            elif isinstance(e.delta, ThinkingPartDelta):
                # print(f"\n[Thinking...] {e}", flush=True)
                sys.stdout.write(e.delta.content_delta)
            elif isinstance(e.delta, ToolCallPartDelta):
                sys.stdout.write(e.delta.args_delta)
            else:
                print(f"\n[Unhandled PartDeltaEvent SubType] {e.delta}", flush=True)
                
        elif isinstance(e, PartEndEvent):
            if isinstance(e.part, ThinkingPart):
                print(f"\n[Done Thinking.]\n {e}", flush=True)
            elif isinstance(e.part, ToolCallPart):
                print(f"\nSupervisor is calling tool: {e.part.tool_name}", flush=True)
            else:
                print(f"\n[Unhandled PartEndEvent SubType] {e.part}", flush=True)
            
        elif isinstance(e, PartStartEvent):
            print(f"\n[supervisor-start] {e.part.id}", flush=True)
            pretty_print_ctx_messages(ctx)
            
        elif isinstance(e, FinalResultEvent):
            print(f"\nFinalResultEvent")
            
        else:
            print(f"\n[Unhandled Event Type] {e}", flush=True)
            
async def on_events_status(ctx, event_stream: AsyncIterable[AgentStreamEvent]):
    async for e in event_stream:
        if isinstance(e, FunctionToolCallEvent):
            print(f"\n[tool-call] {e.part.tool_name} args={e.part.args}", flush=True)
        elif isinstance(e, FunctionToolResultEvent):
            print(f"\n[tool-result] {e.tool_call_id}", flush=True)
        elif isinstance(e, FinalResultEvent):
            print("\n[final-found] (stream text next)", flush=True)


from pydantic import BaseModel

class SupervisorAnswer(BaseModel):
    answer: str
    used_librarian: bool

"""
###############################################################################
Main Chat Loop
###############################################################################
"""
while True:
    user = input("\nyou> ").strip()
    if user.lower() in {"exit", "quit"}:
        break

    result = supervisor_agent.run_sync(
        user, 
        deps=deps, 
        message_history=supervisor_history,
        event_stream_handler=on_events
        )
    
    print("supervisor>", getattr(result, "output", None) or getattr(result, "data", ""))

    # Persist supervisor conversation
    supervisor_history = result.all_messages()  # :contentReference[oaicite:3]{index=3}
    
    ###########################################################
    """
    Below is an alternate run paradigm with agent.run_stream_sync()
    
    It's kind nice because you can chat with the supervisor while other agents are running
    
    """
    
    # streamed = supervisor_agent.run_stream_sync(
    #     user,
    #     deps=deps,
    #     message_history=supervisor_history,
    #     event_stream_handler=on_events_status,
    #     output_type=SupervisorAnswer        
    #     )
    # print("supervisor> ", end="", flush=True)

    # # prev = ""
    # # for full in streamed.stream_text(delta=False):
    # #     # print only what’s new since last chunk
    # #     print(full[len(prev):], end="", flush=True)
    # #     prev = full

    # # # Ensure the run is “complete” and you can safely read output/history
    # # output = streamed.get_output()
    
    # # (You can still stream events/text deltas if you want, but final output is structured)
    # final = streamed.get_output()
    # print(final.answer)
    
    # supervisor_history = streamed.all_messages()
    

