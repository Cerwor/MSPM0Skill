#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>

#include "ti_msp_dl_config.h"

#define UART_TX_BUF_SIZE 256
#define HEARTBEAT_HALF_PERIOD_CYCLES (CPUCLK_FREQ)

int UART0_sendStr(const char *str)
{
    int cnt = 0;
    while (*str) {
        DL_UART_transmitDataBlocking(UART_0_INST, (uint8_t) *str);
        str++;
        cnt++;
    }
    return cnt;
}

int UART0_printf(const char *fmt, ...)
{
    static char buf[UART_TX_BUF_SIZE];
    int len;
    va_list args;

    va_start(args, fmt);
    len = vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);

    if (len < 0) {
        return len;
    }
    return UART0_sendStr(buf);
}

int main(void)
{
    int n = 0;

    SYSCFG_DL_init();

    while (1) {
        DL_GPIO_clearPins(LED_PORT, LED_PIN_22_PIN);
        delay_cycles(HEARTBEAT_HALF_PERIOD_CYCLES);
        DL_GPIO_setPins(LED_PORT, LED_PIN_22_PIN);
        delay_cycles(HEARTBEAT_HALF_PERIOD_CYCLES);
        UART0_printf("Hello World! %d\n", n);
        n++;
    }
}
