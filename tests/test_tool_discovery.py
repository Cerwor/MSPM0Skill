import importlib.util
import os
import sys
import tempfile
import unittest
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
