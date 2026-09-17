# Helper script to launch Anki Desktop safely
$ankiExe = "$env:USERPROFILE\Downloads\Anki\anki.exe"

if (-not (Test-Path $ankiExe)) {
    Write-Host "Executavel do Anki nao encontrado em: $ankiExe" -ForegroundColor Red
    exit 1
}

Write-Host "Iniciando Anki Desktop..." -ForegroundColor Green
Start-Process $ankiExe
