#!/usr/bin/env python3
"""Create a minimal Godot prototype scene scaffold under Game.Godot/Prototypes."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8", newline="\n")


def sanitize_slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value or "").strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-_")
    return cleaned or "prototype"


def slug_to_pascal(slug: str) -> str:
    parts = [part for part in re.split(r"[-_]+", slug) if part]
    return "".join(part[:1].upper() + part[1:] for part in parts) or "Prototype"


def render_script(*, class_name: str, scene_root: str) -> str:
    return "\n".join(
        [
            "using Godot;",
            "",
            "namespace Game.Godot.Prototypes;",
            "",
            f"public partial class {class_name} : {scene_root}",
            "{",
            "    public override void _Ready()",
            "    {",
            '        GD.Print("Prototype scaffold ready: replace this scene with the minimum playable loop.");',
            "    }",
            "}",
            "",
        ]
    )


def render_scene(*, class_name: str, scene_root: str, script_res_path: str) -> str:
    lines = [
        "[gd_scene load_steps=2 format=3]",
        "",
        f'[ext_resource type="Script" path="{script_res_path}" id="1"]',
        "",
        f'[node name="{class_name}" type="{scene_root}"]',
        'script = ExtResource("1")',
    ]
    if scene_root == "Control":
        lines += [
            "layout_mode = 3",
            "anchors_preset = 15",
            "anchor_right = 1.0",
            "anchor_bottom = 1.0",
            "grow_horizontal = 2",
            "grow_vertical = 2",
            "",
            '[node name="PrototypeHint" type="Label" parent="."]',
            "layout_mode = 0",
            "offset_left = 24.0",
            "offset_top = 24.0",
            "offset_right = 640.0",
            "offset_bottom = 80.0",
            'text = "Replace this scaffold with your minimum playable loop."',
        ]
    else:
        lines += [
            "",
            '[node name="PrototypeLoop" type="Node2D" parent="."]',
        ]
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Create a minimal prototype scene scaffold.")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--prototype-root", default="Game.Godot/Prototypes")
    ap.add_argument("--scene-root", default="Control", choices=["Control", "Node2D"])
    ap.add_argument("--force", action="store_true", help="Overwrite the scaffold when files already exist.")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = (Path(args.repo_root).resolve() if str(args.repo_root or "").strip() else repo_root())
    slug = sanitize_slug(args.slug)
    pascal = slug_to_pascal(slug)
    class_name = f"{pascal}Prototype"
    prototype_dir = root / args.prototype_root / slug
    scene_path = prototype_dir / f"{class_name}.tscn"
    script_path = prototype_dir / "Scripts" / f"{class_name}.cs"
    assets_dir = prototype_dir / "Assets"

    if (scene_path.exists() or script_path.exists()) and not args.force:
        print(
            f"PROTOTYPE_SCENE ERROR: scaffold already exists for slug={slug}; pass --force to overwrite.",
            file=sys.stderr,
        )
        return 1

    ensure_dir(assets_dir)
    script_res_path = f"res://{args.prototype_root.strip('/').replace(chr(92), '/')}/{slug}/Scripts/{class_name}.cs"
    write_text(script_path, render_script(class_name=class_name, scene_root=str(args.scene_root)))
    write_text(
        scene_path,
        render_scene(
            class_name=class_name,
            scene_root=str(args.scene_root),
            script_res_path=script_res_path,
        ),
    )
    print(
        "PROTOTYPE_SCENE created "
        f"scene={scene_path.relative_to(root).as_posix()} "
        f"script={script_path.relative_to(root).as_posix()}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
