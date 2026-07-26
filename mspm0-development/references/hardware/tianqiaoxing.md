# 天巧星 MSPM0G3519 通用外设指南

## Scope

只保留天巧星 MSPM0G3519 的器件/封装基线、基础板级约束和通用外设入口。天猛星是本 skill 的主要维护方向；天巧星的板载应用不随 skill 打包，后续任务必须以用户当次提供的资料为准。

## 器件与证据

- 器件：MSPM0G3519。
- 封装基线：LQFP-64(PM)；仍要以项目 `.syscfg`、芯片丝印和当前原理图为准。
- `assets/templates/tianqiaoxing/blink/` 只提供 PB22 GPIO 冒烟测试，不代表其他引脚或外设已经适配。
- 本地 SDK/SysConfig metadata 决定可选实例、合法复用和字段枚举；TI LaunchPad 的 PZ 封装和板级引脚不能直接套用。

## 基础约束

| 引脚 | 约束 |
| --- | --- |
| PA5、PA6 | 使用外部高速晶振时保留 |
| PA19、PA20 | SWDIO、SWCLK，调试期间保留 |
| PA18 | 与启动路径相关，复位电平必须符合当前板卡资料 |
| PB22 | 板载 LED，低有效 |

未列出的引脚不等于空闲。先检查当前 `.syscfg`、原理图、封装复用和工程占用，再做电气分配。

## 时钟与生成结果

- 最小 blink 模板使用内部默认时钟基线。
- 改为 PLL、外部晶振或更高频率时，在 SysConfig 中显式启用并重新生成。
- 读取 `ti_msp_dl_config.h` 的 `CPUCLK_FREQ`，不要从模板版本或延时现象反推时钟。
- 频率、PWM 周期、UART 波特率和定时器周期都从生成时钟推导。

## 通用外设索引

每次只读取当前任务对应的一份参考：

- [GPIO](tianqiaoxing-peripherals/gpio.md)
- [ADC](tianqiaoxing-peripherals/adc.md)
- [PWM](tianqiaoxing-peripherals/pwm.md)
- [Timer](tianqiaoxing-peripherals/timer.md)
- [QEI](tianqiaoxing-peripherals/qei.md)
- [UART](tianqiaoxing-peripherals/uart.md)
- [SPI](tianqiaoxing-peripherals/spi.md)
- [I2C](tianqiaoxing-peripherals/i2c.md)

## 工程入口

- 修改现有工程：先读 [project-lifecycle.md](../workflows/project-lifecycle.md)。
- 新建最小工程：先读 [scaffolding.md](../workflows/scaffolding.md)。
- 探针、烧录和调试：读 [backends.md](../debugging/backends.md)，并按实际 J-Link、XDS110 或其他已识别探针显式选择。
- 如果任务超出上述通用外设范围，先读取用户提供的当前资料，不从已删除的旧应用知识重建接线或驱动。
