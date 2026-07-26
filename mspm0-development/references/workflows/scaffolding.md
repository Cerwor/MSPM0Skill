# Project Scaffolding

## Scope

Use this reference only when creating a new MSPM0 project from a packaged template or a local TI SDK example. Existing projects should follow `project-lifecycle.md` and receive minimal edits instead.

## Safe workflow

1. Inspect available packaged templates:

   ```powershell
   python -B scripts/list_examples.py
   python -B scripts/list_examples.py --board Tianmengxing --peripheral UART
   ```

   Read `validation_level` and `physical_behavior_revalidated` independently; `validated=true` does not by itself claim current physical-board behavior.

2. Inspect the scaffold command and run a dry run:

   ```powershell
   python -B scripts/scaffold_project.py demo --board tianmengxing --template led_blink --output <output-dir> --probe jlink --dry-run
   ```

3. Confirm board, device, package, probe, template source, and a destination that does not exist.
4. Run the same command without `--dry-run`.
5. Open the generated `.projectspec`, regenerate SysConfig output, and verify generated names before editing runtime code.
6. Validate in order: source inspection, SysConfig generation, build, probe detection, flash, serial/physical behavior.

The scaffolder refuses an existing destination and has no force mode. It copies source, headers, `.syscfg`, and linker command files only; it does not copy generated build output or program a device.

## Packaged template versus SDK example

- Prefer a packaged template for a maintained Tianmengxing feature or the Tianqiaoxing GPIO smoke test.
- Prefer a local SDK example when no packaged template matches, when the installed SDK version matters, or when the task targets a generic/custom board.
- Pass the SDK DriverLib example name as `--template <name>` together with `--source sdk --sdk-root <path>`.
- SDK examples are LaunchPad-oriented sources. The scaffolder removes the LaunchPad board selector and adapts supported package metadata, but it does not claim automatic peripheral/pin remapping; review every retained pin against the selected board guide before generation or build.
- Templates are pattern sources, not authoritative pin maps for unrelated boards.

## Tianqiaoxing application boundary

Only the common-peripheral references and the minimal blink template are bundled for Tianqiaoxing. When a task needs a board-application module, treat the user's current schematic, code, datasheet, and wiring notes as task-local input; do not infer a missing application template or silently promote it into the skill.

## Board and probe starting points

| Board key | Device/package | LCKFB documentation starting point |
| --- | --- | --- |
| `tianmengxing` | MSPM0G3507 / LQFP-64 | External J-Link in the CCS tutorial |
| `tianqiaoxing` | MSPM0G3519 / LQFP-64(PM) | External XDS110 supplied with the kit |

These are starting points, not hard board bindings. Detect or inspect the actual probe, then pass `--probe jlink` or `--probe xds110` explicitly. Probe selection is metadata for the generated project and does not authorize connecting to or programming a target.

## Capturing a reusable candidate

Capture outside the installed skill:

```powershell
python -B scripts/capture_example.py <project-dir> --name <template-name> --board "<board>" --auto --output-dir <review-dir>
```

Review `manifest.json`, source licenses, pin assignments, generated-name dependencies, and validation evidence before manually promoting the candidate into `assets/templates/<board>/`.
