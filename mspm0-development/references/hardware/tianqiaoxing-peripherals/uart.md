# 天巧星 UART

## 通用流程

1. 从当前原理图、连接器和工程中确认 TX/RX 方向、电平、UART 实例和物理引脚。
2. 在 SysConfig 中设置波特率、数据位、校验、停止位、FIFO 和所需中断/DMA。
3. 重新生成后，从 `ti_msp_dl_config.h` 获取实例、IRQ、DMA 和引脚宏。
4. 先验证阻塞发送，再添加 RX 中断或 DMA；ISR 只搬运数据并记录状态。
5. 用已知终端配置验证字节流，并区分 MCU UART、USB 串口桥和调试探针后端。

示意代码：

```c
DL_UART_transmitDataBlocking(UART_INST, byte);

void UART_INST_IRQHandler(void)
{
    if (DL_UART_getPendingInterrupt(UART_INST) == DL_UART_IIDX_RX) {
        uint8_t data = DL_UART_receiveData(UART_INST);
        /* 写入有界缓冲区，业务解析放到主循环。 */
    }
}
```

实际函数族可能随 UART 实例和 SDK 版本变化，以本地 DriverLib 头文件和生成代码为准。

## 验证重点

- 不从旧示例继承固定 baud 或引脚。
- RX 缓冲区必须处理满、溢出和并发访问。
- 串口端口出现不等于目标固件已连接；先确认端口来源。
- 只有接收端观察到正确数据，才能证明物理链路和串口参数一致。
