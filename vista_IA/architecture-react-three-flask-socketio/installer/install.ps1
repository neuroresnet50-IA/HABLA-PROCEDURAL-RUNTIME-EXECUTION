param(
    [string]$Profile = "base",
    [string]$Recipe = "",
    [string]$Requirement = "",
    [string]$FromRequirement = "",
    [switch]$Ask,
    [switch]$Execute,
    [switch]$AllowSystem,
    [switch]$NoPause,
    [double]$Speed = 0.05
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Resolve-Path (Join-Path $ScriptDir "..")
$InstallerVenv = Join-Path $AppRoot ".installer-venv"
$Python = "python"

Set-Location $AppRoot

& $Python -m venv $InstallerVenv
$VenvPython = Join-Path $InstallerVenv "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -r (Join-Path $ScriptDir "requirements.txt") --quiet

if ($PSBoundParameters.Count -eq 0) {
    $Ask = $true
    $Execute = $true
    $AllowSystem = $true
}

$HasSmartInput = $Ask -or ($Recipe -ne "") -or ($Requirement -ne "") -or ($FromRequirement -ne "")

$ArgsList = @("--profile", $Profile, "--speed", "$Speed")
if ($Ask) {
    $ArgsList += "--ask"
}
if ($Recipe -ne "") {
    $ArgsList += @("--recipe", $Recipe)
}
if ($Requirement -ne "") {
    $ArgsList += @("--requirement", $Requirement)
}
if ($FromRequirement -ne "") {
    $ArgsList += @("--from-requirement", $FromRequirement)
}
if ($HasSmartInput -and -not $Execute) {
    $Execute = $true
}
if ($HasSmartInput -and -not $AllowSystem) {
    $AllowSystem = $true
}
if ($Execute) {
    $ArgsList += "--execute"
}
if ($AllowSystem) {
    $ArgsList += "--allow-system"
}
if (-not $NoPause) {
    $ArgsList += "--pause"
}

try {
    & $VenvPython (Join-Path $ScriptDir "habla_observer_installer.py") @ArgsList
    if ($LASTEXITCODE -ne 0) {
        throw "Installer exited with code $LASTEXITCODE"
    }
}
catch {
    Write-Host ""
    Write-Host "HABLA installer fallo: $_" -ForegroundColor Red
    Write-Host "Revisa installer/logs/ o copia este mensaje para diagnostico."
    if (-not $NoPause) {
        Read-Host "Presiona Enter para cerrar el instalador"
    }
    exit 1
}
