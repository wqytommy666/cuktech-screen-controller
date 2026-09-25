[CmdletBinding()]
param(
    [string]$InputImage,
    [ValidateSet("contain", "cover", "stretch")]
    [string]$Fit = "contain",
    [switch]$App,
    [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "CUKTECH Screen Controller · Windows Agent Setup"
Write-Host "================================================="

if (Get-Command py -ErrorAction SilentlyContinue) {
    $Launcher = "py"
    $LauncherArgs = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Launcher = "python"
    $LauncherArgs = @()
} else {
    throw "Python 3.9+ was not found. Install it from https://www.python.org/downloads/windows/"
}

& $Launcher @LauncherArgs -c "import sys; raise SystemExit(sys.version_info < (3, 9))"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.9 or later is required."
}
Write-Host "[1/4] Python is available."

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    & $Launcher @LauncherArgs -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
}
Write-Host "[2/4] Virtual environment is ready."

$Requirements = if ($App) { "requirements-windows-app.txt" } else { "requirements.txt" }
& $VenvPython -m pip install --disable-pip-version-check -r $Requirements
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed; Bridge was not started." }
if ($App) {
    & $VenvPython -c "import PIL, requests, cryptography, PySide6"
} else {
    & $VenvPython -c "import PIL, requests, cryptography"
}
if ($LASTEXITCODE -ne 0) { throw "Dependency import check failed." }
Write-Host "[3/4] Python dependencies are ready."

New-Item -ItemType Directory -Force -Path (Join-Path $Root "artifacts") | Out-Null
if ($InputImage) {
    $ResolvedImage = (Resolve-Path $InputImage).Path
    & $VenvPython ap01_prepare_screen.py $ResolvedImage artifacts\custom-screen.gif --fit $Fit --background "#01040B"
    if ($LASTEXITCODE -ne 0) { throw "Image conversion failed." }
    Write-Host "[4/4] Created artifacts\custom-screen.gif"
} else {
    Write-Host "[4/4] Environment setup completed."
}

Write-Host ""
Write-Host "Run the static image bridge:"
Write-Host "  .\.venv\Scripts\python.exe -u ap01_screen_bridge.py artifacts\custom-screen.gif --port 8765"
Write-Host ""
Write-Host "Then allow Python through Windows Defender Firewall for Private networks."
Write-Host "AP01 and this PC must be on the same non-isolated LAN."

if ($App) {
    Write-Host ""
    Write-Host "Windows controller:"
    Write-Host "  .\.venv\Scripts\pythonw.exe windows\AP01ScreenController.py"
    if (-not $NoLaunch) {
        $ControllerScript = Join-Path $Root "windows\AP01ScreenController.py"
        Start-Process -FilePath (Join-Path $Root ".venv\Scripts\pythonw.exe") `
            -ArgumentList ('"' + $ControllerScript + '"') `
            -WorkingDirectory $Root
    }
}
