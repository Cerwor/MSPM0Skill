#!/usr/bin/env python3
"""从内置模板或本地 TI SDK 例程创建非覆盖式 MSPM0 CCS 工程骨架。"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
SKIP_DIRS = {
    ".git",
    ".svn",
    "__pycache__",
    "Debug",
    "Release",
    "Objects",
    "Listings",
    "iar",
    "keil",
    "ticlang",
    "targetConfigs",
}
SKIP_FILES = {"README.md", "README.html", "manifest.json"}
COPY_SUFFIXES = {".c", ".cc", ".cpp", ".h", ".hpp", ".syscfg", ".cmd"}


@dataclass(frozen=True)
class BoardProfile:
    key: str
    display_name: str
    chip: str
    sdk_board: str
    package: str


BOARD_PROFILES = {
    "tianmengxing": BoardProfile(
        key="tianmengxing",
        display_name="LCKFB Tianmengxing MSPM0G3507",
        chip="MSPM0G3507",
        sdk_board="LP_MSPM0G3507",
        package="LQFP-64(PM)",
    ),
    "tianqiaoxing": BoardProfile(
        key="tianqiaoxing",
        display_name="LCKFB Tianqiaoxing MSPM0G3519",
        chip="MSPM0G3519",
        sdk_board="LP_MSPM0G3519",
        package="LQFP-64(PM)",
    ),
}

PROBE_CONNECTIONS = {
    "xds110": "TIXDS110_Connection.xml",
    "jlink": "segger_j-link_connection.xml",
}


def validate_project_name(value: str) -> str:
    if not PROJECT_NAME_RE.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "工程名必须以字母或数字开头，且只能包含字母、数字、下划线和连字符"
        )
    return value


def source_candidates(
    board: BoardProfile,
    template: str,
    source_kind: str,
    sdk_root: Path | None,
) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    packaged = SKILL_ROOT / "assets" / "templates" / board.key / template
    if source_kind in {"auto", "packaged"}:
        candidates.append(("packaged", packaged))
    if source_kind in {"auto", "sdk"} and sdk_root is not None:
        sdk = (
            sdk_root
            / "examples"
            / "nortos"
            / board.sdk_board
            / "driverlib"
            / template
        )
        candidates.append(("sdk", sdk))
    return candidates


def select_source(
    board: BoardProfile,
    template: str,
    source_kind: str,
    sdk_root: Path | None,
) -> tuple[str, Path]:
    candidates = source_candidates(board, template, source_kind, sdk_root)
    for kind, path in candidates:
        if path.is_dir():
            return kind, path.resolve()
    searched = "\n".join(f"  - {kind}: {path}" for kind, path in candidates)
    raise SystemExit(f"找不到模板或 SDK 例程 {template!r}；已检查：\n{searched}")


def iter_source_files(source: Path) -> list[Path]:
    files: list[Path] = []
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(source)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.name in SKIP_FILES or path.suffix.lower() not in COPY_SUFFIXES:
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(source).as_posix())


def destination_relative(path: Path, source: Path, project_name: str) -> Path:
    rel = path.relative_to(source)
    if path.suffix.lower() == ".syscfg":
        return Path(f"{project_name}.syscfg")
    if rel.parts and rel.parts[0] == "src":
        return rel
    return rel


def make_plan(
    board: BoardProfile,
    project_name: str,
    template: str,
    source_kind: str,
    source: Path,
    destination: Path,
    probe: str | None,
) -> dict[str, object]:
    source_files = iter_source_files(source)
    syscfgs = [path for path in source_files if path.suffix.lower() == ".syscfg"]
    if len(syscfgs) != 1:
        raise SystemExit(
            f"脚手架要求源中恰好有一个 .syscfg，实际找到 {len(syscfgs)} 个：{source}"
        )
    operations = [
        {
            "source": str(path),
            "destination": str(destination / destination_relative(path, source, project_name)),
        }
        for path in source_files
    ]
    return {
        "status": "planned",
        "board": asdict(board),
        "project_name": project_name,
        "template": template,
        "source_kind": source_kind,
        "source": str(source),
        "destination": str(destination),
        "probe": probe or "unresolved",
        "connection": PROBE_CONNECTIONS.get(probe or "", ""),
        "operations": operations,
        "writes_project": True,
        "writes_device": False,
    }


def adapt_syscfg(text: str, board: BoardProfile) -> str:
    text = re.sub(
        r'--package\s+"LQFP-100\(PZ\)"',
        f'--package "{board.package}"',
        text,
    )
    return text.replace("\r\n", "\n")


def project_spec(
    board: BoardProfile,
    project_name: str,
    connection: str,
    copied_files: list[Path],
    destination: Path,
) -> str:
    file_entries = []
    for path in copied_files:
        if path.suffix.lower() not in {".c", ".cc", ".cpp", ".h", ".hpp"}:
            continue
        rel = path.relative_to(destination).as_posix()
        file_entries.append(
            f'        <file path="{rel}" openOnCreation="false" '
            'excludeFromBuild="false" action="copy"/>'
        )
    files = "\n".join(file_entries)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<projectSpec>
    <applicability><when><context deviceFamily="ARM" deviceId="{board.chip}"/></when></applicability>
    <project
        title="{project_name}" name="{project_name}"
        configurations="Debug" toolChain="TICLANG"
        connection="{connection}" device="{board.chip}"
        ignoreDefaultDeviceSettings="true" ignoreDefaultCCSSettings="true"
        products="MSPM0-SDK;sysconfig"
        compilerBuildOptions="-I${{PROJECT_ROOT}} -I${{PROJECT_ROOT}}/${{ConfigName}}
            -I${{COM_TI_MSPM0_SDK_INSTALL_DIR}}/source/third_party/CMSIS/Core/Include
            -I${{COM_TI_MSPM0_SDK_INSTALL_DIR}}/source
            -O2 @device.opt -gdwarf-3 -mcpu=cortex-m0plus -march=thumbv6m
            -mfloat-abi=soft -mthumb"
        linkerBuildOptions="-ldevice.cmd.genlibs
            -L${{COM_TI_MSPM0_SDK_INSTALL_DIR}}/source
            -L${{PROJECT_ROOT}} -L${{PROJECT_BUILD_DIR}}/syscfg
            -Wl,--rom_model -Wl,--warn_sections -L${{CG_TOOL_ROOT}}/lib -llibc.a"
        sysConfigBuildOptions="--output . --product
            ${{COM_TI_MSPM0_SDK_INSTALL_DIR}}/.metadata/product.json --compiler ticlang">
        <property name="buildProfile" value="release"/>
        <property name="isHybrid" value="true"/>
        <file path="{project_name}.syscfg" openOnCreation="true"
              excludeFromBuild="false" action="copy"/>
{files}
    </project>
</projectSpec>
"""


def execute_plan(plan: dict[str, object], board: BoardProfile) -> list[Path]:
    destination = Path(str(plan["destination"]))
    if destination.exists():
        raise SystemExit(f"目标已存在，拒绝覆盖：{destination}")
    destination.mkdir(parents=True)
    copied: list[Path] = []
    try:
        for operation in plan["operations"]:
            assert isinstance(operation, dict)
            source = Path(str(operation["source"]))
            target = Path(str(operation["destination"]))
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.suffix.lower() == ".syscfg":
                content = adapt_syscfg(
                    source.read_text(encoding="utf-8", errors="strict"),
                    board,
                )
                target.write_text(content, encoding="utf-8", newline="\n")
            else:
                shutil.copy2(source, target)
            copied.append(target)

        connection = str(plan["connection"])
        spec = project_spec(
            board,
            str(plan["project_name"]),
            connection,
            copied,
            destination,
        )
        spec_path = destination / f"{plan['project_name']}.projectspec"
        spec_path.write_text(spec, encoding="utf-8", newline="\n")
        copied.append(spec_path)
    except Exception:
        # 只清理本次刚创建且尚未交付的目标目录。
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return copied


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_name", type=validate_project_name, help="新工程名")
    parser.add_argument("--board", required=True, choices=sorted(BOARD_PROFILES))
    parser.add_argument("--template", required=True, help="内置模板名或 SDK driverlib 例程名")
    parser.add_argument(
        "--source",
        choices=("auto", "packaged", "sdk"),
        default="auto",
        help="源选择；auto 优先内置模板，再尝试 SDK",
    )
    parser.add_argument("--sdk-root", type=Path, help="本地 MSPM0 SDK 根目录")
    parser.add_argument("--output", type=Path, default=Path.cwd(), help="工程父目录")
    parser.add_argument(
        "--probe",
        choices=sorted(PROBE_CONNECTIONS),
        help="实际创建时必须明确选择调试探针",
    )
    parser.add_argument("--dry-run", action="store_true", help="只输出结构化计划，不写文件")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.source == "sdk" and args.sdk_root is None:
        parser.error("--source sdk 需要 --sdk-root")

    board = BOARD_PROFILES[args.board]
    sdk_root = args.sdk_root.resolve() if args.sdk_root else None
    source_kind, source = select_source(
        board,
        args.template,
        args.source,
        sdk_root,
    )
    output = args.output.expanduser().resolve()
    destination = (output / args.project_name).resolve()
    plan = make_plan(
        board,
        args.project_name,
        args.template,
        source_kind,
        source,
        destination,
        args.probe,
    )

    if args.dry_run:
        plan["status"] = "dry-run"
    else:
        if not args.probe:
            parser.error("实际创建工程前必须用 --probe 明确选择 xds110 或 jlink")
        copied = execute_plan(plan, board)
        plan["status"] = "created"
        plan["created_files"] = [str(path) for path in copied]

    if args.json or args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(f"工程已创建：{destination}")
        print(f"下一步：python -B scripts/check_syscfg.py \"{destination}\"")
        print(f"然后运行：python -B scripts/run_sysconfig.py \"{destination}\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
