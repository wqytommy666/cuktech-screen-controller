[CmdletBinding()]
param()

$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$DataRoot = if ($env:CUKTECH_DATA_ROOT) { $env:CUKTECH_DATA_ROOT } elseif ($env:LOCALAPPDATA) {
    Join-Path $env:LOCALAPPDATA "CUKTECH Screen Controller"
} else { $Root }
$Artifacts = if ($env:CUKTECH_ARTIFACTS_DIR) { $env:CUKTECH_ARTIFACTS_DIR } else { Join-Path $DataRoot "artifacts" }
$Pass = 0
$Warn = 0
$Fail = 0

function Good([string]$Name, [string]$Message) {
    $script:Pass++
    Write-Host "[OK]   $Name - $Message" -ForegroundColor Green
}
function Caution([string]$Name, [string]$Message) {
    $script:Warn++
    Write-Host "[WARN] $Name - $Message" -ForegroundColor Yellow
}
function Bad([string]$Name, [string]$Message) {
    $script:Fail++
    Write-Host "[FAIL] $Name - $Message" -ForegroundColor Red
}

Write-Host "CUKTECH Screen Controller · Windows read-only diagnostics"
Write-Host "=========================================================="

if ($env:OS -eq "Windows_NT") {
    Good "System" ([System.Environment]::OSVersion.VersionString)
} else {
    Caution "System" "This script is intended for Windows."
}

if (Test-Path $VenvPython) {
    & $VenvPython -c "import PIL, requests, cryptography"
    if ($LASTEXITCODE -eq 0) {
        Good "Runtime" (& $VenvPython --version)
    } else {
        Bad "Runtime" "Python dependencies are incomplete."
    }
} else {
    Bad "Runtime" "Missing .venv; run .\scripts\setup-windows.ps1 first."
}

$LanAddress = Get-NetIPConfiguration -ErrorAction SilentlyContinue |
    Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } |
    ForEach-Object { $_.IPv4Address.IPAddress } |
    Where-Object { $_ -and $_ -notlike "169.254.*" } |
    Select-Object -First 1
if ($LanAddress) {
    Good "LAN address" "http://${LanAddress}:8765/screen.gif"
} else {
    Caution "LAN address" "No active private IPv4 route was found."
}

try {
    $Health = Invoke-RestMethod -Uri "http://127.0.0.1:8765/health" -TimeoutSec 3
    if ($Health.status -eq "partial") {
        Caution "Bridge" "HTTP is available, but at least one quota account is unavailable."
    } elseif ($Health.ok -eq $true) {
        Good "Bridge" "HTTP/data are ready; verify an AP01-originated image request separately."
    } else {
        Caution "Bridge" "HTTP is available, but live content is not ready."
    }
} catch {
    Caution "Bridge" "http://127.0.0.1:8765/health is not responding."
}

$ScreenFiles = @(
    (Join-Path $Artifacts "custom-screen.gif"),
    (Join-Path $Artifacts "quota-dashboard.gif")
) | Where-Object { Test-Path $_ }
if ($ScreenFiles.Count -gt 0) {
    Good "Screen file" ($ScreenFiles -join ", ")
} else {
    Caution "Screen file" "No generated GIF was found yet."
}

$Listener = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if ($Listener) {
    Good "TCP 8765" "A local process is listening."
} else {
    Caution "TCP 8765" "Start the Bridge and allow it on Private networks."
}

Write-Host "----------------------------------------------------------"
Write-Host "Result: $Pass OK, $Warn warnings, $Fail failures"
Write-Host "This diagnostic does not read account cookies, passwords, or OTA URLs."
if ($Fail -gt 0) { exit 1 }
