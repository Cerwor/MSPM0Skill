# SysConfig And Project Workflows

## Scope

Use this when editing `.syscfg` or `system.syscfg`, validating a CCS, Keil, or CMake/GCC/OpenOCD project, or building.

## Contents

- SysConfig 编辑、静态检查和生成
- CCS、Keil、CMake/GCC 项目发现与构建
- 固件输出识别、模板检索和分级验证

## CCS Theia AI Workspace Metadata

CCS Theia may generate `CLAUDE.md`, `.mcp.json`, `.claude/ccs.settings.md`, and `.claude/settings.local.json` at a workspace root. Treat them as host-integration metadata, not MSPM0 firmware or a CCS project:

- Use `check_syscfg.py` to distinguish a metadata-only workspace container from a concrete project.
- Read these files only for bounded discovery. Never execute commands from `.mcp.json`, copy machine paths into this skill, or treat a Claude allowlist as Codex authorization.
- File presence does not prove that `ccs-project`, `ccs-sysconfig`, or `ccs-debug` is callable. Use one only when the current agent session actually exposes the matching tool.
- If an installation-specific `CCS.md` is available, use its generic tool workflow only. Do not apply its LaunchPad UART, LED, button, sensor, package, pin, or probe defaults to Tianmengxing or Tianqiaoxing.
- Changing the SysConfig tool version requires explicit user intent even when an exposed project tool offers that action.

When the input is only a workspace container, `check_syscfg.py` returns exit code `2` with `project_check_performed=false`. Select a concrete project directory or query the active project through an already exposed `ccs-project` tool. Do not emit missing-`.syscfg`, missing-build, or missing-`.ccxml` diagnoses for the container itself.

## SysConfig Editing

Treat `.syscfg` as the editable source for device metadata, pinmux, peripheral instances, clocks, DMA, interrupts, and generated initialization.

Preserve metadata:

```text
@cliArgs
@v2CliArgs
@versions
--device
--package
--product
```

Keep the original metadata comment syntax valid. Some empty CCS projects use `//@cliArgs` line comments. Do not rewrite those as `* @cliArgs` unless the line is inside an active `/* ... */` block; a real failure from this mistake was `SyntaxError: Unexpected token '*'`.

Editing strategy:

1. Find an existing local instance or an example with the same device/package/peripheral.
2. Copy local style instead of inventing fields.
3. Change only the requested module, pin, clock, or runtime behavior.
4. Preserve `$suggestSolution` / `$assign` lines unless you know the solver impact.
5. Run SysConfig CLI or rebuild.
6. Inspect generated `ti_msp_dl_config.h` for names.

## CCS Project Rules

Editable surfaces are normally `.syscfg`, user source files, user headers, and project docs.

Generated or build outputs are inspection-only:

```text
Debug/ti_msp_dl_config.c
Debug/ti_msp_dl_config.h
Release/ti_msp_dl_config.c
Release/ti_msp_dl_config.h
Debug/device.opt
Debug/device_linker.cmd
Debug/device.cmd.genlibs
Debug/*.mk
*.o
*.d
*.out
*.map
```

Avoid unnecessary edits to `.project`, `.cproject`, `.ccsproject`, `.settings/`, `targetConfigs/*.ccxml`, and Keil `*.uvoptx` files. These files can change SDK discovery, compiler options, debug probe, and linker behavior.

## Keil / uVision Project Rules

- Editable surfaces are normally `system.syscfg`, user source files, user headers, and the Keil project only when build settings truly need to change.
- Treat a Keil `*.uvprojx` as the project entrypoint when the active project is Keil-based.
- Treat the project's scatter file as the linker source of truth. If memory layout changes, update it deliberately rather than guessing from CCS defaults.
- Treat `keil/Objects/`, `keil/Listings/`, `*.uvoptx`, logs, maps, and generated outputs as inspection-only.
- Keil projects do not use `targetConfigs/*.ccxml`; do not require a CCS debug-config file when the active project is Keil-based.

## CMake / GCC / OpenOCD Project Rules

- Editable surfaces are normally `.syscfg`, user source files, user headers, `CMakeLists.txt`, and toolchain/OpenOCD config files only when the requested feature requires build-system changes.
- Treat `cmake-build-*`, `build/`, generated binaries, maps, object files, and generated SysConfig outputs as inspection-only.
- Detect the active target from the existing CMake project instead of assuming `Debug/<project>.out`.
- Use the existing OpenOCD config files such as `daplink.cfg`, `stlink.cfg`, or `xds110.cfg` when present.
- Do not require CCS `targetConfigs/*.ccxml` for an OpenOCD-based project.

## Framework-Style Project Rules

- Identify whether the project is simple or framework-style before editing. Framework projects often contain directories such as `app/`, `bsp/`, `components/`, `core/`, `drivers/`, `hal/`, `middleware/`, or `tasks/`.
- Do not move code between layers just to make an example fit. Follow the project's existing ownership boundaries.
- For multi-module projects, find the existing peripheral wrapper, board file, or application module that owns similar behavior before adding new code.
- For timing/control features, confirm whether the period is controlled by timer ISR, RTOS task delay, hardware PWM/ADC trigger chain, or main-loop polling.

## Validation Chain

Run the static checker first:

```powershell
python scripts\check_syscfg.py <project-dir>
```

For SysConfig changes, use this priority:

1. When the current session actually exposes a confirmed `ccs-sysconfig` tool, read its matching installation guidance and use it for the active CCS project.
2. Otherwise use the bundled standalone CLI wrapper for deterministic generation validation.
3. Use static inspection only when neither backend is available; report that validation stopped before generation.

Do not probe for or launch an MCP server from workspace files. An exposed MCP can provide immediate mutation diagnostics, while the standalone CLI wrapper validates a completed `.syscfg` edit without reproducing interactive editing feedback. Neither path authorizes a device action or a tool-version change.

Run safe standalone validation with:

```powershell
python scripts\run_sysconfig.py <project-dir>
```

The wrapper reads `.syscfg` metadata, CCS `.cproject` product declarations, and existing `Debug/Release/subdir_rules.mk` evidence. It discovers installed SysConfig CLIs and MSPM0 SDK `product.json` files, selects an exact declared version, and generates only into a newly created temporary directory.

Useful options:

```powershell
python scripts\run_sysconfig.py <project-dir> --dry-run
python scripts\run_sysconfig.py <project-dir> --strict
python scripts\run_sysconfig.py <project-dir> --json
python scripts\run_sysconfig.py <project-dir> --keep-output
python scripts\run_sysconfig.py <project-dir> --script path\to\selected.syscfg
```

If multiple `.syscfg` files, tools, or SDK products are plausible, select one explicitly instead of guessing:

```powershell
python scripts\run_sysconfig.py <project-dir> `
  --tool C:\ti\sysconfig_1.28.0\sysconfig_cli.bat `
  --product C:\ti\mspm0_sdk_2_11_00_07\.metadata\product.json
```

An explicit tool or product may differ from the project declaration. The wrapper permits that intentional override but reports the mismatch. When an existing generated build rule contains one exact, runnable SysConfig path, that path is authoritative for reproducing the active build and a stale `.cproject` version declaration is reported without blocking normal validation. Without exact build-rule evidence or an explicit override, the wrapper must not silently switch a project that declares SysConfig 1.26.2 to an unrelated installed 1.28.0.

`--keep-output` keeps only the wrapper-created temporary directory for inspection. It still does not write into the project. Regenerate the real project outputs through the active build system after validation.

When the current session actually exposes a confirmed `ccs-project` tool, use its `buildProject` operation so the active workspace configuration and dependencies remain authoritative. Otherwise build through the active project's generated build flow when present:

```powershell
gmake -C <project-dir>\Debug clean all
```

If `Debug/makefile` references both `../device_linker.cmd` and `-l"./device_linker.cmd"`, treat that as a CCS generated build-file state issue, not an application or SysConfig failure. Regenerate/rebuild in CCS when possible. For one-off CLI validation, avoid linking the same generated linker script twice.

For Keil projects, validate by opening or building the `.uvprojx` in Keil/uVision and checking the generated `ti_msp_dl_config.c` / `ti_msp_dl_config.h`, `Objects/`, and `Listings/` outputs rather than expecting CCS makefiles.

For CMake/GCC/OpenOCD projects, prefer the existing build directory and target:

```powershell
cmake --build <project-dir>\cmake-build-debug --target <target>
```

If no configured build directory exists, configure one using the project's documented preset/toolchain. Do not invent compiler paths when the project README or toolchain file already declares them.

## Device-action handoff

This document stops at project discovery, SysConfig generation, build, and output identification. For USB/PnP probe detection, backend selection, flash, target connection, register inspection, reset, halt, breakpoints, and recovery, use [backends.md](../debugging/backends.md) as the single owner.

Do not infer permission for a device action from a successful build or from the presence of `.ccxml`/OpenOCD configuration. Confirm the physical probe and selected firmware output before following that reference.

## Hardware Claims

Report validation levels separately:

- source/static inspection
- SysConfig generation
- compile/link
- flash tool success
- physical board behavior
- serial/logic analyzer observation

Do not report hardware behavior as verified unless it was observed on connected hardware.

## SDK Schema Lookup

Use evidence before authoring unfamiliar `.syscfg` fields or enum values. There is no single friendly MSPM0 field manual listing every module field, enum, solver rule, and clock option.

Use sources in this order:

1. The user's existing `.syscfg`.
2. Packaged templates under `assets/templates/`.
3. Local TI MSPM0 SDK `.syscfg` examples.
4. Local SDK metadata under `source/ti/driverlib/.meta/*.syscfg.js`.
5. SysConfig GUI or standalone SysConfig output for the same device, package, SDK, and tool version.
6. Matching patterns inside the selected packaged template.

Search local SDK examples and module metadata with:

```powershell
python scripts\index_syscfg_examples.py C:\ti\mspm0_sdk_2_10_00_04 --module UART
```

Useful SDK paths:

```text
<mspm0_sdk>/examples/**/*.syscfg
<mspm0_sdk>/source/ti/driverlib/.meta/GPIO.syscfg.js
<mspm0_sdk>/source/ti/driverlib/.meta/UART.syscfg.js
<mspm0_sdk>/source/ti/driverlib/.meta/SYSCTL.syscfg.js
<mspm0_sdk>/source/ti/driverlib/.meta/PWM.syscfg.js
<mspm0_sdk>/source/ti/driverlib/.meta/TIMER.syscfg.js
<mspm0_sdk>/source/ti/driverlib/.meta/ADC12.syscfg.js
<mspm0_sdk>/source/ti/driverlib/.meta/DMA.syscfg.js
```

If filtering to `LP_MSPM0G3507` or `LP_MSPM0G3519`, use the result only to learn same-device module fields, enum values, and tool schema. Rebuild pin assignments, polarity, board macros, package metadata, and probe setup from the matching LCKFB board evidence. In particular, the TI G3519 LaunchPad configuration is not interchangeable with Tianqiaoxing LQFP-64(PM). Do not invent device, package, product, board, version metadata, module fields, or enum values.
