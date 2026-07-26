#!/usr/bin/env python3
"""把现有 MSPM0 CCS 工程捕获为紧凑、可审计的模板候选。"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Iterable


BUILD_DIRS = {"Debug", "Release"}
SKIP_DIRS = {".git", ".svn", ".hg", ".metadata", ".settings", "__pycache__", ".agents", ".claude", ".codex"}
GENERATED_NAMES = {
    "ti_msp_dl_config.c",
    "ti_msp_dl_config.h",
    "device.opt",
    "device_linker.cmd",
    "device.cmd.genlibs",
    "Event.dot",
}
DEFAULT_EXCLUDES = [
    "Debug/**",
    "Release/**",
    "**/*.o",
    "**/*.d",
    "**/*.out",
    "**/*.map",
    "**/*_linkInfo.xml",
    "**/ti_msp_dl_config.c",
    "**/ti_msp_dl_config.h",
    "**/device_linker.cmd",
    "**/device.opt",
    "**/device.cmd.genlibs",
]
EXAMPLE_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
V2_CLI_ARGS_RE = re.compile(
    r"(?m)^[ \t]*(?://|/\*+|\*)?[ \t]*@v2CliArgs\b([^\r\n]*)"
)
CLI_OPTION_RE = re.compile(r'--([A-Za-z0-9_-]+)\s+"([^"]*)"')
VALIDATION_LEVELS = (
    "static",
    "sysconfig_generation",
    "compile_link",
    "flash",
    "serial",
    "physical_behavior",
)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="strict")
    except UnicodeError as exc:
        raise SystemExit(f"文件不是有效 UTF-8，已停止捕获：{path}: {exc}") from exc


def iter_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS and name not in BUILD_DIRS]
        for filename in filenames:
            yield Path(dirpath) / filename


def rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def matches_any(value: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(value, pattern) for pattern in patterns)


def find_syscfg(project: Path, explicit: str | None) -> Path:
    if explicit:
        path = (project / explicit).resolve()
        try:
            path.relative_to(project)
        except ValueError as exc:
            raise SystemExit(f"SysConfig file must stay inside the source project: {path}") from exc
        if not path.is_file() or path.suffix.lower() != ".syscfg":
            raise SystemExit(f"SysConfig file not found: {path}")
        return path

    syscfgs = sorted(p for p in iter_files(project) if p.suffix == ".syscfg")
    if len(syscfgs) == 1:
        return syscfgs[0]
    if not syscfgs:
        raise SystemExit("No .syscfg file found. Pass --syscfg explicitly if needed.")
    options = "\n".join(f"  - {rel_posix(path, project)}" for path in syscfgs)
    raise SystemExit(f"Multiple .syscfg files found. Pass --syscfg explicitly:\n{options}")


def select_sources(project: Path, includes: list[str], excludes: list[str], auto: bool) -> list[Path]:
    if not includes and not auto:
        raise SystemExit("Pass one or more --include patterns, or use --auto for a best-effort capture.")

    files = []
    for path in iter_files(project):
        rel = rel_posix(path, project)
        if matches_any(rel, excludes):
            continue
        if path.name in GENERATED_NAMES:
            continue
        if includes and matches_any(rel, includes):
            files.append(path)
            continue
        if auto and is_auto_source(path, rel):
            files.append(path)

    return sorted(set(files))


def is_auto_source(path: Path, rel: str) -> bool:
    if path.suffix.lower() not in {".c", ".h", ".cpp", ".cc", ".hpp"}:
        return False
    top = rel.split("/", 1)[0]
    if "/" not in rel:
        return True
    return top in {"src", "app", "bsp", "board", "drivers", "include", "user", "Core"}


def parse_metadata(syscfg_text: str) -> dict[str, Any]:
    """只从精确的 v2 SysConfig 参数读取规范器件元数据。"""
    v2_lines = V2_CLI_ARGS_RE.findall(syscfg_text)
    if not v2_lines:
        raise SystemExit("SysConfig 缺少 @v2CliArgs；无法确定精确 device/package/product。")

    candidates: list[dict[str, str]] = []
    for line in v2_lines:
        values = {key: value.strip() for key, value in CLI_OPTION_RE.findall(line)}
        if values:
            candidates.append(values)
    if not candidates:
        raise SystemExit("@v2CliArgs 不含可解析的 device/package/product。")

    metadata: dict[str, Any] = {}
    for key in ("device", "package", "product"):
        values = {candidate.get(key, "").strip() for candidate in candidates}
        values.discard("")
        if len(values) != 1:
            raise SystemExit(f"@v2CliArgs 必须提供唯一且非空的 --{key}；实际为 {sorted(values)}。")
        metadata[key] = values.pop()

    if "X" in str(metadata["device"]).upper():
        raise SystemExit(
            f"@v2CliArgs device 必须是精确器件，不能使用族通配值：{metadata['device']}"
        )

    versions = re.search(r"@versions\s+(\{[^\n]+\})", syscfg_text)
    if versions:
        metadata["versions"] = versions.group(1).strip()
    return metadata


def parse_modules(syscfg_text: str) -> list[str]:
    modules = set()
    for match in re.finditer(r'scripting\.addModule\("([^"]+)"', syscfg_text):
        modules.add(match.group(1).rsplit("/", 1)[-1])
    return sorted(modules)


def parse_pins(syscfg_text: str) -> list[str]:
    pins = set(re.findall(r'\$assign\s*=\s*"(P[A-Z]\d+)"', syscfg_text))
    pins.update(re.findall(r'\$suggestSolution\s*=\s*"(P[A-Z]\d+)"', syscfg_text))
    for pin in re.findall(r"assignedPin\s*=\s*\"(\d+)\"", syscfg_text):
        pins.add(f"pin:{pin}")
    return sorted(pins)


def detect_generated_names(project: Path) -> list[str]:
    headers = sorted(project.glob("Debug/**/ti_msp_dl_config.h")) + sorted(project.glob("Release/**/ti_msp_dl_config.h"))
    names: set[str] = set()
    for header in headers:
        text = read_text(header)
        names.update(re.findall(r"^#define\s+([A-Za-z_][A-Za-z0-9_]*)", text, flags=re.MULTILINE))
        names.update(re.findall(r"\bvoid\s+(SYSCFG_DL_[A-Za-z]*[Ii]nit)\s*\(", text))
    return sorted(name for name in names if not name.startswith("__"))[:80]


def source_mentions_freertos(files: list[Path]) -> bool:
    for path in files:
        try:
            text = read_text(path)
        except OSError:
            continue
        if "FreeRTOS" in text or "task.h" in text or "xTaskCreate" in text:
            return True
    return False


def classify_complexity(peripherals: list[str], pins: list[str], sources: list[Path], freertos: bool) -> str:
    if freertos or len(peripherals) >= 8 or len(pins) >= 12 or len(sources) >= 16:
        return "advanced"
    if len(peripherals) >= 5 or len(pins) >= 6 or len(sources) >= 6:
        return "intermediate"
    return "basic"


def validation_candidate() -> dict[str, Any]:
    """新捕获模板没有验证证据，必须从候选状态开始。"""
    return {
        "highest_level": "unverified",
        "levels": {level: "not_run" for level in VALIDATION_LEVELS},
        "records": [],
    }


def sdk_display_name(product: str) -> str:
    prefix = "mspm0_sdk@"
    if not product.startswith(prefix) or not product[len(prefix) :].strip():
        raise SystemExit(f"@v2CliArgs product 不是精确 MSPM0 SDK：{product}")
    return f"MSPM0 SDK {product[len(prefix):].strip()}"


def sysconfig_display_version(versions: str) -> str:
    if not versions:
        raise SystemExit("SysConfig 缺少 @versions.tool，无法记录 SysConfig 版本。")
    try:
        payload = json.loads(versions)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"@versions 不是有效 JSON：{exc}") from exc
    tool = payload.get("tool") if isinstance(payload, dict) else None
    if not isinstance(tool, str) or not tool.strip():
        raise SystemExit("@versions 必须包含非空 tool 版本。")
    return tool.split("+", 1)[0].strip()


def calculate_content_sha256(template_root: Path, relative_files: Iterable[str]) -> str:
    """按规范相对路径与 UTF-8 文本计算跨平台可复现的模板内容摘要。"""
    digest = hashlib.sha256()
    normalized = sorted({Path(value).as_posix() for value in relative_files})
    for value in normalized:
        candidate = (template_root / value).resolve()
        try:
            candidate.relative_to(template_root.resolve())
        except ValueError as exc:
            raise SystemExit(f"摘要文件必须位于模板目录内：{value}") from exc
        if not candidate.is_file():
            raise SystemExit(f"摘要文件不存在：{value}")
        try:
            content = candidate.read_text(encoding="utf-8", errors="strict")
        except UnicodeError as exc:
            raise SystemExit(f"摘要文件不是有效 UTF-8：{value}: {exc}") from exc
        canonical_bytes = content.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
        digest.update(canonical_bytes)
        digest.update(b"\0")
    return digest.hexdigest()


def resolve_template_destination(output_dir: Path, name: str) -> Path:
    if not EXAMPLE_NAME_RE.fullmatch(name):
        raise SystemExit(
            "Example name must start with a letter or digit and contain only letters, digits, '-' or '_'."
        )

    root = output_dir.expanduser().resolve()
    if root.exists() and not root.is_dir():
        raise SystemExit(f"Output path is not a directory: {root}")

    dest = (root / name).resolve()
    try:
        dest.relative_to(root)
    except ValueError as exc:
        raise SystemExit(f"Template destination must stay inside the output directory: {dest}") from exc
    return dest


# 保留旧模块调用名；默认输出位置仍由新命令行参数控制。
resolve_example_destination = resolve_template_destination


def main() -> int:
    parser = argparse.ArgumentParser(description="捕获紧凑的 MSPM0 CCS 模板候选包。")
    parser.add_argument("project", type=Path, help="Source CCS project directory.")
    parser.add_argument("--name", required=True, help="Example directory name to create.")
    parser.add_argument("--title", help="Human-readable example title.")
    parser.add_argument("--description", help="Short example description.")
    parser.add_argument("--syscfg", help="Relative path to the .syscfg file if the project has more than one.")
    parser.add_argument("--include", action="append", default=[], help="Source glob to include, relative to project root. Repeatable.")
    parser.add_argument("--exclude", action="append", default=[], help="Additional glob to exclude. Repeatable.")
    parser.add_argument("--auto", action="store_true", help="Best-effort include of common source directories.")
    parser.add_argument("--board", required=True, help="Non-empty board name for manifest.")
    parser.add_argument("--force", action="store_true", help="显式覆盖输出目录中的同名模板。")
    parser.add_argument(
        "--output-dir",
        "--examples-dir",
        dest="output_dir",
        type=Path,
        default=Path.cwd() / "mspm0-captured-templates",
        help="输出目录；默认写入当前目录的 mspm0-captured-templates，不修改已安装技能。",
    )
    args = parser.parse_args()

    project = args.project.resolve()
    if not project.is_dir():
        raise SystemExit(f"Project directory not found: {project}")

    syscfg = find_syscfg(project, args.syscfg)
    syscfg_text = read_text(syscfg)
    sources = select_sources(project, args.include, DEFAULT_EXCLUDES + args.exclude, args.auto)
    if not sources:
        raise SystemExit("No source files matched. Refusing to create a manifest with an empty source_files list.")
    board = args.board.strip()
    if not board:
        raise SystemExit("--board must not be empty.")

    metadata = parse_metadata(syscfg_text)
    sdk = sdk_display_name(metadata["product"])
    sysconfig = sysconfig_display_version(metadata.get("versions", ""))
    peripherals = parse_modules(syscfg_text)
    pins = parse_pins(syscfg_text)
    freertos = source_mentions_freertos(sources)
    complexity = classify_complexity(peripherals, pins, sources, freertos)
    generated_names = detect_generated_names(project)

    # 所有只读预检通过后才创建或覆盖候选目录，避免留下半成品。
    dest = resolve_template_destination(args.output_dir, args.name)
    if dest.exists():
        if not args.force:
            raise SystemExit(f"Destination exists: {dest}. Pass --force to overwrite.")
        if not dest.is_dir() or dest.is_symlink():
            raise SystemExit(f"Refusing to overwrite a non-directory or symlink destination: {dest}")
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    src_dest = dest / "src"
    src_dest.mkdir()

    shutil.copy2(syscfg, dest / "example.syscfg")
    for source in sources:
        rel = source.relative_to(project)
        out = src_dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, out)

    source_files = [f"src/{rel_posix(path, project)}" for path in sources]
    content_sha256 = calculate_content_sha256(
        dest,
        ["example.syscfg", *source_files],
    )
    manifest = {
        "schema": 2,
        "name": args.name,
        "title": args.title or args.name.replace("_", " ").title(),
        "description": args.description or "Captured MSPM0 CCS example.",
        "board": board,
        "device": metadata["device"],
        "package": metadata["package"],
        "product": metadata["product"],
        "sdk": sdk,
        "sysconfig": sysconfig,
        "sysconfig_versions": metadata.get("versions") or "",
        "lifecycle": "candidate",
        "validation": validation_candidate(),
        "complexity": complexity,
        "peripherals": peripherals,
        "pins": pins,
        "source_files": source_files,
        "syscfg": "example.syscfg",
        "content_sha256": content_sha256,
        "generated_names": generated_names,
        "tags": sorted(set(peripherals + pins + ([ "freertos" ] if freertos else []))),
    }

    (dest / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Captured template candidate: {dest}")
    print(f"Sources copied: {len(sources)}")
    print(f"Complexity: {complexity}")
    if complexity == "advanced":
        print("Note: advanced examples should be used as module references, not copied wholesale.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
