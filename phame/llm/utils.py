from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

def _build_openai_model(*, model_name: str, api_key: str, base_url: str) -> OpenAIChatModel:
    return OpenAIChatModel(
        model_name,
        provider=OpenAIProvider(base_url=base_url, api_key=api_key),
    )
    
from dataclasses import asdict, is_dataclass
from pprint import pformat
import textwrap

WRAP_COL = 80
TRUNCATE_THRESH_LEN = 10000

# --------- generic helpers ---------

def _dump_obj(o):
    if o is None:
        return None
    if hasattr(o, "model_dump"):  # pydantic BaseModel
        return o.model_dump()
    if is_dataclass(o):
        return asdict(o)
    if hasattr(o, "__dict__"):
        return {
            k: v for k, v in vars(o).items()
            if "key" not in k.lower() and "secret" not in k.lower()
        }
    return repr(o)

def _wrap_text(s: str, width: int = WRAP_COL, indent: str = "") -> str:
    s = "" if s is None else str(s)
    return "\n".join(
        textwrap.fill(
            line,
            width=width,
            subsequent_indent=indent,
            break_long_words=False,
            break_on_hyphens=False,
        )
        for line in s.splitlines()
    )

def _short(s, n=None):
    if s is None:
        return ""
    s = str(s)
    if n is None:
        return s
    return s if len(s) <= n else s[:n] + "…"

# --------- ctx summary (agent/tool/run info) ---------

def _get_any(obj, *names, default=None):
    for n in names:
        if hasattr(obj, n):
            v = getattr(obj, n)
            # Call no-arg callables safely (rare, but happens)
            if callable(v):
                try:
                    v = v()
                except TypeError:
                    pass
            if v is not None:
                return v
    return default

def format_ctx_summary(ctx, width: int = WRAP_COL) -> str:
    """
    Tries to extract "what agent/tool/run is this?" from ctx without assuming
    exact PydanticAI version. Uses getattr-based probing.
    """
    # Common-ish candidates across versions / integrations
    run_id = _get_any(ctx, "run_id", "trace_id", "id")
    run_step = _get_any(ctx, "run_step", "step")
    tool_name = _get_any(ctx, "tool_name")
    tool_call_id = _get_any(ctx, "tool_call_id")
    retry = _get_any(ctx, "retry")
    max_retries = _get_any(ctx, "max_retries")

    # "Which agent is this?" varies; these fields may or may not exist.
    agent_name = _get_any(ctx, "agent_name", "name", "agent")
    model_name = _get_any(ctx, "model", "model_name", "llm_model")

    # deps type + (optional) a safe preview
    deps = _get_any(ctx, "deps")
    deps_type = type(deps).__name__ if deps is not None else None

    metadata = _get_any(ctx, "metadata")

    # Build a compact header line from whatever exists
    pieces = []
    if agent_name is not None:
        pieces.append(f"agent={agent_name!r}")
    if model_name is not None:
        pieces.append(f"model={model_name!r}")
    if run_id is not None:
        pieces.append(f"run_id={run_id!r}")
    if run_step is not None:
        pieces.append(f"step={run_step!r}")
    if tool_name is not None:
        pieces.append(f"tool={tool_name!r}")
    if tool_call_id is not None:
        pieces.append(f"tool_call_id={tool_call_id!r}")
    if retry is not None or max_retries is not None:
        pieces.append(f"retry={retry}/{max_retries}")
    if deps_type is not None:
        pieces.append(f"deps_type={deps_type}")

    header = "[ctx] " + " ".join(pieces) if pieces else "[ctx]"
    out = [header]

    # Optional: pretty-print metadata (often small and useful)
    if metadata is not None:
        meta_s = pformat(_dump_obj(metadata), width=width)
        meta_s = _wrap_text(meta_s, width=width, indent="  ")
        out.append("metadata:")
        out.append("  " + meta_s.replace("\n", "\n  "))

    return "\n".join(out)

# --------- message + part formatting ---------

def format_part(part, width: int = WRAP_COL,  max_chars=None):
    name = part.__class__.__name__

    # Some parts expose `content` (TextPart, ThinkingPart, ToolReturnPart, etc.)
    if hasattr(part, "content") and getattr(part, "content") is not None:
        content = _wrap_text(
            _short(getattr(part, "content", ""), max_chars),
            width=width,
            indent="  ",
        )
        return f"- {name}:\n  {content}"

    # Some versions/providers may put thinking on `.thinking`
    if hasattr(part, "thinking") and getattr(part, "thinking") is not None:
        thinking = _wrap_text(
            _short(getattr(part, "thinking", ""), max_chars),
            width=width,
            indent="  ",
        )
        return f"- {name}:\n  {thinking}"

    # Tool call parts usually have tool_name/args or similar
    tool_name = getattr(part, "tool_name", None) or getattr(part, "name", None)
    if tool_name:
        args = getattr(part, "args", None) or getattr(part, "arguments", None)
        args_s = pformat(_dump_obj(args), width=width)
        args_s = _wrap_text(args_s, width=width, indent="  ")
        return f"- {name}: tool={tool_name}\n  args:\n  {args_s}"

    # Fallback: dump it
    dumped = pformat(_dump_obj(part), width=width)
    dumped = _wrap_text(dumped, width=width, indent="  ")
    return f"- {name}:\n  {dumped}"

def format_message(msg, width: int = WRAP_COL, max_chars = None):
    mname = msg.__class__.__name__
    role = getattr(msg, "role", None)
    header = f"{mname}" + (f" role={role}" if role else "")

    if hasattr(msg, "content") and getattr(msg, "content") is not None:
        body = _wrap_text(_short(getattr(msg, "content"), max_chars), width=width, indent="  ")
        return header + "\n  " + body

    parts = getattr(msg, "parts", None)
    if parts:
        rendered = "\n".join(format_part(p, width=width, max_chars=max_chars) for p in parts)
        return header + "\n" + rendered

    dumped = pformat(_dump_obj(msg), width=width)
    dumped = _wrap_text(dumped, width=width, indent="  ")
    return header + "\n  " + dumped

# --------- main entry point ---------

def pretty_print_ctx_messages(ctx, width: int = WRAP_COL, show_ctx_summary: bool = True):
    if show_ctx_summary:
        print(format_ctx_summary(ctx, width=width), flush=True)

    msgs = getattr(ctx, "messages", None) or []
    print(f"ctx.messages ({len(msgs)}):", flush=True)

    for i, m in enumerate(msgs):
        print(f"\n--- message[{i}] ---", flush=True)
        print(format_message(m, width=width, max_chars=TRUNCATE_THRESH_LEN), flush=True)