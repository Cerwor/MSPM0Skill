# PWM on Tianmengxing G3507

## Scope

本参考负责天猛星 MSPM0G3507 的 Timer PWM 实例、已核对的板载引脚和运行时边界。

## Device instances

MSPM0G3507 的 Timer 实例是 TIMG0、TIMG6、TIMG7、TIMG8、TIMG12、TIMA0 和 TIMA1。不存在 `TIMG2`。不同实例的位宽、通道、QEI、dead-band 和 shadow 能力不同，必须从当前器件 metadata 求解。

## Board mappings

只保留下列已经用 TI LQFP-64 pinmux 与板载连接交叉核对的映射：

| Board pin | Timer channel | Board function | Constraint |
| --- | --- | --- | --- |
| PB22 | TIMG8 CCP1 | 板载 LED，高有效 | 与任何其他 TIMG8 用途互斥 |
| PB26 | TIMG6 CCP0 | LCD 背光 | 与任何其他 TIMG6 用途互斥 |

旧文档中的 PB26/TIMG8、PA3/TIMG0、PA4/TIMG0、PB0/TIMG6、PB2/TIMG6-CCP1 和 PB4/TIMG8 映射均不可使用。选择其他 PWM 引脚时，从精确 SysConfig metadata 重新求解，不按“空闲 GPIO”猜测 Timer 通道。

## Canonical PB22 pattern

完整配置由 [`pwm_breath_led`](../../../assets/templates/tianmengxing/pwm_breath_led/example.syscfg) 负责。局部关键值是：

```js
PWM1.$name                      = "PWM_0";
PWM1.peripheral.$assign         = "TIMG8";
PWM1.peripheral.ccp1Pin.$assign = "PB22";
PWM1.PWM_CHANNEL_1.dutyCycle    = 50;
```

使用前重新生成并检查：

- `PWM_0_INST`
- `GPIO_PWM_0_C1_IDX`
- Timer 功能时钟、period 和 compare 范围

不要把这段局部配置当作独立、可直接生成的完整 `.syscfg`。

## Runtime

初始化后显式启动计数器：

```c
SYSCFG_DL_init();
DL_TimerG_startCounter(PWM_0_INST);
```

对当前 EDGE_ALIGN_UP 配置，高电平占比取决于生成模式和 compare 方向。使用模板时将 compare 限制在 `1..period-1`，并在示波器或 LED 上确认极性；不要把其他 MCU 的 ARR/CCR 经验直接迁移。

```c
DL_TimerG_setCaptureCompareValue(
    PWM_0_INST,
    compare,
    GPIO_PWM_0_C1_IDX);
```

呼吸循环使用有符号变量或显式边界，避免无符号递减回绕。PWM ISR 如存在，也必须遵循短 ISR 规则。

## Resource conflicts

- TIMG8 用于 QEI 时，PB22 不能继续作为 TIMG8 PWM。
- PB26 属于 TIMG6 CCP0，因此不会仅因 TIMG8 QEI 而发生实例冲突；仍须检查当前工程中的 TIMG6 和引脚占用。
- PB6～PB9 连接板载 SPI Flash，不能作为任意 PWM 默认候选。

## Primary source

[TI MSPM0G3507 datasheet, pin attributes and TIMx configurations](https://www.ti.com/lit/ds/symlink/mspm0g3507.pdf)。
