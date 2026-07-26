---
name: mspm0-development
description: Develop, inspect, modify, validate, scaffold, build, flash, and debug TI MSPM0 DriverLib/SysConfig firmware, with LCKFB Tianmengxing MSPM0G3507 as the primary board and common-peripheral support for Tianqiaoxing MSPM0G3519, while preserving CCS, Keil, and CMake/GCC/OpenOCD project workflows. Use for MSPM0 C/C++ firmware, .syscfg edits, GPIO/UART/SPI/I2C/ADC/Timer/PWM/QEI work, generated-name checks, probe selection, serial tests, reusable template capture, and NUEDC/e-contest bring-up. Tianqiaoxing board-application modules without user-provided current material, other TI MCU families, arbitrary custom-board pinouts without schematics, full RTOS architecture migration, production electrical certification, and automatic unlock/mass-erase recovery are outside mature support.
---

# MSPM0 Unified Development

## Core Defaults

- Resolve bundled paths relative to this `SKILL.md`; never rely on a maintainer-local path.
- Preserve the user's project structure and treat `.syscfg` as the source of truth for pinmux, clocks, peripherals, interrupts, and DMA.
- Inspect generated `ti_msp_dl_config.h` before using macro, IRQ, instance, or init-function names.
- Prefer the user's project and matching local SDK metadata over bundled templates.
- Report `static`, `sysconfig_generation`, `compile_link`, `flash`, `serial`, and `physical_behavior` independently. A passed lower level never implies a higher one.
- Treat Tianmengxing as the primary maintained board. When the board is not explicit, identify it from project or hardware evidence instead of assuming Tianmengxing.
- Use exact LCKFB board evidence for pins and onboard hardware. Use TI LaunchPad material only for transferable device/tool behavior.
- Follow the user's language. Workflow/general references may use English for stable tool terms; LCKFB board facts and script diagnostics may use Chinese.

## Quick Routing

- **Existing project, source-only change:** run `python -B scripts/check_syscfg.py <project> --detect-probe` first. Its output is the preferred source for exact build and flash commands. If `.syscfg` and hardware assignments stay unchanged, one `.ccxml` and one `.out` are selected, and the detected probe matches the target configuration, edit `.c/.h`, build, and—only with user intent—flash without reading a reference.
- **Change `.syscfg`, pins, clocks, or peripherals:** read [project-lifecycle.md](references/workflows/project-lifecycle.md), then use [task-routing.md](references/task-routing.md) to select only one matching runtime/board/peripheral reference.
- **Create or reuse a project:** read [scaffolding.md](references/workflows/scaffolding.md) and inspect metadata with `python -B scripts/list_examples.py`; open only the chosen template.
- **Ambiguity, mismatch, failed device action, or advanced debug:** read [backends.md](references/debugging/backends.md). Do not load it for a confirmed source-only fast path.

For less common Timer, I2C, QEI, board, template, and maintenance tasks, read [task-routing.md](references/task-routing.md) only when needed.

## Template Selection

- Filter `list_examples.py` with `--board`, `--peripheral`, or `--tag` before opening files.
- Treat templates as starting evidence, not universal layouts; copy only the needed pattern.
- Packaged templates carry `static` evidence only unless their schema-2 manifest proves a higher level.

## Safety Boundary

- Read-only inspection and OS-level probe enumeration are safe defaults.
- Source/config edits stay within user-authorized files and preserve unrelated content.
- Flash, reset, halt, debugger attach, state-changing serial commands, destructive recovery, and hardware/toolchain identity changes require explicit user intent or evidence.
- A unique `.ccxml` plus unique output is not enough by itself: for the fast path, the detected probe must also match the target configuration and the user must have requested the device action.
- Never guess among multiple `.syscfg`, probes, target configurations, or outputs; never hand-edit generated files as the source fix.
- Never automate unlock, mass erase, factory reset, or replacement `.ccxml` creation during recovery.
- After a failed device action, stop repeated writes and load [backends.md](references/debugging/backends.md).

## Validation Shortcuts

- `.c/.h` only: run static checks and the project build. For a generated CCS makefile, its successful SysConfig generation is sufficient; skip standalone `run_sysconfig.py`.
- `.syscfg` changed: validate generation before or as part of the authoritative project build; use isolated `run_sysconfig.py` when early separation is useful.
- Report only reached levels. Flash success never proves `serial` or `physical_behavior`.

## Delivery

- State changed files and the exact validation levels reached.
- Report warnings, unresolved hardware facts, probe/backend, and physical observation independently.
- After changing this skill, run `python -B scripts/validate_skill.py .` and the system `quick_validate.py`.
- Only when preparing an installation or release, validate the copied/packaged artifact and compare it with the validated repository source.
