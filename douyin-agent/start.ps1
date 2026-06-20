# ============================================
# 抖音陪玩Agent - 一键启动脚本 (Windows)
# 功能: 环境检查 → 依赖安装 → 启动服务
# ============================================

param(
    [switch]$SkipInstall,  # 跳过依赖安装，直接启动
    [switch]$Force,        # 强制重新安装依赖
    [int]$Port = 5002      # 自定义端口号
)

# ====== 全局配置 ======
$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "抖音陪玩Agent - 启动器"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvName = "venv"
$RequirementsFile = "requirements.txt"
$LogFile = "logs\startup.log"

# 颜色定义
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

# ====== 初始化日志目录 ======
if (-not (Test-Path "$ProjectRoot\logs")) {
    New-Item -ItemType Directory -Path "$ProjectRoot\logs" | Out-Null
}

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    Add-Content -Path "$ProjectRoot\$LogFile" -Value $logMessage -Encoding UTF8
}

# ============================================
# 步骤 0: 欢迎信息
# ============================================
Clear-Host
Write-Host ""
Write-ColorOutput "╔══════════════════════════════════════════════╗" "Cyan"
Write-ColorOutput "║       抖音陪玩Agent - 一键启动脚本 v1.0      ║" "Cyan"
Write-ColorOutput "╚══════════════════════════════════════════════╝" "Cyan"
Write-Host ""
Write-Log "===== 启动脚本开始执行 ====="

# ============================================
# 步骤 1: 检查Python环境
# ============================================
Write-Host "[步骤 1/5] 检查Python环境..." -ForegroundColor Yellow

try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        
        if ($major -ge 3 -and $minor -ge 7) {
            Write-ColorOutput "  ✓ Python $major.$minor 已安装" "Green"
            Write-Log "Python版本: $pythonVersion"
        } else {
            throw "Python版本过低，需要3.7+，当前: $pythonVersion"
        }
    } else {
        throw "未检测到Python或版本解析失败"
    }
} catch {
    Write-ColorOutput "  ✗ Python环境异常: $_" "Red"
    Write-Host ""
    Write-ColorOutput "请安装Python 3.7+:" "Yellow"
    Write-Host "  下载地址: https://www.python.org/downloads/" "Cyan"
    Write-Host "  安装时务必勾选 'Add Python to PATH'" "Yellow"
    Read-Host "按回车键退出..."
    exit 1
}

# 检查pip
$pipVersion = pip --version 2>&1
if ($pipVersion) {
    Write-ColorOutput "  ✓ Pip已安装" "Green"
} else {
    Write-ColorOutput "  ✗ Pip未安装" "Red"
    Read-Host "按回车键退出..."
    exit 1
}

Write-Host ""

# ============================================
# 步骤 2: 创建虚拟环境(可选)
# ============================================
Write-Host "[步骤 2/5] 检查虚拟环境..." -ForegroundColor Yellow

$VenvPath = Join-Path $ProjectRoot $VenvName

if (-not (Test-Path $VenvPath)) {
    Write-Host "  正在创建虚拟环境..."
    try {
        python -m venv $VenvName
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "  ✓ 虚拟环境创建成功: .\$VenvName\" "Green"
            Write-Log "虚拟环境已创建"
        } else {
            throw "虚拟环境创建失败 (退出码: $LASTEXITCODE)"
        }
    } catch {
        Write-ColorOutput "  ⚠ 虚拟环境创建失败，将使用全局Python: $_" "Yellow"
        Write-Log "警告: 虚拟环境创建失败 - $_"
    }
} else {
    Write-ColorOutput "  ✓ 虚拟环境已存在" "Green"
}

Write-Host ""

# ============================================
# 步骤 3: 安装依赖包
# ============================================
if ($SkipInstall) {
    Write-Host "[步骤 3/5] 跳过依赖安装 (使用了 --SkipInstall 参数)" -ForegroundColor Gray
} else {
    Write-Host "[步骤 3/5] 安装依赖包..." -ForegroundColor Yellow
    
    $ReqPath = Join-Path $ProjectRoot $RequirementsFile
    
    if (-not (Test-Path $ReqPath)) {
        Write-ColorOutput "  ✗ 未找到 requirements.txt" "Red"
        Read-Host "按回车键退出..."
        exit 1
    }

    # 检查是否需要强制重装
    if ($Force) {
        Write-Host "  使用 --Force 参数，将重新安装所有依赖..." "Gray"
    }

    Write-Host ""
    Write-Host "  正在安装依赖 (可能需要几分钟)..." "Gray"
    Write-Host "  ┌─────────────────────────────────────┐" "DarkGray"

    try {
        pip install -r $ReqPath --upgrade 2>&1 | ForEach-Object {
            if ($_ -match "(Successfully|Requirement already|Installing|Collecting)") {
                Write-Host "  │ $_" "Green"
            } elseif ($_ -match "(ERROR|error|failed)") {
                Write-Host "  │ ✗ $_" "Red"
            } elseif ($_ -match "(WARNING|warning)") {
                Write-Host "  │ ⚠ $_" "Yellow"
            } else {
                Write-Host "  │ $_" "Gray"
            }
        }
        
        Write-Host "  └─────────────────────────────────────┘" "DarkGray"
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "  ✓ 依赖安装完成!" "Green"
            Write-Log "依赖安装成功"
        } else {
            throw "依赖安装失败 (退出码: $LASTEXITCODE)"
        }
    } catch {
        Write-ColorOutput "  ✗ 依赖安装失败: $_" "Red"
        Write-Log "错误: 依赖安装失败 - $_"
        Write-Host ""
        Write-ColorOutput "常见解决方案:" "Yellow"
        Write-Host "  1. 检查网络连接是否正常" "Gray"
        Write-Host "  2. 尝试使用国内镜像源:" "Gray"
        Write-Host "     pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple" "Cyan"
        Write-Host "  3. 升级pip: python -m pip install --upgrade pip" "Gray"
        Read-Host "按回车键退出..."
        exit 1
    }
}

Write-Host ""

# ============================================
# 步骤 4: 验证关键模块
# ============================================
Write-Host "[步骤 4/5] 验证关键模块..." -ForegroundColor Yellow

$RequiredModules = @("flask", "flask_socketio", "mss", "easyocr", "sklearn")
$MissingModules = @()

foreach ($module in $RequiredModules) {
    try {
        python -c "import $module" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "  ✓ $module" "Green"
        } else {
            $MissingModules += $module
            Write-ColorOutput "  ✗ $module (缺失)" "Red"
        }
    } catch {
        $MissingModules += $module
        Write-ColorOutput "  ✗ $module (导入失败)" "Red"
    }
}

if ($MissingModules.Count -gt 0) {
    Write-ColorOutput "  ⚠ 缺少 $($MissingModules.Count) 个模块，尝试自动修复..." "Yellow"
    
    foreach ($mod in $MissingModules) {
        Write-Host "  安装 $mod ..." "Gray"
        pip install $mod 2>$null
    }
    
    Write-ColorOutput "  ✓ 自动修复完成!" "Green"
    Write-Log "自动安装缺失模块: $($MissingModules -join ', ')"
}

Write-Host ""

# ============================================
# 步骤 5: 启动Web服务
# ============================================
Write-Host "[步骤 5/5] 启动Web服务..." -ForegroundColor Yellow

$ServerScript = Join-Path $ProjectRoot "web\server.py"

if (-not (Test-Path $ServerScript)) {
    Write-ColorOutput "  ✗ 未找到 server.py" "Red"
    Read-Host "按回车键退出..."
    exit 1
}

Write-Host ""
Write-ColorOutput "╔═════════════════════════════════════════╗" "Cyan"
Write-ColorOutput "║  抖音陪玩Agent 即将启动...              ║" "Cyan"
Write-ColorOutput "╠═════════════════════════════════════════╣" "Cyan"
Write-ColorOutput "║  访问地址: http://localhost:$Port        ║" "Green"
Write-ColorOutput "║  按 Ctrl+C 停止服务                     ║" "Yellow"
Write-ColorOutput "╚═════════════════════════════════════════╝" "Cyan"
Write-Host ""

Write-Log "===== Web服务启动 ====="
Write-Log "端口: $Port"
Write-Log "项目路径: $ProjectRoot"

# 设置环境变量
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

try {
    # 切换到项目目录
    Set-Location $ProjectRoot
    
    # 启动Flask服务器
    python web\server.py --port $Port
    
    # 如果正常退出
    Write-Host ""
    Write-ColorOutput "服务已停止" "Yellow"
    Write-Log "===== 服务正常停止 ====="
} catch {
    Write-Host ""
    Write-ColorOutput "✗ 服务启动失败: $_" "Red"
    Write-Log "错误: 服务启动失败 - $_"
    Write-Host ""
    Write-ColorOutput "可能的原因:" "Yellow"
    Write-Host "  1. 端口 $Port 已被占用" "Gray"
    Write-Host "  2. 依赖包未正确安装" "Gray"
    Write-Host "  3. 配置文件(.env)有误" "Gray"
    Write-Host ""
    Write-ColorOutput "调试命令:" "Cyan"
    Write-Host "  python web\server.py --debug --port $Port" "White"
}

Read-Host "`n按回车键退出..."
