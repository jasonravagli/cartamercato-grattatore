# DeepLaw Agent Guide

Select one of the following resources for detailed descriptions this project:

- [Project Snapshot](./coding-agents-res/project-snapshot.md)
- [Architecture](./coding-agents-res/architecture.md)
- [Technologies used](./coding-agents-res/technologies.md)
- [SW Engineering Guidelines and Coding Style](./coding-agents-res/developer-guidelines.md)
- [Execution flow and info](./coding-agents-res/execution.md)

## Source Tree Guidelines

### Scope

- This file defines cross-cutting rules for all `AGENTS.md` files in this repository.
- Nearest-file precedence still applies: a nested `AGENTS.md` can add stricter local rules.

### Keep AGENTS Aligned With Code

- If a code change makes any instruction in an `AGENTS.md` inaccurate, update the relevant `AGENTS.md` in the same change.
- This includes specific operational details (entry configs, bootstrap paths, command names, module paths, workflow steps).
- Do not leave stale guidance after refactors: outdated instructions are considered defects.

### Stability Over Churn

- Update `AGENTS.md` files only when needed to preserve correctness, safety, or clarity.
- Avoid rewriting guidance for minor code edits that do not change behavior, contracts, or workflows.
- Prefer small, targeted edits over broad style rewrites.

### Specific Details Policy

- Keep concrete details when they materially reduce ambiguity for agents.
- When a concrete detail is likely to change, keep it but pair it with clear maintenance responsibility.
- Example: if bootstrap initialization changes, update both code and all references to that bootstrap flow in `AGENTS.md`.

### Change Workflow

1. Check whether the planned code edit conflicts with any nearby `AGENTS.md` instruction.
2. Determine which docs and tests are affected before editing code; update them in the same change by default.
3. Remove or replace nearby template example code if the new work makes it obsolete.
4. If conflict exists, update the closest relevant `AGENTS.md` in the same PR/commit.
5. Keep the update minimal and scoped to changed behavior.
6. Preserve existing workflow unless there is a strong reason to change it.