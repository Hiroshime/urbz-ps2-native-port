param(
    [ValidateSet('padrao','original','hd','alto','ultra','qhd')][string]$Graphics,
    [ValidateSet('off','fsr1')][string]$Upscaler,
    [switch]$Widescreen,
    [string]$WindowSize,
    [switch]$Fullscreen,
    [ValidateRange(0,2147483647)][int]$Frames = 0,
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$GameOptions
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
. (Join-Path $PSScriptRoot 'Graphics-Windows.ps1')
Set-UrbzGraphics -Profile $Graphics
if ($Upscaler) { $env:PS2_UPSCALER = $Upscaler }
if ($WindowSize) { $env:PS2_WINDOW_SIZE = $WindowSize }
if (-not (Test-Path -LiteralPath 'disc.iso')) { throw 'Coloque sua ISO PAL nesta pasta com o nome disc.iso.' }
New-Item -ItemType Directory -Force -Path 'user' | Out-Null
$gameArgs = @('--disc','disc.iso','--game-dir','.','--pal','--language','en','--window','--memcard','user/card.ps2','--quick-dir','user')
if ($Fullscreen) { $gameArgs += '--fullscreen' }
if ($Widescreen) { $gameArgs += '--widescreen' }
if ($Frames -gt 0) { $gameArgs += @('--frames',"$Frames") }
if ($GameOptions) { $gameArgs += $GameOptions }
$process = Start-Process -FilePath (Join-Path $PSScriptRoot 'Urbz.exe') -WorkingDirectory $PSScriptRoot -ArgumentList $gameArgs -Wait -PassThru
exit $process.ExitCode
