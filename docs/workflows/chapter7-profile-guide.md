# Chapter 7 Profile Guide

## Purpose

`docs/workflows/chapter7-profile.json` is the repo-local override file for the Chapter 7 UI wiring toolchain.
Use it when a business repo needs different bucket mapping, closure task ids, task identity templates, labels, refs, headings, or surface defaults without forking the Python scripts.

## Load Order

1. Built-in defaults in `scripts/python/_chapter7_profile.py`
2. Optional repo-local override: `docs/workflows/chapter7-profile.json`
3. Optional explicit CLI override: `--chapter7-profile-path <path>`

The scripts deep-merge overrides over the built-in defaults.

## Common Files

- Active repo profile: `docs/workflows/chapter7-profile.json`
- Full seed: `docs/workflows/templates/chapter7-profile.template.json`
- Minimal seed: `docs/workflows/templates/chapter7-profile.minimal.example.json`

## Top-Level Fields

### `bucket_order`

Defines the traversal order for Chapter 7 slices.
Default value in this repo:

```json
[
  "entry",
  "loop",
  "combat",
  "economy",
  "meta",
  "governance"
]
```

### `fallback_bucket`

Used when a feature cannot be matched by task id or feature family.
Current value: `meta`

### `surface_aliases`

Maps logical surface names to node-name aliases used during closure detection.
Current keys:

```json
[
  "RuntimeHud",
  "SettingsMenu"
]
```

### `task_creation`

Controls task generation defaults used by `create_chapter7_tasks_from_ui_candidates.py`.
Important fields:

- `priority_by_bucket`: maps bucket to Taskmaster priority
- `layer_by_bucket`: maps bucket to `adapter` or `core`
- `view_priority_map`: maps master priority to view priority like `P1`
- `adr_refs`: default ADR refs for generated tasks
- `chapter_refs`: default chapter refs for generated tasks
- `base_labels`: labels appended to generated view rows
- `owners`: default owners for `NG` and `GM` rows
- `source_labels`: source labels for `NG` and `GM` rows
- `view_id_templates`: generated id format for `NG` and `GM`
- `default_story_templates`: derived story id templates

Current `task_creation` block:

```json
{
  "priority_by_bucket": {
    "entry": "high",
    "loop": "high",
    "combat": "high",
    "economy": "high",
    "meta": "medium",
    "governance": "medium",
    "default": "medium"
  },
  "layer_by_bucket": {
    "entry": "adapter",
    "loop": "adapter",
    "combat": "adapter",
    "economy": "adapter",
    "meta": "adapter",
    "governance": "core",
    "default": "adapter"
  },
  "view_priority_map": {
    "high": "P1",
    "medium": "P2",
    "low": "P3"
  },
  "adr_refs": [
    "ADR-0010",
    "ADR-0011",
    "ADR-0019",
    "ADR-0025"
  ],
  "chapter_refs": [
    "CH02",
    "CH06",
    "CH07",
    "CH10"
  ],
  "base_labels": [
    "taskmaster-view",
    "chapter7-ui"
  ],
  "owners": {
    "NG": "architecture",
    "GM": "gameplay"
  },
  "source_labels": {
    "NG": "backlog",
    "GM": "prd"
  },
  "view_id_templates": {
    "NG": "NG-{task_id:04d}",
    "GM": "GM-{task_id_plus_100:04d}"
  },
  "default_story_templates": {
    "back": "BACKLOG-{repo_label_upper_underscore}-M1",
    "gameplay": "PRD-{repo_label_upper_underscore}-v1.2"
  }
}
```

## Bucket Fields

Each bucket under `buckets.<name>` can override:

- `feature_task_ids`
- `feature_families`
- `slice_title`
- `screen_group`
- `audience`
- `ui_entry`
- `player_action`
- `system_response`
- `suggested_surfaces`
- `section_headings`
- `scene_rel_path`
- `closure_task_ids`
- `wiring_task_id`
- `semantics_defaults`
- `screen_contract`
- `screen_state`


## Field-To-Script Impact

| Field Area | Primary Consumer Scripts | Typical Effect |
| --- | --- | --- |
| `bucket_order`, `fallback_bucket` | `chapter7_ui_gdd_writer.py`, `run_chapter7_ui_wiring.py` | changes slice traversal order and fallback grouping |
| `surface_aliases` | `run_chapter7_ui_wiring.py` | changes closure detection for scene nodes and surface-path matching |
| `task_creation.adr_refs`, `chapter_refs` | `create_chapter7_tasks_from_ui_candidates.py` | changes generated task refs |
| `task_creation.base_labels`, `owners`, `source_labels` | `create_chapter7_tasks_from_ui_candidates.py` | changes generated view labels and ownership |
| `task_creation.view_id_templates` | `create_chapter7_tasks_from_ui_candidates.py` | changes generated `NG` / `GM` ids |
| `task_creation.default_story_templates` | `create_chapter7_tasks_from_ui_candidates.py` | changes derived story ids when CLI does not override them |
| `buckets.*.feature_task_ids`, `feature_families` | `chapter7_ui_gdd_writer.py` | changes how done tasks are grouped into Chapter 7 slices |
| `buckets.*.section_headings` | `run_chapter7_ui_wiring.py` | changes which audit sections are read during closure summary generation |
| `buckets.*.closure_task_ids`, `wiring_task_id` | `run_chapter7_ui_wiring.py` | changes which Chapter 7 task rows are treated as closure targets |
| `buckets.*.scene_rel_path` | `run_chapter7_ui_wiring.py` | changes which `.tscn` files are probed for implemented surfaces |
| `buckets.*.slice_title`, `screen_group`, `audience`, `ui_entry`, `player_action`, `system_response`, `suggested_surfaces`, `semantics_defaults`, `screen_contract`, `screen_state` | `chapter7_ui_gdd_writer.py` | changes generated UI GDD wording and candidate sidecar content |
| `--chapter7-profile-path` only | `run_chapter7_ui_wiring.py`, `chapter7_ui_gdd_writer.py`, `create_chapter7_tasks_from_ui_candidates.py`, `validate_chapter7_ui_wiring.py` | selects a non-default override file |

## Why This Repo Uses A Short Profile

The built-in defaults in `scripts/python/_chapter7_profile.py` already encode the template's base Chapter 7 behavior.
This repo-level `docs/workflows/chapter7-profile.json` is intentionally shorter and only keeps the fields that are useful as explicit, git-visible local policy:

- `surface_aliases`: local closure matching rules worth keeping visible
- `task_creation.*`: generated ids, owners, labels, and refs that business repos often need to customize first
- `buckets.*.section_headings`: explicit English + Chinese heading aliases that protect closure parsing against legacy audit docs

Everything else falls back to the built-in default profile.

## Typical Override Scenarios

### Different closure task ids

Override only:

```json
{
  "buckets": {
    "entry": {
      "closure_task_ids": [61],
      "wiring_task_id": 61
    }
  }
}
```

### Different generated ids, owners, or labels

Override only:

```json
{
  "task_creation": {
    "owners": {"NG": "design", "GM": "implementation"},
    "source_labels": {"NG": "plan", "GM": "delivery"},
    "view_id_templates": {"NG": "BK-{task_id:04d}", "GM": "GP-{task_id_plus_1000:04d}"}
  }
}
```

### Different heading aliases for legacy docs

Override only:

```json
{
  "buckets": {
    "entry": {
      "section_headings": [
        "### 6.1.1 MainMenu And Boot Flow",
        "### Custom Entry Flow"
      ]
    }
  }
}
```

## Field-To-Example Diff

### 1. Change closure task ids only

Use when the business repo does not use template defaults like `T41-T46` for Chapter 7 closure rows.

```json
{
  "buckets": {
    "entry": {
      "closure_task_ids": [61],
      "wiring_task_id": 61
    }
  }
}
```

### 2. Change generated ids and owners

Use when `NG-*` / `GM-*` naming or default ownership is not acceptable.

```json
{
  "task_creation": {
    "owners": {
      "NG": "design",
      "GM": "implementation"
    },
    "view_id_templates": {
      "NG": "BK-{task_id:04d}",
      "GM": "GP-{task_id_plus_1000:04d}"
    }
  }
}
```

### 3. Change derived story id templates

Use when generated `BACKLOG-*` / `PRD-*` story ids do not match the business repo naming scheme.

```json
{
  "task_creation": {
    "default_story_templates": {
      "back": "BACK-{repo_label_upper_underscore}-M2",
      "gameplay": "GAME-{repo_label_upper_underscore}-v2"
    }
  }
}
```

### 4. Change labels or default refs

Use when generated task rows must carry different ADR refs, chapter refs, or base labels.

```json
{
  "task_creation": {
    "adr_refs": ["ADR-9001"],
    "chapter_refs": ["CH77"],
    "base_labels": ["custom-view", "ui-slice"],
    "source_labels": {
      "NG": "plan",
      "GM": "delivery"
    }
  }
}
```

### 5. Add legacy heading aliases

Use when closure analysis must read existing audit docs that use different section titles.

```json
{
  "buckets": {
    "entry": {
      "section_headings": [
        "### 6.1.1 MainMenu And Boot Flow",
        "### Custom Entry Flow"
      ]
    }
  }
}
```

### 6. Expand beyond the short repo profile

Use the full seed when the business repo must also override task grouping, surface defaults, screen copy, or state-matrix wording.

Source file:

- `docs/workflows/templates/chapter7-profile.template.json`

Typical fields that require the full seed:

- `bucket_order`
- `fallback_bucket`
- `buckets.*.feature_task_ids`
- `buckets.*.feature_families`
- `buckets.*.ui_entry`
- `buckets.*.player_action`
- `buckets.*.system_response`
- `buckets.*.suggested_surfaces`
- `buckets.*.semantics_defaults`
- `buckets.*.screen_contract`
- `buckets.*.screen_state`

## Commands

Read-only self-check:

```powershell
py -3 scripts/python/run_chapter7_ui_wiring.py --delivery-profile fast-ship --chapter7-profile-path docs/workflows/chapter7-profile.json --self-check
```

Top-level entrypoint:

```powershell
py -3 scripts/python/dev_cli.py run-chapter7-ui-wiring --delivery-profile fast-ship --chapter7-profile-path docs/workflows/chapter7-profile.json --write-doc
```
