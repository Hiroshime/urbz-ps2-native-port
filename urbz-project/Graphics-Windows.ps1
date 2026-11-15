# Shared by the offline/network launchers; no game files or saves are changed.
function Set-UrbzGraphics {
    param([string]$Profile)
    $env:PS2_NO_VU_THREAD = '1'
    $env:PS2_GS_SYNC_READBACK = '1'
    $table = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'graphics-presets.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $Profile) {
        $Profile = $env:URBZ_GRAFICOS
        if (-not $Profile) { $Profile = $env:URBZ_GRAPHICS_PROFILE }
    }
    if (-not $Profile) {
        $config = Join-Path $PSScriptRoot 'user/graphics.json'
        if (Test-Path -LiteralPath $config) {
            $saved = Get-Content -LiteralPath $config -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($saved.version -ne 1) { throw 'Configuração gráfica inválida. Use Configurar-Graficos.cmd.' }
            $Profile = $saved.profile
        } else { $Profile = $table.default }
    }
    $property = $table.presets.PSObject.Properties[$Profile]
    if (-not $property) { throw 'Perfil gráfico inválido. Escolha padrao, original, hd, alto ou ultra.' }
    $preset = $property.Value
    if ($null -ne $preset.scale) {
        $env:PS2_SCALE = [string]$preset.scale
        $env:PS2_LOOK = [string]$preset.look
        $env:PS2_SHARP_2D = [string]$preset.sharp_2d
        Write-Host "Gráficos: $($preset.label)."
    }
}
