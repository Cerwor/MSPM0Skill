# Sources and Support Boundaries

## Scope

This file records where the unified skill came from, which source owns each class of fact, and what has or has not reached mature support.

## Source families

- `mspm0-skill-main` is the engineering core for project discovery, SysConfig checking/generation, probe detection, CCS DSS, OpenOCD, serial interaction, example indexing, and reusable-template metadata.
- The Tianmengxing source contributes MSPM0G3507 board/peripheral facts and hardware-observed templates.
- The Tianqiaoxing source contributes distilled MSPM0G3519 common-peripheral facts, board-independent TimerG QEI lessons, and a minimal GPIO smoke-test template.
- Current [LCKFB Tianmengxing](https://wiki.lckfb.com/zh-hans/tmx-mspm0g3507/) and [LCKFB Tianqiaoxing](https://wiki.lckfb.com/zh-hans/tqx-mspm0g3519/index.html) board pages, download packages, and schematics are dynamic upstream evidence for board facts.
- TI SDK, SysConfig device metadata, compiler/linker output, and probe tools remain upstream evidence for the exact installed device/tool version, not for LCKFB board wiring.

Bundled source license texts are retained under `references/maintenance/licenses/`. New contributions should retain compatible attribution and must not silently relicense imported code.

## Distillation Coverage

| Source | Retained capability | Deliberate treatment |
| --- | --- | --- |
| `mspm0-skill-main/skills/mspm0-ccs` | All nine core scripts; project discovery; SysConfig generation; probe detection; serial, CCS DSS, and OpenOCD workflows; six compact G3507 templates | Five scripts remain byte-equivalent. Template listing/capture, workspace recognition, and bounded Windows probe discovery are maintained changes; the unified scaffolder is a maintained addition. |
| Standalone `mspm0-ccs` snapshot | Same core rules, snippets, examples, and hardware lessons | Screenshots, cache files, README files, and raw duplicate prose snippets are not copied. Their reusable content is represented by canonical templates and the normalized `references/runtime/sysconfig-patterns.md` view. |
| `mspm0kit-tianmengxing` | Board pin/clock/occupancy facts and all six peripheral references | Board-local setup/build/flash/cleanup/serial scripts were consolidated into core discovery, project workflow, debug backends, and the unified scaffolder. Maintainer-local path defaults and implicit cleanup/device actions were not retained. |
| `mspm0kit-tianqiaoxing` | Device/package baseline, common GPIO/ADC/PWM/Timer/QEI/UART/SPI/I2C patterns, and the minimal blink source/config | QEI is retained only as board-independent TimerG configuration, wrap-safe delta, scaling, and validation guidance rechecked against the matching TI SDK. No old QEI application code/config is copied; fixed encoder pins, button/display behavior, polling interval, board driver, and example template remain deliberately absent with the other board applications. |
| CCS Theia-generated AI workspace metadata | Workspace-container recognition; conditional routing to actually exposed project, SysConfig, or debug tools; one-session/reload safety rules | `.mcp.json`, `.claude/`, `CLAUDE.md`, machine paths, and host allowlists are not copied. TI Arm Clang coverage is specialized and remains outside this distillation. |

“Retained” means the usable knowledge or behavior has one maintained owner in this skill. It does not mean every source file is copied verbatim.

## Evidence precedence

Use evidence by fact class:

1. Start with the user's exact project, board revision, schematic, device marking, and generated output.
2. For Tianmengxing board wiring, polarity, onboard occupancy, and common probe setup, use matching current LCKFB material, then the bundled board guide/template.
3. For Tianqiaoxing common peripherals, use the user's exact project and current schematic first, then the bounded common-peripheral references. Its generic QEI guidance is not evidence for old encoder wiring or physical behavior; the skill intentionally carries no advanced board-application wiring.
4. For MCU capabilities, package schema, DriverLib, SysConfig fields, SDK/compiler behavior, and CCS mechanics, use matching installed TI metadata and official device/tool documentation.
5. Use TI LaunchPad and other-board examples only as adaptation patterns. Never transfer their pins, LEDs, buttons, UART backchannels, sensors, package defaults, or probe configuration to an LCKFB board.

When sources conflict, preserve the conflict explicitly and ask for missing hardware/project evidence instead of choosing by convenience.

## Known board distinctions

- Tianmengxing is the primary maintained board and its guidance/templates target MSPM0G3507 LQFP-64. Tianqiaoxing support targets MSPM0G3519-family LQFP-64 only at the common-peripheral layer.
- TI `LP_MSPM0G3519` examples target the LaunchPad's PZ device/board configuration, while Tianqiaoxing uses LQFP-64(PM). The scaffolder may adapt package metadata, but every retained pin and board macro still requires Tianqiaoxing review.
- Current LCKFB CCS material uses external J-Link as the Tianmengxing tutorial example and supplies external XDS110 with the Tianqiaoxing kit. Either board can still be used with another supported probe when the physical connection and project configuration agree.
- Tianqiaoxing board-application pin maps and middleware are intentionally absent. Reload them only from material supplied for the current task and keep that evidence task-local unless the user explicitly requests a new distillation.
- The historical Tianqiaoxing QEI example is not a trusted template: its packaged dependencies and alternate GPIO path are incomplete, while midpoint reset, fixed `/4`, fixed 5 ms timing, and application callbacks are hardware/application assumptions. Its old hardware-validation label does not transfer to this skill.
- The old QEI/OLED application subtree does not carry self-contained component attribution and notices in the inspected snapshot. Do not copy code or config from it; any future import requires an explicit upstream license/notice review.
- The old Tianmengxing peripheral snapshot claims PA0/PA1 board pull-ups without a bundled schematic. Official LCKFB CCS and Keil software-I2C tutorials use PA0/PA1 with opposite SDA/SCL roles, so tutorial wiring is not hardware-mux evidence. For hardware I2C0, treat PA0/SDA and PA1/SCL only as current MSPM0G3507 metadata candidates, and require the current schematic, external-module data, or measurement before claiming pull-ups.

## Mature support

- Source and `.syscfg` inspection, generated-name checks, bounded SysConfig execution, template enumeration/capture, deterministic scaffolding, probe detection, serial monitoring, CCS DSS setup, and OpenOCD setup.
- Full maintained Tianmengxing routing plus bounded Tianqiaoxing routing for board facts in `references/hardware/`, with reusable cross-board methods in `references/peripherals/`.

## Partial or conditional support

- Keil and CMake/GCC projects: inspect and preserve the existing project flow; local toolchain evidence determines exact commands.
- Hardware I2C alternate pin routing: verify against the installed SysConfig device data and schematic.
- Advanced recovery: identify and explain, but do not automate unlock or mass erase.
- CCS MCP integration: use only when the current host actually exposes the matching tool; generated workspace files alone are only read-only discovery evidence.

## Out of scope

- Other TI MCU families, undocumented custom-board pin maps, production electrical certification, and full RTOS architecture migration.
- TI LaunchPad board-specific defaults and TI Arm Clang code-coverage instrumentation.
- Claims of physical correctness without observed serial, waveform, or other board evidence.
