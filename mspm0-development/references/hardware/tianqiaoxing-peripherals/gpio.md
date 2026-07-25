# 天巧星 GPIO

## PB22 最小验证

PB22 板载 LED 为低有效：低电平点亮，高电平熄灭。推荐 SysConfig 写法显式创建 pin 子项并固定物理引脚：

```js
const GPIO = scripting.addModule("/ti/driverlib/GPIO", {}, false);
const GPIO1 = GPIO.addInstance();

GPIO1.$name                          = "GPIO_LED";
GPIO1.associatedPins.create(1);
GPIO1.associatedPins[0].$name        = "PIN";
GPIO1.associatedPins[0].direction    = "OUTPUT";
GPIO1.associatedPins[0].initialValue = "SET";
GPIO1.associatedPins[0].assignedPort = "PORTB";
GPIO1.associatedPins[0].assignedPin  = "22";
GPIO1.associatedPins[0].pin.$assign  = "PB22";
```

运行时代码使用生成宏：

```c
DL_GPIO_togglePins(GPIO_LED_PORT, GPIO_LED_PIN_PIN);
delay_cycles(CPUCLK_FREQ / (2U * LED_BLINK_HZ));
```

`associatedPins.create(1)`、`assignedPort`、`assignedPin` 和 `pin.$assign` 共同表达“这个逻辑 GPIO 明确绑定 PB22”。不要回退到顶层 `GPIO1.port` 或只给建议值的旧写法。

## 通用流程

1. 在 `.syscfg` 中创建输入、输出或中断 GPIO，并显式分配当前原理图允许的引脚。
2. 重新生成后，从 `ti_msp_dl_config.h` 读取端口、pin mask、IOMUX 和 IRQ 名。
3. 输出先确认有效电平和上电初值；输入先确认上下拉、最大电压和外部驱动方式。
4. 中断处理函数只读取 pending source、清状态并记录事件；耗时工作放回主循环。
5. 分别报告 SysConfig、构建、烧录和实际电平/LED 观察结果。

## 常见错误

- `DL_GPIO_initDigitalOutput()` 只配置复用时，仍需确认生成初始化是否启用了输出方向。
- 直接写 `GPIOA`、`DL_GPIO_PIN_x` 会绕过生成名，换引脚后容易静默失配。
- 把低有效 LED 当成高有效会让初始状态和亮灭语义相反。
- 忙等待只适合最小冒烟测试；并发任务改用周期 Timer。
