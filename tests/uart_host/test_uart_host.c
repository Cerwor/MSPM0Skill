#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "UART.h"

UART_Regs mock_uart0_inst;
uint8_t mock_uart_rx_data;
uint16_t mock_dma_transfer_size;

static uint32_t callback_count;

void NVIC_ClearPendingIRQ(IRQn_Type irqn)
{
    (void) irqn;
}

void NVIC_EnableIRQ(IRQn_Type irqn)
{
    (void) irqn;
}

void DL_UART_transmitDataBlocking(UART_Regs *uart, uint8_t data)
{
    (void) uart;
    (void) data;
}

uint8_t DL_UART_receiveData(UART_Regs *uart)
{
    (void) uart;
    return mock_uart_rx_data;
}

void DL_DMA_setSrcAddr(void *dma, uint8_t channel, uint32_t address)
{
    (void) dma;
    (void) channel;
    (void) address;
}

void DL_DMA_setDestAddr(void *dma, uint8_t channel, uint32_t address)
{
    (void) dma;
    (void) channel;
    (void) address;
}

void DL_DMA_setTransferSize(void *dma, uint8_t channel, uint16_t size)
{
    (void) dma;
    (void) channel;
    mock_dma_transfer_size = size;
}

void DL_DMA_enableChannel(void *dma, uint8_t channel)
{
    (void) dma;
    (void) channel;
}

static void record_frame(UART_Context *uart)
{
    (void) uart;
    callback_count++;
}

static void feed_byte(UART_Regs *uart, uint8_t data)
{
    mock_uart_rx_data = data;
    (void) UART_RxIRQHandler(uart);
}

static void feed_text(UART_Regs *uart, const char *text)
{
    while (*text != '\0') {
        feed_byte(uart, (uint8_t) *text);
        text++;
    }
}

#define CHECK(condition)                                                        \
    do {                                                                        \
        if (!(condition)) {                                                     \
            fprintf(stderr, "检查失败：%s，第 %d 行\n", #condition, __LINE__); \
            return 1;                                                           \
        }                                                                       \
    } while (0)

int main(void)
{
    uint16_t i;
    UART_Regs unknown_uart;
    UART_Context *ctx;

    memset(&unknown_uart, 0, sizeof(unknown_uart));
    CHECK(UART_getContext(&unknown_uart) == NULL);
    CHECK(UART_init(&unknown_uart, UART_RX_MODE_IRQ_DEFERRED, record_frame) == NULL);
    CHECK(UART_getContext(&unknown_uart) == NULL);

    ctx = UART_init(UART_0_INST, UART_RX_MODE_IRQ_DEFERRED, record_frame);
    CHECK(ctx != NULL);

    feed_text(UART_0_INST, "first\n");
    CHECK(ctx->frameReady == 1u);
    CHECK(strcmp(ctx->rxBuf, "first") == 0);
    CHECK(callback_count == 0u);

    CHECK(UART_poll(UART_0_INST) == 1u);
    CHECK(callback_count == 1u);
    CHECK(ctx->frameReady == 1u);

    feed_text(UART_0_INST, "sec");
    CHECK(ctx->discardUntilLF == 1u);
    CHECK(strcmp(ctx->rxBuf, "first") == 0);

    UART_clearNewFrame(UART_0_INST);
    CHECK(ctx->frameReady == 0u);
    CHECK(ctx->discardUntilLF == 1u);
    feed_text(UART_0_INST, "ond\n");
    CHECK(ctx->discardUntilLF == 0u);
    CHECK(ctx->frameReady == 0u);
    CHECK(ctx->rxDroppedFrameCount == 1u);

    feed_text(UART_0_INST, "third\n");
    CHECK(ctx->frameReady == 1u);
    CHECK(strcmp(ctx->rxBuf, "third") == 0);
    UART_clearNewFrame(UART_0_INST);

    for (i = 0; i < UART_RX_BUF_SIZE; i++) {
        feed_byte(UART_0_INST, (uint8_t) 'A');
    }
    CHECK(ctx->frameReady == 1u);
    CHECK(ctx->rxOverflow == 1u);
    CHECK(ctx->rxLen == UART_RX_BUF_SIZE - 1u);
    CHECK(ctx->rxBuf[UART_RX_BUF_SIZE - 1u] == '\0');
    CHECK(ctx->discardUntilLF == 1u);
    feed_byte(UART_0_INST, (uint8_t) '\n');
    CHECK(ctx->discardUntilLF == 0u);
    CHECK(ctx->rxDroppedFrameCount == 2u);
    UART_clearNewFrame(UART_0_INST);

    CHECK(UART_trySendStrDMA(UART_0_INST, "abc", 3u) == 1u);
    CHECK(memcmp(ctx->txBuf, "abc", 3u) == 0);
    CHECK(mock_dma_transfer_size == 3u);
    CHECK(ctx->txDMADone == 0u);
    UART_DMADoneTxCallback(UART_0_INST);
    CHECK(ctx->txDMADone == 1u);

    return 0;
}
