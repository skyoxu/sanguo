# Workflow Source Summary: Chapter 2

Generated from the template repo `workflow.md` by `scripts/python/update_workflow_chapter_skills.py`.

- Canonical English name: Repository Bootstrap
- Source line span: 86-167
- Heading count: 6
- Command-like line count: 4
- Artifact/reference line count: 0

## Headings

- 2. Repository Bootstrap
- 2.1 Clean name and path residue
- 2.2 Rebuild entry indexes
- 2.3 Run repository-level hard checks immediately
- 2.4 Optional local project-health page service
- 2.5 Optional OpenAI backend bootstrap

## Command And Artifact Signals

- `py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "$env:GODOT_BIN"`
- `py -3 scripts/python/dev_cli.py inspect-run --kind local-hard-checks`
- `py -3 scripts/python/dev_cli.py serve-project-health`
- `py -3 scripts/python/dev_cli.py project-health-scan --serve`

## Repository-Specific Extension

After Chapter 2 initialization, create `docs/prd`, `docs/gdd`, and `docs/prototypes`.

Then ask the player in two separate prompts:

1. Game name.
2. Game type or reference game name.

Classify the second answer with `codex exec` against the 24 canonical ids in `docs/game-type-guides/game-types.csv`. Persist the resulting metadata in both `AGENTS.md` and `README.md` under `## Game Project Metadata`.
