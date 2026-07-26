from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "mspm0-development"
SCRIPTS_ROOT = SKILL_ROOT / "scripts"


def load_script(name: str):
    path = SCRIPTS_ROOT / name
    spec = importlib.util.spec_from_file_location(f"test_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载脚本：{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CAPTURE = load_script("capture_example.py")
VALIDATOR = load_script("validate_skill.py")


def write_syscfg(path: Path) -> None:
    path.write_text(
        "\n".join(
            (
                '//@cliArgs --device "MSPM0G350X" --package "LQFP-64(PM)" '
                '--part "Default" --product "mspm0_sdk@2.10.00.04"',
                '//@v2CliArgs --device "MSPM0G3507" --package "LQFP-64(PM)" '
                '--product "mspm0_sdk@2.10.00.04"',
                '// @versions {"tool":"1.27.0+4565"}',
                'const SYSCTL = scripting.addModule("/ti/driverlib/SYSCTL");',
            )
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


class CaptureContractTests(unittest.TestCase):
    def test_parse_metadata_only_trusts_exact_v2(self) -> None:
        text = (
            '//@cliArgs --device "MSPM0G350X" --package "LQFP-64(PM)" '
            '--product "mspm0_sdk@2.10.00.04"\n'
            ' * @v2CliArgs --device "MSPM0G3507" --package "LQFP-64(PM)" '
            '--product "mspm0_sdk@2.10.00.04"\n'
        )
        metadata = CAPTURE.parse_metadata(text)
        self.assertEqual(metadata["device"], "MSPM0G3507")
        self.assertEqual(metadata["package"], "LQFP-64(PM)")
        self.assertEqual(metadata["product"], "mspm0_sdk@2.10.00.04")

    def test_parse_metadata_rejects_wildcard_v2_device(self) -> None:
        text = (
            '//@v2CliArgs --device "MSPM0G350X" --package "LQFP-64(PM)" '
            '--product "mspm0_sdk@2.10.00.04"\n'
        )
        with self.assertRaises(SystemExit):
            CAPTURE.parse_metadata(text)

    def test_capture_rejects_empty_source_selection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mspm0-capture-empty-") as temp_dir:
            temp = Path(temp_dir)
            project = temp / "project"
            project.mkdir()
            write_syscfg(project / "empty.syscfg")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPTS_ROOT / "capture_example.py"),
                    str(project),
                    "--name",
                    "empty",
                    "--board",
                    "LCKFB Tianmengxing MSPM0G3507",
                    "--auto",
                    "--output-dir",
                    str(temp / "output"),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("No source files matched", completed.stderr + completed.stdout)
            self.assertFalse((temp / "output" / "empty").exists())

    def test_capture_emits_schema2_candidate_and_reproducible_hash(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mspm0-capture-valid-") as temp_dir:
            temp = Path(temp_dir)
            project = temp / "project"
            project.mkdir()
            write_syscfg(project / "empty.syscfg")
            (project / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
            output = temp / "output"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPTS_ROOT / "capture_example.py"),
                    str(project),
                    "--name",
                    "valid",
                    "--board",
                    "LCKFB Tianmengxing MSPM0G3507",
                    "--include",
                    "main.c",
                    "--output-dir",
                    str(output),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            template = output / "valid"
            manifest = json.loads((template / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema"], 2)
            self.assertEqual(manifest["device"], "MSPM0G3507")
            self.assertEqual(manifest["sdk"], "MSPM0 SDK 2.10.00.04")
            self.assertEqual(manifest["sysconfig"], "1.27.0")
            self.assertEqual(manifest["lifecycle"], "candidate")
            self.assertEqual(manifest["validation"]["highest_level"], "unverified")
            self.assertEqual(
                set(manifest["validation"]["levels"].values()),
                {"not_run"},
            )
            self.assertEqual(manifest["validation"]["records"], [])
            expected = VALIDATOR.calculate_template_content_sha256(template, manifest)
            self.assertEqual(manifest["content_sha256"], expected)
            source_path = template / "src" / "main.c"
            source_bytes = source_path.read_bytes()
            lf_bytes = source_bytes.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            source_path.write_bytes(lf_bytes.replace(b"\n", b"\r\n"))
            self.assertEqual(
                VALIDATOR.calculate_template_content_sha256(template, manifest),
                expected,
            )
            findings: list[VALIDATOR.Finding] = []
            VALIDATOR.check_validation_contract(
                manifest,
                template / "manifest.json",
                temp,
                findings,
            )
            self.assertEqual(findings, [])

    def test_failed_force_capture_does_not_overwrite_existing_candidate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mspm0-capture-force-") as temp_dir:
            temp = Path(temp_dir)
            project = temp / "project"
            project.mkdir()
            (project / "bad.syscfg").write_text(
                '//@v2CliArgs --device "MSPM0G350X" --package "LQFP-64(PM)" '
                '--product "mspm0_sdk@2.10.00.04"\n',
                encoding="utf-8",
            )
            (project / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
            candidate = temp / "output" / "existing"
            candidate.mkdir(parents=True)
            sentinel = candidate / "keep.txt"
            sentinel.write_text("keep\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPTS_ROOT / "capture_example.py"),
                    str(project),
                    "--name",
                    "existing",
                    "--board",
                    "LCKFB Tianmengxing MSPM0G3507",
                    "--include",
                    "main.c",
                    "--output-dir",
                    str(temp / "output"),
                    "--force",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")

    def test_read_text_rejects_invalid_utf8(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mspm0-capture-utf8-") as temp_dir:
            path = Path(temp_dir) / "invalid.c"
            path.write_bytes(b"\xff\xfe")
            with self.assertRaises(SystemExit):
                CAPTURE.read_text(path)


class ValidatorRegressionTests(unittest.TestCase):
    def test_static_record_requires_top_level_content_hash(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mspm0-manifest-record-") as temp_dir:
            root = Path(temp_dir)
            manifest_path = root / "manifest.json"
            manifest = {
                "content_sha256": "a" * 64,
                "validation": {
                    "highest_level": "static",
                    "levels": {
                        "static": "passed",
                        "sysconfig_generation": "not_run",
                        "compile_link": "not_run",
                        "flash": "not_run",
                        "serial": "not_run",
                        "physical_behavior": "not_run",
                    },
                    "records": [
                        {
                            "level": "static",
                            "status": "passed",
                            "checked_at": "2026-07-26",
                            "result": "仅静态检查。",
                            "artifact_sha256": "b" * 64,
                        }
                    ],
                },
            }
            findings: list[VALIDATOR.Finding] = []
            VALIDATOR.check_validation_contract(
                manifest,
                manifest_path,
                root,
                findings,
            )
            self.assertTrue(
                any("静态记录摘要" in finding.message for finding in findings)
            )

    def test_markdown_command_checker_rejects_legacy_and_missing_scripts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mspm0-doc-command-") as temp_dir:
            root = Path(temp_dir)
            (root / "SKILL.md").write_text(
                "\n".join(
                    (
                        "# Test",
                        "```powershell",
                        r"python skills\mspm0-ccs\scripts\ccs_dss_debug.py demo probe",
                        "python scripts\\missing.py --help",
                        "python scaffold.py demo",
                        "```",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            findings: list[VALIDATOR.Finding] = []
            VALIDATOR.check_markdown_commands(root, findings)
            messages = "\n".join(finding.message for finding in findings)
            self.assertIn("旧 mspm0-ccs", messages)
            self.assertIn("scaffold.py", messages)
            self.assertIn("不存在的技能脚本", messages)

    def test_uart_safety_rejects_flash_pins_and_complex_isr(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mspm0-uart-safety-") as temp_dir:
            root = Path(temp_dir)
            template = (
                root
                / "assets"
                / "templates"
                / "tianmengxing"
                / "uart_dma_tx_irq_rx"
            )
            template.mkdir(parents=True)
            (template / "example.syscfg").write_text(
                'UART1.peripheral.txPin.$assign = "PB6";\n',
                encoding="utf-8",
            )
            (template / "unsafe.c").write_text(
                "\n".join(
                    (
                        "void UART0_IRQHandler(void)",
                        "{",
                        '    printf("unsafe");',
                        "}",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            findings: list[VALIDATOR.Finding] = []
            VALIDATOR.check_uart_template_safety(root, findings)
            messages = "\n".join(finding.message for finding in findings)
            self.assertIn("PB6–PB9", messages)
            self.assertIn("中断路径执行复杂", messages)

    def test_device_instance_checker_rejects_nonexistent_instances(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mspm0-instance-safety-") as temp_dir:
            root = Path(temp_dir)
            refs = root / "references" / "hardware" / "tianmengxing-peripherals"
            refs.mkdir(parents=True)
            (refs / "timer.md").write_text(
                "UART7、TIMG2、TIMG13、TIMG0–TIMG7\n",
                encoding="utf-8",
            )
            findings: list[VALIDATOR.Finding] = []
            VALIDATOR.check_tianmengxing_device_instances(root, findings)
            messages = "\n".join(finding.message for finding in findings)
            self.assertIn("UART7", messages)
            self.assertIn("TIMG2", messages)
            self.assertIn("TIMG13", messages)
            self.assertIn("连续范围", messages)

    def test_script_help_checker_executes_scripts(self) -> None:
        public_scripts = (
            "capture_example.py",
            "ccs_dss_debug.py",
            "check_syscfg.py",
            "detect_probe.py",
            "index_syscfg_examples.py",
            "list_examples.py",
            "openocd_debug.py",
            "run_sysconfig.py",
            "scaffold_project.py",
            "serial_console.py",
            "validate_skill.py",
        )
        with tempfile.TemporaryDirectory(prefix="mspm0-help-check-") as temp_dir:
            root = Path(temp_dir)
            scripts = root / "scripts"
            scripts.mkdir()
            good = (
                "import argparse\n"
                "parser = argparse.ArgumentParser()\n"
                "parser.parse_args()\n"
            )
            for name in public_scripts:
                (scripts / name).write_text(good, encoding="utf-8")
            (scripts / "serial_console.py").write_text(
                "raise SystemExit(7)\n",
                encoding="utf-8",
            )
            findings: list[VALIDATOR.Finding] = []
            VALIDATOR.check_script_help(root, findings)
            self.assertTrue(
                any(
                    finding.path == "scripts/serial_console.py"
                    and "--help 返回 7" in finding.message
                    for finding in findings
                )
            )


if __name__ == "__main__":
    unittest.main()
