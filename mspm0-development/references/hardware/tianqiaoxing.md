# 天巧星 MSPM0G3519 板级指南

## Scope

本指南只负责天堑星 MSPM0G3519 LQFP-64 的板级事实、冲突和外设入口。通用工程流程由工作流参考负责。

## Contents

- 板卡与时钟
- 引脚约束
- 脚手架工作流
- I2C 与 OLED
- SDK 版本注意事项

## 板卡与时钟

- 芯片：MSPM0G3519，LQFP-64。
- 已整理资源以 MSPM0 SDK 2.05.01.00 为基线，实际操作仍以项目和本地 SDK metadata 为准。
- 新工程默认使用 32 MHz 内部时钟。
- 80 MHz HFXT + PLL 配置必须启用 `SYSCTL.clockTreeEn = true`，否则可能静默回退到 32 MHz。
- SysConfig 后读取 `ti_msp_dl_config.h` 中的 `CPUCLK_FREQ` 验证实际频率。

## 引脚约束

### 禁止分配

| 引脚 | 原因 |
|---|---|
| PA2 | 频率精度控制，未引出 |
| PA5、PA6 | 40 MHz HFXT 晶振 |
| PA19、PA20 | SWDIO、SWCLK 调试接口 |

### 特殊和板载占用

| 引脚 | 功能或约束 |
|---|---|
| PA18 | BSL 入口，复位时必须满足板卡电平要求 |
| PA0、PA1 | OLED 与板载/共享软件 I2C 基线，板载 2.2 kΩ 上拉 |
| PA10、PA11 | UART0 / CH340，默认 9600 baud |
| PA24、PB21、PB24 | KEY1、ENTER、KEY2，低有效 |
| PB6–PB9 | SPI1 / W25Q64 |
| PB17、PB18 | UART7 无线模块，默认 115200 baud |
| PB22 | 板载 LED，低有效 |
| PB23 | 无线连接状态 |
| PB26 | TIMA1 CCP0 / WS2812 |
| PB27 | TIMG6 CCP1 / 蜂鸣器 PWM |
| PA29、PA30、PA31 | 可选编码器与按键，占用前确认当前功能是否启用 |

未列出的引脚也必须检查 `.syscfg`、封装复用和工程占用。

## 工程入口

- 新工程：先读 [scaffolding.md](../workflows/scaffolding.md)，使用 `scripts/scaffold_project.py --board tianqiaoxing --probe jlink`。
- 现有工程、生成和构建：读 [project-lifecycle.md](../workflows/project-lifecycle.md)。
- 探针、烧录和调试：读 [backends.md](../debugging/backends.md)。设备写入必须来自用户明确意图。
- 可复用起点：`assets/templates/tianqiaoxing/`。

即使是 blink，也应在修改延时或 SDK 版本不确定时保留 SysConfig/生成宏检查。

## I2C 与 OLED

- 默认共享/板载 I2C 基线为 PA0/PA1 软件 I2C。
- `imu_lsm6ds3` 模板保留另一套经硬件验证的 PA28/PA27 软件 I2C 接线，不能当作板载共享总线的同义配置。
- 需要硬件 I2C 时，读取 [hw-i2c-pins.md](tianqiaoxing-peripherals/hw-i2c-pins.md) 并验证当前 SDK 引脚复用。
- OLED 起点使用 `assets/templates/tianqiaoxing/oled_draw/` 或 `oled_menu/`。

## 外设索引

按任务只读取一个入口：[GPIO](tianqiaoxing-peripherals/gpio.md)、[UART](tianqiaoxing-peripherals/uart.md)、[无线 UART](tianqiaoxing-peripherals/wireless_uart.md)、[I2C](tianqiaoxing-peripherals/i2c.md)、[SPI](tianqiaoxing-peripherals/spi.md)、[ADC](tianqiaoxing-peripherals/adc.md)、[PWM/Timer](tianqiaoxing-peripherals/pwm_timer.md)、[OLED UI](tianqiaoxing-peripherals/oled_ui.md)、[IMU](tianqiaoxing-peripherals/imu.md)、[编码器](tianqiaoxing-peripherals/encoder.md)、[蜂鸣器](tianqiaoxing-peripherals/buzzer.md) 或 [WS2812](tianqiaoxing-peripherals/ws2812.md)。

## SDK 版本注意事项

SDK 2.04 + SysConfig 1.27 的 LQFP-64 引脚映射可能生成错误的端口/引脚宏。遇到该组合时，必须检查生成头中的 `_PORT`、`_PIN` 和时钟宏；优先升级到已修复版本，不要长期用硬编码掩盖配置错误。
