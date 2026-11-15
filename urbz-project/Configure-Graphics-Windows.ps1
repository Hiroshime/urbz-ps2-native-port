param([ValidateSet('padrao','original','hd','alto','ultra')][string]$Profile)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$table = Get-Content -LiteralPath 'graphics-presets.json' -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $Profile) {
    $options = @($table.presets.PSObject.Properties)
    for ($i=0; $i -lt $options.Count; $i++) {
        Write-Host "$($i+1). $($options[$i].Value.label) ($($options[$i].Name)) - $($options[$i].Value.description)"
    }
    $choice = Read-Host 'Escolha o número ou o nome do perfil'
    $number = 0
    if ([int]::TryParse($choice,[ref]$number) -and $number -ge 1 -and $number -le $options.Count) { $Profile = $options[$number-1].Name }
    else { $Profile = $choice.Trim().ToLowerInvariant() }
}
if (-not $table.presets.PSObject.Properties[$Profile]) { throw 'Perfil gráfico inválido.' }
New-Item -ItemType Directory -Force -Path 'user' | Out-Null
$target = Join-Path $PSScriptRoot 'user/graphics.json'
$temp = Join-Path $PSScriptRoot ('user/graphics-' + [guid]::NewGuid().ToString('N') + '.tmp')
try {
    @{version=1;profile=$Profile} | ConvertTo-Json | Set-Content -LiteralPath $temp -Encoding UTF8
    if (Test-Path -LiteralPath $target) { [IO.File]::Replace($temp,$target,$null) }
    else { [IO.File]::Move($temp,$target) }
} finally { if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp } }
Write-Host "Perfil $Profile selecionado para a próxima abertura."
