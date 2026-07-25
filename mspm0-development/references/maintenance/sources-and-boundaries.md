# Sources and Support Boundaries

## Scope

This file records where the unified skill came from, which source owns each class of fact, and what has or has not reached mature support.

## Source families

- `mspm0-skill-main` is the engineering core for project discovery, SysConfig checking/generation, probe detection, CCS DSS, OpenOCD, serial interaction, example indexing, and reusable-template metadata.
- The Tianmengxing source contributes MSPM0G3507 board/peripheral facts and hardware-observed templates.
- The Tianqiaoxing source contributes MSPM0G3519 board/peripheral facts and hardware-observed templates.
- TI SDK, SysConfig device metadata, compiler/linker output, probe tools, schematics, and the user's generated files remain higher-authority evidence for the exact installed version and project.

Bundled source license texts are retained under `references/maintenance/licenses/`. New contributions should retain compatible attribution and must not silently relicense imported code.

## Evidence precedence

Use evidence in this order:

1. User project, schematic, device marking, and generated output.
2. Matching installed TI SDK/SysConfig metadata and official device documentation.
3. Matching board guide and packaged template manifest.
4. Similar examples used only as adaptation patterns.

When sources conflict, preserve the conflict explicitly and ask for missing hardware/project evidence instead of choosing by convenience.

## Known board distinctions

- Tianmengxing guidance and templates target MSPM0G3507 LQFP-64; Tianqiaoxing guidance and templates target MSPM0G3519-family LQFP-64.
- Tianqiaoxing's shared/onboard software-I2C guidance may use PA0/PA1, while the packaged `imu_lsm6ds3` template is a separately validated PA28/PA27 wiring variant.
- Tianqiaoxing board guidance recommends 115200 baud for new wireless UART work, while the packaged `wireless_uart7` artifact preserves a validated 9600-baud baseline. Adapting it to 115200 requires a SysConfig regeneration and serial test.

## Mature support

- Source and `.syscfg` inspection, generated-name checks, bounded SysConfig execution, template enumeration/capture, deterministic scaffolding, probe detection, serial monitoring, CCS DSS setup, and OpenOCD setup.
- Maintained Tianmengxing and Tianqiaoxing board routing for the peripherals documented in `references/hardware/`.

## Partial or conditional support

- Keil and CMake/GCC projects: inspect and preserve the existing project flow; local toolchain evidence determines exact commands.
- Hardware I2C alternate pin routing: verify against the installed SysConfig device data and schematic.
- Advanced recovery: identify and explain, but do not automate unlock or mass erase.

## Out of scope

- Other TI MCU families, undocumented custom-board pin maps, production electrical certification, and full RTOS architecture migration.
- Claims of physical correctness without observed serial, waveform, display, motion, or other board evidence.

