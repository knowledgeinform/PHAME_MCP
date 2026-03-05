from __future__ import annotations
import yaml

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Union, Optional
from abc import ABC, abstractmethod

from phame.haystack.cad_query_rag import build_query_pipeline
from phame.haystack.trusted_references_rag import make_chroma_document_store

# getting cadquery models
CHROMA_PERSIST = "./chroma_db/cadquery_example_parts/db/"
document_store = make_chroma_document_store(CHROMA_PERSIST)
with open(CHROMA_PERSIST + "metadata.yaml") as fp:
    metadata = yaml.safe_load(fp)

if "embedding_model" in metadata:
    EMBED_MODEL = metadata["embedding_model"]
else:
    assert 0, f"no metadata file in cadquery db: {CHROMA_PERSIST}"

cq_rag_pipeline = build_query_pipeline(document_store, EMBED_MODEL)



@dataclass(frozen=True, slots=True)
class ExampleFile:
    """A single example file loaded from disk."""
    path: Path
    content: str

@dataclass(frozen=True, slots=True)
class ExampleCQFile:
    """A single example file loaded from disk."""
    description: str
    code: str

## Use this if there is any need for abstraction between Cad Generation classes
@dataclass 
class CadGenerationAgentDeps(ABC):
    
    @abstractmethod
    def load_examples(self) -> list[ExampleFile]:
        """Return the examples this CAD agent should use as reference."""
        raise NotImplementedError
    
@dataclass(slots=True)
class CadQueryGenDeps(CadGenerationAgentDeps):

    def load_examples(self, design: str, top_k: int=3) -> list[ExampleCQFile]:

        result = cq_rag_pipeline.run(
            {
                "text_embedder": {"text": design},  # must be string
                "retriever": {"top_k": top_k},
            }
        )
        docs = result["retriever"]["documents"]

        out = []
        for d in docs:
            out.append(ExampleCQFile(description=d.content, code=d.meta['cad_code']))

        return out

@dataclass(slots=True)
class SolidworksExampleDeps(CadGenerationAgentDeps):
    """
    Deps container for a macro/code-generator agent.

    Provide one or more directories containing example files. At runtime,
    the agent/tool can call .load_examples() to read them into memory.
    """

    example_dirs: list[Path] = field(default_factory=list)

    # Optional filters / safety limits
    include_globs: tuple[str, ...] = ("**/*.py",)
    exclude_globs: tuple[str, ...] = ("**/.git/**", "**/__pycache__/**", "**/*.pyc", "**/*.vba", "**/*.bas", "**/*.txt", "**/*.md")
    max_files: int = 50
    max_bytes_per_file: int = 200_000  # ~200 KB per file

    def add_dir(self, path: str | Path) -> None:
        p = Path(path).expanduser().resolve()
        self.example_dirs.append(p)

    def iter_example_paths(self) -> Iterable[Path]:
        """Yield candidate example files from example_dirs applying include/exclude globs."""
        seen: set[Path] = set()

        def excluded(p: Path) -> bool:
            s = p.as_posix()
            for g in self.exclude_globs:
                # cheap-ish glob-like check: use Path.match for patterns
                if p.match(g):
                    return True
            return False

        for d in self.example_dirs:
            d = d.expanduser().resolve()
            if not d.exists() or not d.is_dir():
                continue

            for g in self.include_globs:
                for p in d.glob(g):
                    if not p.is_file():
                        continue
                    p = p.resolve()
                    if p in seen:
                        continue
                    if excluded(p):
                        continue
                    seen.add(p)
                    yield p

    def load_examples(self) -> list[ExampleFile]:
        """
        Read example files into memory (bounded by max_files and max_bytes_per_file).
        """
        out: list[ExampleFile] = []
        for i, p in enumerate(self.iter_example_paths()):
            if i >= self.max_files:
                break
            try:
                data = p.read_bytes()
            except OSError:
                continue

            if len(data) > self.max_bytes_per_file:
                # Skip huge files; you can also truncate instead if you prefer.
                continue

            # Decode with a forgiving strategy; most macros/examples will be utf-8.
            text = data.decode("utf-8", errors="replace")
            out.append(ExampleFile(path=p, content=text))

        return out

    def load_examples_text(self, header: bool = True) -> str:
        """
        Convenience: return a single string blob suitable to inject into prompts.
        """
        examples = self.load_examples()
        parts: list[str] = []
        for ex in examples:
            if header:
                parts.append(f"\n### {ex.path.name}\n")
            parts.append(ex.content)
        return "\n".join(parts).strip()


CadGenAgentDeps = Union[CadQueryGenDeps, SolidworksExampleDeps]