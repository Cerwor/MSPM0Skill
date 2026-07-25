# MSPM0 TimerG QEI

## Scope

本参考只负责 MSPM0 TimerG 两相正交编码器接口（QEI）的通用配置、位置增量、方向和验证方法。板卡引脚、编码器按键、UI 和具体机构参数必须来自当前工程、原理图与器件资料。

## Evidence order

1. 先确认当前芯片、封装、板卡原理图、电压、编码器输出类型和工程资源占用。
2. 用匹配的本地 SDK `timg_qei_mode` 例程确认当前 `/ti/driverlib/QEI` schema、DriverLib API 和生成命名。
3. 用 SysConfig 求解当前器件上同一个支持 QEI 的 TimerG 实例及其 CCP0/CCP1 合法引脚；不要复制 LaunchPad 或其他板卡的实例和引脚。
4. 旧板卡例程只能提供流程经验；其接线、按键、显示、轮询周期和实物验证不能转移为当前板卡证据。

## Hardware or GPIO decoding

- 有合法的 TimerG QEI 引脚组合且脉冲率较高时，优先硬件 QEI，减少逐边沿中断负担。
- 只有在没有合法 QEI 复用、需要特殊状态机或输入整形无法由当前硬件表达时，才考虑 GPIO/捕获软件解码，并核算最坏边沿率、中断延迟和丢脉冲风险。
- 机械编码器可能抖动。先检查器件的电气输出、上拉和波形；若当前 SysConfig/器件支持输入滤波，再按实测脉宽配置，不能用固定延时掩盖问题。

## SysConfig workflow

1. 在当前 `.syscfg` 中添加 `/ti/driverlib/QEI` 实例，优先使用两输入模式。
2. PHA 使用该 TimerG 的 CCP0，PHB 使用同一实例的 CCP1；让当前 schema 求解封装复用，再核对原理图和其他外设冲突。
3. 只在确实要响应方向变化时启用 `DC_EVENT`。方向变化中断不是“每个计数边沿”中断。
4. 保存并重新生成，检查 `ti_msp_dl_config.h/.c` 中的实例、IRQ、PHA/PHB、装载值和 `DL_TimerG_configQEI()`；应用代码只使用本工程生成的名字。
5. `SYSCFG_DL_init()` 后调用 `DL_TimerG_startCounter()`。只有配置了中断时才启用对应的生成 IRQ。

方向变化 ISR 使用 `DL_TimerG_getPendingInterrupt()` 识别 `DL_TIMER_IIDX_DIR_CHANGE`，再用 `DL_TimerG_getQEIDirection()` 读取当前计数方向。若当前器件和 schema 暴露 QEI 非法状态转换事件，可把它作为信号质量诊断，但不要在 ISR 中做显示、串口阻塞或控制计算。

若工程进入 STOP/STANDBY 等低功耗模式，先检查当前 SysConfig 诊断和器件保持能力；不能假定 QEI 寄存器与累计位置自动保留，必要时在应用层保存/恢复状态或重新初始化。

## Position and signed delta

用 `DL_TimerG_getTimerCount()` 读取位置计数。连续运动测量优先保留上次读数并计算模差，不要每次读取后重置计数器；“读后重置”在读与写之间可能丢失边沿。

设生成的装载值为 `load`，计数模数 `M = load + 1`：

```text
raw = (current - previous) mod M
if M is even and raw == M / 2:
    report sample_too_sparse
else if raw > M / 2:
    delta = raw - M
else:
    delta = raw
previous = current
```

恰好跨越半个模数时方向不可判定，应当作为采样不足处理。必须让两次采样间的最大绝对位移严格小于 `M / 2`；采样周期由最大边沿率、模数和系统最坏延迟推导，不存在通用的固定 5 ms 要求。累计位置使用足够宽的有符号类型，并明确主循环与 ISR 间的并发访问方式。

## Counts, direction, and units

- 不要固定“除以 4”。正交信号常见每个电气周期包含四个有效状态转换，但编码器资料中的 PPR、CPR、线数和机械卡点定义并不统一；从数据手册、当前 QEI 模式和整圈实测共同确定 `counts_per_rev`。
- 角度可由 `position_counts / counts_per_rev * 360°` 推导；速度还需要可靠的采样时间基准，并根据低速分辨率和高速溢出风险选择窗口。
- 正负号取决于 PHA/PHB 顺序和机构观察方向。先定义“物理正方向”，低速转动验证；必要时交换相线或在软件语义层统一取反，并记录选择。
- 三输入 QEI/Index 不是两相例程的自然延伸；只有当前器件、封装、schema 和编码器都提供合法索引输入时才增加。

## Validation ladder

1. 静态：核对器件/封装、供电电平、输出类型、共地、CCP0/CCP1 复用和 TimerG 资源冲突。
2. SysConfig：以严格模式重新生成，无错误；检查生成名字、QEI 模式、装载值和可选中断。
3. 编译/链接：确认应用没有猜测实例或 IRQ 名，也没有依赖旧例程的板级文件。
4. 波形：用示波器或逻辑分析仪确认 A/B 相位、幅值、抖动和最高边沿率。
5. 实物：分别验证慢速正反转、已知整圈计数、快速运动、换向、计数回绕和静止抖动。

生成、编译或烧录成功都不能证明方向、每圈计数或机械行为正确；只有实际波形和已知位移测试才能把这些结论提升为实物证据。
