# DriverLib Runtime Rules

Use this when changing C/C++ runtime code, interrupts, timing, clocks, or external-module behavior.

## Initialization And Generated Names

Application code must call the generated SysConfig init function before using generated peripherals. Do not guess the spelling; inspect `ti_msp_dl_config.h`.

Common spelling:

```c
SYSCFG_DL_init();
```

Use generated macros for instances, ports, pins, IRQ names, and channel indexes. Do not copy example-specific macro names into a project unless the local generated header defines them.

## DriverLib Ownership

Prefer DriverLib APIs such as:

```c
DL_GPIO_setPins(port, pin);
DL_GPIO_clearPins(port, pin);
DL_GPIO_togglePins(port, pin);
DL_UART_transmitDataBlocking(uart, byte);
DL_TimerG_startCounter(timer);
DL_TimerG_setCaptureCompareValue(timer, value, index);
```

Keep pinmux, peripheral initialization, clocks, DMA, and interrupts in `.syscfg` when possible. Use application code for runtime behavior.

Avoid direct register-level peripheral configuration unless the user requested it, DriverLib cannot express the operation, and the reason is documented.

## Interrupts

Interrupt handlers should:

- clear the relevant interrupt flag
- do minimal work
- record state for the main loop or task
- use `volatile` for variables shared with non-ISR code

Avoid long delays, blocking serial I/O, complex parsing, slow bus transactions, and heavy control logic inside ISRs.

UART RX 中断只完成有界的数据搬运：读取一个或少量 FIFO 字节、写入预分配缓冲区或环形队列、更新索引，并在遇到帧结束条件时置 `frame_ready`。ISR 中不要调用浮点解析、`sscanf`、`strtof`、`snprintf`/`vsnprintf`，也不要启动 DMA 发送。主循环或任务取得完整帧后再解析和格式化，并在确认 DMA 空闲后启动发送。

For a SysConfig periodic TIMER interrupt:

- set `timerPeriod`, `timerMode = "PERIODIC"`, `interrupts = ["ZERO"]`, and the selected timer peripheral in `.syscfg`
- enable the generated IRQ with `NVIC_EnableIRQ(TIMER_x_INST_INT_IRQN)`
- start the counter with `DL_TimerG_startCounter(TIMER_x_INST)`
- use `DL_TimerG_getPendingInterrupt()` and handle `DL_TIMER_IIDX_ZERO` in the ISR
- confirm the generated load value after changing CPUCLK

## FreeRTOS Projects

If a project includes `FreeRTOSConfig.h`, `FreeRTOS.h`, `task.h`, `xTaskCreate`, or `vTaskStartScheduler`, first map the existing task/ISR boundaries.

- Do not add blocking DriverLib calls to an ISR.
- Do not replace an existing queue, notification, semaphore, or task-delay pattern without a clear reason.
- Confirm whether a requested control period belongs in a hardware timer interrupt, RTOS task delay, PWM/ADC trigger chain, or main loop.
- Keep changes compatible with the project's existing framework rather than assuming a single-file demo layout.

## Clock And Delay Rules

天猛星晶振、引脚和板级时钟约束由 [tianmengxing.md](../hardware/tianmengxing.md) 负责；可复用的 SysConfig 时钟配置由 [sysconfig-patterns.md](sysconfig-patterns.md) 负责。本运行时文档只规定：延时计算读取当前生成的 `CPUCLK_FREQ`，时钟变化后重新生成并检查宏；真实定时和控制循环使用 Timer 或工程既有时间基准，`delay_cycles()` 仅用于短小冒烟测试。

## Common Mistakes

- Editing `Debug/ti_msp_dl_config.*` instead of `.syscfg`.
- Removing SysConfig metadata.
- Guessing `SYSCFG_DL_Init()` when the local project declares `SYSCFG_DL_init()`.
- Assuming any package pin can serve any peripheral function.
- Renaming generated instances casually and breaking application code.
- Reinitializing by hand a peripheral already owned by SysConfig.
- Reporting SysConfig warnings as clean success.
- Rewriting unrelated user code or copyright headers.
- 从旧工程盲拷时钟树属性，而不是按 [sysconfig-patterns.md](sysconfig-patterns.md) 和匹配 SDK 示例重新求解。

## External Modules

For sensors, displays, motor drivers, servos, radios, or custom modules, collect the datasheet, schematic or wiring table, voltage levels, protocol, address/mode pins, reset/enable pins, and required timing before writing a driver.

If repeated firmware attempts fail but SysConfig, build, flash, and runtime logic appear correct, ask the user to verify wiring, power, ground, level shifting, module mode, address pins, chip select, UART TX/RX crossover, pull-ups, and test procedure.
