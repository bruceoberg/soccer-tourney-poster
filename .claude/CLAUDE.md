# CLAUDE.md — soccer-tourney-poster (`stp`)

Generates print-ready PDF posters of soccer tournament schedules (group standings +
elimination bracket) from Excel data. One tournament can be rendered across ~25
languages, any IANA timezone, and many paper sizes. Live at
<http://soccer-tournament-poster.com>.

## Conventions

Follow the user's global rules in `~/.claude/` — **tabs not spaces**, Hungarian
notation, `from __future__ import annotations` atop every typed file, Pydantic
`S`-models `frozen=True`. Match the surrounding code; it is already consistent.

## Where things live

The package is `src/stp/`. Responsibilities, roughly:

- **Orchestration** — entry point, worklist build, serial/parallel render, `manifest.yaml`
  assembly for the website.
- **Config** — CLI args (typed-argument-parser) and the Pydantic models behind
  `config.yaml`'s named documents.
- **Data** — parsing tournament `.xlsx` into teams / matches / groups / results / colors.
- **Drawing** — one module per poster element (group standings, daily calendar,
  elimination bracket, final match), each a `bolay.CBlot` subclass, assembled by the
  `CPage` base + its page-kind subclasses.
- **Localization** — gettext `.po` lookups, timezone display names, paper-format best-fit.
- **Support** — font registry (style × script → TTF), git versioning for PDF metadata,
  cProfile wrapper + diff CLI.

Data lives alongside code: `database/` (tournament `.xlsx`, filename starts with a digit),
`fonts/` (Noto/CJK/Arabic/handwritten TTFs), `localization/` (`stp.pot` + `stp-<lang>.po`).
Outside `src/`: `bolay/` (PDF layout library, git submodule — see `bolay/CLAUDE.md`),
`published/` (committed sample PDFs), `playground/` (default `-o` output), `profiles/`
(cProfile dumps), `scripts/` (translation helpers driven via the justfile).

## How it works (data flow)

1. `stp -t <tournament> -d <document>` → `config.py:ParseArgs` loads `config.yaml`.
2. `database.py:CTournamentDataBase.TournFromStrName` parses the `.xlsx` (openpyxl) into
   teams (seeded e.g. `A1`), matches (staged Group→…→Final, elim stages **inferred** from
   feeder ids), per-team results, and per-group colors. Singleton-cached.
3. Each `SPageArgs` (tz, locale, format, page_kind, scoring, coloring) → a `CPage`
   subclass. Times convert to the page timezone; `CTomorrowTime` renders post-midnight
   matches as 24+ hours.
4. The page draws `bolay.CBlot` subclasses (group, day, elim, final) into a `bolay.CPdf`
   (fpdf2). All text comes from gettext `.po` lookups; RTL handled for ar/fa.
5. `main.py` builds pages serially or via `ProcessPoolExecutor` (`-j`), writes the PDF,
   and — when unwinding/grid-filling — emits a `manifest.yaml` listing every
   tz × language × format combination for the website.

## CLI

`stp` (entry `stp.main:main`):
- `-t/--tournament` name from `database/` (or `latest`)
- `-d/--document` key in `config.yaml` (default = the one marked `default: true`)
- `-o/--output_dir` (default `playground`)
- `-j/--jobs` workers (0 = auto, 1 = serial)
- `--profile` / `--profile_dump <file.prof>`

`config.yaml`: each top-level key is a document — `tournament`, optional `coloring`
(srgb/gracol/swop/fogra ICC), `file_suffix`, and a `pages` list of per-page overrides
(`tz`, `loc`, `format`, `page_kind`, `orientation`, `scoring`). Scoring modes:
`fixtures` (blank boxes), `archive` (filled results), `instructions`.

## Environment & commands

devenv + direnv (`devenv.nix`); `uv` for deps with `bolay` as a **workspace member**
(`[tool.uv.workspace]`). Python 3.13. System pkgs: gettext, just, icu.

- `stp -t 2026-mens-world-cup` — generate into `playground/`
- `just publish` — render the latest tournament into `published/` and stage it
- `just pot-push` / `just po-accept <files>` — sync translation strings
- `stp-profile-diff before.prof after.prof` — compare profiling runs

## Gotchas

- Elimination stages aren't in the spreadsheet explicitly — they're derived from match
  feeder ids (`W1`/`L2`…); bracket order comes from a DFS off the final (`sortElim`).
- Module-level singletons load at import: `loc.g_loc`, `versioning.g_repover`,
  the tournament cache. Keep import side effects in mind when refactoring.
- A timezone that maps two cities to the same name aborts the run — add an override.
- See `todo.md` for the planned layout-engine rework (`SRect`/`SVector`/`CBlotSet`).
