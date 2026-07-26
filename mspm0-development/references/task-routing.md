# Detailed Task Routing

## Scope

Use this index only when the four paths in `SKILL.md` do not identify a single
reference. Read the selected reference, not this entire package.

| Task | First reference | Conditional detail |
| --- | --- | --- |
| Runtime GPIO, UART, SPI, ADC, PWM, DMA, interrupt, or clock code | [DriverLib runtime](runtime/driverlib-runtime.md) | [SysConfig patterns](runtime/sysconfig-patterns.md) only for a listed matching pattern |
| MSPM0G3507 Timer selection or period calculation | [Tianmengxing Timer](hardware/tianmengxing-peripherals/timer.md) | [DriverLib runtime](runtime/driverlib-runtime.md) for ISR integration |
| I2C controller, target, or bus diagnosis | [I2C](peripherals/i2c.md) | Matching board I2C guide, schematic, and target datasheet |
| TimerG quadrature encoder | [QEI](peripherals/qei.md) | Matching board guide and installed SDK `timg_qei_mode` example |
| Tianmengxing pins or onboard hardware | [Tianmengxing](hardware/tianmengxing.md) | One matching file under `hardware/tianmengxing-peripherals/` |
| Tianqiaoxing common peripherals | [Tianqiaoxing](hardware/tianqiaoxing.md) | One matching board file and one generic peripheral reference |
| Hardware symptom after a valid build/flash | [Hardware validation](troubleshooting/hardware-validation.md) | [Backends](debugging/backends.md) only for probe/debug failure |
| Maintain, validate, or install this skill | [Maintenance](maintenance/maintenance.md) | [Sources and boundaries](maintenance/sources-and-boundaries.md) for provenance |
