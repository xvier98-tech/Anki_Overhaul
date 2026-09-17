# PowerShell script to synchronize development addon files to Anki production directory
$ErrorActionPreference = "Stop"

$src = "$env:USERPROFILE\Downloads\Obsidian Addon"
$dst = "$env:APPDATA\Anki2\addons21\Obsidian Addon"

Write-Host "Iniciando sincronizacao de arquivos para o Anki..." -ForegroundColor Cyan
robocopy $src $dst /E /XD __pycache__ .git .pytest_cache /XF *.pyc

$exitCode = $LASTEXITCODE
if ($exitCode -le 7) {
    Write-Host "Sincronizacao concluida com sucesso! (Exit code: $exitCode)" -ForegroundColor Green
} else {
    Write-Host "Falha na sincronizacao com Robocopy (Exit code: $exitCode)" -ForegroundColor Red
    exit $exitCode
}
