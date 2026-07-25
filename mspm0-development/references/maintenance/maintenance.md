# Skill Maintenance

## Scope

Use this file when changing, validating, packaging, or installing this skill. It owns package structure and validation policy; board facts remain in the hardware references.

## Ownership map

| Concern | Unique owner |
| --- | --- |
| Task routing and safety summary | `SKILL.md` |
| Project inspection/build lifecycle | `references/workflows/project-lifecycle.md` |
| New-project creation | `references/workflows/scaffolding.md` |
| DriverLib/SysConfig runtime rules | `references/runtime/driverlib-runtime.md` |
| Board-independent TimerG QEI method | `references/runtime/qei.md` |
| Probe/debug recovery | `references/debugging/backends.md` |
| Board facts | `references/hardware/<board>.md` |
| Peripheral detail | `references/hardware/<board>-peripherals/*.md` |
| Source provenance and maturity | `references/maintenance/sources-and-boundaries.md` |
| Executable behavior | one public script in `scripts/` |
| Copyable code/config | `assets/templates/<board>/<template>/` |

Do not add a second exhaustive routing table, duplicate public board scripts, generated build output, or prose snippets under `assets/`.

## Change workflow

1. Identify the unique owner and update that file.
2. Keep `SKILL.md` concise and route to details progressively.
3. Parameterize scripts; never embed a maintainer machine path.
4. Preserve board distinctions, validation levels, and upstream license notices.
5. Give every template a UTF-8 `manifest.json` with board, device, package, source list, and validation status.
6. Run local validation:

   ```powershell
   python -B scripts/validate_skill.py .
   python -B <skill-creator-root>\scripts\quick_validate.py .
   ```

7. Stop after repository validation when the skill is not being installed or released.
8. Only when preparing an installation or release, synchronize a validated tree, run both validators against that artifact, and compare file hashes.

## Validation levels

Report levels independently: static inspection, SysConfig generation, compilation/link, probe detection, flash, serial evidence, and physical behavior. A lower level never implies a higher level.

## Packaging rules

- Required root entries: `SKILL.md`, `agents/`, `scripts/`, `references/`, and `assets/`.
- The skill directory name must exactly match the `name` declared in `SKILL.md`.
- No `README.md`, `CLAUDE.md`, `.mcp.json`, `.claude/`, caches, editor metadata, temporary output, build directories, or board-local duplicate script trees.
- Long references include `## Scope` and `## Contents` near the top.
- Markdown links and template source paths must resolve within the package.
- Any absolute path in documentation must be a generic tool-location example, never a maintainer-local workspace path.
