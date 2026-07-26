#include "BSP/UART.h"
#include "ti_msp_dl_config.h"

static UART_Context *uart0;

static void UART_ProcessFrame(UART_Context *uart)
{
    uint8_t sent;

    if ((uart == 0) || (!uart->frameReady)) {
        return;
    }

    UART_parseRxFloats(uart->inst);
    sent = UART_tryPrintfDMA(uart->inst, "%s | %.2f,%.2f,%.2f\n",
        uart->rxBuf,
        uart->floatBuf[0], uart->floatBuf[1], uart->floatBuf[2]);
    if (sent) {
        UART_clearNewFrame(uart->inst);
    }
}

int main(void)
{
    SYSCFG_DL_init();
    uart0 = UART_init(UART_0_INST, UART_RX_MODE_IRQ_DEFERRED, UART_ProcessFrame);
    if (uart0 == 0) {
        while (1) {
        }
    }

    while (1) {
        /*
         * IRQ 只收字节并置 frameReady；浮点解析、格式化和 DMA 启动均在前台执行。
         * DMA 忙时保留当前帧，下一轮主循环继续尝试。
         */
        UART_poll(UART_0_INST);
    }
}

void UART0_IRQHandler(void)
{
    switch (DL_UART_getPendingInterrupt(UART_0_INST)) {
        case DL_UART_IIDX_DMA_DONE_TX:
            UART_DMADoneTxCallback(UART_0_INST);
            break;
        case DL_UART_IIDX_RX:
            UART_RxIRQHandler(UART_0_INST);
            break;
        default:
            break;
    }
}
