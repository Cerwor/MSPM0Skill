#include "ti_msp_dl_config.h"

#define LED_BLINK_HZ (1U)
#define LED_HALF_PERIOD_CYCLES (CPUCLK_FREQ / (2U * LED_BLINK_HZ))

int main(void)
{
    SYSCFG_DL_init();

    while (1) {
        DL_GPIO_togglePins(LED_PORT, LED_PIN_22_PIN);
        /* 忙等待仅用于板级冒烟测试；精确定时应改用定时器。 */
        delay_cycles(LED_HALF_PERIOD_CYCLES);
    }
}
