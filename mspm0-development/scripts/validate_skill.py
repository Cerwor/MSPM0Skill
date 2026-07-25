#!/usr/bin/env python3
"""验证 MSPM0 skill 的结构、路由、资源、编码和安装包边界。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


FORBIDDEN_NAMES = {
    "README.md",
    "CHANGELOG.md",
    "INSTALLATION_GUIDE.md",
    "QUICK_REFERENCE.md",
}
FORBIDDEN_DIRS = {
    "__pycache__",
    ".git",
    ".github",
    ".pytest_cache",
    ".mypy_cache",
    "tests",
}
TEMP_SUFFIXES = {".pyc", ".pyo", ".tmp", ".temp", ".bak", ".log"}
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
DRIVE_PATH_RE = re.compile(r"(?i)(?<![A-Za-z0-9_])[A-Z]:[\\/]")
ALLOWED_GENERIC_PATHS = (
    "C:/ti",
    "C:\\ti",
    "C:/Program Files",
    "C:\\Program Files",
)


@dataclass
class Finding:
    level: str
    path: str
    message: str


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def read_utf8(path: Path, findings: list[Finding], root: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="strict")
    except UnicodeError as exc:
        findings.append(Finding("error", relative(path, root), f"不是有效 UTF-8：{exc}"))
        return None


def check_frontmatter(root: Path, findings: list[Finding]) -> tuple[str, str]:
    skill = root / "SKILL.md"
    text = read_utf8(skill, findings, root)
    if text is None:
        return "", ""
    match = FRONTMATTER_RE.match(text)
    if not match:
        findings.append(Finding("error", "SKILL.md", "缺少有效 YAML frontmatter"))
        return "", ""
    keys = []
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        keys.append(key.strip())
        values[key.strip()] = value.strip()
    if keys != ["name", "description"]:
        findings.append(
            Finding("error", "SKILL.md", f"frontmatter 只能按顺序包含 name、description；实际为 {keys}")
        )
    body = text[match.end() :]
    if body.count("## Quick Routing") != 1:
        findings.append(Finding("error", "SKILL.md", "必须且只能有一个 Quick Routing"))
    if len(text.splitlines()) > 500:
        findings.append(Finding("error", "SKILL.md", "SKILL.md 超过 500 行"))
    description = values.get("description", "")
    for boundary in ("outside mature support", "automatic unlock"):
        if boundary not in description:
            findings.append(
                Finding("error", "SKILL.md", f"description 缺少支持边界：{boundary}")
            )
    return values.get("name", ""), description


def check_package_files(root: Path, findings: list[Finding]) -> None:
    for path in root.rglob("*"):
        rel = relative(path, root)
        if path.is_dir() and path.name in FORBIDDEN_DIRS:
            findings.append(Finding("error", rel, "安装包包含禁止目录"))
            continue
        if not path.is_file():
            continue
        if path.name in FORBIDDEN_NAMES:
            findings.append(Finding("error", rel, "安装包包含禁止文档"))
        if path.suffix.lower() in TEMP_SUFFIXES:
            findings.append(Finding("error", rel, "安装包包含缓存或临时文件"))


def check_markdown(root: Path, findings: list[Finding]) -> None:
    for path in root.rglob("*.md"):
        text = read_utf8(path, findings, root)
        if text is None:
            continue
        lines = text.splitlines()
        if path != root / "SKILL.md" and len(lines) > 100:
            first = "\n".join(lines[:40])
            if "## Scope" not in first or "## Contents" not in first:
                findings.append(
                    Finding("error", relative(path, root), "长 reference 前 40 行缺少 Scope 或 Contents")
                )
        for target in MARKDOWN_LINK_RE.findall(text):
            clean = target.strip().split("#", 1)[0]
            if not clean or clean.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (path.parent / clean).resolve()
            if not resolved.exists():
                findings.append(
                    Finding("error", relative(path, root), f"失效链接：{target}")
                )


def check_absolute_paths(root: Path, findings: list[Finding]) -> None:
    text_suffixes = {".md", ".py", ".yaml", ".yml", ".json", ".syscfg", ".c", ".h"}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        text = read_utf8(path, findings, root)
        if text is None:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not DRIVE_PATH_RE.search(line):
                continue
            normalized = line.replace("\\\\", "\\")
            if any(value in normalized for value in ALLOWED_GENERIC_PATHS):
                continue
            findings.append(
                Finding(
                    "error",
                    relative(path, root),
                    f"第 {line_number} 行包含本机绝对路径",
                )
            )


def check_openai_yaml(root: Path, skill_name: str, findings: list[Finding]) -> None:
    path = root / "agents" / "openai.yaml"
    text = read_utf8(path, findings, root)
    if text is None:
        return
    required = ("display_name:", "short_description:", "default_prompt:")
    for key in required:
        if key not in text:
            findings.append(Finding("error", relative(path, root), f"缺少 {key}"))
    if f"${skill_name}" not in text:
        findings.append(Finding("error", relative(path, root), "default_prompt 未引用当前 skill"))
    short = re.search(r'short_description:\s*"([^"]+)"', text)
    if not short or not 25 <= len(short.group(1)) <= 64:
        findings.append(Finding("error", relative(path, root), "short_description 长度不在 25–64"))


def manifest_files(manifest: dict[str, object]) -> list[str]:
    values = manifest.get("source_files", [])
    if isinstance(values, list):
        return [str(value) for value in values]
    return []


def check_templates(root: Path, findings: list[Finding]) -> None:
    templates_root = root / "assets" / "templates"
    if not templates_root.is_dir():
        findings.append(Finding("error", "assets/templates", "缺少模板目录"))
        return
    for board_dir in sorted(path for path in templates_root.iterdir() if path.is_dir()):
        for template in sorted(path for path in board_dir.iterdir() if path.is_dir()):
            rel = relative(template, root)
            manifest_path = template / "manifest.json"
            if not manifest_path.is_file():
                findings.append(Finding("error", rel, "模板缺少 manifest.json"))
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                findings.append(Finding("error", relative(manifest_path, root), f"manifest 无效：{exc}"))
                continue
            for key in ("schema", "name", "title", "description", "board", "device", "validated", "validation_level"):
                if key not in manifest:
                    findings.append(Finding("error", relative(manifest_path, root), f"缺少字段 {key}"))
            syscfgs = list(template.glob("*.syscfg"))
            if len(syscfgs) != 1:
                findings.append(Finding("error", rel, f"模板应有一个根级 .syscfg，实际 {len(syscfgs)} 个"))
            for item in manifest_files(manifest):
                candidate = template / item
                if not candidate.exists():
                    findings.append(
                        Finding("error", relative(manifest_path, root), f"source_files 路径不存在：{item}")
                    )


def check_script_help(root: Path, findings: list[Finding]) -> None:
    public_scripts = (
        "capture_example.py",
        "ccs_dss_debug.py",
        "check_syscfg.py",
        "detect_probe.py",
        "index_syscfg_examples.py",
        "list_examples.py",
        "openocd_debug.py",
        "run_sysconfig.py",
        "scaffold_project.py",
        "serial_console.py",
        "validate_skill.py",
    )
    for name in public_scripts:
        if not (root / "scripts" / name).is_file():
            findings.append(Finding("error", f"scripts/{name}", "缺少公共脚本"))


def validate(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    if not (root / "SKILL.md").is_file():
        return [Finding("error", ".", "目标不是 skill 目录")]
    skill_name, _description = check_frontmatter(root, findings)
    check_package_files(root, findings)
    check_markdown(root, findings)
    check_absolute_paths(root, findings)
    check_openai_yaml(root, skill_name, findings)
    check_templates(root, findings)
    check_script_help(root, findings)
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)
    root = args.skill_dir.resolve()
    findings = validate(root)
    payload = {
        "skill": str(root),
        "status": "ok" if not findings else "error",
        "findings": [asdict(finding) for finding in findings],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"MSPM0 skill validation: {root}")
        for finding in findings:
            print(f"{finding.level.upper():7} {finding.path}: {finding.message}")
        print(f"RESULT status={payload['status']} findings={len(findings)}")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
