from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Union, Optional
from abc import ABC, abstractmethod


@dataclass(frozen=True, slots=True)
class ExampleFile:
    """A single example file loaded from disk."""
    path: Path
    content: str

## Use this if there is any need for abstraction between Cad Generation classes
@dataclass 
class CadGenerationAgentDeps(ABC):
    
    @abstractmethod
    def load_examples(self) -> list[ExampleFile]:
        """Return the examples this CAD agent should use as reference."""
        raise NotImplementedError
    
@dataclass(slots=True)
class CadQueryGenDeps(CadGenerationAgentDeps):
        
    def load_examples(self) -> list[ExampleFile]:
        single_example = ExampleFile(
        path="/foo/bar/baz",
        content="CadQueryGenDeps still needs a  client implementation for the MCP server"
    )
        return [single_example]

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