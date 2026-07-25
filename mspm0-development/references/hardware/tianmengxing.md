# 天猛星 MSPM0G3507 板级指南

## Scope

本指南只负责天猛星 MSPM0G3507 LQFP-64 的板级事实、冲突和外设入口。通用工程流程由工作流参考负责。

## Contents

- 板卡与时钟
- 引脚约束
- 脚手架工作流
- 烧录注意事项

## 板卡与时钟

- 芯片：MSPM0G3507，LQFP-64。
- SDK：以用户工程的 `--product`、本机 SDK metadata 和生成文件为准。
- 安全默认：32 MHz 内部时钟，并使用 `CPUCLK_FREQ` 计算延时。
- 配置 80 MHz 前，先从当前 SDK 的 `LP_MSPM0G3507` 示例确认 SysConfig 属性名；不同 SDK 版本可能不同。

## 引脚约束

### 禁止分配

| 引脚 | 原因 |
|---|---|
| PA2 | 频率精度控制，未引出 |
| PA5、PA6 | 40 MHz HFXT 晶振 |
| PA19、PA20 | SWDIO、SWCLK 调试接口 |

### 特殊引脚

| 引脚 | 约束 |
|---|---|
| PA18 | BSL 入口，上电复位状态需满足板卡要求 |
| PA21 | VREF-，串联电容到地，仅考虑低速 GPIO |
| PA23 | VREF+，串联电容到地，仅考虑低速 GPIO |
| PA10、PA11 | 板载 CH340 UART0，可从排针共用；改作其他功能会失去或干扰默认串口 |

### 板载占用

| 引脚 | 功能 |
|---|---|
| PA10、PA11 | UART0 / CH340 |
| PB6、PB7、PB8、PB9 | W25Q64/SPI1；其中 PB8、PB9 也连接 LCD |
| PB10、PB11、PB14、PB26 | LCD RES、DC、CS、背光 |
| PB21 | 用户按键，低有效 |
| PB22 | 板载 LED，高有效 |

其余候选引脚仍须结合 `.syscfg`、原理图、封装复用和当前工程占用检查，不能只凭“空闲表”分配。

## 工程入口

- 新工程：先读 [scaffolding.md](../workflows/scaffolding.md)，使用 `scripts/scaffold_project.py --board tianmengxing --probe xds110`。
- 现有工程、生成和构建：读 [project-lifecycle.md](../workflows/project-lifecycle.md)。
- 探针、烧录和调试：读 [backends.md](../debugging/backends.md)。设备写入必须来自用户明确意图。
- 可复用起点：`assets/templates/tianmengxing/`。

## 外设索引

按任务只读取一个入口：[GPIO](tianmengxing-peripherals/gpio.md)、[UART](tianmengxing-peripherals/uart.md)、[SPI](tianmengxing-peripherals/spi.md)、[ADC](tianmengxing-peripherals/adc.md)、[Timer](tianmengxing-peripherals/timer.md) 或 [PWM](tianmengxing-peripherals/pwm.md)。

## 烧录注意事项

若 DSLite 报 XDS110 `Error -260`，先检查 Windows 设备管理器中的 XDS110 驱动；CCS 安装通常附带 `ccs_base/emulation/windows/xds110_drivers/DPInst64.exe`。驱动问题与固件编译问题分开报告。
