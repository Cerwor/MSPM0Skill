import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "mspm0-development" / "scripts"


def load_script(name: str):
    path = SCRIPTS_ROOT / name
    spec = importlib.util.spec_from_file_location(f"test_{path.stem}_discovery", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载脚本：{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CCS_DSS = load_script("ccs_dss_debug.py")
CHECK_SYSCFG = load_script("check_syscfg.py")
DETECT_PROBE = load_script("detect_probe.py")
RUN_SYSCONFIG = load_script("run_sysconfig.py")


class CcsDssDiscoveryTests(unittest.TestCase):
    def test_find_run_bat_from_project_build_rule(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mspm0-ccs-discovery-") as temp_dir:
            root = Path(temp_dir)
            project = root / "project"
            debug_dir = project / "Debug"
            debug_dir.mkdir(parents=True)
            ccs_root = root / "MSPSDK" / "CCS" / "ccs"
            run_bat = ccs_root / "scripting" / "run.bat"
            run_bat.parent.mkdir(parents=True)
            run_bat.write_text("@echo off\n", encoding="utf-8", newline="\n")
            tool = ccs_root / "utils" / "sysconfig_1.27.0" / "sysconfig_cli.bat"
            build_rule = (
                f'"{tool.as_posix()}" --script "{(project / "empty.syscfg").as_posix()}" '
                '--compiler ticlang\n'
            )
            (debug_dir / "subdir_rules.mk").write_text(
                build_rule,
                encoding="utf-8",
                newline="\n",
            )
            clean_env = {
                variable: ""
                for variable in (
                    *CCS_DSS.RUN_BAT_ENV_VARS,
                    *CCS_DSS.CCS_ROOT_ENV_VARS,
                    "TI_ROOT",
                )
            }
            with (
                mock.patch.dict(os.environ, clean_env, clear=False),
                mock.patch.object(CCS_DSS, "DEFAULT_RUN_BAT_CANDIDATES", ()),
            ):
                selected = CCS_DSS.find_run_bat(None, project)
            self.assertEqual(selected.resolve(), run_bat.resolve())


class CcsToolDiscoveryTests(unittest.TestCase):
    def make_project(self, root: Path, include_dslite: bool = True) -> tuple[Path, Path]:
        project = root / "project"
        debug_dir = project / "Debug"
        target_dir = project / "targetConfigs"
        debug_dir.mkdir(parents=True)
        target_dir.mkdir()
        (project / "empty.syscfg").write_text(
            '//@v2CliArgs --device "MSPM0G3507" --package "LQFP-64(PM)"\n',
            encoding="utf-8",
            newline="\n",
        )
        (debug_dir / "makefile").write_text("all:\n", encoding="utf-8", newline="\n")
        (debug_dir / "firmware.out").write_bytes(b"ELF")
        (target_dir / "target.ccxml").write_text(
            "<configurations/>\n",
            encoding="utf-8",
            newline="\n",
        )

        ccs_root = root / "MSPSDK" / "CCS" / "ccs"
        sysconfig = ccs_root / "utils" / "sysconfig_1.27.0" / "sysconfig_cli.bat"
        gmake = ccs_root / "utils" / "bin" / "gmake.exe"
        run_bat = ccs_root / "scripting" / "run.bat"
        for path in (sysconfig, gmake, run_bat):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"tool")
        if include_dslite:
            dslite = ccs_root / "ccs_base" / "DebugServer" / "bin" / "DSLite.exe"
            dslite.parent.mkdir(parents=True)
            dslite.write_bytes(b"tool")

        build_rule = (
            f'"{sysconfig.as_posix()}" --script "{(project / "empty.syscfg").as_posix()}" '
            '--compiler ticlang\n'
        )
        (debug_dir / "subdir_rules.mk").write_text(
            build_rule,
            encoding="utf-8",
            newline="\n",
        )
        return project, ccs_root

    def discovery_context(self):
        clean_env = {
            variable: ""
            for variable in (
                *CHECK_SYSCFG.CCS_ROOT_ENV_VARS,
                "TI_ROOT",
            )
        }
        return (
            mock.patch.dict(os.environ, clean_env, clear=False),
            mock.patch.object(CHECK_SYSCFG.shutil, "which", return_value=None),
        )

    def test_check_syscfg_discovers_exact_ccs_tools_and_prefers_dss_flash(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mspm0-tool-layout-") as temp_dir:
            project, ccs_root = self.make_project(Path(temp_dir))
            env_patch, which_patch = self.discovery_context()
            with env_patch, which_patch:
                tools = CHECK_SYSCFG.discover_ccs_tools(project)
                hints = CHECK_SYSCFG.find_validation_hints(project, tools)

            for name in ("sysconfig_cli", "gmake", "ccs_run", "dslite"):
                self.assertEqual(tools[name]["status"], "found")
            self.assertEqual(
                Path(str(tools["gmake"]["path"])),
                (ccs_root / "utils" / "bin" / "gmake.exe").resolve(),
            )
            self.assertIn("ccs_dss_debug.py", hints["flash"])
            self.assertIn('load --reset "System Reset" --leave-running', hints["flash"])
            self.assertIn("dslite_flash_fallback", hints)
            self.assertIn("sysconfig_isolated", hints)
            self.assertNotIn("sysconfig_validate", hints)
            self.assertTrue(hints["gmake"].startswith(f'"{tools["gmake"]["path"]}"'))

    def test_missing_dslite_suppresses_only_dslite_hints(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mspm0-tool-missing-") as temp_dir:
            project, _ccs_root = self.make_project(Path(temp_dir), include_dslite=False)
            env_patch, which_patch = self.discovery_context()
            with env_patch, which_patch:
                tools = CHECK_SYSCFG.discover_ccs_tools(project)
                hints = CHECK_SYSCFG.find_validation_hints(project, tools)

            self.assertEqual(tools["dslite"]["status"], "not_found")
            self.assertIn("flash", hints)
            self.assertNotIn("dslite_list_cores", hints)
            self.assertNotIn("dslite_flash_fallback", hints)


class ProbePresentationTests(unittest.TestCase):
    def test_known_vid_uses_usb_vendor_in_text_output(self) -> None:
        probe = DETECT_PROBE.Probe(
            kind="jlink",
            display_name="SEGGER J-Link",
            manufacturer="localized host controller",
            usb_vendor=DETECT_PROBE.usb_vendor_name("1366:0105"),
            usb_id="1366:0105",
            serial_ports=["COM5"],
            confidence="high",
            recommended_backend="ccs_dss_or_vendor_tool",
            recommended_config="",
            evidence=[],
        )
        output = io.StringIO()
        with redirect_stdout(output):
            DETECT_PROBE.print_text([probe])
        rendered = output.getvalue()
        self.assertIn("USB vendor: SEGGER", rendered)
        self.assertNotIn("localized host controller", rendered)


class SysConfigSelectionTests(unittest.TestCase):
    def test_build_rule_version_drift_is_non_blocking(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mspm0-sysconfig-drift-") as temp_dir:
            root = Path(temp_dir)
            tool = root / "sysconfig_cli.bat"
            tool.write_text("@echo off\n", encoding="utf-8", newline="\n")
            info = RUN_SYSCONFIG.ProjectInfo(
                project=str(root),
                script=str(root / "empty.syscfg"),
                metadata={},
                ccs_products={"sysconfig": "1.26.2"},
                ccs_product_conflicts={},
                ccs_compiler="ticlang",
                ccs_compiler_conflicts=[],
                build_evidence=[
                    RUN_SYSCONFIG.BuildEvidence(
                        tool=str(tool),
                        script=str(root / "empty.syscfg"),
                        product="",
                        compiler="ticlang",
                        source=str(root / "Debug" / "subdir_rules.mk"),
                    )
                ],
            )
            with mock.patch.object(
                RUN_SYSCONFIG,
                "query_tool_version",
                return_value="1.27.0+4565",
            ):
                selected, warnings, candidates = RUN_SYSCONFIG.select_tool(info, None)
            self.assertEqual(selected.version, "1.27.0+4565")
            self.assertEqual(candidates, [selected])
            self.assertEqual(len(warnings), 1)
            self.assertIn("active build rule", warnings[0])


if __name__ == "__main__":
    unittest.main()
