# Python Coding Conventions

Python-specific naming, typing, and project conventions. Follows the Hungarian notation
system described in `CLAUDE-coding.md`, with the adaptations listed here.

---

## Scope Prefixes

| Prefix | Meaning |
|--------|---------|
| *(none)* | Local variable, or module-level global intended for import by other modules |
| `g_` | File-private (module-private) global — not intended for external import |

Note: no `m_` prefix on class members — `self.` already provides that context. No `s_`
prefix — Python has no static-scope equivalent.

---

## Python-Specific Tags

These supplement the shared tags in `CLAUDE-coding.md`:

| Tag | Type |
|-----|------|
| `str` | string (`str`) |
| `l` | list |
| `t` | `datetime` / Arrow instance |
| `dT` | duration / `timedelta` |
| `path` | `pathlib.Path` |
| `obj` | raw unvalidated dict (slurped from JSON/YAML) |

Container stacking follows the same capitalization rule as C++:

```python
lStrNames       # list of strings
mpStrInt        # dict mapping str → int
setStr          # set of strings
lEnumColor      # list of COLOR enum values
mpEnumStr       # dict mapping COLOR → str
```

---

## Variable Name Examples

```python
strName         # local string
lStrNames       # local list of strings
mpStrInt        # dict mapping str → int
setStr          # set of strings
tCreated        # datetime instance
dTElapsed       # duration / timedelta
cItems          # count of items
iItem           # index into item list
fEnabled        # bool flag
pathOutput      # filesystem Path
objConfig       # raw dict from YAML/JSON (unvalidated)
g_mpStrCache    # file-private module global dict
```

---

## Class and Type Naming

| Pattern | Usage |
|---------|-------|
| `CClassName` | Regular class |
| `SClassName` | Struct-like class (Pydantic model, dataclass, named tuple) |
| `IClassName` | Interface / abstract base class |
| `clsEnum` | Variable holding a class/type object |

Always comment the tag, even if it equals the class name:

```python
class CProxyFile:  # tag = prxf
    ...

class SDocumentArgs:  # tag = doca
    ...

class IRenderer:  # tag = rndr
    ...
```

---

## Enum Naming

```python
from enum import IntEnum

class COLOR(IntEnum):       # ALL_CAPS type name
    COLOR_Red   = 0
    COLOR_Green = 1
    COLOR_Blue  = 2
    COLOR_Max   = 3
    COLOR_Min   = 0
    COLOR_Nil   = -1
```

- Bit-flag enums: `F` as first letter — `FBUTTON`
- Instances holding multiple flags: `grf` prefix — `grfbutton`
- State enums: `S` as last letter — `BUTTONS`
- Classification enums: `K` as last letter — `COLORK`
- Nil sentinel = -1
- Subclass `IntEnum` (allows integer conversion, consistent with C++ plain-enum rule)
- Provide `_Max`, `_Min`, `_Nil = -1` sentinels on non-flag enums

---

## Function and Method Naming

Pattern: `[ReturnTypeTag]VerbNoun(...)`

```python
def FIsEmpty(self) -> bool: ...
def StrName(self) -> str: ...
def SetName(self, strName: str) -> None: ...
def PropagateChanges(self) -> None: ...

def FTryFindFile(strFile: str) -> tuple[bool, Path | None]: ...
def StrFromColor(color: COLOR) -> str: ...
def MpStrDocaLoad(pathYaml: Path) -> dict[str, SDocumentArgs]: ...
```

- Void functions: omit return tag — `PropagateChanges()`
- Bool queries: `FIs...` — `FIsEmpty()`
- May-fail functions returning bool: `FTry...` — `FTryFindFile()`
- Factory / lookup: return tag as prefix — `StrName()`, `PathOutput()`
- Setters: `Set...` — `SetName()`; no `Get` prefix for getters (use the return tag instead)

---

## Type Hints

- **Always** annotate all function parameters and return types.
- Add `from __future__ import annotations` at the top of every typed file (enables
  forward references without quotes — add inline comment `# Forward refs without quotes`).
- Prefer `X | None` over `Optional[X]` (Python 3.10+).
- Use `from typing import TYPE_CHECKING` for imports needed only at type-check time.

```python
from __future__ import annotations  # Forward refs without quotes

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .other_module import CWidget


def FTryLoad(pathYaml: Path) -> tuple[bool, SConfig | None]:
    ...
```

---

## Class Members

- No `m_` prefix — `self.` provides the same scoping signal as `m_` in C++.
- Comment all non-obvious member fields.
- Pydantic `S`-prefixed models: `frozen=True` by default.

```python
from pydantic import BaseModel, ConfigDict

class SDocumentArgs(BaseModel):  # tag = doca
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    strTitle: str
    pathOutput: Path
    cPages: int = 0                 # page count; 0 = unknown
```

---

## Data Loading

- Use **Pydantic** for all structured YAML/JSON loading into typed models.
- `S`-prefixed structs are the natural fit for Pydantic models.
- Use the `obj` tag for raw unvalidated dicts; switch to the model type once validated.
- Inject dict keys into models explicitly before construction when needed.

```python
objRaw: dict = yaml.safe_load(pathYaml.read_text())   # obj = raw/unvalidated
doca = SDocumentArgs.model_validate(objRaw)            # now it's a typed model
```

---

## Module Layout

Preferred project structure:

```
project/
├── src/
│   └── packagename/
│       ├── __init__.py
│       ├── common/         # shared utilities
│       └── commands/       # CLI subcommands
├── tests/
├── pyproject.toml
├── devenv.nix
├── .envrc
└── uv.lock
```

- `src/` layout with `pyproject.toml` — avoids import shadowing issues.
- `uv` for dependency management and lockfiles.
- `devenv` / `direnv` for automatic per-project environment activation.
- Editable installs via `uv sync` — no re-sync needed on source changes.
- CLI entry points defined in `[project.scripts]` in `pyproject.toml`.
- Relative imports (`from .common import helpers`) within a package.

---

## Indentation

Tabs, not spaces — consistent with the C++ standard. Tab stop = 4 spaces.

---

## Quick Reference

```
# Variable anatomy:    [scope][prefix][Tag][Detail][Suffix]
# scope:  g_ = file-private global  |  (none) = local or exported global
# prefix: c = count | i = index | f = bool | d = delta
# Tag:    str | n | g | f | t | dT | l | mp | set | obj | path
# Suffix: Min/Max/Mic/Mac/Cur/Prev/Next/Src/Dst

# Function anatomy:    [ReturnTag]VerbNoun
# void:           PropagateChanges()
# bool:           FIsEmpty() / FTryLoad()
# str:            StrName()
# Path:           PathOutput()
# dict[str, X]:   MpStrXLoad()
# datetime:       TCreated()   (note capital T — it's a return tag)

# Type prefixes:  C = class | S = struct/Pydantic | I = interface | ALL_CAPS = enum
```