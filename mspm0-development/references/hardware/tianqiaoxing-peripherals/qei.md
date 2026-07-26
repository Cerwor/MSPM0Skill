# 天巧星 QEI

## Scope

本参考只保留天巧星 MSPM0G3519 的 QEI 板级边界。TimerG 配置、位置模差、方向、换算与验证方法见 [MSPM0 TimerG QEI](../../peripherals/qei.md)。

## 板级适配

- 目标基线是 MSPM0G3519 LQFP-64(PM)，仍以用户工程、芯片丝印和当前原理图为准。
- 从本地 SysConfig metadata 选择同一支持 QEI 的 TimerG 实例及其 CCP0/CCP1 合法引脚。
- 不保留旧编码器应用的固定引脚、按键、显示、轮询周期、驱动文件或模板；这些内容不能作为当前板卡证据。
- 核对所选 TimerG 与当前 PWM、Timer、捕获任务的整实例冲突，并确认两相输入的电平、上拉和最高边沿率。
- 当前 skill 没有天巧星 QEI 规范模板；只有已知位移、整圈计数、正反转和回绕实测才能提升为物理验证。
