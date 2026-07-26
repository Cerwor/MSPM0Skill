# UART on Tianmengxing G3507

## Scope

本参考只负责天猛星 MSPM0G3507 的 UART 实例、板载连接和引脚冲突。UART 运行时必须使用当前工程生成的实例、IRQ 和 DMA 名称。

## Device instances

MSPM0G3507 只有 `UART0`、`UART1`、`UART2`、`UART3`。不存在 `UART7`。

| Instance | 板级状态 | 选择规则 |
| --- | --- | --- |
| UART0 | PA10/PA11 接板载 CH340，可与排针共用 | 默认调试串口；避免 CH340 与外部发送端同时驱动 RX 网络 |
| UART1 | 无固定板级默认 | 从精确 LQFP-64 pinmux、原理图和工程占用求解 |
| UART2 | 无固定板级默认 | 从精确 LQFP-64 pinmux、原理图和工程占用求解 |
| UART3 | 无固定板级默认 | 从精确 LQFP-64 pinmux、原理图和工程占用求解 |

## Board conflicts

- PB6、PB7、PB8、PB9 已连接板载 SPI Flash，不能作为通用 UART 默认引脚。
- 旧模板曾把 UART1 TX/RX 配到 PB6/PB7。这会让 UART TX 干扰 Flash CS，并可能在 PB7 上形成输出争用；该路由已经移除。
- UART1 的 PA8/PA9、PB4/PB5 只是器件复用候选。恢复第二路 UART 前，必须确认板卡版本原理图、SysConfig 求解结果，并完成 UART 与 Flash 共存实测。
- PA18 是 BSL 相关引脚；即使器件 pinmux 允许，也不应作为模板默认 UART 引脚。

## Packaged templates

- `uart_blocking_tx`：UART0、PA10/PA11、115200 8N1 阻塞发送起点。
- `uart_dma_tx_irq_rx`：仅包含 UART0、PA10/PA11、DMA TX 和 IRQ RX。RX ISR 只收字节并置帧标志；浮点解析、`vsnprintf` 和 DMA 启动均在主循环。

模板只提供当前包记录的静态证据。使用前重新运行匹配版本 SysConfig、编译，并按 manifest 的六级证据分别记录结果。

## Runtime rules

- 115200 波特率不能直接套用只适合低速的 LFCLK 配置；从当前生成配置确认 UART 功能时钟。
- ISR 不做字符串格式化、浮点解析、阻塞发送或业务回调。
- DMA 发送缓冲区在完成中断前不得改写。
- 未知 UART 实例必须使初始化失败，不能回落到 IRQ 0 或 DMA 通道 0。

## Primary sources

- [TI MSPM0G3507 datasheet](https://www.ti.com/lit/ds/symlink/mspm0g3507.pdf)：UART0～UART3、LQFP-64 pinmux。
- [LCKFB Tianmengxing UART tutorial](https://wiki.lckfb.com/zh-hans/tmx-mspm0g3507/ccs-beginner/uart.html)：板载 CH340 与 PA10/PA11。
- [LCKFB Tianmengxing SPI tutorial](https://wiki.lckfb.com/zh-hans/tmx-mspm0g3507/ccs-beginner/spi.html)：板载 Flash 使用 PB6～PB9。
