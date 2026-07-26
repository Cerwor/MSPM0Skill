# 天巧星 I2C

## Scope

本参考只保留天巧星 MSPM0G3519 的 I2C 板级边界。通用电气、SysConfig、DriverLib 事务、错误恢复和验证方法见 [MSPM0 I2C](../../peripherals/i2c.md)。

## 板级适配

1. 目标基线是 MSPM0G3519 LQFP-64(PM)，仍以用户工程、芯片丝印和当前原理图为准。
2. 从本地 SysConfig metadata 选择同一实例的合法 SDA/SCL；不从旧应用恢复固定总线、地址或接线。
3. 核对 PA5/PA6、PA19/PA20、PA18 等板级约束以及当前工程占用。
4. 当前 skill 没有天巧星 I2C 规范模板；以用户工程和当前 SDK 的生成结果为配置证据。
5. 只有当前硬件上的目标器件响应或有效逻辑分析仪波形，才能提升为物理验证。
