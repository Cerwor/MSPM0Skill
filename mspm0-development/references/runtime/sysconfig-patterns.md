# SysConfig 局部模式

## Scope

为天猛星 MSPM0G3507 的常见 SysConfig 修改提供一目了然的局部模式。这里的代码块不是完整 `.syscfg`，也不是第二套模板；应把它们合并进用户现有配置，并以匹配的完整模板、本地 SDK metadata 和生成结果为准。

## Contents

- [使用规则](#使用规则)
- [PB22 GPIO 输出](#pb22-gpio-输出)
- [80 MHz 与 MFCLK](#80-mhz-与-mfclk)
- [UART0 阻塞收发基础](#uart0-阻塞收发基础)
- [UART DMA TX 与 IRQ RX](#uart-dma-tx-与-irq-rx)
- [Timer 周期中断](#timer-周期中断)
- [空配置骨架](#空配置骨架)

## 使用规则

1. 先检查用户工程的 device、package、SDK、SysConfig 版本和已有实例。
2. 不重复导入已经存在的模块；实例名、引脚和资源占用必须按当前工程调整。
3. 对照所链接模板的 `manifest.json` 判断验证层级，不把历史硬件证据当作当前物理复验。
4. 重新生成后检查 `ti_msp_dl_config.h/.c`；不要承诺这里展示的生成名会跨工程保持不变。
5. 完整可复制配置的规范源仍是 `assets/templates/`，本文件只提供局部参考视图。

## PB22 GPIO 输出

天猛星板载 LED 使用 PB22、高电平点亮。使用新版 `associatedPins` 写法，不要回退到顶层 `GPIO1.port` 或只给 `$suggestSolution`。

```js
const GPIO  = scripting.addModule("/ti/driverlib/GPIO", {}, false);
const GPIO1 = GPIO.addInstance();

GPIO1.$name                          = "LED";
GPIO1.associatedPins.create(1);
GPIO1.associatedPins[0].$name        = "PIN_22";
GPIO1.associatedPins[0].initialValue = "CLEARED";
GPIO1.associatedPins[0].assignedPort = "PORTB";
GPIO1.associatedPins[0].assignedPin  = "22";
GPIO1.associatedPins[0].pin.$assign  = "PB22";
```

完整配置和验证元数据见 [`led_blink`](../../assets/templates/tianmengxing/led_blink/example.syscfg) 与其 [`manifest.json`](../../assets/templates/tianmengxing/led_blink/manifest.json)。

## 80 MHz 与 MFCLK

仅在已确认天猛星 40 MHz HFXT 位于 PA5/PA6，且用户明确同意改变时钟树时使用。字段仍须对照当前 SDK/SysConfig metadata。

```js
const SYSCTL = scripting.addModule("/ti/driverlib/SYSCTL");

const ulpClockDivider = system.clockTree["UDIV"];
ulpClockDivider.divideValue = 2;

const mfclkGate = system.clockTree["MFCLKGATE"];
mfclkGate.enable = true;

const pllQDivider = system.clockTree["PLL_QDIV"];
pllQDivider.multiplyValue = 4;

const externalHfMux = system.clockTree["EXHFMUX"];
externalHfMux.inputSelect = "EXHFMUX_XTAL";

const highSpeedMux = system.clockTree["HSCLKMUX"];
highSpeedMux.inputSelect = "HSCLKMUX_SYSPLL0";

const systemPllMux = system.clockTree["SYSPLLMUX"];
systemPllMux.inputSelect = "zSYSPLLMUX_HFCLK";

const hfxt = system.clockTree["HFXT"];
hfxt.inputFreq    = 40;
hfxt.enable       = true;
hfxt.HFXTStartup  = 10;
hfxt.HFCLKMonitor = true;

SYSCTL.forceDefaultClkConfig = true;
SYSCTL.clockTreeEn           = true;

hfxt.peripheral.$suggestSolution           = "SYSCTL";
hfxt.peripheral.hfxInPin.$suggestSolution  = "PA5";
hfxt.peripheral.hfxOutPin.$suggestSolution = "PA6";
```

不要把 `SYSCTL.peripheral.$suggestSolution` 盲目加入这个时钟模式。打开 MFCLK gate 不代表 UART 自动选择 MFCLK；若任务要求 UART 使用 MFCLK，应按当前 metadata 显式选择，并在生成配置中确认实例频率。完整实例见 [`timer_irq_led`](../../assets/templates/tianmengxing/timer_irq_led/example.syscfg)；时钟与复位注意事项见 [driverlib-runtime.md](driverlib-runtime.md)。

## UART0 阻塞收发基础

PA10/PA11 是天猛星板载 CH340 的 UART0 默认候选。先确认它们没有被当前工程改作其他功能。

```js
const UART  = scripting.addModule("/ti/driverlib/UART", {}, false);
const UART1 = UART.addInstance();

UART1.$name                       = "UART_0";
UART1.targetBaudRate              = 115200;
UART1.peripheral.txPin.$assign    = "PA10";
UART1.peripheral.rxPin.$assign    = "PA11";
UART1.peripheral.$suggestSolution = "UART0";
```

UART 时钟源和生成频率以当前生成配置为准；不要用无法支持 115200 的 LFCLK。PA10/PA11 与板载 CH340 共用，外接串口前还要避免两个发送端同时驱动同一信号。完整配置与应用代码见 [`uart_blocking_tx`](../../assets/templates/tianmengxing/uart_blocking_tx/example.syscfg) 及其 [`manifest.json`](../../assets/templates/tianmengxing/uart_blocking_tx/manifest.json)。

## UART DMA TX 与 IRQ RX

下面只展示一个 UART 通道的关键差异。DMA 通道必须与工程现有分配协调；双 UART 完整模式不要从这里拼装。

```js
UART1.enabledInterrupts    = ["DMA_DONE_TX", "RX"];
UART1.enabledDMATXTriggers = "DL_UART_DMA_INTERRUPT_TX";

UART1.DMA_CHANNEL_TX.$name       = "DMA_UART0Tx";
UART1.DMA_CHANNEL_TX.addressMode = "b2f";
UART1.DMA_CHANNEL_TX.srcLength   = "BYTE";
UART1.DMA_CHANNEL_TX.dstLength   = "BYTE";

UART1.DMA_CHANNEL_TX.peripheral.$suggestSolution = "DMA_CH0";
```

完整双 UART 配置、自定义 BSP 和 ISR 入口见 [`uart_dma_tx_irq_rx`](../../assets/templates/tianmengxing/uart_dma_tx_irq_rx/example.syscfg) 及其 [`manifest.json`](../../assets/templates/tianmengxing/uart_dma_tx_irq_rx/manifest.json)。

## Timer 周期中断

周期、实例和中断事件属于 `.syscfg`；NVIC 使能、启动计数器和 ISR 处理属于应用代码。TIMG12 只是已验证模板的明确分配，不是任意工程的默认空闲资源。

```js
const TIMER  = scripting.addModule("/ti/driverlib/TIMER", {}, false);
const TIMER1 = TIMER.addInstance();

TIMER1.$name              = "TIMER_0";
TIMER1.timerPeriod        = "1 ms";
TIMER1.timerMode          = "PERIODIC";
TIMER1.interrupts         = ["ZERO"];
TIMER1.peripheral.$assign = "TIMG12";
```

80 MHz 下模板生成的 1 ms 装载值为 `79999U`，改变 CPUCLK 后必须重新生成确认。完整配置与应用代码见 [`timer_irq_led`](../../assets/templates/tianmengxing/timer_irq_led/example.syscfg) 及其 [`manifest.json`](../../assets/templates/tianmengxing/timer_irq_led/manifest.json)。

## 空配置骨架

只在没有更匹配的用户工程或本地 SDK 示例时使用。device、package、product 和工具版本元数据应从规范模板保留或按当前目标重新生成。

```js
const SYSCTL = scripting.addModule("/ti/driverlib/SYSCTL");
const Board  = scripting.addModule("/ti/driverlib/Board", {}, false);

SYSCTL.forceDefaultClkConfig = true;
```

完整骨架见 [`empty_project`](../../assets/templates/tianmengxing/empty_project/empty.syscfg) 及其 [`manifest.json`](../../assets/templates/tianmengxing/empty_project/manifest.json)。PA19/PA20 调试接口事实见 [天猛星板级指南](../hardware/tianmengxing.md)，不要用硬编码 suggestion 替代当前求解结果。
