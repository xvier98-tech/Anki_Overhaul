# Gerenciador de Prioridades de Baralhos (Deck Priority Manager)

Este addon permite definir prioridades numéricas para baralhos e sub-baralhos, reordenando a fila de cartões novos (`due`) no banco de dados do Anki.

## Características

1. **Estudo em Blocos Fechados**: Cartões de baralhos distintos nunca são misturados. Todos os cartões novos de um baralho são apresentados antes de iniciar o próximo baralho.
2. **Herança Hierárquica Bottom-Up**: Sub-baralhos herdam a prioridade do pai mais próximo, a menos que uma prioridade manual seja definida especificamente para eles.
3. **Desempate com Elemento Aleatório ou Determinístico**:
   - `randomize_same_priority_decks`: Quando `true`, a ordem entre baralhos que possuem o mesmo nível de prioridade é sorteada aleatoriamente a cada reordenação, mas ainda mantendo o bloco 100% contíguo de cada baralho!
   - `randomize_cards_within_deck`: Quando `true`, os cartões novos dentro de um mesmo baralho também são embaralhados.
4. **Compatibilidade Total**: Funciona perfeitamente com o Scheduler V3 (Rust), AnkiMobile (iOS), AnkiDroid (Android) e AnkiWeb.

## Configurações

- `deck_priorities`: Mapeamento de `ID_DO_BARALHO: PRIORIDADE`. Menor valor = maior prioridade (ex: 1 antes de 2).
- `default_priority`: Prioridade padrão atribuída a baralhos sem prioridade definida (padrão: `100`).
- `randomize_same_priority_decks`: Se `true`, desempata baralhos de mesma prioridade de forma aleatória em blocos fechados.
- `randomize_cards_within_deck`: Se `true`, embaralha cartões dentro do próprio baralho.
- `auto_reorder_on_profile_open`: Se `true`, executa a reordenação automaticamente ao carregar o perfil.
- `auto_reorder_on_sync`: Se `true`, executa a reordenação automaticamente após sincronizar com AnkiWeb.
