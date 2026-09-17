# 🔮 Obsidian Addon Suite para Anki Desktop (Anki Overhaul)
> *A suíte tudo-em-um definitiva para estudantes de medicina, concurseiros, poliglotas e usuários de controle: Pesquisador de Imagens Web com Editor Integrado, Pomodoro Adaptativo com Modo Foco, Suporte Total a Gamepads, Temas OLED de Alto Contraste (WCAG 2.1 AA), Sequenciador de Baralhos, Múltipla Escolha e Dashboard Analítico.*

[![Anki Version](https://img.shields.io/badge/Anki-23.10%20--%2025.09+-blue.svg?logo=anki)](https://apps.ankiweb.net/)
[![Python](https://img.shields.io/badge/Python-3.9%20|%203.10%20|%203.11%20|%203.12%20|%203.13-blue.svg?logo=python)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6%20|%20Qt6-brightgreen.svg?logo=qt)](https://www.riverbankcomputing.com/software/pyqt/)
[![Accessibility](https://img.shields.io/badge/Accessibility-WCAG%202.1%20AA-success.svg)](https://www.w3.org/WAI/standards-guidelines/wcag/)
[![Tests](https://img.shields.io/badge/Tests-128%20Passing-success.svg)](tests/)
[![i18n](https://img.shields.io/badge/i18n-PT%20|%20EN%20|%20ES%20|%20FR-orange.svg)](#-internacionaliza%C3%A7%C3%A3o-nativa-i18n)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Índice

- [Visão Geral](#-vis%C3%A3o-geral)
- [Módulos e Funcionalidades](#-m%C3%B3dulos-e-funcionalidades)
  - [1. 🔍 Pesquisador Clínico & Educacional de Imagens](#1--pesquisador-cl%C3%ADnico--educacional-de-imagens)
  - [2. ✏️ Ferramentas de Edição Visual (Setas, Círculos e Recorte)](#2-️-ferramentas-de-edi%C3%A7%C3%A3o-visual-setas-c%C3%ADrculos-e-recorte)
  - [3. 🕒 Histórico Inteligente de Recentes](#3--hist%C3%B3rico-inteligente-de-recentes)
  - [4. 🍅 Pomodoro Adaptativo com Modo Foco (Tela Cheia)](#4--pomodoro-adaptativo-com-modo-foco-tela-cheia)
  - [5. 🎮 Suíte de Acessibilidade Total com Gamepads](#5--su%C3%ADte-de-acessibilidade-total-com-gamepads)
  - [6. 🎨 Temas Escuros OLED & Acessibilidade WCAG 2.1 AA](#6--temas-escuros-oled--acessibilidade-wcag-21-aa)
  - [7. 📊 Modern Stats Dashboard (Global & Por Baralho)](#7--modern-stats-dashboard-global--por-baralho)
  - [8. 🗂️ Sequenciador de Baralhos & Blocos Fechados](#8-️-sequenciador-de-baralhos--blocos-fechados)
  - [9. 📝 Templates de Múltipla Escolha](#9--templates-de-m%C3%BAltipla-escolha)
  - [10. 🌐 AnkiConnect Local Integrado](#10--ankiconnect-local-integrado)
  - [11. 🌍 Internacionalização Nativa (i18n)](#11--internacionaliza%C3%A7%C3%A3o-nativa-i18n)
- [Perfis de Usuários Beneficiados](#-perfis-de-usu%C3%A1rios-beneficiados)
- [Desafios Técnicos & Engenharia de Soluções](#-desafios-t%C3%A9cnicos--engenharia-de-solu%C3%A7%C3%B5es)
- [Instalação e Configuração](#-instala%C3%A7%C3%A3o-e-configura%C3%A7%C3%A3o)
- [Bateria de Testes Automatizados](#-bateria-de-testes-automatizados)

---

## 🌟 Visão Geral

O **Obsidian Addon Suite** nasceu para eliminar as principais fricções encontradas por quem estuda intensamente no Anki Desktop: a lentidão para encontrar e editar imagens de alta qualidade médica ou acadêmica, a fadiga de estudar horas em frente ao monitor com teclado e mouse, o cansaço visual de temas com baixo contraste e a falta de métricas consolidadas sobre o ritmo real de aprendizado.

Integrando **10 subsistemas de alta engenharia** em um único add-on leve, rápido e sem dependências externas pesadas, a suíte transforma o Anki Desktop em uma estação de estudo de padrão profissional.

---

## 🚀 Módulos e Funcionalidades

### 1. 🔍 Pesquisador Clínico & Educacional de Imagens
*Acesse em qualquer card no Editor pressionando `Ctrl+Shift+I` ou clicando no ícone de lupa na barra de ferramentas.*

- **Múltiplos Motores Integrados**:
  - 🌐 **Google Imagens (`udm=2`)**: Acesso direto à grade de imagens web de alta resolução sem carrosséis de IA ou anúncios.
  - 🏛️ **Wikimedia Commons**: Milhões de diagramas anatômicos, mapas e ilustrações científicas de domínio público.
  - 📖 **Wikipédia Artigos**: Extração automática das principais figuras ilustrativas de verbetes enciclopédicos.
  - 🦆 **DuckDuckGo Images**: Fallback resiliente caso haja restrições temporárias de rede.
  - ✨ **Modo Combinado ("Todas as Fontes")**: Agrega e classifica os resultados ordenados por relevância.
- **Expansão Terminológica Radiológica & Médica**:
  - Normaliza termos em português para terminologia médica canônica internacional em inglês (ex: `pancreatite necrotizante tomografia contraste` ➔ `necrotizing pancreatitis contrast-enhanced CT / CECT`).
  - Dispara **busca dual concorrente** (PT + EN) em threads assíncronas para trazer artigos e casos de periódicos médicos de alto impacto (*Radiopaedia*, *PMC/NIH*, *ScienceDirect*, *AJR*).
- **Filtro Anti-Biografia e Anti-Obituário**:
  - Elimina santos, políticos e figuras históricas que faleceram de determinada doença, garantindo que você receba peças anatômicas, fotos clínicas e tomografias em vez de retratos históricos.
- **SafeSearch Anti-Censura Patológica**:
  - Detecta automaticamente consultas com patologia interna, necrose e lesões cirúrgicas, ajustando os parâmetros do scraper para que o motor de busca não oculte exames e cortes patológicos vitais para o estudo médico.
- **Rolagem Infinita Fluida (*Infinite Scroll*)**:
  - Carregamento automático de mais imagens ao rolar até o final da grade, sem travar a interface e sem reiniciar a posição de rolagem.
- **Painel de Zoom & Botão de Fonte (`🌐`)**:
  - Clique em qualquer miniatura para abrir a pré-visualização ampliada com zoom.
  - Botão **`🌐 Abrir página da imagem`**: abre o artigo ou site original no navegador para leitura do contexto clínico/acadêmico da figura.

---

### 2. ✏️ Ferramentas de Edição Visual (Setas, Círculos e Recorte)
*Destaque lesões, aponte estruturas e recorte a área de interesse antes de colar no card.*

- **🏹 Seta Anatômica Vetorial**:
  - Desenho vetorial de setas com pontas proporcionais à espessura e traçado com anti-aliasing nítido em qualquer ângulo.
- **⭕ Círculo / Elipse de Foco**:
  - Marcação de nódulos, órgãos ou conceitos com arrasto dinâmico normalizado em qualquer direção.
- **✂️ Recorte Interativo (*Crop*)**:
  - Seleção retangular com máscara translúcida e contorno tracejado; botão para recortar pixels nativos instantaneamente.
- **🎨 Paleta Clínica de Alto Contraste**:
  - 5 cores vibrantes pré-calibradas: 🔴 Vermelho (`#ef4444`), 🟡 Amarelo (`#eab308`), 🟢 Verde (`#22c55e`), 🔵 Azul (`#38bdf8`), ⚪ Branco (`#ffffff`).
- **📏 Espessuras Rápidas**: Seletor intuitivo entre 2px, 4px, 6px e 8px.
- **↩️ Desfazer (`Ctrl+Z`) & 🔄 Redefinir**: Histórico com reversão passo a passo.
- 💡 **Preservação da Imagem Original no Histórico**:
  - A imagem inserida no cartão contém as suas edições e anotações personalizadas. Porém, a imagem guardada no histórico de recentes permanece **100% original e limpa**, permitindo reutilizá-la no futuro em outros cartões sem anotações prévias indesejadas!

---

### 3. 🕒 Histórico Inteligente de Recentes
- Aba dedicada **"🕒 Recentes"** no diálogo de imagens.
- Mantém em cache local (`user_files/recent_images.json`) as últimas 15 imagens utilizadas nos seus cards.
- Permite reaproveitar uma imagem recém-pesquisada em múltiplos cartões em segundos, com clique simples para zoom ou duplo clique para inserção imediata.

---

### 4. 🍅 Pomodoro Adaptativo com Modo Foco (Tela Cheia)
- **Modo "Soft Break" (Pausa Suave)**:
  - O cronômetro nunca bloqueia a tela no meio de uma pergunta. Ele avisa suavemente e aguarda você avaliar o card atual antes de abrir o intervalo, preservando o raciocínio.
- **Imunidade no Intervalo de Descanso**:
  - As pausas de descanso (`BREAK` e `LONG_BREAK`) rodam livremente de forma contínua até `00:00` sem pausas indevidas por inatividade.
- **Detecção Inteligente de Inatividade & Perda de Foco**:
  - Durante o trabalho (`WORK`), detecta se o usuário ficou ocioso ou mudou para outro aplicativo/janela (ex: redes sociais), pausando o timer e emitindo alerta sonoro configurável.
- **Modo Foco em Tela Cheia (`F11`)**:
  - Maximiza a imersão escondendo barras distratoras e centralizando o card de estudo.
- **Diálogo de Descanso com Overtime & Extensão (+5 min)**:
  - Ao término do intervalo, exibe tela de descanso sugerindo alongamento e água, com botão rápido para adicionar mais 5 minutos ou retomar os estudos imediatamente.
- **Áudio Assíncrono com Latência Zero**:
  - Notificações sonoras embutidas (`.wav`) via `winsound` no Windows, garantindo reprodução instantânea sem interferir no reprodutor de mídia do Anki (`mpv`).

---

### 5. 🎮 Suíte de Acessibilidade Total com Gamepads
*Estude recostado na poltrona, na cama ou no sofá sem tocar no teclado ou mouse. Compatível nativamente com controles de Xbox (XInput), PlayStation (DirectInput), 8BitDo e genéricos USB/Bluetooth.*

- **Revisor de Cartões 100% Mapeável**:
  - Mapeie avaliações (*De novo*, *Difícil*, *Bom*, *Fácil*), *Desfazer* (`Ctrl+Z`), bandeiras (*Flags*), áudios e suspensões.
  - Zona morta radial anti-drift (*radial deadzone*) e resposta a 60Hz.
  - Feedback tátil-visual: botões na tela contraem fisicamente ao serem pressionados no controle.
  - Sons de clique e confirmação ao acionar botões no controle.
- **Atalhos Globais Dedicados**:
  - `pomo_fullscreen`: Alterna tela cheia / modo foco com um botão do controle.
  - `open_settings`: Abre a Central de Configurações do addon direto do controle.
- **Navegação no Diálogo de Descanso do Pomodoro**:
  - Use o analógico (ou D-Pad) para alternar entre **"➕ +5 min no Intervalo"** e **"🚀 Voltar a Estudar"** com anel luminoso dinâmico.
  - Botão **`A`** confirma a escolha; botão **`B`** retoma os estudos imediatamente.
- **Navegação Integral na Central de Configurações**:
  - **`LB` e `RB`**: alternam entre abas (`Geral`, `Temas`, `Dashboard`, `Pomodoro`, `Gamepad`, `Sequenciador`, `Integrações`).
  - **Analógico Esquerdo (`⬆️` / `⬇️`) ou D-Pad**: navega verticalmente pelos itens com auto-scroll e anel de foco destacado em azul ciano.
  - **Botão `A`**: ativa opções (marca/desmarca checkboxes, clica em botões, abre dropdowns).
  - **Analógico Direito (`⬅️` / `➡️`)**: ajusta sliders, barras de opacidade e campos numéricos.
  - **Botão `B`**: fecha dropdowns/listas suspensas se abertas, ou fecha a Central de Configurações se nenhum menu estiver aberto.

---

### 6. 🎨 Temas Escuros OLED & Acessibilidade WCAG 2.1 AA
- **Predefinições Visuais Elegantes**:
  - 🖤 **OLED Dark**: Preto absoluto (`#000000`) para economia de energia em telas OLED/AMOLED e alívio ocular em ambientes escuros.
  - 🌌 **Midnight Obsidian**: Azul espacial profundo com detalhes em ciano e púrpura.
  - 🌲 **Nord Dark**: Paleta ártica suave em tons frios de azul e cinza.
  - 🧛 **Dracula**: Roxo suave clássico com detalhes em rosa e verde.
  - ☀️ **Solarized Dark**: Equilíbrio cromático projetado para longas sessões de leitura.
  - 🛠️ **Personalizado (Custom)**: Ajuste livre de cor primária, superfícies, bordas e destaque (*accent*).
- **Conformidade Matemática WCAG 2.1 AA**:
  - O addon calcula em tempo real a luminância perceptual CIE dos fundos e escolhe automaticamente texto claro ou escuro garantindo contraste superior a 4.5:1.
  - Cores dos botões de facilidade (*Again*, *Hard*, *Good*, *Easy*) e indicadores de status permanecem legíveis mesmo com cores customizadas exóticas.

---

### 7. 📊 Modern Stats Dashboard (Global & Por Baralho)
- **Estatísticas Per-Deck & Globais**:
  - Exibido tanto na tela inicial de baralhos quanto no topo da tela de visão geral (*Overview*) de qualquer deck.
- **Métricas em Tempo Real**:
  - **⚡ Progresso de Hoje**: Cartões estudados, tempo total, ritmo médio (segundos/card, cards/minuto) e taxa de retenção.
  - **⏳ Fila de Revisão**: Contagem clara de novos, aprendizado e revisões devidas, com estimativa para amanhã.
  - **✅ Concluídos**: Novos dominados, repetições de aprendizado, revisões mantidas e cards maduros (≥21 dias).
- **Design com Glassmorphism**:
  - Slider de opacidade para efeito de vidro fosco personalizável e layout adaptável em até 3 colunas.

---

### 8. 🗂️ Sequenciador de Baralhos & Blocos Fechados
- **Estudo em Blocos Contíguos**:
  - Garante que 100% dos cartões novos de um baralho sejam estudados consecutivamente antes de iniciar outro assunto, evitando mistura prejudicial de matérias distintas.
- **Herança Hierárquica Bottom-Up**:
  - Sub-baralhos herdam a prioridade dos baralhos superiores, a menos que uma prioridade manual específica seja definida.
- **Compatibilidade Scheduler V3 & AnkiMobile / AnkiDroid**:
  - Ajusta diretamente os metadados nativos de ordenação (`due`), funcionando perfeitamente em celulares, tablets e no AnkiWeb após a sincronização.

---

### 9. 📝 Templates de Múltipla Escolha
- Modelos de notas incorporados `AllInOne (kprim, mc, sc)`.
- Suporte a múltipla escolha com opções embaralhadas dinamicamente a cada revisão, evitando que você memorize a posição da letra em vez do conceito.
- Correção visual instantânea com destaque verde para respostas certas e vermelho para incorretas.

---

### 10. 🌐 AnkiConnect Local Integrado
- Servidor local HTTP JSON-RPC na porta padrão `8765`.
- Permite integração com **Obsidian** (plugin *Obsidian_to_Anki*), *Yomichan*, extensões do navegador e scripts de automação Python sem necessidade de instalar addons adicionais.

---

### 11. 🌍 Internacionalização Nativa (i18n)
- Suporte nativo completo para **4 idiomas**:
  - 🇧🇷 / 🇵🇹 **Português**
  - 🇺🇸 / 🇬🇧 **English**
  - 🇪🇸 **Español**
  - 🇫🇷 **Français**
- Detecção automática baseada nas preferências do Anki ou seleção manual na aba Geral.

---

## 👥 Perfis de Usuários Beneficiados

| Perfil | Como o Obsidian Addon Suite ajuda |
| :--- | :--- |
| **Estudantes de Medicina & Residentes** | Pesquisa instantânea de tomografias com contraste (CECT), ressonâncias e imagens clínicas na Radiopaedia e PubMed; ferramentas para apontar lesões com setas e círculos; estudo contíguo de matérias pesadas (ex: Cardiologia depois Nefrologia). |
| **Concurseiros & Estudantes de Direito / Exatas** | Pomodoro com Soft Break que não interrompe resoluções longas de questões; metas diárias e cards/minuto visíveis no Dashboard; blocos fechados para dominar tópicos específicos do edital. |
| **Estudantes de Idiomas & Poliglotas** | AnkiConnect para envio direto de frases do Obsidian ou navegador; suporte a áudio contínuo e repetição de pronúncia rápida via gamepad; templates de múltipla escolha. |
| **Gamers, Usuários de Controle & Ergonomia** | Possibilidade de revisar 500+ cards por dia deitado ou recostado, navegando menus, abas e diálogos 100% pelo controle de videogame com feedback sonoro e tátil. |
| **Pessoas com Fadiga Visual ou TDAH** | Modo Foco em tela cheia (`F11`) que isola qualquer distração visual; tema OLED com contraste calibrado; alerta sonoro quando a atenção se dispersa fora do Anki durante o trabalho. |

---

## 🛠️ Desafios Técnicos & Engenharia de Soluções

Durante o desenvolvimento do addon, diversos obstáculos técnicos específicos do ecossistema Qt/Anki foram superados com arquitetura sob medida:

1. **Latência de Áudio e Conflito com MPV no Windows**:
   - *Desafio*: Players convencionais travavam se o Anki estivesse minimizado ou bloqueavam o `mpv` nativo de pronúncia.
   - *Solução*: Implementação com `winsound.PlaySound(..., SND_ASYNC | SND_FILENAME)`, fornecendo latência zero, consumo nulo de CPU e imunidade total ao player de mídia nativo.
2. **Bypass de Falso Positivo na Aba de Recentes (`bool(QLayout) == False`)**:
   - *Desafio*: Em PyQt6, a classe `QLayout` implementa o protocolo de sequência (`__len__`). Quando vazio, `bool(empty_layout)` avalia como `False` no Python, causando bypass precoce no código que preenchia os cards.
   - *Solução*: Substituição por verificação estrita de identidade de ponteiro (`if getattr(self, "recent_grid_layout", None) is None:`), restaurando a renderização imediata da grade.
3. **Navegação Modal Desacoplada para Gamepads**:
   - *Desafio*: Quando um diálogo modal (como a tela de descanso ou as configurações) abria, o despachante de eventos de controle perdia a rota ou tentava disparar atalhos do revisor em background.
   - *Solução*: Sistema de isolamento dinâmico no `GamepadActionDispatcher` que detecta a janela modal ativa e delega os eventos analógicos e botões diretamente para o controlador do diálogo.
4. **Proteção de Licença e Censura em Consultas Clínicas**:
   - *Desafio*: Consultas médicas com palavras como "necrotizante" sofriam restrição pesada de SafeSearch nos motores de busca web.
   - *Solução*: Detector semântico de termos patológicos que relaxa o filtro exclusivamente para o domínio clínico, priorizando portais de autoridade médica.

---

## 📥 Instalação e Configuração

### Método 1: Instalação Manual (Recomendado para Desenvolvedores)
1. Abra a pasta de addons do seu Anki:
   - **Windows**: `%APPDATA%\Anki2\addons21\`
   - **macOS**: `~/Library/Application Support/Anki2/addons21/`
   - **Linux**: `~/.local/share/Anki2/addons21/`
2. Clone este repositório para uma pasta chamada `Obsidian Addon`:
   ```bash
   git clone https://github.com/xvier98-tech/Anki_Overhaul.git "Obsidian Addon"
   ```
3. Reinicie o Anki Desktop.

### Atalhos Principais
- `Ctrl + Shift + I`: Abrir Buscador de Imagens Clínicas e Educacionais (no Editor de Cards).
- `F11` (ou atalho no gamepad): Alternar Modo Foco em Tela Cheia.
- `Alt + P`: Iniciar / Pausar Pomodoro.
- `Alt + S`: Pular para o Intervalo.
- `Alt + R`: Reiniciar Etapa do Pomodoro.

---

## 🧪 Bateria de Testes Automatizados

O projeto conta com **128 testes unitários e de integração** automatizados e projetados para rodar de forma *headless* (inclusive em ambientes sem servidor gráfico):

```bash
python -m unittest discover -s tests
```

Todos os testes validam matemática de cores, trigonometria de setas vetoriais, parsing de motores de busca, integridade de sessões do Pomodoro e navegabilidade com controles de videogame.

---

## 📄 Licença

Distribuído sob a licença **MIT**. Consulte `LICENSE` para mais informações.
