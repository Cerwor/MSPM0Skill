# 天巧星 ADC

## 适用范围

用于单次采样、序列采样和定时触发采样。ADC 实例、通道和引脚复用必须从当前 MSPM0G3519 LQFP-64(PM) SysConfig metadata 与项目占用中选择，不能把示例板引脚当成天巧星空闲引脚。

## 推荐流程

1. 先确定输入电压范围、信号源阻抗、采样速率、分辨率和参考源。
2. 在 SysConfig 中创建 `/ti/driverlib/ADC12`，选择合法模拟输入和 memory slot。
3. 需要稳定采样率时使用 Timer event 触发；需要连续搬运时再引入 DMA。
4. 重新生成后，从 `ti_msp_dl_config.h` 读取 ADC 实例、MEM 索引、事件和 IRQ 名。
5. 先以已知直流电平验证原始码，再验证缩放、滤波和业务阈值。

常用 DriverLib 形态：

```c
DL_ADC12_enableConversions(ADC_INST);
DL_ADC12_startConversion(ADC_INST);
uint16_t sample = DL_ADC12_getMemResult(ADC_INST, DL_ADC12_MEM_IDX_0);
```

实际宏名以生成头为准。

## 验证边界

- 静态检查：引脚支持模拟功能，输入不超过器件允许范围。
- SysConfig：生成成功且通道/参考源与意图一致。
- 构建：实例和 MEM 宏解析正确。
- 硬件：用已知输入或仪表对照原始码；没有测量时不要声称精度、线性或噪声达标。
