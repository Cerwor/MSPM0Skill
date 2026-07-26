# Hardware Validation Notes

## Scope

Use this for Tianmengxing MSPM0G3507 historical observations and real-board caveats. Historical notes are not current physical evidence unless their evidence record is complete.

## Contents

- 历史观察环境与证据缺口
- 时钟、SysConfig、构建与串口故障模式
- 不可从软件结果推导的硬件结论

## Historical Observation Environment

The following combination was recorded by an earlier test:

- Board: LCKFB Tianmengxing MSPM0G3507
- IDE: CCS / CCS Theia
- SDK: MSPM0 SDK 2.10.00.04
- SysConfig: 1.26.2
- Compiler: TI Arm Clang 4.0.3 LTS
- Debug probe: J-Link through UniFlash / DSLite
- Observed peripherals: PB22 onboard LED, UART0 blocking TX, PB22 TIMG8 PWM breathing LED, TIMG12 periodic interrupt
- Clock context: defer to the board and SysConfig owners linked below; this historical record is not complete enough to restate clock facts

This record lacks the test date, exact board revision, commands, logs, firmware hash, and structured observations. It therefore cannot prove current physical behavior or qualify a template as hardware-validated. Other boards, packages, SDK versions, CCS versions, probes, and pin maps may work, but they are not guaranteed by these notes.

## Tianmengxing Special Pin Caution

The LCKFB Tianmengxing documentation marks A21, A23, A02, A18, A10, and A11 as special pins and says they should not be used unless necessary. In SysConfig or generated headers these may appear as PA21, PA23, PA02, PA18, PA10, and PA11.

PA10 and PA11 need a narrower rule than the other special pins because Tianmengxing routes them as its default UART connection. When the user asks the agent to choose UART pins, PA10 TX and PA11 RX are preferred candidates if they are free and compatible with the selected UART instance. This pairing is also the historical UART0 baseline recorded by this skill.

For GPIO, PWM, SPI, I2C, timer capture, or other non-UART functions, continue to treat PA10/PA11 as special and prefer other available pins. Repurposing them may conflict with or remove the board's default UART connection, so explain that consequence first. For A21/PA21, A23/PA23, A02/PA02, and A18/PA18, prefer other available pins for ordinary assignments unless the user explicitly requests them or the existing project already deliberately uses them.

## PB22 LED Lessons

The LCKFB Tianmengxing onboard LED uses PB22. A historical GPIO blink recorded generated names similar to:

```c
LED_PORT
LED_PIN_22_PIN
SYSCFG_DL_init()
```

The historical LED blink used `delay_cycles()` as a smoke-test convenience. Recalculate from the generated `CPUCLK_FREQ`; do not treat an elapsed-time impression as clock proof.

## Clock Troubleshooting Entry

天猛星晶振、引脚和板级时钟事实只由 [tianmengxing.md](../hardware/tianmengxing.md) 负责；可复用的 SysConfig 时钟写法只由 [sysconfig-patterns.md](../runtime/sysconfig-patterns.md) 负责。排障时检查当前工程的 `.syscfg`、生成的 `CPUCLK_FREQ`、SysConfig 警告和时钟树 GUI，不要把生成成功或软件延时观感当作实测频率。

## UART0 Blocking TX Lessons

The historical UART smoke test used UART0 at 115200 8N1 with PA10/PA11 and a CH340 PC adapter. Treat it as a blocking transmit baseline, not current physical evidence or a final DMA or variable-length receive design.

## Invalid Historical Dual-UART Record

An earlier observation recorded UART0 on PA10/PA11 and UART1 on PB6/PB7. This record is invalid as a reusable board configuration: PB6 through PB9 are assigned to the onboard SPI Flash, so PB6 UART TX can drive Flash CS and an external UART transmitter on PB7 can contend with Flash MISO.

Do not reproduce, recommend, or reconnect the PB6/PB7 UART wiring. The old record also lacks a test date, exact board revision, command log, firmware hash, Flash coexistence procedure, and electrical observations, so it cannot support any current physical-validation claim. A replacement pin pair requires exact-board schematic review, matching SysConfig generation, build evidence, and a UART-plus-Flash coexistence test.

Important firmware lessons:

- Store DMA printf buffers per UART context, not in a function-static buffer shared by all UARTs.
- Use `char[]` RX buffers when printing with `%s`; keep flags and indexes volatile instead of making the whole text buffer volatile.
- Use `const char *fmt` for printf helpers because call sites usually pass string literals.
- If no DMA TX channel is configured, a fallback helper that accepts `len` should transmit exactly `len` bytes.
- Do not let an unknown UART instance fall back to IRQn 0; use a sentinel and fail the initialization.
- UART RX ISR 只接收字节、更新缓冲区索引并置 `frame_ready` 等帧标志。
- 浮点解析、命令处理、`snprintf`/`vsnprintf` 格式化和 DMA 发送启动放在主循环或任务中；前台取得完整帧所有权并确认 DMA 空闲后再发送。
- For multiple UARTs, use a foreground poll loop or an RTOS task so RX ISRs stay short.
- `UART_RX_MODE_NONE` is useful for TX-only debug UARTs while still allowing `DMA_DONE_TX` interrupts to release the DMA busy flag.

## PWM Breathing LED Lessons

The historical PB22 PWM observation used TIMG8 CCP1, a period of 1000 counts, and generated macro `GPIO_PWM_0_C1_IDX`.

Successful runtime pattern:

- set the first compare value before starting the timer
- update CCP1, not channel 0
- avoid exact compare boundaries `0` and `period`
- use `1..999` for a period of `1000`
- at 80 MHz, `delay_cycles(800000)` is roughly 10 ms per step

Failed patterns included one-second delay per brightness step and exact boundary values that made the LED appear off or glitchy.

## TIMG12 Periodic Interrupt Lessons

A historical timer interrupt observation recorded:

- CPUCLK: 80 MHz
- Timer: TIMG12
- TIMER period: 1 ms
- Generated load value: `79999U`
- ISR event: `DL_TIMER_IIDX_ZERO`
- Runtime behavior: toggle PB22 after 500 timer interrupts, so the LED state changes every 500 ms

At the original 32 MHz baseline, the same 1 ms timer generated a load value of `31999U`. After changing CPUCLK, rebuild and inspect the generated header instead of reusing an old load value.

Keep timing ownership split cleanly:

- `.syscfg`: timer instance, period, mode, interrupt event, clocks, and PB22 pinmux
- application code: `NVIC_EnableIRQ()`, `DL_TimerG_startCounter()`, a short ISR counter, and `DL_GPIO_togglePins()`

不要从历史工程盲拷时钟树属性；从 [sysconfig-patterns.md](../runtime/sysconfig-patterns.md) 取得当前模式，并用匹配版本的 SysConfig 重新生成。若属性不存在，回到当前 SDK 示例和时钟树 GUI 核对，不要凭旧工程补写。

## Flash And Reset

One historical record observed different blink timing before and after a board reset following a clock-tree change, and recorded DSLite `-r 2 -u` as its load-and-run command. Because that record lacks the required logs and firmware identity, use it only as a prompt to compare reset paths; do not infer the running clock or current-board behavior from it.

If J-Link connection fails after a previous attempt, stale `DSLite`, `JLink`, or `JLinkGUIServer` processes may need to be closed before retrying.
