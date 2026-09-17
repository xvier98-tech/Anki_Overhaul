# Comandos Operacionais Homologados

Todos os comandos abaixo são garantidos para execução imediata no Windows/PowerShell sem testes empíricos.

---

## 1. Suíte de Testes Unitários
```powershell
python -m unittest discover -s tests
```
- **Local**: `$env:USERPROFILE\Downloads\Obsidian Addon`
- **Resultado Esperado**: Todos os testes com status `OK`.

---

## 2. Sincronização de Arquivos com Produção (Anki Addons)
```powershell
robocopy "$env:USERPROFILE\Downloads\Obsidian Addon" "$env:APPDATA\Anki2\addons21\Obsidian Addon" /E /XD __pycache__ .git .pytest_cache /XF *.pyc
```
- **Critério de Sucesso**: Exit code 0 ou 1 do robocopy.

---

## 3. Inicialização e Monitoramento do Anki
```powershell
# Iniciar o Anki em segundo plano
Start-Process "$env:USERPROFILE\Downloads\Anki\anki.exe"

# Verificar se o processo do Anki está em execução
Get-Process anki -ErrorAction SilentlyContinue

# Finalizar o processo do Anki
Stop-Process -Name anki -Force -ErrorAction SilentlyContinue
```

---

## 4. Comandos Proibidos (Anti-Patterns)
- ⛔ `where anki` (trava o PowerShell aguardando stdin).
- ⛔ `taskkill /IM anki.exe` sem tratar erros (prefira `Stop-Process`).
