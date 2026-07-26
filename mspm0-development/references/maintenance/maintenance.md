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
| Concise SysConfig pattern views | `references/runtime/sysconfig-patterns.md` |
| Board-independent peripheral methods | `references/peripherals/*.md` |
| Probe/debug recovery | `references/debugging/backends.md` |
| Board facts | `references/hardware/<board>.md` |
| Peripheral detail | `references/hardware/<board>-peripherals/*.md` |
| Source provenance and maturity | `references/maintenance/sources-and-boundaries.md` |
| Executable behavior | one public script in `scripts/` |
| Copyable code/config | `assets/templates/<board>/<template>/` |

Do not add a second exhaustive routing table, duplicate public board scripts, generated build output, or prose snippets under `assets/`. Keep `references/runtime/sysconfig-patterns.md` as the only concise pattern view; complete copyable configuration remains owned by `assets/templates/`.

## Change workflow

1. Identify the unique owner and update that file.
2. Keep `SKILL.md` concise and route to details progressively.
3. Parameterize scripts; never embed a maintainer machine path.
4. Preserve board distinctions, validation levels, and upstream license notices.
5. Give every template a UTF-8 schema-2 `manifest.json` with board, device, package, source list, `content_sha256`, lifecycle, and six-level validation evidence.
6. When a canonical template changes a represented field, review the concise SysConfig pattern view in the same change.
7. Run local validation:

   ```powershell
   python -B scripts/validate_skill.py .
   python -B <skill-creator-root>\scripts\quick_validate.py .
   ```

8. Stop after repository validation when the skill is not being installed or released.
9. Only when preparing an installation or release, synchronize a validated tree, run both validators against that artifact, and compare file hashes.

## Validation levels

Report exactly these levels independently: `static`, `sysconfig_generation`, `compile_link`, `flash`, `serial`, and `physical_behavior`. OS-level probe detection is a diagnostic prerequisite, not a firmware validation level. A lower level never implies a higher level.

Each passed level needs a dated record with a concrete result and appropriate evidence. Static evidence binds to `content_sha256`, calculated from sorted relative paths plus strict UTF-8 template text with line endings normalized to LF so Git checkout policy does not invalidate the record. Higher levels should retain exact tool versions and commands, while device-facing levels should additionally retain the board revision, firmware hash, and a log or observation reference. Never reconstruct missing historical evidence.

## Packaging rules

- Required root entries: `SKILL.md`, `agents/`, `scripts/`, `references/`, and `assets/`.
- The skill directory name must exactly match the `name` declared in `SKILL.md`.
- No `README.md`, `CLAUDE.md`, `.mcp.json`, `.claude/`, caches, editor metadata, temporary output, build directories, or board-local duplicate script trees.
- Long references include `## Scope` and `## Contents` near the top.
- Markdown links and template source paths must resolve within the package.
- Any absolute path in documentation must be a generic tool-location example, never a maintainer-local workspace path.
