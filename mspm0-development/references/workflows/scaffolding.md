# Project Scaffolding

## Scope

Use this reference only when creating a new MSPM0 project from a packaged template or a local TI SDK example. Existing projects should follow `project-lifecycle.md` and receive minimal edits instead.

## Safe workflow

1. Inspect available packaged templates:

   ```powershell
   python -B scripts/list_examples.py
   ```

2. Inspect the scaffold command and run a dry run:

   ```powershell
   python -B scripts/scaffold_project.py demo --board tianmengxing --template led_blink --output <output-dir> --probe xds110 --dry-run
   ```

3. Confirm board, device, package, probe, template source, and a destination that does not exist.
4. Run the same command without `--dry-run`.
5. Open the generated `.projectspec`, regenerate SysConfig output, and verify generated names before editing runtime code.
6. Validate in order: source inspection, SysConfig generation, build, probe detection, flash, serial/physical behavior.

The scaffolder refuses an existing destination and has no force mode. It copies source, headers, `.syscfg`, and linker command files only; it does not copy generated build output or program a device.

## Packaged template versus SDK example

- Prefer a packaged template for a maintained Tianmengxing or Tianqiaoxing board feature.
- Prefer a local SDK example when no packaged template matches, when the installed SDK version matters, or when the task targets a generic/custom board.
- Pass `--sdk-root <path> --sdk-example <relative-path>` explicitly. The relative example path must remain under the SDK root.
- Templates are pattern sources, not authoritative pin maps for unrelated boards.

## Board and probe defaults

| Board key | Device/package | Expected probe |
| --- | --- | --- |
| `tianmengxing` | MSPM0G3507 / LQFP-64 | `xds110` |
| `tianqiaoxing` | MSPM0G3519 / LQFP-64 | `jlink` |

Probe selection is metadata for the generated project. It does not authorize connecting to or programming a target.

## Capturing a reusable candidate

Capture outside the installed skill:

```powershell
python -B scripts/capture_example.py <project-dir> --name <template-name> --board "<board>" --auto --output-dir <review-dir>
```

Review `manifest.json`, source licenses, pin assignments, generated-name dependencies, and validation evidence before manually promoting the candidate into `assets/templates/<board>/`.
