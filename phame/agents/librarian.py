# librarian.py
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from haystack import Pipeline
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from phame.llm.utils import _build_openai_model

# from phame.agents.supervisor import default_agent_thinking_model_str

default_agent_thinking_model_str = "@openai-enterprise-pilot/gpt-4"
# default_agent_thinking_model_str = "@opal/Qwen/Qwen3-30B-A3B-Thinking-2507-FP8"

@dataclass
class LibrarianDeps:
    textbook_rag: Pipeline  # you can add more pipelines later

agent_chat_model = _build_openai_model(default_agent_thinking_model_str)

librarian_agent = Agent(
    agent_chat_model,
    deps_type=LibrarianDeps,
    system_prompt=(
        "You are the Librarian.\n"
        "Use your tools (RAG pipelines) to answer knowledge-base questions.\n"
        "If the KB doesn't contain the answer or any relevent information say you don't know.\n"
        "Provide references to the documents you match"
    ),
)

@librarian_agent.tool
def kb_basic(ctx: RunContext[LibrarianDeps], question: str) -> str:
    """Answer using the basic Haystack RAG pipeline."""
    p = ctx.deps.textbook_rag
    try:
        out = p.run({
        "text_embedder": {"text": question},
        "prompt_builder": {"question": question},  # matches your template variable
        "answer_builder": {"query": question},     # AnswerBuilder expects query
        })
    except:
        out = {
            'first_answer':
                {'answer':"I don't know."}
        }
    return out["first_answer"]["answer"]
