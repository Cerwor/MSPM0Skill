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
- For Tianmengxing or Tianqiaoxing, prefer the exact board schematic, current LCKFB material, and matching board guide for board-level facts.
- Keep Tianqiaoxing support at the common-peripheral layer. For a removed board application, use only the current material supplied for that task and do not reconstruct it from remembered wiring.
- Use TI LaunchPad material only for transferable device, SDK, SysConfig, and tool behavior; never import its LED, UART, button, sensor, pin, package, or probe defaults into an LCKFB board.

## Quick Routing

Read only one Tier-1 reference first. Load Tier-2 only when the task needs that detail or the first attempt lacks evidence.

| User task | Tier-1 first read | Tier-2 conditional read | Expected result |
| --- | --- | --- | --- |
| Inspect or modify an existing CCS, Keil, or CMake project; edit `.syscfg`; build | [project-lifecycle.md](references/workflows/project-lifecycle.md) | [driverlib-runtime.md](references/runtime/driverlib-runtime.md) for runtime code | Minimal source/config change with an evidence-based validation chain |
| Add GPIO, UART, SPI, ADC, PWM, DMA, interrupt, clock, or external module | [driverlib-runtime.md](references/runtime/driverlib-runtime.md) | Matching board/peripheral guide; use [sysconfig-patterns.md](references/runtime/sysconfig-patterns.md) only when its Contents lists a matching pattern | SysConfig/DriverLib implementation using local generated names |
| Select an MSPM0G3507 Timer instance or calculate its period/range | [timer.md](references/hardware/tianmengxing-peripherals/timer.md) | [driverlib-runtime.md](references/runtime/driverlib-runtime.md) for ISR/runtime integration | Exact discrete instances and a divider/prescaler-aware calculation without board-pin assumptions |
| Add an I2C controller/target or diagnose an I2C bus | [i2c.md](references/peripherals/i2c.md) | Matching board I2C guide, current schematic, and target-device datasheet | Electrically safe transaction flow with bounded waits and observable validation |
| Add a quadrature encoder or configure TimerG QEI | [qei.md](references/peripherals/qei.md) | Matching board guide, current schematic, and installed SDK `timg_qei_mode` example | Pin-safe QEI design with explicit count scaling and wrap handling |
| Create a new project or select a reusable start | [scaffolding.md](references/workflows/scaffolding.md) | Matching board guide; then one selected asset | A dry-run-reviewed, non-overwriting project scaffold |
| Detect a probe, flash, inspect registers, set breakpoints, or diagnose a debug backend | [backends.md](references/debugging/backends.md) | [hardware-validation.md](references/troubleshooting/hardware-validation.md) after failure | Explicit backend selection and bounded device action |
| Use Tianmengxing MSPM0G3507 pins or onboard devices | [tianmengxing.md](references/hardware/tianmengxing.md) | One file under `references/hardware/tianmengxing-peripherals/` | Board-correct pins, polarity, clock, and template choice |
| Use Tianqiaoxing MSPM0G3519 GPIO, ADC, PWM, Timer, QEI, UART, SPI, or I2C | [tianqiaoxing.md](references/hardware/tianqiaoxing.md) | One matching board file and, when routed, one generic peripheral reference | Minimal board adaptation without bundled board-application assumptions |
| Maintain, extend, validate, or install this skill | [maintenance.md](references/maintenance/maintenance.md) | [sources-and-boundaries.md](references/maintenance/sources-and-boundaries.md) | Ownership-preserving update with package validation |

Do not create another exhaustive task-routing table in a reference.

## Template Selection

Use `python -B scripts/list_examples.py` to inspect metadata before opening template files. Add `--board`, `--peripheral`, or `--tag` when narrowing the list.

| Need | Starting asset | Required reference |
| --- | --- | --- |
| Tianmengxing empty, blink, PWM, Timer IRQ, blocking UART, or UART DMA/IRQ | `assets/templates/tianmengxing/<template>/` | [tianmengxing.md](references/hardware/tianmengxing.md) |
| Tianqiaoxing common GPIO smoke test | `assets/templates/tianqiaoxing/blink/` | [tianqiaoxing.md](references/hardware/tianqiaoxing.md) |
| New CCS scaffold from a packaged template or local SDK example | `python -B scripts/scaffold_project.py --help` | [scaffolding.md](references/workflows/scaffolding.md) |

Treat templates as starting evidence, not universal project layouts. Copy only the needed pattern into an existing project.

Packaged templates currently carry `static` evidence only. Read each schema-2 manifest before reuse; do not promote an old observation or a successful static check into SysConfig, build, flash, serial, or physical-behavior evidence.

## Safety Boundary

### Default read-only

- Inspect files, manifests, generated headers, tool versions, PnP/serial devices, and OS-level probe listings.
- Run `check_syscfg.py`, `run_sysconfig.py --dry-run`, `detect_probe.py`, validators, and CLI `--help`.

### Ordinary reversible changes

- Modify user-authorized source and `.syscfg` files while preserving unrelated content.
- Create a new project only in a new destination after reviewing `scaffold_project.py --dry-run`.
- Generate SysConfig output only in the wrapper-created temporary directory unless the user explicitly invokes the project build.

### Require explicit user intent

- Program flash, reset or halt a target, run backend `inspect-target`, attach a debugger, send serial commands that change device state, or overwrite/remove user files.
- Change device, package, SDK, compiler, SysConfig tool version, board, clock source, probe configuration, or electrical pin assignment when project evidence is insufficient.

### Never assume or automate

- Never hand-edit generated SysConfig/build outputs as the source fix.
- Never select among multiple probes, `.ccxml` files, firmware outputs, or `.syscfg` files by guess.
- Never treat `.mcp.json`, Claude allowlists, or CCS-generated workspace metadata as proof that a tool is callable or that a device/project mutation is authorized.
- Never auto-unlock, mass erase, factory reset, or create a replacement `.ccxml` during recovery.
- Never claim physical behavior from source, generation, build, or flash success alone.

After a failed device action, stop repeated writes, preserve logs, return to read-only detection, and follow the recovery section of [backends.md](references/debugging/backends.md).

## Delivery

- State changed files and the exact validation levels reached.
- Report warnings independently from success.
- Name every user decision or hardware fact still required.
- For board work, include pin, voltage/protocol assumptions, probe/backend, and whether behavior was physically observed.
- After changing this skill, run `python -B scripts/validate_skill.py .` and the system `quick_validate.py`.
- Only when preparing an installation or release, validate the copied/packaged artifact and compare it with the validated repository source.
