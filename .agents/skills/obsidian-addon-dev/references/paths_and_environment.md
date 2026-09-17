# Caminhos do Sistema & Ambiente de Execução

## Tabela de Caminhos Homologados

```text
Anki Executable:
$env:USERPROFILE\Downloads\Anki\anki.exe

Development Workspace:
$env:USERPROFILE\Downloads\Obsidian Addon

Anki Production Addon Directory:
$env:APPDATA\Anki2\addons21\Obsidian Addon

Anki Global Preferences SQLite Database:
$env:APPDATA\Anki2\prefs21.db
(Language stored in table: profiles -> key: _global['defaultLang'])

User Profile Directory:
$env:APPDATA\Anki2\<SeuPerfil>

Card Collection SQLite Database:
$env:APPDATA\Anki2\<SeuPerfil>\collection.anki2

Runtime Forensic Log:
runtime_debug.log (located at addon root)
```

## Informações do Ambiente de Execução
- **Sistema Operacional**: Windows 11 (build 10.0.26200).
- **Shell do Agente**: PowerShell.
- **Python do Sistema**: Python 3.12 / 3.13 (usado para unittests rápidos em modo headless).
- **Python Embutido do Anki**: Python 3.13.5 com PyQt 6.9.1.
- **Versão do Anki**: Anki 25.09.4 (d52ca669).
