#ifndef TEST_TI_MSP_DL_CONFIG_H
#define TEST_TI_MSP_DL_CONFIG_H

#include <stdint.h>

typedef int32_t IRQn_Type;

typedef struct {
    uint32_t TXDATA;
} UART_Regs;

extern UART_Regs mock_uart0_inst;
extern uint8_t mock_uart_rx_data;
extern uint16_t mock_dma_transfer_size;

#define UART_0_INST (&mock_uart0_inst)
#define UART_0_INST_INT_IRQN ((IRQn_Type) 5)
#define DMA_UART0Tx_CHAN_ID 0u
#define DMA ((void *) 1)

void NVIC_ClearPendingIRQ(IRQn_Type irqn);
void NVIC_EnableIRQ(IRQn_Type irqn);
void DL_UART_transmitDataBlocking(UART_Regs *uart, uint8_t data);
uint8_t DL_UART_receiveData(UART_Regs *uart);
void DL_DMA_setSrcAddr(void *dma, uint8_t channel, uint32_t address);
void DL_DMA_setDestAddr(void *dma, uint8_t channel, uint32_t address);
void DL_DMA_setTransferSize(void *dma, uint8_t channel, uint16_t size);
void DL_DMA_enableChannel(void *dma, uint8_t channel);

#endif
