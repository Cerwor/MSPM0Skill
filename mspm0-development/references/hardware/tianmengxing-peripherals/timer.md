# Timer on Tianmengxing G3507

## Scope

本参考负责天猛星 MSPM0G3507 的周期 Timer 实例、计时公式和中断边界。PWM 输出由 [pwm.md](pwm.md) 负责。

## Device instances

| Timer | 分辨率 | Prescaler | Repeat counter | 说明 |
| --- | --- | --- | --- | --- |
| TIMG0、TIMG6、TIMG7、TIMG8 | 16-bit | 8-bit | 无 | 通用定时、捕获或 PWM；具体能力按实例核对 |
| TIMG12 | 32-bit | 无 | 无 | 长周期通用 Timer |
| TIMA0、TIMA1 | 16-bit | 8-bit | 8-bit | 高级 Timer，功能与通道数按实例核对 |

不存在笼统的 “TIMG0～TIMG7 全部可用” 范围，也不存在 `TIMG13`。

## Period calculation

不要只按计数器位宽估算“最大周期”。周期同时取决于源时钟、Clock Divider、Prescaler 和 LOAD：

```text
period = (LOAD + 1) × divider × prescale_divisor / source_clock
```

- `divider` 的允许值和 `timerClkPrescale` 的编码以当前 SDK metadata 与生成代码为准。
- 16-bit TIMG0/6/7/8 有 8-bit prescaler；TIMG12 没有该 prescaler。
- 对 TIMA 的 repeat counter，应从生成配置确认它是否参与当前模式，不能把它默认并入公式。
- 最终以生成的 `*_LOAD_VALUE`、实例时钟频率和示波器/逻辑分析仪观测为准。

无分频基准仅用于量级检查：

| Timer | 32 MHz、divider=1 | 80 MHz、divider=1 |
| --- | --- | --- |
| 16-bit TIMG | 约 2.048 ms | 约 0.8192 ms |
| 32-bit TIMG12 | 约 134.218 s | 约 53.687 s |

这些不是绝对最大值。改变 divider、prescaler 或时钟源会改变范围。

## SysConfig and runtime pattern

SysConfig 属性名不能凭经验猜测。优先打开同 SDK、同器件的 Timer 示例或 [timer_irq_led](../../../assets/templates/tianmengxing/timer_irq_led/example.syscfg)，然后重新生成。

```c
SYSCFG_DL_init();
NVIC_EnableIRQ(TIMER_0_INST_INT_IRQN);
DL_TimerG_startCounter(TIMER_0_INST);

void TIMG12_IRQHandler(void)
{
    switch (DL_TimerG_getPendingInterrupt(TIMER_0_INST)) {
        case DL_TIMER_IIDX_ZERO:
            /* 只记录状态或更新短小计数器。 */
            break;
        default:
            break;
    }
}
```

- `SYSCFG_DL_init()` 后显式使能 NVIC 并启动计数器。
- ISR 只完成 pending 分发和短小状态更新；不阻塞、不格式化字符串、不做复杂解析。
- LED 冒烟测试可以用短暂忙等。需要并发按键消抖或周期任务时，使用工程已有 tick、时间戳状态机或共享周期源，不要在 ISR 内延时，也不必仅为消抖独占一个新 Timer。

## Primary source

[TI MSPM0G3507 datasheet, TIMx configurations](https://www.ti.com/lit/ds/symlink/mspm0g3507.pdf)。
