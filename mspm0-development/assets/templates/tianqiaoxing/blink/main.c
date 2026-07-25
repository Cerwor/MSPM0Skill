#include "ti_msp_dl_config.h"

#define LED_BLINK_HZ            (5U)
#define LED_HALF_PERIOD_CYCLES  (CPUCLK_FREQ / (2U * LED_BLINK_HZ))

int main(void)
{
    SYSCFG_DL_init();

    while (1) {
        /* PB22 板载 LED 为低有效，SysConfig 初始高电平表示熄灭。 */
        DL_GPIO_togglePins(GPIO_LED_PORT, GPIO_LED_PIN_PIN);
        /* 忙等待只用于板级冒烟测试；精确定时应改用定时器。 */
        delay_cycles(LED_HALF_PERIOD_CYCLES);
    }
}
