# 天猛星 I2C

## Scope

本参考只保留天猛星 MSPM0G3507 的 I2C 板级差异，不绑定具体器件、地址或应用驱动。通用电气、事务、错误恢复和验证方法见 [MSPM0 I2C](../../peripherals/i2c.md)。

## 板级基线

- MSPM0G3507 当前数据手册中，PA0 是 I2C0 SDA、PA1 是 I2C0 SCL 的硬件复用候选；仍须由本地 LQFP-64 SysConfig metadata 求解确认。
- 嘉立创官方 CCS 与 Keil 入门教程使用 PA0/PA1 演示软件 I2C，但两份教程的 SDA/SCL 角色互换。这只证明两个 GPIO 可用于各自示例，不证明硬件复用方向或板载上拉。
- 当前已检查资料没有足够证据证明 PA0/PA1 带板载上拉。必须从当前板卡原理图、外接模块资料或实测确认上拉与空闲电平。
- PA5/PA6 用于 40 MHz HFXT，PA19/PA20 用于 SWD，PA21/PA23 不适合高速通信。
- PA10/PA11 默认连接板载 CH340；普通 I2C 分配优先避开，确需改用时先说明会影响默认串口。

## 板级适配

1. 硬件 I2C0 可优先尝试 PA0(SDA)/PA1(SCL)；若 SysConfig 对当前器件、封装或已有资源报冲突，停止并重新求解，不能改成硬编码复用。
2. 软件 I2C 的 SDA/SCL 由当前代码定义；不要把嘉立创某一教程的 GPIO 角色当作硬件 I2C 复用。
3. 根据目标速率、当前板卡和外接模块的实际上拉，计算并联后的总上拉值。
4. 若改用其他引脚组合，必须同时证明封装复用合法、排针可达且未碰撞板载资源。
5. 当前 skill 没有天猛星 I2C 规范模板；以用户工程和当前 SDK 的生成结果为配置证据。
6. 至少验证空闲电平、目标地址 ACK 和一次有确定结果的事务，再声明板上 I2C 可用。

证据入口：[TI MSPM0G3507 数据手册](https://www.ti.com/lit/ds/symlink/mspm0g3507.pdf)、[嘉立创 CCS I2C 教程](https://wiki.lckfb.com/zh-hans/tmx-mspm0g3507/ccs-beginner/i2c.html) 与 [嘉立创 Keil I2C 教程](https://wiki.lckfb.com/zh-hans/tmx-mspm0g3507/keil-beginner/i2c.html)。
