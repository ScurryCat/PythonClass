<#
.SYNOPSIS
    wy_site 环境初始化脚本：接手项目后跑这一个就够了。

.DESCRIPTION
    按顺序完成：
      1. 检查 Python 版本（Django 5.2 要求 3.10+）
      2. 安装 requirements.txt 里的依赖
      3. 定位 mysql 客户端并临时加入 PATH
      4. 按 settings.py 的配置创建数据库（utf8mb4 / utf8mb4_unicode_ci）
      5. 执行 migrate 建表
      6. 自检 manage.py check
      7. 可选：创建后台管理员账号

    脚本可以重复执行：数据库已存在、依赖已安装、迁移已完成时都会自动跳过，
    不会重复建库，也不会清空数据。

.PARAMETER SkipInstall
    跳过 pip install（依赖已经装好时使用）。

.PARAMETER SkipDb
    跳过建库步骤。

.PARAMETER SkipSuperuser
    跳过「是否创建管理员」的询问（适合无人值守运行）。

.PARAMETER RunServer
    全部完成后直接启动开发服务器。

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1 -RunServer

.NOTES
    脚本内的中文以 UTF-8 with BOM 保存，Windows PowerShell 5.1 才能正确解析。
    若提示「无法加载文件……在此系统上禁止运行脚本」，说明执行策略是 Restricted，
    请按上面的 .EXAMPLE 用 -ExecutionPolicy Bypass 方式运行。
#>
[CmdletBinding()]
param(
    [switch]$SkipInstall,
    [switch]$SkipDb,
    [switch]$SkipSuperuser,
    [switch]$RunServer
)

$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
if (-not $root) { $root = (Get-Location).Path }
$projectDir = Join-Path $root 'wy_site'
$requirements = Join-Path $root 'requirements.txt'

function Step([string]$number, [string]$text) {
    Write-Host ''
    Write-Host "[$number] $text" -ForegroundColor Cyan
}

function Ok([string]$text) {
    Write-Host "     OK  $text" -ForegroundColor Green
}

function Note([string]$text) {
    Write-Host "     注意 $text" -ForegroundColor Yellow
}

function Die([string]$text) {
    Write-Host ''
    Write-Host "     [失败] $text" -ForegroundColor Red
    exit 1
}

Set-Location -LiteralPath $root

# ---------------------------------------------------------------- 1. Python
Step 1 '检查 Python 版本'

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Die '找不到 python 命令。请先安装 Python 3.10+ 并勾选 "Add Python to PATH"。'
}
$py = $pythonCmd.Source
Write-Host "     解释器: $py"

& $py -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    Die 'Python 版本过低。Django 5.2 需要 Python 3.10 及以上。'
}
Ok '版本满足要求（>= 3.10）'

# ---------------------------------------------------------------- 2. 依赖
Step 2 '安装依赖'

if ($SkipInstall) {
    Write-Host '     已指定 -SkipInstall，跳过'
} elseif (-not (Test-Path -LiteralPath $requirements)) {
    Die "找不到 $requirements"
} else {
    $bytes = [System.IO.File]::ReadAllBytes($requirements)
    if (-not ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)) {
        Note 'requirements.txt 缺少 UTF-8 BOM，本次用 PYTHONUTF8 兜底；建议重新保存为 UTF-8 with BOM。'
    }

    # 中文 Windows 上 pip 默认按 GBK 读 requirements.txt，
    # 这里强制 UTF-8 解码，和文件里的 BOM 形成双保险。
    $savedUtf8 = $env:PYTHONUTF8
    $env:PYTHONUTF8 = '1'
    try {
        & $py -m pip install -r $requirements
        if ($LASTEXITCODE -ne 0) {
            Die 'pip install 失败，请把上面的报错贴出来。'
        }
    } finally {
        if ($null -eq $savedUtf8) {
            Remove-Item Env:\PYTHONUTF8 -ErrorAction SilentlyContinue
        } else {
            $env:PYTHONUTF8 = $savedUtf8
        }
    }
    Ok '依赖安装完成'
}

# ---------------------------------------------------------------- 3. mysql 客户端
Step 3 '定位 mysql 客户端'

$mysqlExe = $null
$onPath = Get-Command mysql.exe -ErrorAction SilentlyContinue
if ($onPath) {
    $mysqlExe = $onPath.Source
} else {
    $guesses = @(
        'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe',
        'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe',
        'C:\Program Files\MySQL\MySQL Server 5.7\bin\mysql.exe',
        'C:\Program Files\MariaDB 11.4\bin\mysql.exe',
        'C:\Program Files\MariaDB 10.11\bin\mysql.exe'
    )
    foreach ($g in $guesses) {
        if (Test-Path -LiteralPath $g) { $mysqlExe = $g; break }
    }
    if (-not $mysqlExe -and (Test-Path -LiteralPath 'C:\Program Files\MySQL')) {
        $hit = Get-ChildItem -LiteralPath 'C:\Program Files\MySQL' -Recurse -Filter 'mysql.exe' -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($hit) { $mysqlExe = $hit.FullName }
    }
}

if ($mysqlExe) {
    $mysqlBin = Split-Path -Parent $mysqlExe
    if (($env:Path -split ';') -notcontains $mysqlBin) {
        $env:Path = "$mysqlBin;$env:Path"
    }
    Ok "已加入当前会话 PATH: $mysqlBin"
} else {
    Note '没找到 mysql.exe。建库由 Python 驱动直接完成，不影响本脚本；'
    Note '只是以后想在命令行用 mysql 需要自己把 bin 目录加进 PATH。'
}

# ---------------------------------------------------------------- 4. 建库
Step 4 '创建数据库'

if ($SkipDb) {
    Write-Host '     已指定 -SkipDb，跳过'
} else {
    if (-not (Test-Path -LiteralPath $projectDir)) {
        Die "找不到项目目录 $projectDir"
    }

    $helper = Join-Path ([System.IO.Path]::GetTempPath()) ("wy_site_db_{0}.py" -f ([guid]::NewGuid().ToString('N')))
    $helperCode = @'
import os
import sys

root = sys.argv[1]
sys.path.insert(0, os.path.join(root, "wy_site"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wy_site.settings")

import django
django.setup()

import MySQLdb
from django.conf import settings

cfg = settings.DATABASES["default"]
name = cfg["NAME"]
conn = MySQLdb.connect(
    host=cfg.get("HOST") or "127.0.0.1",
    port=int(cfg.get("PORT") or 3306),
    user=cfg.get("USER"),
    passwd=cfg.get("PASSWORD") or "",
    charset="utf8mb4",
)
cur = conn.cursor()
cur.execute(
    "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=%s", (name,)
)
if cur.fetchone():
    print("     数据库 %s 已存在，跳过创建" % name)
else:
    cur.execute(
        "CREATE DATABASE `%s` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        % name.replace("`", "``")
    )
    print("     已创建数据库 %s" % name)
cur.execute(
    "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME"
    " FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=%s",
    (name,),
)
charset, collation = cur.fetchone()
print("     字符集: %s / %s" % (charset, collation))
cur.close()
conn.close()
'@

    try {
        Set-Content -LiteralPath $helper -Value $helperCode -Encoding UTF8
        & $py $helper $root
        if ($LASTEXITCODE -ne 0) {
            Die '建库失败：确认 MySQL80 服务已启动，且 settings.py 里的 USER / PASSWORD 正确。'
        }
    } finally {
        Remove-Item -LiteralPath $helper -Force -ErrorAction SilentlyContinue
    }
    Ok '数据库就绪'
}

# ---------------------------------------------------------------- 5/6/7
if (-not (Test-Path -LiteralPath (Join-Path $projectDir 'manage.py'))) {
    Die "找不到 $projectDir\manage.py"
}

Push-Location -LiteralPath $projectDir
try {
    Step 5 '执行数据库迁移'
    & $py manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) {
        Die 'migrate 失败。'
    }
    Ok '迁移完成'

    Step 6 '项目自检'
    & $py manage.py check
    if ($LASTEXITCODE -ne 0) {
        Die 'check 未通过。'
    }
    Ok '配置无误'

    if (-not $SkipSuperuser) {
        Step 7 '后台管理员'
        $answer = Read-Host '     现在创建管理员账号吗? [y/N]'
        if ($answer -match '^y') {
            & $py manage.py createsuperuser
            if ($LASTEXITCODE -ne 0) {
                Note '管理员未创建（用户名可能已存在）。稍后可手动运行: python manage.py createsuperuser'
            } else {
                Ok '管理员已创建'
            }
        } else {
            Write-Host '     已跳过，稍后可运行: python manage.py createsuperuser'
        }
    }
} finally {
    Pop-Location
}

# ---------------------------------------------------------------- 收尾
Write-Host ''
Write-Host ' 全部完成。' -ForegroundColor Green
Write-Host '   启动:  cd wy_site;  python manage.py runserver'
Write-Host '   首页:  http://127.0.0.1:8000/'
Write-Host '   后台:  http://127.0.0.1:8000/admin/'

if ($RunServer) {
    Write-Host ''
    Write-Host ' 正在启动开发服务器（Ctrl+C 停止）...' -ForegroundColor Cyan
    Push-Location -LiteralPath $projectDir
    try {
        & $py manage.py runserver
    } finally {
        Pop-Location
    }
}
