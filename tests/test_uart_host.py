from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
UART_TEMPLATE = (
    REPO_ROOT
    / "mspm0-development"
    / "assets"
    / "templates"
    / "tianmengxing"
    / "uart_dma_tx_irq_rx"
)


class UartHostTests(unittest.TestCase):
    def test_uart_state_machine_with_driverlib_stubs(self) -> None:
        compiler = shutil.which("gcc")
        if compiler is None:
            self.skipTest("没有可用的 GCC，跳过主机端 C 状态机测试")

        with tempfile.TemporaryDirectory(prefix="mspm0-uart-host-") as temp_dir:
            executable = Path(temp_dir) / "uart_host_test.exe"
            completed = subprocess.run(
                [
                    compiler,
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-I",
                    str(REPO_ROOT / "tests" / "uart_host"),
                    "-I",
                    str(UART_TEMPLATE / "src" / "BSP"),
                    str(REPO_ROOT / "tests" / "uart_host" / "test_uart_host.c"),
                    str(UART_TEMPLATE / "src" / "BSP" / "UART.c"),
                    "-o",
                    str(executable),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

            executed = subprocess.run(
                [str(executable)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)


if __name__ == "__main__":
    unittest.main()
