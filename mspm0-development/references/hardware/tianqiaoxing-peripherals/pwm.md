# 天巧星 PWM

## 选择模块

需要输出波形时使用 SysConfig `/ti/driverlib/PWM`；只需要周期事件时使用 `/ti/driverlib/TIMER`。实例、CC 通道和输出引脚由当前项目与 MSPM0G3519 LQFP-64(PM) metadata 决定，不保留板载应用的固定 Timer 分配。

## 计算与配置

1. 从 `CPUCLK_FREQ` 和生成的 Timer 时钟确认计数频率。
2. 根据目标频率计算 period，再把业务 duty 映射为合法 compare 范围。
3. 在 `.syscfg` 中显式选择 Timer、CC 通道和物理引脚。
4. 重新生成并核对实例、CC index、输出极性和启动配置。
5. 运行时更新 compare 值时钳制上下界，避免无符号下溢或 period 边界回绕。

通用关系：

```text
timer_tick_hz = timer_input_hz / divider / prescaler
pwm_hz        = timer_tick_hz / period_counts
```

实际高电平占空比还受计数方向、初始输出和反相设置影响。不要仅凭 compare 数值大小推断“更亮”或“更快”，先阅读生成配置并测量波形。

## 验证

- SysConfig：合法实例/引脚且无资源冲突。
- 构建：生成实例和 CC 宏正确。
- 运行：确认计数器确实启动。
- 物理：用示波器或逻辑分析仪测频率、占空比和极性；仅观察负载现象不足以证明时序精度。
