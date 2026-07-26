# 天猛星 QEI

## Scope

本参考只保留天猛星 MSPM0G3507 的 QEI 引脚候选、可达性和资源冲突。TimerG 配置、位置模差、方向、换算与验证方法见 [MSPM0 TimerG QEI](../../peripherals/qei.md)。

## 板级适配

- 目标基线是 MSPM0G3507 LQFP-64；必须从当前工程、板卡原理图和本地 SysConfig metadata 重新求解 TimerG 的 CCP0/CCP1。
- 匹配 SDK 的 `LP_MSPM0G3507/driverlib/timg_qei_mode` 常见 TIMG8、PA29/PA30 组合，只能作为器件复用候选，不能证明天猛星排针可达或当前工程空闲。
- 使用 PA29/PA30 前核对板卡版本、外部编码器电平、共地、输出类型和现有占用。
- TIMG8 被 QEI 占用后，不能同时供 PB22 LED PWM、PB26 背光 PWM 或其他 Timer/PWM 实例使用；先释放整个实例再重新求解。
- 当前 skill 没有天猛星 QEI 规范模板，也没有本版本物理行为复验；生成、编译和烧录不能证明方向或每圈计数。
