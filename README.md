# MSPM0 Development Skill

面向 Codex 的 TI MSPM0 嵌入式开发 skill，以立创开发板天猛星 MSPM0G3507 为主要维护方向，并为天巧星 MSPM0G3519 保留边界明确的通用外设支持。

本仓库的核心 skill 位于 [`mspm0-development/`](mspm0-development/)。

## 主要能力

- 检查和修改已有 CCS 工程；对 Keil、CMake/GCC 工程按现有项目结构和本地工具链提供条件性支持。
- 以 `.syscfg` 为配置源管理引脚、时钟、外设、中断和 DMA。
- 使用本工程生成的 `ti_msp_dl_config.h/.c` 名称编写 DriverLib 代码。
- 创建或复用最小工程、GPIO、PWM、Timer IRQ 和 UART 模板。
- 提供 GPIO、80 MHz 时钟、UART、Timer IRQ 和空骨架的简洁 SysConfig 局部模式。
- 检测 J-Link、XDS110 等探针，使用 CCS/DSLite、CCS DSS 或 OpenOCD 等调试后端，并保持烧录与调试操作的授权边界。
- 分别报告静态检查、SysConfig 生成、编译、烧录、串口和实物行为证据。
- 支持 GPIO、UART、SPI、I2C、ADC、Timer、PWM、DMA、QEI 等常见 MSPM0 开发任务。

## 板卡支持

| 板卡 | 定位 | 当前支持 |
| --- | --- | --- |
| 天猛星 MSPM0G3507 LQFP-64 | 主要维护板卡 | GPIO、ADC、PWM、Timer、QEI、UART、SPI、I2C 板级入口和 6 个起始模板 |
| 天巧星 MSPM0G3519 LQFP-64(PM) | 通用外设层 | GPIO、ADC、PWM、Timer、QEI、UART、SPI、I2C 参考及最小 blink 模板 |
| TI LaunchPad | 适配证据 | 只复用器件、SDK、SysConfig 和工具行为，不套用其板载引脚或探针默认值 |

天巧星的 IMU、OLED/UI、WS2812、无线、编码器板载应用和蜂鸣器等应用层内容不随 skill 打包。后续任务需要这些模块时，应以用户当次提供的原理图、代码和器件资料为准。

## 安装

先决条件：

- Git。
- Python 3.10 或更高版本，并可通过 `python` 调用。
- 支持本地 skills 的 Codex 环境。
- 只有执行 SysConfig 生成、编译或烧录时，才需要匹配的 TI SDK、SysConfig、编译器和调试工具。

克隆仓库：

```powershell
Get-Command git, python -ErrorAction Stop | Out-Null

git clone https://github.com/Cerwor/MSPM0Skill.git
if ($LASTEXITCODE -ne 0) {
    throw "仓库克隆失败，停止安装。"
}

Set-Location .\MSPM0Skill
```

首次安装时，先复制到同级暂存目录并运行 skill 自检，通过后再落位：

```powershell
$codexDirectory = if ([string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
    Join-Path $env:USERPROFILE ".codex"
} else {
    $env:CODEX_HOME
}

$skillsDirectory = Join-Path $codexDirectory "skills"
$repositorySkill = (Resolve-Path -LiteralPath ".\mspm0-development").Path
$skillDestination = Join-Path $skillsDirectory "mspm0-development"
$quickValidate = Join-Path $skillsDirectory (
    ".system\skill-creator\scripts\quick_validate.py")
$stagingRoot = Join-Path $skillsDirectory (
    ".mspm0-development-install-" + [guid]::NewGuid().ToString("N"))
$stagedSkill = Join-Path $stagingRoot "mspm0-development"

if (Test-Path -LiteralPath $skillDestination) {
    throw "目标 skill 已存在，请先比较并验证更新内容。"
}
if (-not (Test-Path -LiteralPath $quickValidate)) {
    throw "没有找到系统 skill-creator 的 quick_validate.py。"
}

function Get-SkillHashRecords([string]$rootPath) {
    $resolvedRoot = (Resolve-Path -LiteralPath $rootPath).Path
    Get-ChildItem -LiteralPath $resolvedRoot -Recurse -File -Force |
        Sort-Object FullName |
        ForEach-Object {
            [PSCustomObject]@{
                Relative = $_.FullName.Substring($resolvedRoot.Length + 1)
                Hash = (Get-FileHash -LiteralPath $_.FullName `
                    -Algorithm SHA256).Hash
            }
        }
}

New-Item -ItemType Directory -Path $skillsDirectory -Force | Out-Null
$installedByThisRun = $false

try {
    New-Item -ItemType Directory -Path $stagingRoot -ErrorAction Stop | Out-Null
    Copy-Item -LiteralPath $repositorySkill `
        -Destination $stagedSkill -Recurse -ErrorAction Stop

    python -B (Join-Path $stagedSkill "scripts\validate_skill.py") $stagedSkill
    if ($LASTEXITCODE -ne 0) {
        throw "暂存副本自检失败。"
    }
    python -B $quickValidate $stagedSkill
    if ($LASTEXITCODE -ne 0) {
        throw "暂存副本 quick_validate 失败。"
    }

    Move-Item -LiteralPath $stagedSkill `
        -Destination $skillDestination -ErrorAction Stop
    $installedByThisRun = $true

    python -B (Join-Path $skillDestination "scripts\validate_skill.py") `
        $skillDestination
    if ($LASTEXITCODE -ne 0) {
        throw "安装副本自检失败。"
    }
    python -B $quickValidate $skillDestination
    if ($LASTEXITCODE -ne 0) {
        throw "安装副本 quick_validate 失败。"
    }

    $repositoryHashes = @(Get-SkillHashRecords $repositorySkill)
    $installedHashes = @(Get-SkillHashRecords $skillDestination)
    $hashDifference = @(Compare-Object `
        -ReferenceObject $repositoryHashes `
        -DifferenceObject $installedHashes `
        -Property Relative, Hash)
    if ($hashDifference.Count -ne 0) {
        throw "仓库源与安装副本 SHA-256 不一致。"
    }
} catch {
    if (Test-Path -LiteralPath $stagingRoot) {
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
    if ($installedByThisRun -and (Test-Path -LiteralPath $skillDestination)) {
        Remove-Item -LiteralPath $skillDestination -Recurse -Force
    }
    throw
}

if (Test-Path -LiteralPath $stagingRoot) {
    Remove-Item -LiteralPath $stagingRoot -Force
}
```

安装完成后，为确保 skill 列表刷新，请新建一个 Codex 任务并使用 `$mspm0-development`。如果仍未识别，重启 Codex 后再试。

### 更新已有安装

在已克隆的 `MSPM0Skill` 仓库内打开 PowerShell，再运行下面的完整流程。它会定位仓库根目录、检查工作区、拉取更新、校验两份 skill、显示差异并要求确认；替换前会把原安装副本移动到唯一的备份目录。更新失败时会尝试自动恢复；如果文件占用等问题阻止恢复，原备份仍会保留并报告路径。更新成功后也会保留备份供人工复核。

```powershell
Get-Command git, python -ErrorAction Stop | Out-Null

$repositoryRootText = git rev-parse --show-toplevel 2>$null |
    Select-Object -First 1
if ($LASTEXITCODE -ne 0 -or
    [string]::IsNullOrWhiteSpace($repositoryRootText)) {
    throw "当前目录不在已克隆的 Git 仓库内。"
}

$repositoryRoot = (Resolve-Path -LiteralPath $repositoryRootText.Trim()).Path
$repositorySkill = Join-Path $repositoryRoot "mspm0-development"
if (-not (Test-Path -LiteralPath (
    Join-Path $repositorySkill "SKILL.md"))) {
    throw "当前仓库不是 MSPM0Skill，停止更新。"
}
Set-Location -LiteralPath $repositoryRoot

$worktreeChanges = @(git status --porcelain --untracked-files=all)
if ($LASTEXITCODE -ne 0) {
    throw "无法检查仓库工作区状态。"
}
if ($worktreeChanges.Count -ne 0) {
    throw "仓库工作区存在未提交改动，请先处理后再更新。"
}

git pull --ff-only
if ($LASTEXITCODE -ne 0) {
    throw "仓库更新失败，停止同步。"
}

$codexDirectory = if ([string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
    Join-Path $env:USERPROFILE ".codex"
} else {
    $env:CODEX_HOME
}
$skillsDirectory = Join-Path $codexDirectory "skills"
$skillDestination = Join-Path $skillsDirectory "mspm0-development"
$quickValidate = Join-Path $skillsDirectory (
    ".system\skill-creator\scripts\quick_validate.py")

if (-not (Test-Path -LiteralPath $skillDestination)) {
    throw "没有找到已安装的 mspm0-development。"
}
if (-not (Test-Path -LiteralPath $quickValidate)) {
    throw "没有找到系统 skill-creator 的 quick_validate.py。"
}

function Get-SkillHashRecords([string]$rootPath) {
    $resolvedRoot = (Resolve-Path -LiteralPath $rootPath).Path
    Get-ChildItem -LiteralPath $resolvedRoot -Recurse -File -Force |
        Sort-Object FullName |
        ForEach-Object {
            [PSCustomObject]@{
                Relative = $_.FullName.Substring($resolvedRoot.Length + 1)
                Hash = (Get-FileHash -LiteralPath $_.FullName `
                    -Algorithm SHA256).Hash
            }
        }
}

python -B (Join-Path $repositorySkill "scripts\validate_skill.py") `
    $repositorySkill
if ($LASTEXITCODE -ne 0) {
    throw "仓库副本自检失败。"
}
python -B $quickValidate $repositorySkill
if ($LASTEXITCODE -ne 0) {
    throw "仓库副本 quick_validate 失败。"
}

python -B (Join-Path $skillDestination "scripts\validate_skill.py") `
    $skillDestination
if ($LASTEXITCODE -ne 0) {
    throw "现有安装副本自检失败，请先检查本地修改。"
}
python -B $quickValidate $skillDestination
if ($LASTEXITCODE -ne 0) {
    throw "现有安装副本 quick_validate 失败，请先检查本地修改。"
}

$repositoryHashes = @(Get-SkillHashRecords $repositorySkill)
$installedHashes = @(Get-SkillHashRecords $skillDestination)
$difference = @(Compare-Object `
    -ReferenceObject $installedHashes `
    -DifferenceObject $repositoryHashes `
    -Property Relative, Hash)

if ($difference.Count -eq 0) {
    Write-Host "安装副本已经与仓库源一致，无需更新。"
} else {
    $difference |
        Sort-Object Relative, SideIndicator |
        Format-Table Relative, SideIndicator -AutoSize

    $confirmation = Read-Host (
        "请先检查以上差异；确认更新请输入 UPDATE")
    if ($confirmation -cne "UPDATE") {
        throw "未收到 UPDATE 确认，安装副本保持不变。"
    }

    $operationId = [guid]::NewGuid().ToString("N")
    $stagingRoot = Join-Path $skillsDirectory (
        ".mspm0-development-update-" + $operationId)
    $stagedSkill = Join-Path $stagingRoot "mspm0-development"
    $backupSkill = Join-Path $skillsDirectory (
        "mspm0-development.backup-" + $operationId)
    $backupCreated = $false
    $replacementInstalled = $false

    try {
        New-Item -ItemType Directory -Path $stagingRoot `
            -ErrorAction Stop | Out-Null
        Copy-Item -LiteralPath $repositorySkill `
            -Destination $stagedSkill -Recurse -ErrorAction Stop

        python -B (Join-Path $stagedSkill "scripts\validate_skill.py") `
            $stagedSkill
        if ($LASTEXITCODE -ne 0) {
            throw "暂存副本自检失败。"
        }
        python -B $quickValidate $stagedSkill
        if ($LASTEXITCODE -ne 0) {
            throw "暂存副本 quick_validate 失败。"
        }

        Move-Item -LiteralPath $skillDestination `
            -Destination $backupSkill -ErrorAction Stop
        $backupCreated = $true
        Move-Item -LiteralPath $stagedSkill `
            -Destination $skillDestination -ErrorAction Stop
        $replacementInstalled = $true

        python -B (Join-Path $skillDestination "scripts\validate_skill.py") `
            $skillDestination
        if ($LASTEXITCODE -ne 0) {
            throw "更新后的安装副本自检失败。"
        }
        python -B $quickValidate $skillDestination
        if ($LASTEXITCODE -ne 0) {
            throw "更新后的安装副本 quick_validate 失败。"
        }

        $installedHashes = @(Get-SkillHashRecords $skillDestination)
        $difference = @(Compare-Object `
            -ReferenceObject $repositoryHashes `
            -DifferenceObject $installedHashes `
            -Property Relative, Hash)
        if ($difference.Count -ne 0) {
            throw "仓库源与更新后的安装副本 SHA-256 不一致。"
        }
    } catch {
        $updateError = $_
        $recoveryError = $null
        $failedSkill = Join-Path $skillsDirectory (
            "mspm0-development.failed-" + $operationId)

        try {
            if ($replacementInstalled -and
                (Test-Path -LiteralPath $skillDestination)) {
                Move-Item -LiteralPath $skillDestination `
                    -Destination $failedSkill -ErrorAction Stop
            }
            if ($backupCreated -and
                (Test-Path -LiteralPath $backupSkill)) {
                Move-Item -LiteralPath $backupSkill `
                    -Destination $skillDestination -ErrorAction Stop
            }
        } catch {
            $recoveryError = $_
        }

        try {
            if (Test-Path -LiteralPath $stagingRoot) {
                Remove-Item -LiteralPath $stagingRoot `
                    -Recurse -Force -ErrorAction Stop
            }
        } catch {
            Write-Warning "暂存目录清理失败：$stagingRoot"
        }

        if ($null -ne $recoveryError) {
            $recoveryMessage = (
                "更新失败且自动恢复失败。原错误：{0}；" +
                "恢复错误：{1}；备份目录：{2}；失败副本目录：{3}") -f
                $updateError.Exception.Message,
                $recoveryError.Exception.Message,
                $backupSkill,
                $failedSkill
            throw $recoveryMessage
        }
        if (Test-Path -LiteralPath $failedSkill) {
            Write-Warning "失败的新副本已隔离在：$failedSkill"
        }
        throw $updateError
    }

    if (Test-Path -LiteralPath $stagingRoot) {
        Remove-Item -LiteralPath $stagingRoot -Force
    }
    Write-Host "更新完成；原安装副本保留在：$backupSkill"
}
```

确认新 skill 在新的 Codex 任务中工作正常后，再由用户自行决定是否删除备份。不要直接覆盖或自动删除来源不明的本地内容。

## 使用示例

在 Codex 中显式调用：

```text
使用 $mspm0-development 检查这个 CCS 工程，确认 SysConfig、生成名称和构建入口。
```

```text
使用 $mspm0-development 给天猛星 PB22 板载 LED 增加 10 Hz 闪烁。
```

```text
使用 $mspm0-development 规划两相增量编码器的 TimerG QEI 配置，
先检查当前工程、原理图、电平、Timer/PWM 冲突和 PPR 定义。
```

skill 会优先检查用户的当前工程和匹配的本地 SDK metadata。缺少原理图、器件资料或工程占用证据时，不会猜测最终引脚。

## 内置模板

运行以下命令查看模板 metadata：

```powershell
Set-Location .\mspm0-development
python -B scripts\list_examples.py
python -B scripts\list_examples.py --board Tianmengxing --peripheral UART
```

当前模板：

| 板卡 | 模板 |
| --- | --- |
| 天猛星 | `empty_project` |
| 天猛星 | `led_blink` |
| 天猛星 | `pwm_breath_led` |
| 天猛星 | `timer_irq_led` |
| 天猛星 | `uart_blocking_tx` |
| 天猛星 | `uart_dma_tx_irq_rx` |
| 天巧星 | `blink` |

列表会分别显示当前验证层级和是否完成物理行为复验。模板只是起始证据，不是所有工程都能直接复制的固定布局；引脚、时钟、SDK、编译器和探针仍应以当前项目为准。

需要快速查看局部 `.syscfg` 写法时，读取 [SysConfig 局部模式](mspm0-development/references/runtime/sysconfig-patterns.md)，再打开对应完整模板和 `manifest.json`。局部模式不是可独立生成的完整配置。

## I2C 支持

通用 I2C 方法见 [`references/peripherals/i2c.md`](mspm0-development/references/peripherals/i2c.md)，板级差异分别见 [天猛星 I2C](mspm0-development/references/hardware/tianmengxing-peripherals/i2c.md) 和 [天巧星 I2C](mspm0-development/references/hardware/tianqiaoxing-peripherals/i2c.md)。

- 天猛星硬件 I2C0 的候选是 PA0/SDA、PA1/SCL；嘉立创 CCS 与 Keil 软件 I2C 教程对两线角色的示例并不一致，不能据此推断硬件复用或板载上拉。
- 通用方法覆盖开漏与上拉、7 位地址、重复起始、有限超时、错误分类、条件性总线恢复和逻辑分析仪验证。
- 当前没有 I2C 规范模板，因此不会把局部配置片段冒充已生成或已完成实物验证的配置。

## QEI 支持

通用 QEI 参考见 [`references/peripherals/qei.md`](mspm0-development/references/peripherals/qei.md)，板级候选与冲突分别见 [天猛星 QEI](mspm0-development/references/hardware/tianmengxing-peripherals/qei.md) 和 [天巧星 QEI](mspm0-development/references/hardware/tianqiaoxing-peripherals/qei.md)。

- 使用 `/ti/driverlib/QEI` 和同一 TimerG 实例的 CCP0/CCP1。
- 从当前 SysConfig 生成结果读取实例、IRQ、引脚和装载值。
- 使用连续计数与模差处理回绕，不采用读后重置计数器的旧模式。
- 半模数差值方向不可判定，必须报告采样过稀。
- 不固定 5 ms 采样周期，也不固定除以 4；PPR、CPR、相序和方向需要依据手册及实测。
- 天猛星常见的 TIMG8、PA29/PA30 只能作为器件复用候选；TIMG8 QEI 与 PB22/PB26 的 TIMG8 PWM 用途互斥。

skill 不包含 QEI 应用模板，也不会恢复旧天巧星编码器按键、显示或蜂鸣器逻辑。

## 自检

在 `mspm0-development` 目录运行：

```powershell
python -B scripts\validate_skill.py .
python -B scripts\list_examples.py
```

如果本机有系统 `skill-creator`，还应运行其 `quick_validate.py`：

```powershell
$codexDirectory = if ([string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
    Join-Path $env:USERPROFILE ".codex"
} else {
    $env:CODEX_HOME
}
$quickValidate = Join-Path $codexDirectory (
    "skills\.system\skill-creator\scripts\quick_validate.py")
python -B $quickValidate .
```

最近一次发布验证记录：2026-07-26，skill 内容对应提交 [`21dad86`](https://github.com/Cerwor/MSPM0Skill/commit/21dad869d14ce81ecc8c977dda32eec680be54b2)。

- 仓库源和安装副本结构校验。
- 11 个公共脚本的 `--help` 检查。
- SysConfig 1.27.0 + MSPM0 SDK 2.10.00.04：7 个模板严格生成，0 warnings。
- 同版本 TI 官方 G3507 `timg_qei_mode` 严格生成，0 warnings。
- TI Arm Clang 4.0.4.LTS：模板应用源码与 SysConfig 生成配置共 15 个 C 编译单元，以 `-Wall -Wextra -Werror -fsyntax-only` 检查通过。

这些结果不等于所有板卡和外设已经完成实物验证。烧录成功也不能单独证明时序、极性、方向、每圈计数或电气连接正确。

## 安全边界

- 烧录、复位、暂停目标、连接调试器和发送会改变设备状态的串口命令需要明确用户意图。
- 不自动选择多个探针、固件输出、`.ccxml` 或 `.syscfg` 中的某一个。
- 不自动执行解锁、Mass Erase 或恢复出厂。
- 不把 TI LaunchPad 板载 LED、按钮、UART、传感器、引脚和探针设置直接迁移到立创开发板。
- 不手动修改 SysConfig 生成文件来替代 `.syscfg` 源配置。

详细路由与维护边界：

- [`SKILL.md`](mspm0-development/SKILL.md)
- [天猛星板级指南](mspm0-development/references/hardware/tianmengxing.md)
- [天巧星通用外设指南](mspm0-development/references/hardware/tianqiaoxing.md)
- [来源与支持边界](mspm0-development/references/maintenance/sources-and-boundaries.md)

## 许可证与来源

本仓库目前没有选择统一的根级许可证，不应推断为自动允许复制、修改或再分发。skill 内保留的来源许可证文本位于 [`references/maintenance/licenses/`](mspm0-development/references/maintenance/licenses/)。

如需复用或发布其中的代码、模板或文档，请先检查对应来源、版权声明和许可证兼容性。
