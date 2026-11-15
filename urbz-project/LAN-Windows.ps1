param(
    [Parameter(Mandatory=$true)][ValidateSet('Host','Join')][string]$Role,
    [string]$Address,
    [switch]$Internet,
    [ValidateSet('padrao','original','hd','alto','ultra','qhd')][string]$Graphics,
    [ValidateSet('off','fsr1')][string]$Upscaler,
    [switch]$Widescreen,
    [string]$WindowSize,
    [ValidateRange(1,65535)][int]$Port = 27888,
    [ValidateRange(0,12)][int]$Delay = 3,
    [ValidateRange(0,2147483647)][int]$Frames = 0
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
. (Join-Path $PSScriptRoot 'Graphics-Windows.ps1')
Set-UrbzGraphics -Profile $Graphics
if ($Upscaler) { $env:PS2_UPSCALER = $Upscaler }
if ($WindowSize) { $env:PS2_WINDOW_SIZE = $WindowSize }
if ($Internet) {
    if (-not $PSBoundParameters.ContainsKey('Delay')) { $Delay = 6 }
    if (-not $env:URBZ_NET_KEY) {
        if ($Role -eq 'Host') {
            $random = [byte[]]::new(16)
            $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
            try { $rng.GetBytes($random) } finally { $rng.Dispose() }
            $env:URBZ_NET_KEY = ([BitConverter]::ToString($random)).Replace('-','').ToLowerInvariant()
        } else {
            $secret = Read-Host 'Chave da partida enviada pelo anfitrião' -AsSecureString
            $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
            try { $env:URBZ_NET_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr).Trim() }
            finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
        }
    }
    if ($env:URBZ_NET_KEY -notmatch '\A(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{64})\z') { throw 'Copie a chave completa: 32 ou 64 caracteres hexadecimais.' }
    if ($Role -eq 'Host') {
        try {
            $observed = (Invoke-RestMethod -Uri 'https://api.ipify.org' -TimeoutSec 5).Trim()
            $observedAddress = $null
            if ([Net.IPAddress]::TryParse($observed, [ref]$observedAddress) -and $observedAddress.AddressFamily -eq [Net.Sockets.AddressFamily]::InterNetwork) {
                Write-Host "IPv4 público observado: $observed (a porta precisa estar encaminhada)."
            }
        } catch { Write-Host 'Consulte seu IPv4 público no roteador ou em um serviço de consulta de IP.' }
        Write-Host "Chave desta partida (envie ao amigo junto ao IPv4 público): $env:URBZ_NET_KEY"
        Write-Host "Encaminhe TCP $Port no roteador para este PC. Leia INTERNET.md."
    }
}
if ($Role -eq 'Join') {
    if (-not $Address) { $Address = Read-Host $(if ($Internet) { 'IPv4 público do anfitrião' } else { 'IPv4 local do anfitrião' }) }
    $parsed = $null
    if (-not [Net.IPAddress]::TryParse($Address, [ref]$parsed) -or
        $parsed.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork) {
        throw 'Informe apenas um endereço IPv4, sem a porta. Use -Port para escolher outra porta.'
    }
}
$folder = "user/lan-$($Role.ToLowerInvariant())"
New-Item -ItemType Directory -Force -Path $folder | Out-Null
$card = Join-Path $folder 'card.ps2'
if (-not (Test-Path -LiteralPath $card)) {
    # No overwrite: a second simultaneous launcher must not replace this card.
    [IO.File]::Copy((Join-Path $PSScriptRoot 'empty-card.ps2'), (Join-Path $PSScriptRoot $card), $false)
}
$mode = if ($Internet) { 'Internet por IPv4' } else { 'LAN' }
Write-Host "${mode}: $Role, TCP $Port, atraso $Delay frames. Use seu primeiro controle ou teclado."
Write-Host 'O save compartilhado é o do anfitrião. Salve pelo menu do próprio jogo.'
$gameArgs = @('--disc','disc.iso','--game-dir','.','--pal','--language','en','--window',
    '--quick-dir',$folder,'--memcard',$card,'--net-sync-card',
    '--net-delay',"$Delay",'--net-timeout-ms','300000')
if ($Role -eq 'Host') {
    $gameArgs += @('--net-host',"$Port")
}
else { $gameArgs += @('--net-join',"${Address}:$Port") }
if ($Internet) { $gameArgs += '--net-secure' }
if ($Widescreen) { $gameArgs += '--widescreen' }
if ($Frames -gt 0) { $gameArgs += @('--frames',"$Frames") }
$process = Start-Process -FilePath (Join-Path $PSScriptRoot 'Urbz.exe') -WorkingDirectory $PSScriptRoot -ArgumentList $gameArgs -Wait -PassThru
exit $process.ExitCode
