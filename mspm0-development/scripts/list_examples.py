#!/usr/bin/env python3
"""列出技能包内可复用的 MSPM0 工程模板。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - 命令行工具保留简洁诊断
        return {"name": path.parent.name, "error": str(exc)}
    if not isinstance(data, dict):
        return {"name": path.parent.name, "error": "manifest is not an object"}
    return data


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return str(value)


def clock_text(manifest: dict[str, Any]) -> str:
    clock = manifest.get("clock")
    if not isinstance(clock, dict):
        return ""
    cpu = clock.get("cpuclk_hz")
    if isinstance(cpu, int):
        return f"{cpu // 1_000_000}MHz"
    return as_text(cpu)


def validation_text(manifest: dict[str, Any]) -> tuple[str, str]:
    validation = manifest.get("validation")
    if not isinstance(validation, dict):
        return "", ""
    highest = as_text(validation.get("highest_level"))
    levels = validation.get("levels")
    if not isinstance(levels, dict):
        return highest, ""
    abbreviations = (
        ("S", "static"),
        ("G", "sysconfig_generation"),
        ("C", "compile_link"),
        ("F", "flash"),
        ("R", "serial"),
        ("P", "physical_behavior"),
    )
    summary = ",".join(
        f"{label}={as_text(levels.get(key))}" for label, key in abbreviations
    )
    return highest, summary


def list_contains(value: Any, expected: str) -> bool:
    if not isinstance(value, list):
        return False
    folded = expected.casefold()
    return any(str(item).casefold() == folded for item in value)


def matches_filters(manifest: dict[str, Any], args: argparse.Namespace) -> bool:
    if args.name and args.name.casefold() not in as_text(manifest.get("name")).casefold():
        return False
    if args.board:
        board_query = args.board.casefold()
        relative_board = as_text(manifest.get("_relative_path")).split("/", 1)[0]
        board_values = (as_text(manifest.get("board")), relative_board)
        if not any(board_query in value.casefold() for value in board_values):
            return False
    if any(
        not list_contains(manifest.get("peripherals"), peripheral)
        for peripheral in args.peripherals
    ):
        return False
    if any(not list_contains(manifest.get("tags"), tag) for tag in args.tags):
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="列出 MSPM0 技能包内的工程模板。")
    parser.add_argument(
        "--templates-dir",
        "--examples-dir",
        dest="templates_dir",
        default=Path(__file__).resolve().parents[1] / "assets" / "templates",
        type=Path,
        help="模板根目录；默认使用技能包内 assets/templates。",
    )
    parser.add_argument("--name", help="按模板名称筛选，不区分大小写并支持部分匹配。")
    parser.add_argument("--board", help="按板卡名称筛选，不区分大小写并支持部分匹配。")
    parser.add_argument(
        "--peripheral",
        dest="peripherals",
        action="append",
        default=[],
        metavar="PERIPHERAL",
        help="要求模板包含指定外设；可重复使用。",
    )
    parser.add_argument(
        "--tag",
        dest="tags",
        action="append",
        default=[],
        metavar="TAG",
        help="要求模板包含指定标签；可重复使用。",
    )
    parser.add_argument("--json", action="store_true", help="输出机器可读的 JSON。")
    args = parser.parse_args()

    templates_dir = args.templates_dir.resolve()
    if not templates_dir.is_dir():
        print(f"Template directory not found: {templates_dir}", file=sys.stderr)
        return 2

    manifests: list[dict[str, Any]] = []
    manifest_errors: list[str] = []
    for manifest_path in sorted(templates_dir.rglob("manifest.json")):
        manifest = load_manifest(manifest_path)
        if "error" in manifest:
            manifest_errors.append(f"{manifest_path}: {manifest['error']}")
            continue
        manifest["_path"] = str(manifest_path.parent)
        manifest["_relative_path"] = manifest_path.parent.relative_to(templates_dir).as_posix()
        if matches_filters(manifest, args):
            manifests.append(manifest)

    if manifest_errors:
        for error in manifest_errors:
            print(f"Invalid manifest: {error}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(manifests, ensure_ascii=False, indent=2))
        return 0

    if not manifests:
        print(f"No templates matched under {templates_dir}", file=sys.stderr)
        return 0

    headers = (
        "board",
        "name",
        "complexity",
        "clock",
        "pins",
        "peripherals",
        "lifecycle",
        "highest",
        "levels",
        "path",
    )
    rows = []
    for manifest in manifests:
        highest, levels = validation_text(manifest)
        rows.append(
            (
                as_text(manifest.get("board")),
                as_text(manifest.get("name") or Path(manifest.get("_path", "")).name),
                as_text(manifest.get("complexity")),
                clock_text(manifest),
                as_text(manifest.get("pins")),
                as_text(manifest.get("peripherals")),
                as_text(manifest.get("lifecycle")),
                highest,
                levels,
                as_text(manifest.get("_relative_path")),
            )
        )

    widths = [len(header) for header in headers]
    for row in rows:
        widths = [max(width, len(cell)) for width, cell in zip(widths, row)]

    print("  ".join(header.ljust(width) for header, width in zip(headers, widths)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(cell.ljust(width) for cell, width in zip(row, widths)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
