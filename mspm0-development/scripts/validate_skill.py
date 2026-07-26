#!/usr/bin/env python3
"""验证 MSPM0 skill 的结构、路由、资源、编码和安装包边界。"""

from __future__ import annotations

import argparse
import json
import re
import runpy
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path


FORBIDDEN_NAMES = {
    "README.md",
    "CHANGELOG.md",
    "INSTALLATION_GUIDE.md",
    "QUICK_REFERENCE.md",
    "CLAUDE.md",
    ".mcp.json",
}
FORBIDDEN_DIRS = {
    "__pycache__",
    ".claude",
    ".codex",
    ".git",
    ".github",
    ".idea",
    ".pytest_cache",
    ".mypy_cache",
    ".vscode",
    "tests",
}
TEMP_SUFFIXES = {".pyc", ".pyo", ".tmp", ".temp", ".bak", ".log"}
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
DRIVE_PATH_RE = re.compile(r"(?i)(?<![A-Za-z0-9_])[A-Z]:[\\/]")
QUOTED_INCLUDE_RE = re.compile(r'(?m)^\s*#\s*include\s*"([^"]+)"')
EXTERNAL_QUOTED_INCLUDES = {
    "stdbool.h",
    "stddef.h",
    "stdint.h",
    "stdio.h",
    "stdlib.h",
    "string.h",
    "ti_msp_dl_config.h",
}
ALLOWED_GENERIC_PATHS = (
    "C:/ti",
    "C:\\ti",
    "C:/Program Files",
    "C:\\Program Files",
)
TIANQIAOXING_COMMON_REFERENCES = {
    "adc.md",
    "gpio.md",
    "i2c.md",
    "pwm.md",
    "qei.md",
    "spi.md",
    "timer.md",
    "uart.md",
}
TIANMENGXING_COMMON_REFERENCES = TIANQIAOXING_COMMON_REFERENCES.copy()
TIANQIAOXING_TEMPLATES = {"blink"}


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
    skill_name = values.get("name", "")
    if skill_name and root.name != skill_name:
        findings.append(
            Finding(
                "error",
                ".",
                f"skill 目录名必须与 frontmatter name 一致：目录={root.name}，name={skill_name}",
            )
        )
    for boundary in ("outside mature support", "automatic unlock"):
        if boundary not in description:
            findings.append(
                Finding("error", "SKILL.md", f"description 缺少支持边界：{boundary}")
            )
    return skill_name, description


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


def check_tianqiaoxing_scope(root: Path, findings: list[Finding]) -> None:
    reference_dir = root / "references" / "hardware" / "tianqiaoxing-peripherals"
    if not reference_dir.is_dir():
        findings.append(Finding("error", relative(reference_dir, root), "缺少天巧星通用外设参考目录"))
        return
    actual_references = {
        path.name for path in reference_dir.iterdir() if path.is_file() and path.suffix == ".md"
    }
    if actual_references != TIANQIAOXING_COMMON_REFERENCES:
        findings.append(
            Finding(
                "error",
                relative(reference_dir, root),
                "天巧星参考必须只保留通用外设；"
                f"期望={sorted(TIANQIAOXING_COMMON_REFERENCES)}，"
                f"实际={sorted(actual_references)}",
            )
        )

    template_dir = root / "assets" / "templates" / "tianqiaoxing"
    if not template_dir.is_dir():
        findings.append(Finding("error", relative(template_dir, root), "缺少天巧星通用模板目录"))
        return
    actual_templates = {path.name for path in template_dir.iterdir() if path.is_dir()}
    if actual_templates != TIANQIAOXING_TEMPLATES:
        findings.append(
            Finding(
                "error",
                relative(template_dir, root),
                "天巧星资产必须只保留通用 GPIO 冒烟模板；"
                f"期望={sorted(TIANQIAOXING_TEMPLATES)}，实际={sorted(actual_templates)}",
            )
        )


def check_tianmengxing_scope(root: Path, findings: list[Finding]) -> None:
    reference_dir = root / "references" / "hardware" / "tianmengxing-peripherals"
    if not reference_dir.is_dir():
        findings.append(Finding("error", relative(reference_dir, root), "缺少天猛星通用外设参考目录"))
        return
    actual_references = {
        path.name for path in reference_dir.iterdir() if path.is_file() and path.suffix == ".md"
    }
    missing_references = TIANMENGXING_COMMON_REFERENCES - actual_references
    if missing_references:
        findings.append(
            Finding(
                "error",
                relative(reference_dir, root),
                "天猛星主维护板缺少通用外设参考；"
                f"缺少={sorted(missing_references)}",
            )
        )


def check_qei_reference(root: Path, findings: list[Finding]) -> None:
    path = root / "references" / "peripherals" / "qei.md"
    if not path.is_file():
        findings.append(Finding("error", relative(path, root), "缺少通用 TimerG QEI 参考"))
        return
    text = read_utf8(path, findings, root)
    if text is None:
        return
    required = (
        "/ti/driverlib/QEI",
        "DL_TimerG_configQEI",
        "DL_TimerG_startCounter",
        "DL_TimerG_getTimerCount",
        "DL_TimerG_getQEIDirection",
        "DL_TIMER_IIDX_DIR_CHANGE",
        "ti_msp_dl_config.h",
        "M / 2",
        "raw == M / 2",
        "sample_too_sparse",
        "counts_per_rev",
    )
    missing = [value for value in required if value not in text]
    if missing:
        findings.append(
            Finding(
                "error",
                relative(path, root),
                "QEI 参考缺少必要的配置、计数或验证概念：" + ", ".join(missing),
            )
        )
    forbidden_legacy_application_tokens = (
        "encoder_qei",
        "hw_encoder",
        "QEI_ENCODER",
        "PA29",
        "PA30",
        "PA31",
        "TIMG8",
        "OLED",
        "WS2812",
    )
    leaked = [value for value in forbidden_legacy_application_tokens if value in text]
    if leaked:
        findings.append(
            Finding(
                "error",
                relative(path, root),
                "通用 QEI 参考泄漏旧板卡应用或固定引脚：" + ", ".join(leaked),
            )
        )

    board_requirements = {
        root
        / "references"
        / "hardware"
        / "tianmengxing-peripherals"
        / "qei.md": (
            "../../peripherals/qei.md",
            "MSPM0G3507",
            "TIMG8",
            "PA29",
            "PA30",
            "PB22",
            "PB26",
            "没有天猛星 QEI 规范模板",
        ),
        root
        / "references"
        / "hardware"
        / "tianqiaoxing-peripherals"
        / "qei.md": (
            "../../peripherals/qei.md",
            "MSPM0G3519",
            "LQFP-64(PM)",
            "不保留旧编码器应用",
            "没有天巧星 QEI 规范模板",
        ),
    }
    for board_path, expected_values in board_requirements.items():
        if not board_path.is_file():
            findings.append(Finding("error", relative(board_path, root), "缺少板级 QEI 参考"))
            continue
        board_text = read_utf8(board_path, findings, root)
        if board_text is None:
            continue
        board_missing = [value for value in expected_values if value not in board_text]
        if board_missing:
            findings.append(
                Finding(
                    "error",
                    relative(board_path, root),
                    "板级 QEI 参考缺少通用路由或板卡边界：" + ", ".join(board_missing),
                )
            )

    board_indexes = {
        root / "references" / "hardware" / "tianmengxing.md": (
            "tianmengxing-peripherals/qei.md",
        ),
        root / "references" / "hardware" / "tianqiaoxing.md": (
            "tianqiaoxing-peripherals/qei.md",
        ),
    }
    for board_path, expected_values in board_indexes.items():
        if not board_path.is_file():
            findings.append(Finding("error", relative(board_path, root), "缺少板级外设索引"))
            continue
        board_text = read_utf8(board_path, findings, root)
        if board_text is None:
            continue
        if any(value not in board_text for value in expected_values):
            findings.append(
                Finding("error", relative(board_path, root), "板级外设索引未路由到 QEI 参考")
            )

    skill_text = read_utf8(root / "SKILL.md", findings, root)
    if skill_text is not None:
        routing = re.search(
            r"(?ms)^## Quick Routing\s*$\n(?P<body>.*?)(?=^## |\Z)",
            skill_text,
        )
        if routing is None:
            findings.append(Finding("error", "SKILL.md", "无法解析 Quick Routing 段"))
        else:
            routing_targets = {
                target.strip().split("#", 1)[0]
                for target in MARKDOWN_LINK_RE.findall(routing.group("body"))
            }
            if "references/peripherals/qei.md" not in routing_targets:
                findings.append(
                    Finding("error", "SKILL.md", "Quick Routing 未路由到通用 QEI 参考")
                )


def check_i2c_reference(root: Path, findings: list[Finding]) -> None:
    path = root / "references" / "peripherals" / "i2c.md"
    if not path.is_file():
        findings.append(Finding("error", relative(path, root), "缺少通用 MSPM0 I2C 参考"))
        return
    text = read_utf8(path, findings, root)
    if text is None:
        return
    required = (
        "/ti/driverlib/I2C",
        "7 位地址",
        "开漏",
        "上拉",
        "重复起始",
        "超时",
        "NACK",
        "仲裁丢失",
        "9 个 SCL",
        "ti_msp_dl_config.h/.c",
        "逻辑分析仪",
    )
    missing = [value for value in required if value not in text]
    if missing:
        findings.append(
            Finding(
                "error",
                relative(path, root),
                "通用 I2C 参考缺少必要的电气、事务或验证概念：" + ", ".join(missing),
            )
        )

    board_requirements = {
        root
        / "references"
        / "hardware"
        / "tianmengxing-peripherals"
        / "i2c.md": (
            "../../peripherals/i2c.md",
            "PA0",
            "PA1",
            "PA0(SDA)/PA1(SCL)",
            "软件 I2C",
            "不证明硬件复用方向或板载上拉",
            "没有天猛星 I2C 规范模板",
            "ti.com/lit/ds/symlink/mspm0g3507.pdf",
            "wiki.lckfb.com/zh-hans/tmx-mspm0g3507/ccs-beginner/i2c.html",
            "wiki.lckfb.com/zh-hans/tmx-mspm0g3507/keil-beginner/i2c.html",
        ),
        root
        / "references"
        / "hardware"
        / "tianqiaoxing-peripherals"
        / "i2c.md": (
            "../../peripherals/i2c.md",
            "MSPM0G3519",
            "LQFP-64(PM)",
            "不从旧应用恢复",
            "没有天巧星 I2C 规范模板",
        ),
    }
    for board_path, expected_values in board_requirements.items():
        if not board_path.is_file():
            findings.append(Finding("error", relative(board_path, root), "缺少板级 I2C 参考"))
            continue
        board_text = read_utf8(board_path, findings, root)
        if board_text is None:
            continue
        board_missing = [value for value in expected_values if value not in board_text]
        if board_missing:
            findings.append(
                Finding(
                    "error",
                    relative(board_path, root),
                    "板级 I2C 参考缺少通用路由或板卡边界：" + ", ".join(board_missing),
                )
            )
        if (
            "tianmengxing-peripherals" in board_path.parts
            and re.search(r"(?i)2(?:\.2|k2)\s*k?(?:Ω|ohm|欧)?", board_text)
        ):
            findings.append(
                Finding(
                    "error",
                    relative(board_path, root),
                    "没有当前原理图证据时不得声称天猛星 PA0/PA1 带 2.2 kΩ 板载上拉",
                )
            )

    board_indexes = {
        root / "references" / "hardware" / "tianmengxing.md": (
            "tianmengxing-peripherals/i2c.md",
        ),
        root / "references" / "hardware" / "tianqiaoxing.md": (
            "tianqiaoxing-peripherals/i2c.md",
        ),
    }
    for board_path, expected_values in board_indexes.items():
        if not board_path.is_file():
            findings.append(Finding("error", relative(board_path, root), "缺少板级外设索引"))
            continue
        board_text = read_utf8(board_path, findings, root)
        if board_text is None:
            continue
        if (
            board_path.name == "tianmengxing.md"
            and re.search(r"(?i)2(?:\.2|k2)\s*k?(?:Ω|ohm|欧)?", board_text)
        ):
            findings.append(
                Finding(
                    "error",
                    relative(board_path, root),
                    "天猛星板级索引不得恢复未经原理图证明的 2.2 kΩ I2C 上拉",
                )
            )
        if any(value not in board_text for value in expected_values):
            findings.append(
                Finding("error", relative(board_path, root), "板级外设索引未路由到 I2C 参考")
            )

    skill_text = read_utf8(root / "SKILL.md", findings, root)
    if skill_text is None:
        return
    routing = re.search(
        r"(?ms)^## Quick Routing\s*$\n(?P<body>.*?)(?=^## |\Z)",
        skill_text,
    )
    if routing is None:
        findings.append(Finding("error", "SKILL.md", "无法解析 Quick Routing 段"))
        return
    routing_targets = {
        target.strip().split("#", 1)[0]
        for target in MARKDOWN_LINK_RE.findall(routing.group("body"))
    }
    if "references/peripherals/i2c.md" not in routing_targets:
        findings.append(Finding("error", "SKILL.md", "Quick Routing 未路由到通用 I2C 参考"))


def check_sysconfig_patterns(root: Path, findings: list[Finding]) -> None:
    path = root / "references" / "runtime" / "sysconfig-patterns.md"
    if not path.is_file():
        findings.append(Finding("error", relative(path, root), "缺少 SysConfig 局部模式参考"))
        return
    text = read_utf8(path, findings, root)
    if text is None:
        return
    required = (
        "associatedPins.create(1)",
        "assignedPort",
        "pin.$assign",
        "PB22",
        'system.clockTree["MFCLKGATE"]',
        'system.clockTree["SYSPLLMUX"]',
        "UART0",
        "PA10",
        "PA11",
        "DMA_CHANNEL_TX",
        "DMA_CH0",
        "timerPeriod",
        '"1 ms"',
        "TIMG12",
        "empty_project/empty.syscfg",
        "uart_blocking_tx/example.syscfg",
        "uart_dma_tx_irq_rx/example.syscfg",
        "timer_irq_led/example.syscfg",
    )
    missing = [value for value in required if value not in text]
    if missing:
        findings.append(
            Finding(
                "error",
                relative(path, root),
                "SysConfig 局部模式缺少必要配置或规范模板链接：" + ", ".join(missing),
            )
        )
    if re.search(r"(?m)^\s*GPIO\d+\.port\s*=", text):
        findings.append(Finding("error", relative(path, root), "局部模式仍包含 GPIO 顶层 port 旧语法"))
    if re.search(
        r"GPIO\d+\.associatedPins\[\d+\]\.pin\.\$suggestSolution\s*=",
        text,
    ):
        findings.append(Finding("error", relative(path, root), "局部模式 GPIO 应使用显式 pin.$assign"))

    section_names = (
        "PB22 GPIO 输出",
        "80 MHz 与 MFCLK",
        "UART0 阻塞收发基础",
        "UART DMA TX 与 IRQ RX",
        "Timer 周期中断",
        "空配置骨架",
    )
    sections: dict[str, str] = {}
    for section_name in section_names:
        section = re.search(
            rf"(?ms)^## {re.escape(section_name)}\s*$\n(?P<body>.*?)(?=^## |\Z)",
            text,
        )
        if section is None:
            findings.append(
                Finding("error", relative(path, root), f"缺少局部模式章节：{section_name}")
            )
            continue
        sections[section_name] = section.group("body")

    template_paths = {
        "gpio": root / "assets" / "templates" / "tianmengxing" / "led_blink" / "example.syscfg",
        "clock_timer": (
            root
            / "assets"
            / "templates"
            / "tianmengxing"
            / "timer_irq_led"
            / "example.syscfg"
        ),
        "uart": (
            root
            / "assets"
            / "templates"
            / "tianmengxing"
            / "uart_blocking_tx"
            / "example.syscfg"
        ),
        "dma": (
            root
            / "assets"
            / "templates"
            / "tianmengxing"
            / "uart_dma_tx_irq_rx"
            / "example.syscfg"
        ),
        "empty": (
            root
            / "assets"
            / "templates"
            / "tianmengxing"
            / "empty_project"
            / "empty.syscfg"
        ),
    }
    templates = {
        name: read_utf8(template_path, findings, root)
        for name, template_path in template_paths.items()
    }
    clock_alias = r"(?P<alias>[A-Za-z_$][\w$]*)"
    semantic_checks = (
        (
            "GPIO 端口",
            "PB22 GPIO 输出",
            "gpio",
            r'associatedPins\[0\]\.assignedPort\s*=\s*"(?P<value>[^"]+)"',
            "PORTB",
        ),
        (
            "GPIO 引脚号",
            "PB22 GPIO 输出",
            "gpio",
            r'associatedPins\[0\]\.assignedPin\s*=\s*"(?P<value>[^"]+)"',
            "22",
        ),
        (
            "GPIO 封装引脚",
            "PB22 GPIO 输出",
            "gpio",
            r'associatedPins\[0\]\.pin\.\$assign\s*=\s*"(?P<value>[^"]+)"',
            "PB22",
        ),
        (
            "MFCLK gate",
            "80 MHz 与 MFCLK",
            "clock_timer",
            (
                rf'const\s+{clock_alias}\s*=\s*system\.clockTree\["MFCLKGATE"\]\s*;'
                rf"\s*(?P=alias)\.enable\s*=\s*(?P<value>true|false)"
            ),
            "true",
        ),
        (
            "SYSPLL 输入",
            "80 MHz 与 MFCLK",
            "clock_timer",
            (
                rf'const\s+{clock_alias}\s*=\s*system\.clockTree\["SYSPLLMUX"\]\s*;'
                rf'\s*(?P=alias)\.inputSelect\s*=\s*"(?P<value>[^"]+)"'
            ),
            "zSYSPLLMUX_HFCLK",
        ),
        (
            "HFXT 频率",
            "80 MHz 与 MFCLK",
            "clock_timer",
            (
                rf'const\s+{clock_alias}\s*=\s*system\.clockTree\["HFXT"\]\s*;'
                rf"[\s\S]*?(?P=alias)\.inputFreq\s*=\s*(?P<value>[0-9.]+)"
            ),
            "40",
        ),
        (
            "HFXT 输入引脚",
            "80 MHz 与 MFCLK",
            "clock_timer",
            (
                rf'const\s+{clock_alias}\s*=\s*system\.clockTree\["HFXT"\]\s*;'
                rf'[\s\S]*?(?P=alias)\.peripheral\.hfxInPin\.\$suggestSolution\s*='
                rf'\s*"(?P<value>[^"]+)"'
            ),
            "PA5",
        ),
        (
            "HFXT 输出引脚",
            "80 MHz 与 MFCLK",
            "clock_timer",
            (
                rf'const\s+{clock_alias}\s*=\s*system\.clockTree\["HFXT"\]\s*;'
                rf'[\s\S]*?(?P=alias)\.peripheral\.hfxOutPin\.\$suggestSolution\s*='
                rf'\s*"(?P<value>[^"]+)"'
            ),
            "PA6",
        ),
        (
            "UART 波特率",
            "UART0 阻塞收发基础",
            "uart",
            r"UART\d+\.targetBaudRate\s*=\s*(?P<value>\d+)",
            "115200",
        ),
        (
            "UART TX 引脚",
            "UART0 阻塞收发基础",
            "uart",
            r'UART\d+\.peripheral\.txPin\.\$assign\s*=\s*"(?P<value>[^"]+)"',
            "PA10",
        ),
        (
            "UART RX 引脚",
            "UART0 阻塞收发基础",
            "uart",
            r'UART\d+\.peripheral\.rxPin\.\$assign\s*=\s*"(?P<value>[^"]+)"',
            "PA11",
        ),
        (
            "UART 外设实例",
            "UART0 阻塞收发基础",
            "uart",
            r'UART\d+\.peripheral\.\$suggestSolution\s*=\s*"(?P<value>[^"]+)"',
            "UART0",
        ),
        (
            "UART TX DMA 通道",
            "UART DMA TX 与 IRQ RX",
            "dma",
            r'DMA_CHANNEL_TX\.peripheral\.\$suggestSolution\s*=\s*"(?P<value>[^"]+)"',
            "DMA_CH0",
        ),
        (
            "Timer 周期",
            "Timer 周期中断",
            "clock_timer",
            r'TIMER\d+\.timerPeriod\s*=\s*"(?P<value>[^"]+)"',
            "1 ms",
        ),
        (
            "Timer 实例",
            "Timer 周期中断",
            "clock_timer",
            r'TIMER\d+\.peripheral\.\$assign\s*=\s*"(?P<value>[^"]+)"',
            "TIMG12",
        ),
        (
            "空骨架 SYSCTL",
            "空配置骨架",
            "empty",
            r'scripting\.addModule\("(?P<value>/ti/driverlib/SYSCTL)"',
            "/ti/driverlib/SYSCTL",
        ),
        (
            "空骨架默认时钟",
            "空配置骨架",
            "empty",
            r"SYSCTL\.forceDefaultClkConfig\s*=\s*(?P<value>true|false)",
            "true",
        ),
    )
    for label, section_name, template_name, pattern, expected in semantic_checks:
        section_text = sections.get(section_name)
        template_text = templates.get(template_name)
        if section_text is None or template_text is None:
            continue
        reference_match = re.search(pattern, section_text)
        template_match = re.search(pattern, template_text)
        reference_value = reference_match.group("value") if reference_match else None
        template_value = template_match.group("value") if template_match else None
        if reference_value is None:
            findings.append(
                Finding("error", relative(path, root), f"{label} 无法从局部模式中解析")
            )
            continue
        if template_value is None:
            findings.append(
                Finding(
                    "error",
                    relative(template_paths[template_name], root),
                    f"{label} 无法从规范模板中解析",
                )
            )
            continue
        if reference_value != template_value:
            findings.append(
                Finding(
                    "error",
                    relative(path, root),
                    f"{label} 与规范模板不一致：局部模式={reference_value}，模板={template_value}",
                )
            )
        if reference_value != expected or template_value != expected:
            findings.append(
                Finding(
                    "error",
                    relative(path, root),
                    f"{label} 偏离天猛星基准值：期望={expected}",
                )
            )

    skill_text = read_utf8(root / "SKILL.md", findings, root)
    if skill_text is None:
        return
    routing = re.search(
        r"(?ms)^## Quick Routing\s*$\n(?P<body>.*?)(?=^## |\Z)",
        skill_text,
    )
    if routing is None:
        findings.append(Finding("error", "SKILL.md", "无法解析 Quick Routing 段"))
        return
    routing_targets = {
        target.strip().split("#", 1)[0]
        for target in MARKDOWN_LINK_RE.findall(routing.group("body"))
    }
    if "references/runtime/sysconfig-patterns.md" not in routing_targets:
        findings.append(Finding("error", "SKILL.md", "Quick Routing 未路由到 SysConfig 局部模式参考"))


def manifest_files(manifest: dict[str, object]) -> list[str]:
    values = manifest.get("source_files", [])
    if isinstance(values, list):
        return [str(value) for value in values]
    return []


def check_template_includes(template: Path, root: Path, findings: list[Finding]) -> None:
    source_files = [
        path
        for path in template.rglob("*")
        if path.is_file() and path.suffix.lower() in {".c", ".h"}
    ]
    header_names = {path.name for path in source_files if path.suffix.lower() == ".h"}
    for source in source_files:
        text = read_utf8(source, findings, root)
        if text is None:
            continue
        for include in QUOTED_INCLUDE_RE.findall(text):
            if include in EXTERNAL_QUOTED_INCLUDES or include.startswith("ti/"):
                continue
            if (
                (source.parent / include).is_file()
                or (template / include).is_file()
                or Path(include).name in header_names
            ):
                continue
            findings.append(
                Finding(
                    "error",
                    relative(source, root),
                    f"模板内引用的头文件不存在：{include}",
                )
            )


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
            if not isinstance(manifest, dict):
                findings.append(
                    Finding("error", relative(manifest_path, root), "manifest 根节点必须是 JSON 对象")
                )
                continue
            required_keys = (
                "schema",
                "name",
                "title",
                "description",
                "board",
                "device",
                "package",
                "validated",
                "validation_level",
                "physical_behavior_revalidated",
                "source_files",
                "syscfg",
            )
            for key in required_keys:
                if key not in manifest:
                    findings.append(Finding("error", relative(manifest_path, root), f"缺少字段 {key}"))
            if manifest.get("schema") != 1:
                findings.append(
                    Finding("error", relative(manifest_path, root), "manifest schema 必须为 1")
                )
            for key in ("name", "title", "description", "board", "device", "package", "validation_level", "syscfg"):
                if not isinstance(manifest.get(key), str) or not str(manifest.get(key)).strip():
                    findings.append(
                        Finding("error", relative(manifest_path, root), f"字段 {key} 必须是非空字符串")
                    )
            if not isinstance(manifest.get("validated"), bool):
                findings.append(
                    Finding("error", relative(manifest_path, root), "字段 validated 必须是布尔值")
                )
            source_files = manifest.get("source_files")
            if (
                not isinstance(source_files, list)
                or not source_files
                or not all(isinstance(item, str) and item.strip() for item in source_files)
            ):
                findings.append(
                    Finding("error", relative(manifest_path, root), "字段 source_files 必须是非空字符串列表")
                )
            if manifest.get("name") != template.name:
                findings.append(
                    Finding(
                        "error",
                        relative(manifest_path, root),
                        "manifest name 必须与模板目录名一致",
                    )
                )
            physical_revalidated = manifest.get("physical_behavior_revalidated")
            if not isinstance(physical_revalidated, bool):
                findings.append(
                    Finding(
                        "error",
                        relative(manifest_path, root),
                        "缺少布尔字段 physical_behavior_revalidated",
                    )
                )
            if (
                str(manifest.get("validation_level", "")).lower().startswith("hardware")
                and physical_revalidated is not True
            ):
                findings.append(
                    Finding(
                        "error",
                        relative(manifest_path, root),
                        "当前 validation_level 声称 hardware 时必须明确完成物理复验",
                    )
                )
            syscfgs = list(template.glob("*.syscfg"))
            if len(syscfgs) != 1:
                findings.append(Finding("error", rel, f"模板应有一个根级 .syscfg，实际 {len(syscfgs)} 个"))
            elif manifest.get("syscfg") != syscfgs[0].name:
                findings.append(
                    Finding(
                        "error",
                        relative(manifest_path, root),
                        f"manifest syscfg 必须指向 {syscfgs[0].name}",
                    )
                )
            for syscfg in syscfgs:
                syscfg_text = read_utf8(syscfg, findings, root)
                if syscfg_text is None:
                    continue
                metadata_packages = set(re.findall(r'--package\s+"([^"]+)"', syscfg_text))
                expected_package = {str(manifest.get("package"))}
                if metadata_packages != expected_package:
                    findings.append(
                        Finding(
                            "error",
                            relative(manifest_path, root),
                            "manifest package 与 .syscfg metadata 不一致："
                            f"manifest={manifest.get('package')}，"
                            f"metadata={sorted(metadata_packages)}",
                        )
                    )
                metadata_devices = set(
                    re.findall(
                        r'(?m)@v2CliArgs[^\r\n]*--device\s+"([^"]+)"',
                        syscfg_text,
                    )
                )
                expected_device = {str(manifest.get("device"))}
                if metadata_devices != expected_device:
                    findings.append(
                        Finding(
                            "error",
                            relative(manifest_path, root),
                            "manifest device 与 .syscfg v2 metadata 不一致："
                            f"manifest={manifest.get('device')}，"
                            f"metadata={sorted(metadata_devices)}",
                        )
                    )
                if re.search(r"(?m)^\s*GPIO\d+\.port\s*=", syscfg_text):
                    findings.append(
                        Finding(
                            "error",
                            relative(syscfg, root),
                            "模板仍使用 GPIO 顶层 port 旧语法",
                        )
                    )
                if re.search(
                    r"GPIO\d+\.associatedPins\[\d+\]\.pin\.\$suggestSolution",
                    syscfg_text,
                ):
                    findings.append(
                        Finding(
                            "error",
                            relative(syscfg, root),
                            "模板 GPIO 引脚应使用显式 pin.$assign",
                        )
                    )
                if (
                    "associatedPins[" in syscfg_text
                    and ".associatedPins.create(" not in syscfg_text
                ):
                    findings.append(
                        Finding(
                            "error",
                            relative(syscfg, root),
                            "新版 GPIO 写法必须先显式创建 associatedPins 子项",
                        )
                    )
            for item in manifest_files(manifest):
                candidate = template / item
                if not candidate.exists():
                    findings.append(
                        Finding("error", relative(manifest_path, root), f"source_files 路径不存在：{item}")
                    )
            declared_sources = {
                Path(item).as_posix()
                for item in manifest_files(manifest)
                if Path(item).suffix.lower() in {".c", ".h"}
            }
            actual_sources = {
                path.relative_to(template).as_posix()
                for path in template.rglob("*")
                if path.is_file() and path.suffix.lower() in {".c", ".h"}
            }
            undeclared_sources = sorted(actual_sources - declared_sources)
            if undeclared_sources:
                findings.append(
                    Finding(
                        "error",
                        relative(manifest_path, root),
                        "source_files 未声明模板源码：" + ", ".join(undeclared_sources),
                    )
                )
            if template.name in {"led_blink", "blink"} and board_dir.name in {
                "tianmengxing",
                "tianqiaoxing",
            }:
                source_path = (
                    template / "src" / "main.c"
                    if board_dir.name == "tianmengxing"
                    else template / "main.c"
                )
                source_text = read_utf8(source_path, findings, root)
                if source_text is not None:
                    required = ("CPUCLK_FREQ", "LED_BLINK_HZ", "LED_HALF_PERIOD_CYCLES")
                    if any(value not in source_text for value in required) or re.search(
                        r"delay_cycles\s*\(\s*\d+", source_text
                    ):
                        findings.append(
                            Finding(
                                "error",
                                relative(source_path, root),
                                "板载 LED 模板必须用 CPUCLK_FREQ 推导可配置半周期，不能硬编码时钟周期",
                            )
                        )
            check_template_includes(template, root, findings)


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


def check_scaffold_adaptation(root: Path, findings: list[Finding]) -> None:
    script_path = root / "scripts" / "scaffold_project.py"
    try:
        namespace = runpy.run_path(str(script_path))
        adapt_syscfg = namespace["adapt_syscfg"]
        board = namespace["BOARD_PROFILES"]["tianmengxing"]
        validate_template_name = namespace["validate_template_name"]
        iter_source_files = namespace["iter_source_files"]
        project_spec = namespace["project_spec"]
        skip_files = namespace["SKIP_FILES"]
        sample = (
            '//@cliArgs --device "MSPM0G350X" --package "LQFP-100(PZ)" --part "Default"\n'
            '* @cliArgs --device "MSPM0G3507" --package "LQFP-100(PZ)"\n'
            "// @cliArgs --board /ti/boards/LP_MSPM0G3507 --rtos nortos\n"
            "const marker = true;\n"
        )
        adapted = adapt_syscfg(sample, board)
    except (KeyError, OSError, RuntimeError, TypeError) as exc:
        findings.append(
            Finding("error", "scripts/scaffold_project.py", f"无法验证 SysConfig 适配：{exc}")
        )
        return
    required = (
        '//@cliArgs --device "MSPM0G350X" --package "LQFP-64(PM)" --part "Default"',
        '* @cliArgs --device "MSPM0G3507" --package "LQFP-64(PM)"',
        "const marker = true;",
    )
    if any(marker not in adapted for marker in required):
        findings.append(
            Finding(
                "error",
                "scripts/scaffold_project.py",
                "SysConfig 适配破坏了非空 @cliArgs 注释或封装替换",
            )
        )
    if "--board /ti/boards/LP_" in adapted or re.search(
        r"(?m)^[ \t]*(?://|\*)[ \t]*@cliArgs[ \t]*$", adapted
    ):
        findings.append(
            Finding(
                "error",
                "scripts/scaffold_project.py",
                "SysConfig 适配未清理 LaunchPad selector 或空 @cliArgs 行",
            )
        )
    if not {"ti_msp_dl_config.c", "ti_msp_dl_config.h"}.issubset(skip_files):
        findings.append(
            Finding(
                "error",
                "scripts/scaffold_project.py",
                "SDK 脚手架未排除 SysConfig 生成源文件",
            )
        )
    try:
        validate_template_name("../escape")
    except argparse.ArgumentTypeError:
        pass
    else:
        findings.append(
            Finding(
                "error",
                "scripts/scaffold_project.py",
                "模板名校验未拒绝目录穿越",
            )
        )
    with tempfile.TemporaryDirectory(prefix="mspm0-scaffold-check-") as temp_dir:
        sample_root = Path(temp_dir)
        for name in ("main.c", "example.syscfg", "ti_msp_dl_config.c", "ti_msp_dl_config.h"):
            (sample_root / name).write_text("/* 验证文件 */\n", encoding="utf-8", newline="\n")
        selected = {path.name for path in iter_source_files(sample_root)}
    if {"ti_msp_dl_config.c", "ti_msp_dl_config.h"} & selected:
        findings.append(
            Finding(
                "error",
                "scripts/scaffold_project.py",
                "SDK 脚手架仍会复制 SysConfig 生成源文件",
            )
        )
    with tempfile.TemporaryDirectory(prefix="mspm0-projectspec-check-") as temp_dir:
        destination = Path(temp_dir)
        copied = [
            destination / "main.c",
            destination / "bsp" / "hw_delay.h",
            destination / "middleware" / "common" / "driver.c",
            destination / "src" / "empty.c",
            destination / "src" / "BSP" / "UART.h",
            destination / "bsp&drivers" / "special.h",
        ]
        spec = project_spec(board, "validation", "connection.xml", copied, destination)
    try:
        ET.fromstring(spec)
    except ET.ParseError as exc:
        findings.append(
            Finding(
                "error",
                "scripts/scaffold_project.py",
                f"生成的 projectspec 不是有效 XML：{exc}",
            )
        )
        return
    expected_include_dirs = ("bsp", "bsp&amp;drivers", "middleware/common", "src", "src/BSP")
    if (
        f"-D__{board.chip}__" not in spec
        or any(
            f"-I&quot;${{PROJECT_ROOT}}/{path}&quot;" not in spec
            for path in expected_include_dirs
        )
    ):
        findings.append(
            Finding(
                "error",
                "scripts/scaffold_project.py",
                "projectspec 缺少器件宏或嵌套源码目录的头文件搜索路径",
            )
        )


def check_ccs_workspace_classification(root: Path, findings: list[Finding]) -> None:
    script_path = root / "scripts" / "check_syscfg.py"
    try:
        namespace = runpy.run_path(str(script_path))
        inspect_workspace = namespace["inspect_ccs_ai_workspace"]
        check_project = namespace["check_project"]
        with tempfile.TemporaryDirectory(prefix="mspm0-ccs-workspace-check-") as temp_dir:
            workspace = Path(temp_dir)
            skill_dir = workspace / ".claude" / "skills" / "ti-ccstudio-code-coverage"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# CCS\n", encoding="utf-8", newline="\n")
            settings = workspace / ".claude" / "settings.local.json"
            settings.write_text(
                json.dumps(
                    {
                        "permissions": {
                            "allow": [
                                "Bash(CCS/ccs/theia/resources/ai/example)"
                            ]
                        }
                    }
                ),
                encoding="utf-8",
                newline="\n",
            )
            inspection = inspect_workspace(workspace)
            _messages, details = check_project(workspace)
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
        findings.append(
            Finding(
                "error",
                "scripts/check_syscfg.py",
                f"无法验证 CCS Theia 降级元数据分类：{exc}",
            )
        )
        return
    if (
        not inspection.get("detected")
        or inspection.get("complete")
        or details.get("input_kind") != "ccs_theia_workspace"
        or details.get("project_check_performed") is not False
    ):
        findings.append(
            Finding(
                "error",
                "scripts/check_syscfg.py",
                "CCS Theia 降级元数据未被识别为不完整工作区容器",
            )
        )


def validate(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    if not (root / "SKILL.md").is_file():
        return [Finding("error", ".", "目标不是 skill 目录")]
    skill_name, _description = check_frontmatter(root, findings)
    check_package_files(root, findings)
    check_markdown(root, findings)
    check_absolute_paths(root, findings)
    check_openai_yaml(root, skill_name, findings)
    check_tianmengxing_scope(root, findings)
    check_tianqiaoxing_scope(root, findings)
    check_qei_reference(root, findings)
    check_i2c_reference(root, findings)
    check_sysconfig_patterns(root, findings)
    check_templates(root, findings)
    check_script_help(root, findings)
    check_scaffold_adaptation(root, findings)
    check_ccs_workspace_classification(root, findings)
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
