$ErrorActionPreference = "Stop"

function Test-KiCadCli {
    $candidates = @(
        "kicad-cli",
        "C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
        "C:\Program Files\KiCad\8.0\bin\kicad-cli.exe",
        "C:\Program Files\KiCad\7.0\bin\kicad-cli.exe"
    )

    foreach ($candidate in $candidates) {
        try {
            $command = Get-Command $candidate -ErrorAction Stop
            return $command.Source
        } catch {
            if (Test-Path $candidate) {
                return (Resolve-Path $candidate).Path
            }
        }
    }

    return $null
}

$found = Test-KiCadCli
if ($found) {
    Write-Host "KiCad CLI already available at: $found" -ForegroundColor Green
    exit 0
}

Write-Host "KiCad CLI not found." -ForegroundColor Yellow
Write-Host "Trying WinGet install for KiCad..." -ForegroundColor Yellow

$winget = Get-Command winget -ErrorAction SilentlyContinue
if ($winget) {
    winget install --id KiCad.KiCad --exact --accept-package-agreements --accept-source-agreements
    $found = Test-KiCadCli
    if ($found) {
        Write-Host "KiCad CLI installed successfully at: $found" -ForegroundColor Green
        Write-Host "Restart PowerShell after install if `pcb info` still reports missing." -ForegroundColor Cyan
        exit 0
    }
}

Write-Host "Automatic install did not finish." -ForegroundColor Red
Write-Host "Install KiCad 8 or 9 from https://www.kicad.org/download/windows/ and restart the shell." -ForegroundColor Yellow
exit 1
