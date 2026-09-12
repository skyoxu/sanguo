#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one match in {path}, found {count}")
    write(path, text.replace(old, new, 1))


# 1. Sanguo-native Project Health fallback.
replace_once(
    "scripts/python/project_health_knowledge.py",
    """DEFAULT_CONFIG = {\n    'source_paths': SOURCE_PATHS,\n    'source_path_bindings': SOURCE_PATH_BINDINGS,\n    'gdd_paths': ['docs/gdd/ui-gdd-flow.md'],\n    'task_scene_bindings': [{\n        'task_id': 115, 'scene': 'Game.Godot/Scenes/Reward.tscn', 'node': '.',\n        'script': 'Game.Godot/Scripts/RewardScene.gd',\n        'witness': 'func _claim_reward(reward_type: String, selected_card_id: String, selected_index: int) -> void:'\n    }],\n    'query_aliases': {'奖励': ['Reward'], '存档': ['Save'], '战斗': ['Combat']},\n}\n""",
    """DEFAULT_CONFIG = {\n    'source_paths': SOURCE_PATHS,\n    'source_path_bindings': SOURCE_PATH_BINDINGS,\n    'gdd_paths': ['docs/gdd/ui-gdd-flow.md'],\n    'task_scene_bindings': [{\n        'task_id': 192, 'scene': 'Game.Godot/Scenes/UI/Task192MainMenuSurface.tscn', 'node': '.',\n        'script': 'Game.Godot/Scripts/UI/Task192MainMenuSurface.gd',\n        'witness': 'func get_surface_contract_key() -> String:'\n    }],\n    'query_aliases': {\n        '主菜单': ['MainMenu'], '开始菜单': ['MainMenu'], '设置': ['Settings'],\n        '战斗': ['Battle', 'SanguoBattle'], '三国': ['Sanguo']\n    },\n}\n""",
)

# 2. Full knowledge-link rebuild must replace, not merge with, prior generated entries.
replace_once(
    "scripts/python/generate_knowledge_links.py",
    """        catalog_entries = [entry for entry in catalog.get('entries', [])\n                           if not task_ids or str(entry.get('task_id')) not in task_ids]\n        unique = {entry.get('id'): entry for entry in catalog_entries + entries}\n        catalog['entries'] = list(unique.values())\n""",
    """        if task_ids is None:\n            catalog_entries = []\n        else:\n            catalog_entries = [entry for entry in catalog.get('entries', [])\n                               if str(entry.get('task_id')) not in task_ids]\n        unique = {entry.get('id'): entry for entry in catalog_entries + entries}\n        catalog['project'] = 'sanguo'\n        catalog['entries'] = list(unique.values())\n""",
)
replace_once(
    "scripts/python/init_knowledge_catalog.py",
    '"catalog/knowledge-catalog.json": {"schema_version": "1.0", "project": "newrouge", "entries": [], "last_scan_revision": None},',
    '"catalog/knowledge-catalog.json": {"schema_version": "1.0", "project": "sanguo", "entries": [], "last_scan_revision": None},',
)

# 3. Publication freshness: exact commit is not required after a derived-only publication commit,
# but every authority source must still be byte-identical and the published commit must be an ancestor.
publish_path = "scripts/python/publish_knowledge_catalog.py"
publish_helper = '''\n\ndef _snapshot_fresh(root: Path, snapshot: dict[str, Any]) -> bool:\n    ref = snapshot.get("ref")\n    commit = snapshot.get("commit")\n    sources = snapshot.get("sources")\n    if not isinstance(ref, str) or not isinstance(commit, str) or not isinstance(sources, list):\n        return False\n    current = _git(root, "rev-parse", ref)\n    if current.returncode:\n        return False\n    current_commit = current.stdout.strip()\n    ancestor = _git(root, "merge-base", "--is-ancestor", commit, current_commit)\n    if ancestor.returncode:\n        return False\n    for source in sources:\n        if not isinstance(source, dict) or not isinstance(source.get("path"), str) or not isinstance(source.get("sha256"), str):\n            return False\n        blob = subprocess.run(\n            ["git", "-C", str(root), "show", f"{current_commit}:{source['path']}"],\n            capture_output=True,\n            check=False,\n        )\n        if blob.returncode or hashlib.sha256(blob.stdout).hexdigest() != source["sha256"]:\n            return False\n    return True\n'''
replace_once(
    publish_path,
    """def _control_plane_clean(root: Path) -> bool:\n    completed = _git(root, \"status\", \"--porcelain\", \"--\", *CONTROL_PLANE_PATHS)\n    return completed.returncode == 0 and not completed.stdout.strip()\n""",
    """def _control_plane_clean(root: Path) -> bool:\n    completed = _git(root, \"status\", \"--porcelain\", \"--\", *CONTROL_PLANE_PATHS)\n    return completed.returncode == 0 and not completed.stdout.strip()\n""" + publish_helper,
)
replace_once(
    publish_path,
    """    if require_current_ref:\n        current = _git(root, \"rev-parse\", str(manifest.get(\"authority_ref\")))\n        if current.returncode or current.stdout.strip() != manifest.get(\"main_commit\"):\n            raise PublicationBlocked(\"authority_ref_moved\")\n    return manifest, artifacts\n""",
    """    if require_current_ref:\n        snapshot = artifacts.get(\"snapshot\")\n        if (not isinstance(snapshot, dict)\n                or snapshot.get(\"ref\") != manifest.get(\"authority_ref\")\n                or snapshot.get(\"commit\") != manifest.get(\"main_commit\")\n                or not _snapshot_fresh(root, snapshot)):\n            raise PublicationBlocked(\"authority_ref_moved\")\n    return manifest, artifacts\n""",
)

# 4. Locator uses source-equivalence freshness, not raw HEAD equality.
replace_once(
    "scripts/python/knowledge_locator.py",
    """def _fresh(root: Path, catalog: dict[str, Any]) -> bool:\n    snapshot = catalog.get(\"source_snapshot\", {})\n    ref = snapshot.get(\"ref\")\n    commit = snapshot.get(\"commit\")\n    if not isinstance(ref, str) or not isinstance(commit, str):\n        return False\n    current = subprocess.run([\"git\", \"-C\", str(root), \"rev-parse\", ref], capture_output=True, text=True, encoding=\"utf-8\", check=False)\n    if current.returncode or current.stdout.strip() != commit:\n        return False\n    for source in snapshot.get(\"sources\", []):\n        if not isinstance(source, dict):\n            return False\n        if _git_blob_hash(root, commit, str(source.get(\"path\", \"\"))) != source.get(\"sha256\"):\n            return False\n    return True\n""",
    """def _fresh(root: Path, catalog: dict[str, Any]) -> bool:\n    snapshot = catalog.get(\"source_snapshot\", {})\n    ref = snapshot.get(\"ref\")\n    commit = snapshot.get(\"commit\")\n    sources = snapshot.get(\"sources\")\n    if not isinstance(ref, str) or not isinstance(commit, str) or not isinstance(sources, list):\n        return False\n    current = subprocess.run([\"git\", \"-C\", str(root), \"rev-parse\", ref], capture_output=True, text=True, encoding=\"utf-8\", check=False)\n    if current.returncode:\n        return False\n    current_commit = current.stdout.strip()\n    ancestor = subprocess.run([\"git\", \"-C\", str(root), \"merge-base\", \"--is-ancestor\", commit, current_commit], capture_output=True, check=False)\n    if ancestor.returncode:\n        return False\n    for source in sources:\n        if not isinstance(source, dict):\n            return False\n        if _git_blob_hash(root, current_commit, str(source.get(\"path\", \"\"))) != source.get(\"sha256\"):\n            return False\n    return True\n""",
)

# 5. Freeze uses the canonical catalog snapshot to permit derived-only publication commits.
freeze_path = "scripts/python/freeze_knowledge_context.py"
freeze_helper = '''\n\ndef _snapshot_fresh(root: Path, snapshot: dict[str, Any]) -> bool:\n    ref = snapshot.get("ref")\n    commit = snapshot.get("commit")\n    sources = snapshot.get("sources")\n    if not isinstance(ref, str) or not isinstance(commit, str) or not isinstance(sources, list):\n        return False\n    current = _git_text(root, "rev-parse", ref)\n    completed = subprocess.run(\n        ["git", "-C", str(root), "merge-base", "--is-ancestor", commit, current],\n        capture_output=True,\n        check=False,\n    )\n    if completed.returncode:\n        return False\n    for source in sources:\n        if not isinstance(source, dict):\n            return False\n        path = source.get("path")\n        expected = source.get("sha256")\n        if not isinstance(path, str) or not isinstance(expected, str):\n            return False\n        try:\n            current_blob = _git_blob(root, current, path)\n        except FreezeBlocked:\n            return False\n        if hashlib.sha256(current_blob).hexdigest() != expected:\n            return False\n    return True\n'''
replace_once(
    freeze_path,
    """def _policy(root: Path, consumer: str, policy_revision: str) -> dict[str, Any]:\n""",
    freeze_helper + "\n\ndef _policy(root: Path, consumer: str, policy_revision: str) -> dict[str, Any]:\n",
)
replace_once(
    freeze_path,
    """    if _git_text(root, \"rev-parse\", ref) != commit:\n        raise FreezeBlocked(\"authority_ref_moved\")\n    publication_generation, publication_sha256 = _publication_lineage(root, commit)\n""",
    """    catalog = json.loads((root / \"knowledge/catalogs/repository-knowledge-catalog.v1.json\").read_text(encoding=\"utf-8\"))\n    authority_snapshot = catalog.get(\"source_snapshot\", {})\n    if (not isinstance(authority_snapshot, dict)\n            or authority_snapshot.get(\"ref\") != ref\n            or authority_snapshot.get(\"commit\") != commit\n            or not _snapshot_fresh(root, authority_snapshot)):\n        raise FreezeBlocked(\"authority_ref_moved\")\n    publication_generation, publication_sha256 = _publication_lineage(root, commit)\n""",
)

# 6. Project Health behavior validates reproducible current publication in the checkout,
# instead of requiring a committed generated pointer to equal every post-merge HEAD.
replace_once(
    ".github/workflows/project-health-behavior.yml",
    """      - name: Knowledge control plane regressions\n        shell: pwsh\n        run: |\n          py -3 scripts/python/validate_knowledge_control_plane.py\n          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n          py -3 scripts/python/publish_knowledge_catalog.py --check\n          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n""",
    """      - name: Knowledge control plane regressions\n        shell: pwsh\n        run: |\n          py -3 scripts/python/publish_knowledge_catalog.py --publish\n          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n          py -3 scripts/python/publish_knowledge_catalog.py --check\n          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n          py -3 scripts/python/validate_knowledge_control_plane.py --require-generated\n          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n""",
)

# 7. Business identity text only; protocol/schema namespace remains unchanged.
replace_once("knowledge/README.md", "# newrouge Repository Knowledge Control Plane\n", "# Sanguo Repository Knowledge Control Plane\n")

# 8. Regression coverage for fallback and full-rebuild semantics.
replace_once(
    "scripts/sc/tests/test_project_health_sanguo_config.py",
    "from project_health_knowledge import load_config, validate_config\n",
    "from project_health_knowledge import DEFAULT_CONFIG, load_config, validate_config\n",
)
replace_once(
    "scripts/sc/tests/test_project_health_sanguo_config.py",
    """    def test_query_aliases_cover_sanguo_navigation_terms(self) -> None:\n""",
    """    def test_fallback_default_config_is_sanguo_native(self) -> None:\n        binding = DEFAULT_CONFIG[\"task_scene_bindings\"][0]\n        self.assertEqual(binding[\"task_id\"], 192)\n        self.assertEqual(binding[\"scene\"], \"Game.Godot/Scenes/UI/Task192MainMenuSurface.tscn\")\n        self.assertNotIn(\"Reward\", json.dumps(DEFAULT_CONFIG, ensure_ascii=False))\n        self.assertIn(\"Sanguo\", DEFAULT_CONFIG[\"query_aliases\"][\"三国\"])\n\n    def test_query_aliases_cover_sanguo_navigation_terms(self) -> None:\n""",
)

write(
    "scripts/python/tests/test_generate_knowledge_links.py",
    '''from __future__ import annotations\n\nimport json\nimport sys\nimport tempfile\nimport unittest\nfrom pathlib import Path\nfrom unittest import mock\n\nROOT = Path(__file__).resolve().parents[3]\nPYTHON_DIR = ROOT / "scripts" / "python"\nif str(PYTHON_DIR) not in sys.path:\n    sys.path.insert(0, str(PYTHON_DIR))\n\nimport generate_knowledge_links as module\n\n\nclass GenerateKnowledgeLinksTests(unittest.TestCase):\n    def test_full_rebuild_replaces_stale_catalog_entries(self) -> None:\n        with tempfile.TemporaryDirectory() as temporary:\n            root = Path(temporary)\n            base = root / "logs/ci/project-health-knowledge"\n            base.mkdir(parents=True)\n            (base / "latest.json").write_text(json.dumps({\n                "revision": "a" * 40,\n                "tasks": [{"task": {"id": 192, "title": "Main Menu", "test_refs": []}}],\n            }), encoding="utf-8")\n            catalog = root / "docs/knowledge/catalog/knowledge-catalog.json"\n            catalog.parent.mkdir(parents=True)\n            catalog.write_text(json.dumps({\n                "schema_version": "1.0",\n                "project": "newrouge",\n                "entries": [{"id": "scene:115:Reward", "task_id": "115", "path": "Reward.tscn"}],\n                "last_scan_revision": None,\n            }), encoding="utf-8")\n            navigation = {\n                "configs": [{"path": "Game.Core/Data/sanguo.json", "focus": "core"}],\n                "assets": [], "scenes": [], "code": [],\n            }\n            with mock.patch.object(module, "base_dir", return_value=base), mock.patch.object(module, "build_navigation", return_value=navigation):\n                result = module.generate(root)\n            self.assertEqual(result["entries"], 1)\n            rebuilt = json.loads(catalog.read_text(encoding="utf-8"))\n            self.assertEqual(rebuilt["project"], "sanguo")\n            self.assertEqual([entry["task_id"] for entry in rebuilt["entries"]], ["192"])\n            self.assertNotIn("Reward", json.dumps(rebuilt))\n\n\nif __name__ == "__main__":\n    unittest.main()\n''',
)

# 9. Publication regression coverage: derived-only HEAD movement is accepted,
# authority source movement still fails closed.
replace_once(
    "scripts/python/tests/test_knowledge_publication.py",
    """    def test_check_blocks_when_bound_control_plane_artifact_drifts(self) -> None:\n""",
    """    def test_check_accepts_derived_only_commit_after_publication(self) -> None:\n        first = self.run_publish(\"--publish\")\n        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)\n        subprocess.check_call([\"git\", \"add\", \"knowledge/catalogs\", \"knowledge/snapshots\", \"knowledge/projections\", \"knowledge/indexes\"], cwd=self.repo)\n        subprocess.check_call([\"git\", \"commit\", \"-m\", \"publish derived state\"], cwd=self.repo, stdout=subprocess.DEVNULL)\n        check = self.run_publish(\"--check\")\n        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)\n\n    def test_check_blocks_when_authority_source_moves_after_publication(self) -> None:\n        first = self.run_publish(\"--publish\")\n        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)\n        readme = self.repo / \"README.md\"\n        readme.write_text(\"# Game\\nChanged authority.\\n\", encoding=\"utf-8\")\n        subprocess.check_call([\"git\", \"add\", \"README.md\"], cwd=self.repo)\n        subprocess.check_call([\"git\", \"commit\", \"-m\", \"move authority\"], cwd=self.repo, stdout=subprocess.DEVNULL)\n        check = self.run_publish(\"--check\")\n        self.assertNotEqual(check.returncode, 0)\n        self.assertEqual(json.loads(check.stdout)[\"reason\"], \"authority_ref_moved\")\n\n    def test_check_blocks_when_bound_control_plane_artifact_drifts(self) -> None:\n""",
)

# 10. Locator/freeze regression: generated-state-only commit does not invalidate the authority snapshot.
replace_once(
    "scripts/python/tests/test_knowledge_freeze.py",
    """    def test_freeze_blocks_after_authority_ref_moves(self) -> None:\n""",
    """    def test_locator_and_freeze_allow_derived_publication_commit(self) -> None:\n        bundle = self.bundle()\n        bundle_rel, decisions_rel = self.inputs(bundle)\n        subprocess.check_call([\"git\", \"add\", \"knowledge/catalogs\", \"knowledge/snapshots\", \"knowledge/projections\", \"knowledge/indexes\"], cwd=self.repo)\n        subprocess.check_call([\"git\", \"commit\", \"-m\", \"publish derived state\"], cwd=self.repo, stdout=subprocess.DEVNULL)\n        refreshed = self.bundle()\n        self.assertEqual(refreshed[\"snapshot\"], bundle[\"snapshot\"])\n        completed = self.freeze(bundle_rel, decisions_rel)\n        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)\n\n    def test_freeze_blocks_after_authority_ref_moves(self) -> None:\n""",
)

# 11. Long-lived publication workflow adapted from upstream.
write(
    ".github/workflows/publish-knowledge-catalog.yml",
    '''name: Publish knowledge catalog\n\non:\n  push:\n    branches: [main]\n    paths:\n      - ".github/workflows/publish-knowledge-catalog.yml"\n      - "README.md"\n      - "AGENTS.md"\n      - "workflow.md"\n      - "DELIVERY_PROFILE.md"\n      - "docs/**"\n      - ".taskmaster/**"\n      - "Game.Core/Contracts/**"\n      - "knowledge/policies/**"\n      - "knowledge/evaluation/**"\n      - "scripts/python/_knowledge_catalog_builder.py"\n      - "scripts/python/_knowledge_locator_core.py"\n      - "scripts/python/knowledge_locator.py"\n      - "scripts/python/freeze_knowledge_context.py"\n      - "scripts/python/publish_knowledge_catalog.py"\n      - "scripts/python/prepare_knowledge_context.py"\n      - "scripts/python/validate_knowledge_control_plane.py"\n  workflow_dispatch:\n\npermissions:\n  contents: write\n  pull-requests: write\n\nconcurrency:\n  group: knowledge-catalog-main\n  cancel-in-progress: false\n\njobs:\n  publish:\n    runs-on: windows-latest\n    steps:\n      - uses: actions/checkout@v4\n        with:\n          fetch-depth: 0\n\n      - uses: actions/setup-python@v5\n        with:\n          python-version: '3.x'\n\n      - name: Publish and validate\n        shell: pwsh\n        run: |\n          py -3 scripts/python/publish_knowledge_catalog.py --publish\n          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n          py -3 scripts/python/publish_knowledge_catalog.py --check\n          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n          py -3 scripts/python/validate_knowledge_control_plane.py --require-generated\n          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n\n      - name: Open generated-state pull request\n        shell: pwsh\n        env:\n          GH_TOKEN: ${{ github.token }}\n        run: |\n          $changes = git status --porcelain -- knowledge\n          if (-not $changes) {\n            Write-Host "Generated state is already current."\n            exit 0\n          }\n          $branch = "automation/knowledge-catalog-$($env:GITHUB_SHA.Substring(0,12))"\n          git config user.name "github-actions[bot]"\n          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"\n          git switch -c $branch\n          git add knowledge\n          git commit -m "chore(knowledge): publish catalog for main $env:GITHUB_SHA"\n          git push --set-upstream origin $branch\n          gh pr create --base main --head $branch --title "chore(knowledge): publish catalog for main" --body "Automated publication of derived knowledge state for main commit $env:GITHUB_SHA. The publication stays valid after merge only while its authority-source hashes remain unchanged."\n''',
)

print("third-round patch staged")
