# 天巧星 Timer

## 何时使用

- 只做 LED 冒烟测试且主循环无并发工作时，可用 `delay_cycles()`。
- 需要周期调度、超时、采样触发或并发主循环时，使用 `/ti/driverlib/TIMER`。
- 需要输出 PWM 时改读 [pwm.md](pwm.md)，不要把 TIMER 和 PWM 的 SysConfig 字段混用。

## 周期中断模式

1. 从当前项目中选择未占用 Timer；不要维护静态“空闲实例”表。
2. 设置时钟源、分频、周期、启动行为和 `ZERO` 等所需中断。
3. 重新生成并使用 `ti_msp_dl_config.h` 中的实例、IRQ 和初始化名。
4. ISR 只读取 pending source、清状态并增加 `volatile` tick 或设置事件标志。
5. 业务处理、打印和阻塞调用放在主循环。

示意结构：

```c
volatile uint32_t g_tick_count;

void TIMER_TICK_INST_IRQHandler(void)
{
    if (DL_TimerG_getPendingInterrupt(TIMER_TICK_INST) ==
        DL_TIMER_IIDX_ZERO) {
        g_tick_count++;
    }
}
```

TimerA、TimerG、实际 IRQ 名和 pending API 以当前生成代码为准。

## 验证

先核对生成周期和 `CPUCLK_FREQ`，再构建并观察 tick。需要证明周期精度时，用 GPIO 翻转配合仪器测量；不能从源码常量单独得出实际频率。
