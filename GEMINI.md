# ⚠️ OBSIDIAN ADDON SUITE - DIRETRIZES & REGRAS MANDATÓRIAS (GEMINI.md)

Este arquivo é **obrigatoriamente lido e aplicado em TODAS as respostas e interações** neste projeto.
Ele existe para **eliminar completamente o desperdício de tokens** em investigações repetidas de informações e comandos que já foram descobertos e resolvidos.

---

## 📍 1. CAMINHOS ABSOLUTOS & CONSTANTES DO AMBIENTE (NUNCA BUSQUE NOVAMENTE!)

| Recurso | Caminho Absoluto Conhecido | Observações Críticas |
| :--- | :--- | :--- |
| **Executável do Anki** | `$env:USERPROFILE\Downloads\Anki\anki.exe` | ⛔ **NUNCA execute `where anki`** no PowerShell (ele chama `Where-Object` e trava indefinidamente). Use o caminho direto ou `Get-Command anki`. |
| **Diretório de Dev (Workspace)** | `$env:USERPROFILE\Downloads\Obsidian Addon` | Onde todo o código deve ser editado e testado. |
| **Diretório de Produção do Anki** | `$env:APPDATA\Anki2\addons21\Obsidian Addon` | Diretório onde o Anki carrega o addon. Deve ser sincronizado via Robocopy após alterações. |
| **Banco de Dados de Preferências** | `$env:APPDATA\Anki2\prefs21.db` | Contém o idioma global em `profiles` -> `_global['defaultLang']` (`en_US`, `pt_BR`, etc.). |
| **Pasta de Perfil do Anki** | `$env:APPDATA\Anki2\<SeuPerfil>` | Perfil principal do usuário. |
| **Log de Diagnóstico Forense** | `runtime_debug.log` | Arquivo na raiz do addon para registrar eventos críticos de runtime. |

---

## ⚡ 2. SCRIPTS & COMANDOS OPERACIONAIS PADRÃO

### A. Execução da Suíte de Testes Unitários
Execute sempre a partir da raiz do workspace:
```bash
python -m unittest discover -s tests
```
> **Ambiente de Teste**: O Python do sistema executa os testes de forma headless. O código possui mocks/fallbacks transparentes para quando `PyQt6` não está disponível no Python do sistema.

### B. Sincronização Obrigatória com a Pasta de Produção do Anki
Após validar os testes com sucesso, sincronize **sempre** com este comando exato:
```powershell
robocopy "$env:USERPROFILE\Downloads\Obsidian Addon" "$env:APPDATA\Anki2\addons21\Obsidian Addon" /E /XD __pycache__ .git .pytest_cache /XF *.pyc
```
> **Nota do Robocopy**: Código de saída `1` (arquivos copiados) ou `0` (nenhuma alteração necessária) significa **SUCESSO TOTAL**.

### C. Iniciar o Anki
```powershell
Start-Process "$env:USERPROFILE\Downloads\Anki\anki.exe"
```

### D. Verificar se o Anki está em Execução
```powershell
Get-Process anki -ErrorAction SilentlyContinue
```

### E. Encerrar o Anki com Segurança
```powershell
Stop-Process -Name anki -Force -ErrorAction SilentlyContinue
```

---

## 🏗️ 3. ARQUITETURA & REGRAS TÉCNICAS ESPECÍFICAS

1. **Áudio no Windows**:
   - Todos os alertas sonoros embutidos são arquivos `.wav` em `assets/sounds/`.
   - No Windows, use **sempre** `winsound.PlaySound(filepath, winsound.SND_FILENAME | winsound.SND_ASYNC)`.
   - Isso garante reprodução com latência zero, funciona com o Anki minimizado ou sem foco, e não trava nem interfere no player de áudio do Anki (`mpv`).

2. **Pomodoro - Intervalo Contínuo & Perda de Foco**:
   - O mecanismo de pausa por inatividade atua **apenas na fase `WORK`**.
   - As pausas de descanso (`BREAK` e `LONG_BREAK`) **nunca pausam por inatividade**, correndo livremente até `00:00`.
   - A perda de foco é detectada via `QGuiApplication.applicationStateChanged` e só pausa/alerta na fase `WORK`.

3. **Internacionalização (i18n)**:
   - Todo texto visível na interface deve utilizar `tr("chave", "Texto Padrão")` de `utils/i18n.py`.
   - Sempre adicione as 4 línguas suportadas: Inglês (`en`), Português (`pt`), Espanhol (`es`) e Francês (`fr`).

4. **Acessibilidade & Contraste (WCAG 2.1)**:
   - Cores de texto sobre fundos dinâmicos (`accent`) devem usar `get_accessible_text_color(bg_hex)` de `modules/theme_manager/engine.py` para garantir contraste mínimo de 4.5:1.

5. **Documentação de Versões**:
   - Toda alteração deve ser registrada no topo de `CHANGELOG_DEV.md` e em `walkthrough.md`.

---

# PROTOCOLO MESTRE: ORQUESTRAÇÃO TRANSPARENTE, CONTROLE DE FLUXO E ANTI-RABBIT HOLE (V9.0)
<!-- Diretriz operacional imperativa para Google Antigravity -->

---

## 1. PRINCÍPIOS DE COMUNICAÇÃO E CONTROLE DE FLUXO

1. **Visibilidade Contínua (Live Broadcast):** O modelo NUNCA executa ferramentas ou despacha agentes no escuro. Toda ação deve ser precedida por 1 linha de status comunicando ao usuário o que está sendo feito e a intenção técnica imediata.
2. **Plano de Voo Travado (Plan Lock):** Proibido iniciar execução (seja 1 arquivo ou 10) sem declarar previamente uma sequência linear numerada de passos (máximo 4 passos). O plano dita a execução; o agente não inventa passos no meio do caminho.
3. **Trava Anti-Toca de Coelho (Anti-Rabbit Hole Guard):** Se ao executar o Passo 1 o agente descobrir um comportamento novo ou inesperado, é **TERMINANTEMENTE PROIBIDO** mergulhar em uma cadeia reativa de investigação (*"descobri A, então vejo B, então vejo C..."*). O agente deve:
   - Registrar a anomalia.
   - Concluir a verificação do passo atual.
   - Reportar ao usuário e propor ajuste explícito no plano antes de seguir.
4. **Alocação por Complexidade Real:** Tarefas em ≤ 2 arquivos são executadas diretamente, mas **AINDA EXIGEM** declaração de plano prévio e comunicação ativa. Subagentes são reservados para tarefas de ≥ 3 arquivos ou diagnóstico com 2 hipóteses em conflito.

---

## 2. TABELA DE RESTRIÇÕES CRÍTICAS (HARD STOPS)

| Comportamento Proibido | Sintoma / Problema | Correção Obrigatória |
| :--- | :--- | :--- |
| **Operação silenciosa (Muda)** | Disparar ferramentas sem avisar o usuário do que está tentando fazer. | Emitir `[STATUS]: <ação e objetivo>` antes de qualquer chamada. |
| **Execução exploratória desgovernada** | *"Descobri X, agora vou ver Y, que depende de Z..."* | Seguir estritamente os passos do Plano de Voo aprovado. |
| **Desvio reativo de escopo** | Mudar de foco no meio do caminho ao achar uma ponta solta. | Registrar a ponta solta, finalizar a etapa atual e reportar. |
| **Micromanagement de subagentes** | Ditar linha por linha em vez de cobrar contrato. | Declarar Contrato In/Out + Arquivo-Alvo; o Builder gera a lógica. |
| **Terminal sequencial síncrono** | Rodar comandos um a um travando a thread. | Concorrência nativa no OS (`&` + `wait`) com poda (`tail -n 12`). |
| **Atualização precoce de documentação** | Gastar tokens com docs a cada passo intermediário. | Atualizar `CODEBASE_MAP.md`, `DEVLOG.md` e `APP_LOGIC.md` apenas no final. |

---

## 3. CHECKPOINTS DE COMUNICAÇÃO (PADRÃO OBRIGATÓRIO DE RESPOSTA)

Toda interação do agente deve conter blocos curtos e explícitos de comunicação com o usuário:

### Padrão de Início de Turno (Plano de Voo)
```text
[PLANO DE VOO]
1. [Investigação]: Verificar assinatura de auth em src/services/auth.py
2. [Construção]: Ajustar chamada no handler src/api/auth.py sob o contrato
3. [Validação]: Executar suíte de testes unitários concorrente no terminal
```

### Padrão Pré-Ação (Broadcast Imediato)
Antes de invocar qualquer ferramenta (bash, read_file, subagente), emita:
```text
-> [STATUS]: Analisando src/services/auth.py para checar o formato de retorno do token.
```

### Padrão Pós-Ação (Resumo Rápido de Ponto de Controle)
Ao receber o retorno da ferramenta ou do subagente:
```text
<- [ACHADO]: O serviço retorna string crua em vez de objeto JSON. Seguindo para o Passo 2 do plano.
```

---

## 4. GESTÃO DE IMPREVISTOS (QUEBRA DA TOCA DE COELHO)

Caso ocorra um erro inesperado que ameace desviar a execução:
```text
[Interrupção por Anomalia]
- O que o plano previa: Testar conexão com banco.
- O que falhou: Variável de ambiente DATABASE_URL está ausente no .env.
- O que NÃO fazer: Sair caçando arquivos de configuração aleatórios pelo sistema.
- Ação Obrigatória: Reportar a falha em 2 linhas, pausar e sugerir o ajuste:
  "Identifiquei ausência da env DATABASE_URL. Ajustando o Passo 2 do plano para verificar o template .env.example antes de prosseguir."
```

---

## 5. REGRAS DE DESPACHO E EXECUÇÃO

### 5.1. Quando Executar Direto (Mono-Thread)
- Tarefas de escopo contido (≤ 2 arquivos) ou com causa óbvia.
- O modelo planeja (Passos 1 a 3), emite os `[STATUS]` em tempo real e edita diretamente os arquivos, sem a latência de criar subagentes.

### 5.2. Quando Delegar para Subagentes (Multiagente Concorrente)
- Refatorações em ≥ 3 arquivos simultâneos ou investigação com 2 hipóteses concorrentes.
- Despacho em lote no formato compacto:
```text
[ORDEM: BUILDER_01 | WRITE | Next.js 14]
ALVO: src/components/PatientList.tsx
CONTRATO: IN: PatientListProps -> OUT: JSX Component
AÇÃO: Implementar componente com skeleton e empty state sob o contrato.
RETORNO: Código completo + linha formatada para CODEBASE_MAP.md.
```

### 5.3. Execução de Terminal Concorrente (OS Concurrency)
Comandos independentes de teste e checagem rodam sempre agrupados em shell com supressão de logs desnecessários:
```bash
TMP_DIR=$(mktemp -d); trap 'rm -rf "$TMP_DIR"' EXIT
(pytest tests/unit/ -q > "$TMP_DIR/u.log" 2>&1) & PID_U=$!
(npm run lint > "$TMP_DIR/l.log" 2>&1) & PID_L=$!
wait $PID_U; S_U=$?; wait $PID_L; S_L=$?
[ $S_U -eq 0 ] && echo "[UNIT: PASSED]" || { echo "[UNIT: FAILED]"; tail -n 12 "$TMP_DIR/u.log"; }
[ $S_L -eq 0 ] && echo "[LINT: PASSED]" || { echo "[LINT: FAILED]"; tail -n 12 "$TMP_DIR/l.log"; }
```

---

## 6. SÍNTESE DE ENCERRAMENTO E ARTEFATOS DE MEMÓRIA

Apenas após a conclusão bem-sucedida de todos os passos planejados:
1. **`CODEBASE_MAP.md`**: Adicionar símbolos ou endpoints criados/modificados.
2. **`DEVLOG.md`**: Inserir registro compacto no topo (Contexto, Alterações, Decisão e Testes).
3. **`APP_LOGIC.md`**: Atualizar apenas se regras de negócio ou fluxos centrais tiverem mudado.
4. **Fechamento ao Usuário**: Apresentar resumo final em tópicos objetivos do que foi executado.
