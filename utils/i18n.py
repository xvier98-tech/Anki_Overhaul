# -*- coding: utf-8 -*-
"""
Internationalization (i18n) system for Obsidian Addon Suite.
Supported languages:
- English ('en') - Default primary language and universal fallback for any unsupported language (e.g. Polish, German, etc.)
- Portuguese ('pt') - Unified for both Brazilian and European Portuguese (pt_BR, pt_PT)
- Spanish ('es') - Spanish (es_ES, es_419)
- French ('fr') - French (fr_FR, fr_CA)
"""

from typing import Dict, Any, Optional
import os

try:
    from aqt import mw
    from PyQt6.QtCore import QLocale
except ImportError:
    mw = None
    QLocale = None

try:
    from .config_manager import get_module_config
except (ImportError, ValueError):
    try:
        from utils.config_manager import get_module_config
    except ImportError:
        def get_module_config(mod_name: str) -> Dict[str, Any]:
            return {}

_override_language: Optional[str] = None

# Comprehensive Translation Catalog
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # --- Language Names ---
    "lang_auto": {
        "en": "🌐 Automatic (Anki Language)",
        "pt": "🌐 Automático (Idioma do Anki)",
        "es": "🌐 Automático (Idioma de Anki)",
        "fr": "🌐 Automatique (Langue d'Anki)",
    },
    "lang_en": {
        "en": "🇺🇸 English (Default)",
        "pt": "🇺🇸 English (Default)",
        "es": "🇺🇸 English (Default)",
        "fr": "🇺🇸 English (Default)",
    },
    "lang_pt": {
        "en": "🇧🇷 / 🇵🇹 Português",
        "pt": "🇧🇷 / 🇵🇹 Português",
        "es": "🇧🇷 / 🇵🇹 Português",
        "fr": "🇧🇷 / 🇵🇹 Português",
    },
    "lang_es": {
        "en": "🇪🇸 Español",
        "pt": "🇪🇸 Español",
        "es": "🇪🇸 Español",
        "fr": "🇪🇸 Español",
    },
    "lang_fr": {
        "en": "🇫🇷 Français",
        "pt": "🇫🇷 Français",
        "es": "🇫🇷 Français",
        "fr": "🇫🇷 Français",
    },

    # --- Settings Hub Header & Tabs ---
    "hub_title": {
        "en": "⚙️ Obsidian Addon Suite - Settings Hub",
        "pt": "⚙️ Obsidian Addon Suite - Central de Configurações",
        "es": "⚙️ Obsidian Addon Suite - Centro de Ajustes",
        "fr": "⚙️ Obsidian Addon Suite - Centre de Configuration",
    },
    "hub_banner_title": {
        "en": "🔮 <b>Obsidian Addon Suite</b> — Unified Control Panel",
        "pt": "🔮 <b>Obsidian Addon Suite</b> — Painel de Controle Unificado",
        "es": "🔮 <b>Obsidian Addon Suite</b> — Panel de Control Unificado",
        "fr": "🔮 <b>Obsidian Addon Suite</b> — Panneau de Contrôle Unifié",
    },
    "tab_general": {
        "en": "🌐 General",
        "pt": "🌐 Geral",
        "es": "🌐 General",
        "fr": "🌐 Général",
    },
    "tab_theme": {
        "en": "🎨 Themes & Colors",
        "pt": "🎨 Temas & Cores",
        "es": "🎨 Temas y Colores",
        "fr": "🎨 Thèmes & Couleurs",
    },
    "tab_dashboard": {
        "en": "📊 Modern Dashboard",
        "pt": "📊 Modern Dashboard",
        "es": "📊 Modern Dashboard",
        "fr": "📊 Tableau de Bord Moderne",
    },
    "tab_pomodoro": {
        "en": "🍅 Pomodoro & Audio",
        "pt": "🍅 Pomodoro & Áudio",
        "es": "🍅 Pomodoro y Audio",
        "fr": "🍅 Pomodoro & Audio",
    },
    "tab_gamepad": {
        "en": "🎮 Gamepad & Controls",
        "pt": "🎮 Gamepad & Controles",
        "es": "🎮 Gamepad y Mandos",
        "fr": "🎮 Manette & Contrôles",
    },
    "tab_priority": {
        "en": "🗂️ Sequencer",
        "pt": "🗂️ Sequenciador",
        "es": "🗂️ Secuenciador",
        "fr": "🗂️ Séquenceur",
    },
    "tab_integrations": {
        "en": "🔌 Integrations",
        "pt": "🔌 Integrações",
        "es": "🔌 Integraciones",
        "fr": "🔌 Intégrations",
    },

    # --- General Tab ---
    "general_interface_desc": {
        "en": "Select the language used across the addon dialogs, notifications, and floating widgets. 'Automatic' follows Anki's main language (with English as default for other languages).",
        "pt": "Selecione o idioma utilizado nas janelas, notificações e widgets do addon. 'Automático' segue o idioma do Anki (com inglês como padrão para outros idiomas).",
        "es": "Selecciona el idioma utilizado en las ventanas, notificaciones y widgets del addon. 'Automático' sigue el idioma de Anki (con inglés como predeterminado para otros idiomas).",
        "fr": "Sélectionnez la langue utilisée dans les fenêtres, notifications et widgets de l'extension. 'Automatique' suit la langue d'Anki (avec l'anglais par défaut pour les autres langues).",
    },
    "general_interface_lang": {
        "en": "Addon Interface Language:",
        "pt": "Idioma da Interface do Addon:",
        "es": "Idioma de la Interfaz del Addon:",
        "fr": "Langue de l'Interface de l'Extension :",
    },

    # --- Themes Tab ---
    "theme_enable_chk": {
        "en": "Enable Global Color Theming in Anki",
        "pt": "Ativar Personalização Global de Cores no Anki",
        "es": "Activar Personalización Global de Colores en Anki",
        "fr": "Activer la Personnalisation Globale des Couleurs dans Anki",
    },
    "theme_palette_grp": {
        "en": "Color Palette & Visual Style",
        "pt": "Paleta de Cores e Estilo Visual",
        "es": "Paleta de Colores y Estilo Visual",
        "fr": "Palette de Couleurs et Style Visuel",
    },
    "theme_preset_lbl": {
        "en": "Preset Theme:",
        "pt": "Tema Predefinido:",
        "es": "Tema Predefinido:",
        "fr": "Thème Prédéfini :",
    },
    "theme_custom_option": {
        "en": "🛠️ Custom Theme",
        "pt": "🛠️ Personalizado (Custom)",
        "es": "🛠️ Personalizado (Custom)",
        "fr": "🛠️ Personnalisé (Custom)",
    },
    "theme_custom_grp": {
        "en": "Custom Colors (Real-Time Adjustment)",
        "pt": "Cores Customizadas (Ajuste em Tempo Real)",
        "es": "Colores Personalizados (Ajuste en Tiempo Real)",
        "fr": "Couleurs Personnalisées (Ajustement en Temps Réel)",
    },
    "theme_bg_primary": {
        "en": "Main Window Background:",
        "pt": "Fundo Principal da Janela:",
        "es": "Fondo Principal de la Ventana:",
        "fr": "Fond Principal de la Fenêtre :",
    },
    "theme_bg_card": {
        "en": "Cards & Panels Background:",
        "pt": "Fundo dos Cards e Painéis:",
        "es": "Fondo de Tarjetas y Paneles:",
        "fr": "Fond des Cartes et Panneaux :",
    },
    "theme_accent": {
        "en": "Accent Color / Buttons:",
        "pt": "Cor de Destaque / Botões:",
        "es": "Color de Resalte / Botones:",
        "fr": "Couleur d'Accentuation / Boutons :",
    },
    "theme_text_primary": {
        "en": "Primary Text:",
        "pt": "Texto Principal:",
        "es": "Texto Principal:",
        "fr": "Texte Principal :",
    },
    "theme_text_secondary": {
        "en": "Secondary Text:",
        "pt": "Texto Secundário:",
        "es": "Texto Secundario:",
        "fr": "Texte Secondaire :",
    },
    "theme_border": {
        "en": "Card Borders:",
        "pt": "Bordas dos Cards:",
        "es": "Bordes de Tarjetas:",
        "fr": "Bordures des Cartes :",
    },
    "theme_new": {
        "en": "New Cards Color:",
        "pt": "Cor de Novos Cards:",
        "es": "Color de Tarjetas Nuevas:",
        "fr": "Couleur des Nouvelles Cartes :",
    },
    "theme_learn": {
        "en": "Learning Color:",
        "pt": "Cor de Aprendizado:",
        "es": "Color de Aprendizaje:",
        "fr": "Couleur d'Apprentissage :",
    },
    "theme_review": {
        "en": "Review Color:",
        "pt": "Cor de Revisão:",
        "es": "Color de Repaso:",
        "fr": "Couleur de Révision :",
    },
    "theme_ans_grp": {
        "en": "🎨 Reviewer Answer Button Colors",
        "pt": "🎨 Cores dos Botões de Resposta (Reviewer)",
        "es": "🎨 Colores de los Botones de Respuesta",
        "fr": "🎨 Couleurs des Boutons de Réponse",
    },
    "theme_ans_enable": {
        "en": "Enable Custom Colors on Answer Buttons",
        "pt": "Ativar Cores Personalizadas nos Botões de Resposta",
        "es": "Activar Colores Personalizados en Botones de Respuesta",
        "fr": "Activer les Couleurs Personnalisées sur les Boutons de Réponse",
    },
    "theme_ans_again": {
        "en": "🔴 Again (1):",
        "pt": "🔴 De novo (1):",
        "es": "🔴 Otra vez (1):",
        "fr": "🔴 À revoir (1) :",
    },
    "theme_ans_hard": {
        "en": "🟤 Hard (2):",
        "pt": "🟤 Difícil (2):",
        "es": "🟤 Difícil (2):",
        "fr": "🟤 Difficile (2) :",
    },
    "theme_ans_good": {
        "en": "🟢 Good (3):",
        "pt": "🟢 Bom (3):",
        "es": "🟢 Bien (3):",
        "fr": "🟢 Correct (3) :",
    },
    "theme_ans_easy": {
        "en": "🔵 Easy (4):",
        "pt": "🔵 Fácil (4):",
        "es": "🔵 Fácil (4):",
        "fr": "🔵 Facile (4) :",
    },
    "theme_ans_scale": {
        "en": "Button Size Scale:",
        "pt": "Tamanho dos Botões (Escala):",
        "es": "Tamaño de Botones (Escala):",
        "fr": "Échelle de Taille des Boutons :",
    },

    # --- Dashboard Tab & Renderer ---
    "dash_enable_chk": {
        "en": "Enable Modern Dashboard",
        "pt": "Ativar Modern Dashboard",
        "es": "Activar Modern Dashboard",
        "fr": "Activer le Tableau de Bord Moderne",
    },
    "dash_cards_grp": {
        "en": "Visible Cards & Sections",
        "pt": "Cards & Seções Visíveis",
        "es": "Tarjetas y Secciones Visibles",
        "fr": "Cartes et Sections Visibles",
    },
    "dash_show_goals": {
        "en": "Daily Goals & Daily Focus",
        "pt": "Metas Diárias & Foco do Dia",
        "es": "Metas Diarias y Enfoque del Día",
        "fr": "Objectifs Quotidiens et Focus du Jour",
    },
    "dash_show_comp": {
        "en": "Deck Composition (New / Learning / Review)",
        "pt": "Composição do Baralho (Novos / Aprendizado / Revisão)",
        "es": "Composición del Mazo (Nuevas / Aprendiendo / Repaso)",
        "fr": "Composition du Paquet (Nouvelles / Apprentissage / Révision)",
    },
    "dash_show_today": {
        "en": "Today's Progress (Retention & Total Studied)",
        "pt": "Progresso de Hoje (Retenção & Total Estudado)",
        "es": "Progreso de Hoy (Retención y Total Estudiado)",
        "fr": "Progrès du Jour (Rétention & Total Étudié)",
    },
    "dash_show_remaining": {
        "en": "Remaining Cards in Today's Queue",
        "pt": "Cartões Restantes na Fila de Hoje",
        "es": "Tarjetas Restantes en la Cola de Hoy",
        "fr": "Cartes Restantes dans la File d'Aujourd'hui",
    },
    "dash_show_done": {
        "en": "Summary of Completed Cards Today",
        "pt": "Resumo de Concluídos Hoje",
        "es": "Resumen de Completadas Hoy",
        "fr": "Résumé des Cartes Complétées Aujourd'hui",
    },
    "dash_place_grp": {
        "en": "Display Location & Layout",
        "pt": "Local de Exibição & Layout",
        "es": "Ubicación de Visualización y Diseño",
        "fr": "Emplacement d'Affichage et Disposition",
    },
    "dash_on_overview": {
        "en": "Display on Deck Overview Screen",
        "pt": "Exibir na Tela de Overview do Baralho",
        "es": "Mostrar en la Pantalla de Overview del Mazo",
        "fr": "Afficher sur l'Écran d'Aperçu du Paquet",
    },
    "dash_on_browser": {
        "en": "Display on Deck Browser (Below Decks)",
        "pt": "Exibir no Deck Browser (Abaixo dos Baralhos)",
        "es": "Mostrar en el Explorador de Mazos (Debajo de Mazos)",
        "fr": "Afficher dans le Navigateur de Paquets (Sous les Paquets)",
    },
    "dash_hide_native": {
        "en": "Hide native Anki message banner",
        "pt": "Ocultar barra nativa de mensagens do Anki",
        "es": "Ocultar barra nativa de mensajes de Anki",
        "fr": "Masquer la bannière de messages native d'Anki",
    },
    "dash_columns": {
        "en": "Number of Columns in Layout:",
        "pt": "Quantidade de Colunas no Layout:",
        "es": "Cantidad de Columnas en el Diseño:",
        "fr": "Nombre de Colonnes dans la Disposition :",
    },
    "dash_global_collection": {
        "en": "📊 Global Collection",
        "pt": "📊 Coleção Global",
        "es": "📊 Colección Global",
        "fr": "📊 Collection Globale",
    },
    "dash_daily_goals": {
        "en": "Daily Goals",
        "pt": "Metas Diárias",
        "es": "Metas Diarias",
        "fr": "Objectifs Quotidiens",
    },
    "dash_native_config": {
        "en": "Native Preset",
        "pt": "Config Nativa",
        "es": "Config Nativa",
        "fr": "Config Native",
    },
    "dash_new_label": {
        "en": "🌱 New:",
        "pt": "🌱 Novos:",
        "es": "🌱 Nuevas:",
        "fr": "🌱 Nouvelles :",
    },
    "dash_rev_label": {
        "en": "📅 Reviews:",
        "pt": "📅 Revisões:",
        "es": "📅 Repasos:",
        "fr": "📅 Révisions :",
    },
    "dash_streak": {
        "en": "🔥 Streak: <b>{days} days in a row</b>",
        "pt": "🔥 Sequência: <b>{days} dias seguidos</b>",
        "es": "🔥 Racha: <b>{days} días seguidos</b>",
        "fr": "🔥 Série : <b>{days} jours consécutifs</b>",
    },
    "dash_today_progress": {
        "en": "Today's Progress",
        "pt": "Progresso de Hoje",
        "es": "Progreso de Hoy",
        "fr": "Progrès du Jour",
    },
    "dash_cards_completed_today": {
        "en": "Cards Completed Today",
        "pt": "Cartões Concluídos Hoje",
        "es": "Tarjetas Completadas Hoy",
        "fr": "Cartes Complétées Aujourd'hui",
    },
    "dash_done_badge": {
        "en": "{count} done",
        "pt": "{count} feitas",
        "es": "{count} hechas",
        "fr": "{count} faites",
    },
    "dash_time_spent": {
        "en": "⏱️ Time Spent",
        "pt": "⏱️ Tempo Gasto",
        "es": "⏱️ Tiempo Empleado",
        "fr": "⏱️ Temps Passé",
    },
    "dash_retention": {
        "en": "🎯 Retention",
        "pt": "🎯 Retenção",
        "es": "🎯 Retención",
        "fr": "🎯 Rétention",
    },
    "dash_pace": {
        "en": "🏃 Pace",
        "pt": "🏃 Ritmo",
        "es": "🏃 Ritmo",
        "fr": "🏃 Rythme",
    },
    "dash_speed": {
        "en": "📈 Speed",
        "pt": "📈 Velocidade",
        "es": "📈 Velocidad",
        "fr": "📈 Vitesse",
    },
    "dash_queue_today": {
        "en": "Today's Queue",
        "pt": "Fila de Hoje",
        "es": "Cola de Hoy",
        "fr": "File du Jour",
    },
    "dash_to_clear": {
        "en": "{count} to clear",
        "pt": "{count} para zerar",
        "es": "{count} para terminar",
        "fr": "{count} à terminer",
    },
    "dash_session_pending": {
        "en": "Pending in Today's Session",
        "pt": "Pendentes na Sessão de Hoje",
        "es": "Pendientes en la Sesión de Hoy",
        "fr": "En attente dans la Session d'Aujourd'hui",
    },
    "dash_new_today": {
        "en": "🌱 New Today",
        "pt": "🌱 Novos Hoje",
        "es": "🌱 Nuevas Hoy",
        "fr": "🌱 Nouvelles Aujourd'hui",
    },
    "dash_learning": {
        "en": "🔄 Learning",
        "pt": "🔄 Aprendizado",
        "es": "🔄 Aprendiendo",
        "fr": "🔄 Apprentissage",
    },
    "dash_review_today": {
        "en": "📅 Review Today",
        "pt": "📅 Revisão Hoje",
        "es": "📅 Repaso Hoy",
        "fr": "📅 Révision Aujourd'hui",
    },
    "dash_tomorrow": {
        "en": "🔮 Tomorrow",
        "pt": "🔮 Amanhã",
        "es": "🔮 Mañana",
        "fr": "🔮 Demain",
    },
    "dash_deck_library": {
        "en": "Deck Collection",
        "pt": "Acervo Total",
        "es": "Colección Total",
        "fr": "Collection Totale",
    },
    "dash_cards_badge": {
        "en": "{count} cards",
        "pt": "{count} cards",
        "es": "{count} tarjetas",
        "fr": "{count} cartes",
    },
    "dash_maturity_rate": {
        "en": "Maturity Rate (≥ 21d)",
        "pt": "Grau de Maturação (≥ 21d)",
        "es": "Grado de Maduración (≥ 21d)",
        "fr": "Taux de Maturation (≥ 21j)",
    },
    "dash_mature": {
        "en": "🌳 Mature",
        "pt": "🌳 Maduros",
        "es": "🌳 Maduras",
        "fr": "🌳 Mûres",
    },
    "dash_young": {
        "en": "🌿 Young (&lt;21d)",
        "pt": "🌿 Jovens (&lt;21d)",
        "es": "🌿 Jóvenes (&lt;21d)",
        "fr": "🌿 Jeunes (&lt;21j)",
    },
    "dash_unseen": {
        "en": "🌱 Unseen",
        "pt": "🌱 Não Vistos",
        "es": "🌱 No Vistas",
        "fr": "🌱 Non Vues",
    },
    "dash_suspended": {
        "en": "💤 Suspended",
        "pt": "💤 Suspensos",
        "es": "💤 Suspendidas",
        "fr": "💤 Suspendues",
    },
    "dash_completed_today": {
        "en": "Completed Today",
        "pt": "Concluídos Hoje",
        "es": "Completadas Hoy",
        "fr": "Terminées Aujourd'hui",
    },
    "dash_breakdown": {
        "en": "Breakdown",
        "pt": "Detalhamento",
        "es": "Desglose",
        "fr": "Détails",
    },
    "dash_new_learned": {
        "en": "🌱 New Learned",
        "pt": "🌱 Novos Aprendidos",
        "es": "🌱 Nuevas Aprendidas",
        "fr": "🌱 Nouvelles Apprises",
    },
    "dash_learn_reps": {
        "en": "🔄 Learn Reps",
        "pt": "🔄 Repetições Aprend.",
        "es": "🔄 Repeticiones Aprend.",
        "fr": "🔄 Répétitions Appr.",
    },
    "dash_reviews_done": {
        "en": "📝 Reviews Done",
        "pt": "📝 Revisões Feitas",
        "es": "📝 Repasos Hechos",
        "fr": "📝 Révisions Faites",
    },
    "dash_mature_reviewed": {
        "en": "🌳 Mature Reviewed",
        "pt": "🌳 Maduros Revisados",
        "es": "🌳 Maduras Repasadas",
        "fr": "🌳 Mûres Révisées",
    },
    "dash_errors_again": {
        "en": "❌ Lapses (Again): <b>{count}</b>",
        "pt": "❌ Erros (Again): <b>{count}</b>",
        "es": "❌ Fallos (Otra vez): <b>{count}</b>",
        "fr": "❌ Échecs (À revoir) : <b>{count}</b>",
    },
    "dash_fail_pct": {
        "en": "({rate:.1f}% lapses)",
        "pt": "({rate:.1f}% falhas)",
        "es": "({rate:.1f}% fallos)",
        "fr": "({rate:.1f}% d'échecs)",
    },

    # --- Pomodoro Tab & FAB ---
    "pomo_enable_chk": {
        "en": "Enable Pomodoro Timer & Floating Action Button (FAB)",
        "pt": "Ativar Pomodoro Timer & Floating Action Button (FAB)",
        "es": "Activar Temporizador Pomodoro y Botón Flotante (FAB)",
        "fr": "Activer le Minuteur Pomodoro et le Bouton Flottant (FAB)",
    },
    "pomo_durations_grp": {
        "en": "Focus & Break Durations",
        "pt": "Durações de Foco e Intervalo",
        "es": "Duraciones de Enfoque y Descanso",
        "fr": "Durées de Concentration et de Pause",
    },
    "pomo_focus_min": {
        "en": "Focus (min):",
        "pt": "Foco (min):",
        "es": "Enfoque (min):",
        "fr": "Concentration (min) :",
    },
    "pomo_short_break_min": {
        "en": "Short Break (min):",
        "pt": "Pausa Curta (min):",
        "es": "Descanso Corto (min):",
        "fr": "Pause Courte (min) :",
    },
    "pomo_long_break_min": {
        "en": "Long Break (min):",
        "pt": "Pausa Longa (min):",
        "es": "Descanso Largo (min):",
        "fr": "Pause Longue (min) :",
    },
    "pomo_rounds_to_long_break": {
        "en": "Rounds to Long Break:",
        "pt": "Rodadas até Pausa Longa:",
        "es": "Rondas hasta Pausa Larga:",
        "fr": "Cycles avant Pause Longue :",
    },
    "pomo_flow_grp": {
        "en": "Card-Adaptive Flow Mechanics",
        "pt": "Mecânica Adaptada aos Cards",
        "es": "Mecánica Adaptada a las Tarjetas",
        "fr": "Mécanique Adaptée aux Cartes",
    },
    "pomo_soft_break_chk": {
        "en": "Soft Break Mode (Alerts at time end, automatically pops up break after card answer)",
        "pt": "Modo Soft Break (Avisa ao fim do tempo e abre o intervalo automaticamente após responder o card)",
        "es": "Modo Soft Break (Avisa al terminar el tiempo y abre el descanso automáticamente tras responder)",
        "fr": "Mode Soft Break (Alerte à la fin du temps et ouvre la pause automatiquement après avoir répondu)",
    },
    "pomo_inactivity_chk": {
        "en": "Auto-Pause on Inactivity (prevents timer advance when stepping away)",
        "pt": "Pausa Automática por Inatividade (evita contagem se o usuário se afastar)",
        "es": "Pausa Automática por Inactividad (evita conteo si te alejas)",
        "fr": "Pause Automatique en cas d'Inactivité (évite le décompte en cas d'absence)",
    },
    "pomo_inactivity_sec": {
        "en": "Inactivity Timeout (seconds):",
        "pt": "Tempo Limite de Inatividade (segundos):",
        "es": "Tiempo Límite de Inactividad (segundos):",
        "fr": "Délai d'Inactivité (secondes) :",
    },
    "pomo_auto_pause_chk": {
        "en": "Auto-Pause outside Reviewer (Browser, Add Cards, etc.)",
        "pt": "Pausa Automática ao sair do Reviewer (Browser, Add, etc.)",
        "es": "Pausa Automática al salir del Reviewer (Explorador, Añadir, etc.)",
        "fr": "Pause Automatique en dehors du Reviewer (Navigateur, Ajout, etc.)",
    },
    "pomo_focus_loss_chk": {
        "en": "Pause & alert when clicking outside Anki (Anti-Distraction / Focus Loss)",
        "pt": "Pausar e alertar ao clicar fora do Anki (Anti-Distração / Perda de Foco)",
        "es": "Pausar y alertar al hacer clic fuera de Anki (Anti-Distracción)",
        "fr": "Pause et alerte en cas de clic hors d'Anki (Anti-Distraction)",
    },
    "pomo_hide_cursor_chk": {
        "en": "Auto-hide mouse cursor during inactivity in Focus Mode",
        "pt": "Ocultar cursor do mouse por inatividade durante o Modo Foco",
        "es": "Ocultar cursor del ratón por inactividad durante el Modo Enfoque",
        "fr": "Masquer le curseur de souris en cas d'inactivité en Mode Concentration",
    },
    "pomo_auto_advance_grp": {
        "en": "⏩ Smart Auto-Advance (Focus Mode)",
        "pt": "⏩ Passagem Automática de Cards (Modo Foco)",
        "es": "⏩ Avance Automático Inteligente (Modo Enfoque)",
        "fr": "⏩ Avancement Automatique Intelligent (Mode Concentration)",
    },
    "pomo_auto_advance_chk": {
        "en": "Enable Auto-Advance for Questions and Answers during Focus",
        "pt": "Ativar Passagem Automática de Perguntas e Respostas durante o Foco",
        "es": "Activar Avance Automático de Preguntas y Respuestas durante el Enfoque",
        "fr": "Activer l'Avancement Automatique des Questions et Réponses pendant la Concentration",
    },
    "pomo_auto_show_ans_sec": {
        "en": "Question Timeout (seconds to reveal answer):",
        "pt": "Tempo Limite da Pergunta (segundos para ver resposta):",
        "es": "Tiempo Límite de Pregunta (segundos para mostrar respuesta):",
        "fr": "Délai de la Question (secondes pour afficher la réponse) :",
    },
    "pomo_auto_ans_again_sec": {
        "en": "Answer Timeout (seconds before grading 'Again' if question timed out):",
        "pt": "Tempo da Resposta (segundos antes de marcar 'Errei' se a pergunta estourou):",
        "es": "Tiempo de Respuesta (segundos antes de marcar 'Repetir' si la pregunta expiró):",
        "fr": "Délai de Réponse (secondes avant d'évaluer 'À revoir' si la question a expiré) :",
    },
    "pomo_auto_advance_hint": {
        "en": "ℹ️ If the question times out, the answer will automatically grade as 'Again'. If you reveal the answer manually, no timer is applied. Auto-advance pauses automatically during inactivity.",
        "pt": "ℹ️ Se o tempo da pergunta estourar, a resposta será avaliada automaticamente como 'Errei'. Se você revelar a pergunta manualmente, a resposta não será temporizada. Pausa automaticamente por inatividade.",
        "es": "ℹ️ Si expira el tiempo de la pregunta, se calificará automáticamente como 'Repetir'. Si revelas la pregunta manualmente, la respuesta no se temporiza. Se pausa por inactividad.",
        "fr": "ℹ️ Si le délai de la question expire, elle sera notée 'À revoir'. Si vous affichez la réponse manuellement, aucun décompte n'est appliqué. Pause automatique en cas d'inactivité.",
    },
    "pomo_sound_grp": {
        "en": "🔔 Sound Alerts & Alarm Notifications",
        "pt": "🔔 Alertas Sonoros e Notificações de Alarme",
        "es": "🔔 Alertas Sonoras y Notificaciones de Alarma",
        "fr": "🔔 Alertes Sonores et Notifications d'Alarme",
    },
    "pomo_sound_enable": {
        "en": "Play sound when Pomodoro / Break finishes",
        "pt": "Tocar som ao terminar o Pomodoro / Intervalo",
        "es": "Reproducir sonido al finalizar Pomodoro o Descanso",
        "fr": "Jouer un son à la fin du Pomodoro ou de la Pause",
    },
    "pomo_sound_work": {
        "en": "Sound on Focus End:",
        "pt": "Som ao Fim do Foco:",
        "es": "Sonido al Final del Enfoque:",
        "fr": "Son à la Fin de la Concentration :",
    },
    "pomo_sound_break": {
        "en": "Sound on Break End:",
        "pt": "Som ao Fim do Intervalo:",
        "es": "Sonido al Final del Descanso:",
        "fr": "Son à la Fin de la Pause :",
    },
    "pomo_sound_alarm": {
        "en": "Alarm Sound (Focus Loss & Inactivity):",
        "pt": "Sinal de Alarme (Perda de Foco & Inatividade):",
        "es": "Señal de Alarma (Pérdida de Enfoque e Inactividad):",
        "fr": "Signal d'Alarme (Perte de Focus & Inactivité) :",
    },
    "snd_bell": {
        "en": "🔔 Soft Chime / Bell",
        "pt": "🔔 Sino / Chime Suave",
        "es": "🔔 Campana Suave",
        "fr": "🔔 Carillon Doux",
    },
    "snd_school_bell": {
        "en": "🏫 School Bell",
        "pt": "🏫 Sinal / Campainha Escolar",
        "es": "🏫 Timbre Escolar",
        "fr": "🏫 Cloche d'École",
    },
    "snd_analog_alarm": {
        "en": "⏰ Analog Alarm Clock",
        "pt": "⏰ Alarme de Relógio Analógico",
        "es": "⏰ Despertador Analógico",
        "fr": "⏰ Réveil Analogique",
    },
    "snd_digital_alarm": {
        "en": "📟 Digital Beep-Beep Alarm",
        "pt": "📟 Alarme de Relógio Digital (Bip-Bip)",
        "es": "📟 Alarma Digital (Bip-Bip)",
        "fr": "📟 Alarme Digitale (Bip-Bip)",
    },
    "snd_system": {
        "en": "🎵 System Default Sound",
        "pt": "🎵 Som Padrão do Sistema",
        "es": "🎵 Sonido Predeterminado del Sistema",
        "fr": "🎵 Son Système par Défaut",
    },
    "snd_custom": {
        "en": "📁 Custom File (MP3/WAV)...",
        "pt": "📁 Arquivo Personalizado (MP3/WAV)...",
        "es": "📁 Archivo Personalizado (MP3/WAV)...",
        "fr": "📁 Fichier Personnalisé (MP3/WAV)...",
    },
    "btn_test": {
        "en": "▶️ Test",
        "pt": "▶️ Testar",
        "es": "▶️ Probar",
        "fr": "▶️ Tester",
    },
    "btn_browse": {
        "en": "📁 Browse...",
        "pt": "📁 Procurar...",
        "es": "📁 Examinar...",
        "fr": "📁 Parcourir...",
    },
    "snd_file_focus": {
        "en": "File (Focus):",
        "pt": "Arquivo (Foco):",
        "es": "Archivo (Enfoque):",
        "fr": "Fichier (Concentration) :",
    },
    "snd_file_break": {
        "en": "File (Break):",
        "pt": "Arquivo (Intervalo):",
        "es": "Archivo (Descanso):",
        "fr": "Fichier (Pause) :",
    },
    "snd_file_alarm": {
        "en": "File (Alarm):",
        "pt": "Arquivo (Alarme):",
        "es": "Archivo (Alarma):",
        "fr": "Fichier (Alarme) :",
    },
    "snd_placeholder": {
        "en": "Select a .mp3 or .wav file...",
        "pt": "Selecione um arquivo .mp3 ou .wav...",
        "es": "Selecciona un archivo .mp3 ou .wav...",
        "fr": "Sélectionnez un fichier .mp3 ou .wav...",
    },
    "pomo_sound_vol_focus": {
        "en": "Volume (Focus):",
        "pt": "Volume (Foco):",
        "es": "Volumen (Enfoque):",
        "fr": "Volume (Concentration) :",
    },
    "pomo_sound_vol_break": {
        "en": "Volume (Break):",
        "pt": "Volume (Intervalo):",
        "es": "Volumen (Descanso):",
        "fr": "Volume (Pause) :",
    },
    "pomo_sound_vol_alarm": {
        "en": "Volume (Alarm):",
        "pt": "Volume (Alarme):",
        "es": "Volumen (Alarma):",
        "fr": "Volume (Alarme) :",
    },

    # --- Priority Tab ---
    "prio_random_tie": {
        "en": "Random Tie-Breaker for decks with same priority",
        "pt": "Desempate Aleatório para baralhos com a mesma prioridade",
        "es": "Desempate Aleatorio para mazos con la misma prioridad",
        "fr": "Départage Aléatoire pour les paquets de même priorité",
    },
    "prio_auto_reorder": {
        "en": "Automatically reorder new cards upon sync",
        "pt": "Reordenar novos cartões automaticamente ao sincronizar",
        "es": "Reordenar tarjetas nuevas automáticamente al sincronizar",
        "fr": "Réordonner automatiquement les nouvelles cartes lors de la synchronisation",
    },
    "prio_open_tree": {
        "en": "📂 Open Deck Priority Tree Manager...",
        "pt": "📂 Abrir Gerenciador de Árvore de Prioridades...",
        "es": "📂 Abrir Gestor de Árbol de Prioridades...",
        "fr": "📂 Ouvrir le Gestionnaire d'Arbre de Priorités...",
    },

    # --- Integrations Tab ---
    "integ_anki_grp": {
        "en": "AnkiConnect (Obsidian / Yomichan Integration)",
        "pt": "AnkiConnect (Integração com Obsidian / Yomichan)",
        "es": "AnkiConnect (Integración con Obsidian / Yomichan)",
        "fr": "AnkiConnect (Intégration Obsidian / Yomichan)",
    },
    "integ_anki_port": {
        "en": "Integrated JSON-RPC server running on port: <b>8765</b>",
        "pt": "Servidor JSON-RPC integrado rodando na porta: <b>8765</b>",
        "es": "Servidor JSON-RPC integrado ejecutándose en el puerto: <b>8765</b>",
        "fr": "Serveur JSON-RPC intégré s'exécutant sur le port : <b>8765</b>",
    },
    "integ_anki_status": {
        "en": "Status: <b>Active & Synced</b>",
        "pt": "Status: <b>Ativo e Sincronizado</b>",
        "es": "Estado: <b>Activo y Sincronizado</b>",
        "fr": "État : <b>Actif & Synchronisé</b>",
    },
    "integ_mc_grp": {
        "en": "Multiple Choice for Anki",
        "pt": "Multiple Choice for Anki",
        "es": "Multiple Choice for Anki",
        "fr": "Multiple Choice for Anki",
    },
    "integ_mc_desc": {
        "en": "Note Type: <b>AllInOne (kprim, mc, sc)</b> embedded.",
        "pt": "Tipo de Nota: <b>AllInOne (kprim, mc, sc)</b> incorporado.",
        "es": "Tipo de Nota: <b>AllInOne (kprim, mc, sc)</b> incorporado.",
        "fr": "Type de Note : <b>AllInOne (kprim, mc, sc)</b> intégré.",
    },

    # --- Global Action Buttons ---
    "btn_cancel": {
        "en": "Cancel",
        "pt": "Cancelar",
        "es": "Cancelar",
        "fr": "Annuler",
    },
    "btn_save_apply": {
        "en": "💾 Save & Apply",
        "pt": "💾 Salvar & Aplicar",
        "es": "💾 Guardar y Aplicar",
        "fr": "💾 Enregistrer & Appliquer",
    },

    # --- Pomodoro FAB Labels, Tooltips & Accessibility ---
    "fab_badge_ready": {
        "en": "READY",
        "pt": "PRONTO",
        "es": "LISTO",
        "fr": "PRÊT",
    },
    "fab_badge_paused": {
        "en": "PAUSED",
        "pt": "PAUSADO",
        "es": "PAUSADO",
        "fr": "EN PAUSE",
    },
    "fab_badge_focus": {
        "en": "FOCUS",
        "pt": "FOCO",
        "es": "ENFOQUE",
        "fr": "FOCUS",
    },
    "fab_badge_soft_break": {
        "en": "SOFT BRK",
        "pt": "P. SUAVE",
        "es": "PAUSA S.",
        "fr": "PAUSE D.",
    },
    "fab_badge_break": {
        "en": "BREAK",
        "pt": "INTERVALO",
        "es": "DESCANSO",
        "fr": "PAUSE",
    },
    "fab_btn_focus_enter": {
        "en": "🎯 Focus Mode",
        "pt": "🎯 Modo Foco",
        "es": "🎯 Modo Enfoque",
        "fr": "🎯 Mode Focus",
    },
    "fab_btn_focus_exit": {
        "en": "🗗 Exit Focus",
        "pt": "🗗 Sair Foco",
        "es": "🗗 Salir Enfoque",
        "fr": "🗗 Quitter Focus",
    },
    "fab_btn_skip": {
        "en": "⏭️ Skip",
        "pt": "⏭️ Pular",
        "es": "⏭️ Saltar",
        "fr": "⏭️ Passer",
    },
    "fab_btn_reset": {
        "en": "🔄 Reset",
        "pt": "🔄 Reset",
        "es": "🔄 Reiniciar",
        "fr": "🔄 Réinitialiser",
    },
    "fab_btn_config": {
        "en": "⚙️ Config",
        "pt": "⚙️ Config",
        "es": "⚙️ Ajustes",
        "fr": "⚙️ Config",
    },
    "fab_remaining_cards": {
        "en": "Remaining: <b>{count}</b>",
        "pt": "Restantes: <b>{count}</b>",
        "es": "Restantes: <b>{count}</b>",
        "fr": "Restantes : <b>{count}</b>",
    },
    "fab_eta": {
        "en": "ETA: <b>{eta}</b>",
        "pt": "ETA: <b>{eta}</b>",
        "es": "ETA: <b>{eta}</b>",
        "fr": "ETA : <b>{eta}</b>",
    },
    "fab_tooltip": {
        "en": "🍅 Pomodoro - Drag to position anywhere (Double-click to reset position)",
        "pt": "🍅 Pomodoro - Clique e arraste para posicionar onde desejar (Clique duplo para restaurar)",
        "es": "🍅 Pomodoro - Haz clic y arrastra para colocar donde quieras (Doble clic para restaurar)",
        "fr": "🍅 Pomodoro - Cliquez et glissez pour repositionner (Double-clic pour réinitialiser)",
    },
    "fab_btn_play_tip": {
        "en": "Start / Pause Pomodoro (Alt+P)",
        "pt": "Iniciar / Pausar Pomodoro (Alt+P)",
        "es": "Iniciar / Pausar Pomodoro (Alt+P)",
        "fr": "Démarrer / Mettre en pause le Pomodoro (Alt+P)",
    },
    "fab_btn_expand_tip": {
        "en": "Expand / Collapse panel",
        "pt": "Expandir / Minimizar painel",
        "es": "Expandir / Minimizar panel",
        "fr": "Développer / Réduire le panneau",
    },
    "fab_btn_focus_tip": {
        "en": "Toggle Fullscreen & Study Immersion",
        "pt": "Ativar modo tela cheia e imersão nos estudos",
        "es": "Activar pantalla completa e inmersión de estudio",
        "fr": "Basculer en plein écran et immersion d'étude",
    },
    "fab_btn_skip_tip": {
        "en": "Skip to next phase (break or focus) (Alt+S)",
        "pt": "Pular para intervalo ou próximo bloco de foco (Alt+S)",
        "es": "Saltar al descanso o próximo bloque de enfoque (Alt+S)",
        "fr": "Passer à la pause ou au bloc suivant (Alt+S)",
    },
    "fab_btn_reset_tip": {
        "en": "Reset current phase timer (Alt+R)",
        "pt": "Reiniciar contagem da fase atual (Alt+R)",
        "es": "Reiniciar conteo de la fase actual (Alt+R)",
        "fr": "Réinitialiser le décompte de la phase actuelle (Alt+R)",
    },
    "fab_btn_cfg_tip": {
        "en": "Open Pomodoro settings",
        "pt": "Abrir configurações do Pomodoro",
        "es": "Abrir ajustes de Pomodoro",
        "fr": "Ouvrir les paramètres du Pomodoro",
    },

    # --- ARIA & Accessibility Descriptions ---
    "aria_pomo_fab": {
        "en": "Pomodoro floating widget",
        "pt": "Widget flutuante do Pomodoro",
        "es": "Widget flotante de Pomodoro",
        "fr": "Widget flottant du Pomodoro",
    },
    "aria_pomo_timer": {
        "en": "Remaining study countdown timer",
        "pt": "Contagem regressiva do tempo de estudo",
        "es": "Cuenta regresiva del tiempo de estudio",
        "fr": "Compte à rebours du temps d'étude",
    },
    "aria_pomo_badge": {
        "en": "Current Pomodoro session state",
        "pt": "Estado atual da sessão do Pomodoro",
        "es": "Estado actual de la sesión de Pomodoro",
        "fr": "État actuel de la session Pomodoro",
    },
    "aria_pomo_cycles": {
        "en": "Completed Pomodoro cycles count",
        "pt": "Contagem de ciclos completos do Pomodoro",
        "es": "Recuento de ciclos completados de Pomodoro",
        "fr": "Nombre de cycles Pomodoro terminés",
    },
    "aria_pomo_progress": {
        "en": "Pomodoro phase progress percentage",
        "pt": "Porcentagem de progresso da fase do Pomodoro",
        "es": "Porcentaje de progreso de la fase de Pomodoro",
        "fr": "Pourcentage de progression de la phase Pomodoro",
    },
    "aria_pomo_remaining": {
        "en": "Cards remaining in today's study queue",
        "pt": "Cartões restantes na fila de estudos de hoje",
        "es": "Tarjetas restantes en la cola de estudio de hoy",
        "fr": "Cartes restantes dans la file d'étude d'aujourd'hui",
    },
    "aria_pomo_eta": {
        "en": "Estimated completion time based on study pace",
        "pt": "Tempo estimado de conclusão baseado no ritmo de estudo",
        "es": "Tiempo estimado de finalización según el ritmo de estudio",
        "fr": "Temps estimé d'achèvement basé sur le rythme d'étude",
    },

    # --- Rest Overlay Dialog ---
    "rest_title": {
        "en": "☕ Time for a Break!",
        "pt": "☕ Hora do Intervalo!",
        "es": "☕ ¡Hora del Descanso!",
        "fr": "☕ L'Heure de la Pause !",
    },
    "rest_long_title": {
        "en": "🎉 Long Break!",
        "pt": "🎉 Pausa Longa!",
        "es": "🎉 ¡Pausa Larga!",
        "fr": "🎉 Longue Pause !",
    },
    "rest_desc": {
        "en": "Great job! Step away from the screen, stretch, drink water, and rest your eyes.",
        "pt": "Excelente trabalho! Afaste-se da tela, alongue-se, beba água e descanse os olhos.",
        "es": "¡Excelente trabajo! Aléjate de la pantalla, estírate, bebe agua y descansa la vista.",
        "fr": "Excellent travail ! Éloignez-vous de l'écran, étirez-vous, buvez de l'eau et reposez vos yeux.",
    },
    "rest_btn_add_5m": {
        "en": "⏳ +5 min",
        "pt": "⏳ +5 min",
        "es": "⏳ +5 min",
        "fr": "⏳ +5 min",
    },
    "rest_btn_end_break": {
        "en": "🚀 Resume Focus",
        "pt": "🚀 Voltar ao Foco",
        "es": "🚀 Volver al Enfoque",
        "fr": "🚀 Reprendre le Focus",
    },

    # --- Gamepad Tab ---
    "gp_status_grp": {
        "en": "🎮 Device Status",
        "pt": "🎮 Status do Dispositivo",
        "es": "🎮 Estado del Dispositivo",
        "fr": "🎮 État de l'Appareil",
    },
    "gp_status_checking": {
        "en": "Checking connected gamepads...",
        "pt": "Verificando controles conectados...",
        "es": "Comprobando mandos conectados...",
        "fr": "Vérification des manettes connectées...",
    },
    "gp_status_connected": {
        "en": "Connected: {name}",
        "pt": "Conectado: {name}",
        "es": "Conectado: {name}",
        "fr": "Connecté : {name}",
    },
    "gp_status_none": {
        "en": "No gamepad detected. Connect a controller.",
        "pt": "Nenhum controle detectado. Conecte um joystick.",
        "es": "No se detectó ningún mando. Conecta un control.",
        "fr": "Aucune manette détectée. Connectez une manette.",
    },
    "gp_tbl_action": {
        "en": "Action",
        "pt": "Ação",
        "es": "Acción",
        "fr": "Action",
    },
    "gp_tbl_triggers": {
        "en": "Assigned Controls & Shortcuts",
        "pt": "Comandos & Atalhos Associados",
        "es": "Mandos y Atajos Asignados",
        "fr": "Commandes et Raccourcis Assignés",
    },
    "gp_btn_add": {
        "en": "+ Add",
        "pt": "+ Adicionar",
        "es": "+ Añadir",
        "fr": "+ Ajouter",
    },
    "gp_btn_press": {
        "en": "🟡 Press button, stick, or key...",
        "pt": "🟡 Pressione botão, stick ou tecla...",
        "es": "🟡 Pulsa botón, stick o tecla...",
        "fr": "🟡 Appuyez sur bouton, stick ou touche...",
    },
    "gp_deadzone_grp": {
        "en": "Analog Stick Calibration (Deadzone)",
        "pt": "Calibração dos Sticks Analógicos (Deadzone)",
        "es": "Calibración de Sticks Analógicos (Deadzone)",
        "fr": "Calibration des Sticks Analogiques (Deadzone)",
    },
    "gp_scroll_sens": {
        "en": "Scroll Sensitivity:",
        "pt": "Sensibilidade de Rolagem:",
        "es": "Sensibilidad de Desplazamiento:",
        "fr": "Sensibilité de Défilement :",
    },
    "gp_calib_grp": {
        "en": "⚙️ Stick & Trigger Calibration",
        "pt": "⚙️ Calibração de Analógicos e Gatilhos",
        "es": "⚙️ Calibración de Sticks y Gatillos",
        "fr": "⚙️ Calibration des Sticks et Gâchettes",
    },
    "gp_deadzone_lbl": {
        "en": "Radial Deadzone:",
        "pt": "Zona Morta Radial (Deadzone):",
        "es": "Zona Muerta Radial (Deadzone):",
        "fr": "Zone Morte Radiale (Deadzone) :",
    },
    "gp_scroll_lbl": {
        "en": "Scroll Sensitivity:",
        "pt": "Sensibilidade de Rolagem (Scroll):",
        "es": "Sensibilidad de Desplazamiento (Scroll):",
        "fr": "Sensibilité de Défilement (Scroll) :",
    },
    "gp_trigger_lbl": {
        "en": "LT / RT Triggers Threshold:",
        "pt": "Limiar dos Gatilhos LT / RT:",
        "es": "Umbral de Gatillos LT / RT:",
        "fr": "Seuil des Gâchettes LT / RT :",
    },
    "gp_stick_scroll_lbl": {
        "en": "Analog Stick for Scrolling:",
        "pt": "Analógico para Rolagem:",
        "es": "Stick Analógico para Desplazamiento:",
        "fr": "Stick Analogique pour le Défilement :",
    },
    "gp_stick_right": {
        "en": "Right Stick (Recommended)",
        "pt": "Analógico Direito (Recomendado)",
        "es": "Stick Derecho (Recomendado)",
        "fr": "Stick Droit (Recommandé)",
    },
    "gp_stick_left": {
        "en": "Left Stick",
        "pt": "Analógico Esquerdo",
        "es": "Stick Izquierdo",
        "fr": "Stick Gauche",
    },
    "gp_sound_grp": {
        "en": "🔊 Command Sound Feedback",
        "pt": "🔊 Feedback Sonoro de Comandos",
        "es": "🔊 Feedback Sonoro de Comandos",
        "fr": "🔊 Retour Sonore des Commandes",
    },
    "gp_sound_enable": {
        "en": "Enable audio feedback when pressing gamepad buttons",
        "pt": "Ativar feedback auditivo ao pressionar botões no controle",
        "es": "Activar feedback auditivo al presionar botones en el mando",
        "fr": "Activer le retour audio lors de l'appui sur les touches",
    },
    "gp_sound_preset_lbl": {
        "en": "Button Sound:",
        "pt": "Som dos Botões:",
        "es": "Sonido de los Botones:",
        "fr": "Son des Boutons :",
    },
    "gp_snd_click": {
        "en": "🎮 Modern Tactile Click",
        "pt": "🎮 Clique Tátil Moderno",
        "es": "🎮 Clic Táctil Moderno",
        "fr": "🎮 Clic Tactile Moderne",
    },
    "gp_snd_pop": {
        "en": "💧 Soft Pop / Bubble",
        "pt": "💧 Pop Suave / Bubble",
        "es": "💧 Pop Suave / Burbuja",
        "fr": "💧 Pop Doux / Bulle",
    },
    "gp_snd_chime": {
        "en": "🔔 Chime / Gentle Bell",
        "pt": "🔔 Chime / Sino Suave",
        "es": "🔔 Campana / Chime Suave",
        "fr": "🔔 Carillon / Cloche Douce",
    },
    "gp_snd_beep": {
        "en": "📟 Short Electronic Beep",
        "pt": "📟 Bip Eletrônico Curto",
        "es": "📟 Beep Electrónico Corto",
        "fr": "📟 Bip Électronique Court",
    },
    "snd_file_audio": {
        "en": "Audio File:",
        "pt": "Arquivo de Áudio:",
        "es": "Archivo de Audio:",
        "fr": "Fichier Audio :",
    },
    "gp_sound_volume_lbl": {
        "en": "Sound Feedback Volume:",
        "pt": "Volume do Feedback Sonoro:",
        "es": "Volumen del Feedback Sonoro:",
        "fr": "Volume du Retour Sonore :",
    },
    "gp_visual_grp": {
        "en": "✨ On-Screen Visual Button Feedback",
        "pt": "✨ Feedback Visual dos Botões na Tela",
        "es": "✨ Feedback Visual de Botones en Pantalla",
        "fr": "✨ Retour Visuel des Boutons à l'Écran",
    },
    "gp_release_mode_chk": {
        "en": "Trigger commands on button release (Release Mode - hold to see button depress)",
        "pt": "Acionar comandos ao soltar o botão (Release Mode - permite segurar para ver o botão afundar na tela)",
        "es": "Ejecutar comandos al soltar el botón (Release Mode)",
        "fr": "Déclencher les commandes au relâchement du bouton (Release Mode)",
    },
    "gp_intensity_lbl": {
        "en": "Visual Contraction Intensity:",
        "pt": "Intensidade da Contração Visual:",
        "es": "Intensidad de la Contracción Visual:",
        "fr": "Intensité de la Contraction Visuelle :",
    },
    "gp_int_subtle": {
        "en": "Subtle (88% Contraction)",
        "pt": "Sutil (Contração a 88%)",
        "es": "Sutil (Contracción al 88%)",
        "fr": "Subtile (Contraction à 88%)",
    },
    "gp_int_moderate": {
        "en": "Moderate (78% Contraction - Recommended)",
        "pt": "Moderada (Contração a 78% - Recomendado)",
        "es": "Moderada (Contracción al 78% - Recomendado)",
        "fr": "Modérée (Contraction à 78% - Recommandé)",
    },
    "gp_int_intense": {
        "en": "Intense (68% Contraction with Reinforced Halo)",
        "pt": "Intensa (Contração a 68% com Halo Reforçado)",
        "es": "Intensa (Contracción al 68% con Halo Reforzado)",
        "fr": "Intense (Contraction à 68% avec Halo Renforcé)",
    },
    "gp_btn_scale_lbl": {
        "en": "Base Answer Buttons Size:",
        "pt": "Tamanho Básico dos Botões de Resposta:",
        "es": "Tamaño Básico de los Botones de Respuesta:",
        "fr": "Taille de Base des Boutons de Réponse :",
    },
    "gp_mappings_grp": {
        "en": "🎯 Gamepad Button Mapping",
        "pt": "🎯 Mapeamento de Botões do Controle",
        "es": "🎯 Mapeo de Botones del Mando",
        "fr": "🎯 Mappage des Boutons de la Manette",
    },
    "gp_tbl_actions_btn": {
        "en": "Actions",
        "pt": "Ações",
        "es": "Acciones",
        "fr": "Actions",
    },
    "gp_reset_defaults": {
        "en": "🔄 Restore Defaults (8BitDo / Xbox)",
        "pt": "🔄 Restaurar Padrões (8BitDo / Xbox)",
        "es": "🔄 Restaurar Predeterminados (8BitDo / Xbox)",
        "fr": "🔄 Restaurer les Paramètres par Défaut",
    },
    "gp_clear_all": {
        "en": "🧹 Unbind All",
        "pt": "🧹 Desvincular Todos",
        "es": "🧹 Desvincular Todos",
        "fr": "🧹 Tout Dissocier",
    },
    "gp_btn_clear": {
        "en": "🧹 Clear",
        "pt": "🧹 Limpar",
        "es": "🧹 Limpiar",
        "fr": "🧹 Effacer",
    },
    "gp_btn_clear_tip": {
        "en": "Remove all shortcuts for this action",
        "pt": "Remover todos os atalhos desta ação",
        "es": "Eliminar todos los atajos de esta acción",
        "fr": "Supprimer tous les raccourcis pour cette action",
    },

    # --- Gamepad Toast Notifications ---
    "toast_pomo_started": {
        "en": "🍅 Pomodoro started! Focus now.",
        "pt": "🍅 Pomodoro iniciado! Foco agora.",
        "es": "🍅 ¡Pomodoro iniciado! A concentrarse.",
        "fr": "🍅 Pomodoro démarré ! Concentration en cours.",
    },
    "toast_pomo_paused": {
        "en": "⏸️ Pomodoro paused.",
        "pt": "⏸️ Pomodoro pausado.",
        "es": "⏸️ Pomodoro pausado.",
        "fr": "⏸️ Pomodoro en pause.",
    },
    "toast_pomo_resumed": {
        "en": "▶️ Pomodoro resumed.",
        "pt": "▶️ Pomodoro retomado.",
        "es": "▶️ Pomodoro reanudado.",
        "fr": "▶️ Pomodoro repris.",
    },
    "toast_pomo_skipped": {
        "en": "⏭️ Pomodoro skipped to next phase.",
        "pt": "⏭️ Pomodoro avançou para a próxima etapa.",
        "es": "⏭️ Pomodoro avanzó a la siguiente etapa.",
        "fr": "⏭️ Pomodoro avancé à l'étape suivante.",
    },
    "toast_pomo_reset": {
        "en": "🔄 Pomodoro round reset.",
        "pt": "🔄 Rodada do Pomodoro reiniciada.",
        "es": "🔄 Ronda de Pomodoro reiniciada.",
        "fr": "🔄 Cycle Pomodoro réinitialisé.",
    },

    # --- Image Search & Inserter ---
    "image_search_tooltip": {
        "en": "Search & Insert Web Images (Ctrl+Shift+I)",
        "pt": "Pesquisar e Inserir Imagens da Web (Ctrl+Shift+I)",
        "es": "Buscar e Insertar Imágenes de la Web (Ctrl+Shift+I)",
        "fr": "Rechercher et Insérer des Images Web (Ctrl+Shift+I)",
    },
    "image_search_title": {
        "en": "🖼️ Web Image Search & Inserter",
        "pt": "🖼️ Buscador e Baixador de Imagens da Web",
        "es": "🖼️ Buscador y Descargador de Imágenes Web",
        "fr": "🖼️ Recherche et Téléchargement d'Images Web",
    },
    "image_search_placeholder": {
        "en": "Type your search query and press Enter...",
        "pt": "Digite o termo para buscar imagens e pressione Enter...",
        "es": "Escriba el término para buscar imágenes y presione Enter...",
        "fr": "Tapez le terme à rechercher et appuyez sur Entrée...",
    },
    "image_search_btn_search": {
        "en": "Search",
        "pt": "Buscar",
        "es": "Buscar",
        "fr": "Rechercher",
    },
    "image_search_searching": {
        "en": "Searching images...",
        "pt": "Buscando imagens...",
        "es": "Buscando imágenes...",
        "fr": "Recherche d'images en cours...",
    },
    "image_search_download_insert": {
        "en": "⬇️ Download & Insert into Card",
        "pt": "⬇️ Baixar e Inserir no Card",
        "es": "⬇️ Descargar e Insertar en la Tarjeta",
        "fr": "⬇️ Télécharger et Insérer dans la Carte",
    },
    "image_search_btn_open_page": {
        "en": "🌐 Open Image Webpage",
        "pt": "🌐 Abrir página da imagem",
        "es": "🌐 Abrir página de la imagen",
        "fr": "🌐 Ouvrir la page de l'image",
    },
    "image_search_open_page_tooltip": {
        "en": "Open original image webpage in browser",
        "pt": "Abrir página original da imagem no navegador",
        "es": "Abrir página original de la imagen en el navegador",
        "fr": "Ouvrir la page originale de l'image dans le navigateur",
    },
    "image_search_view_zoom": {
        "en": "🔍 View with Zoom",
        "pt": "🔍 Visualizar com Zoom",
        "es": "🔍 Visualizar con Zoom",
        "fr": "🔍 Afficher avec Zoom",
    },
    "image_search_downloading": {
        "en": "Downloading image...",
        "pt": "Baixando imagem...",
        "es": "Descargando imagem...",
        "fr": "Téléchargement de l'image...",
    },
    "image_search_no_results": {
        "en": "No images found for this search.",
        "pt": "Nenhuma imagem encontrada para esta busca.",
        "es": "No se encontraron imágenes para esta búsqueda.",
        "fr": "Aucune image trouvée pour cette recherche.",
    },
    "image_search_back": {
        "en": "◀ Back to Results",
        "pt": "◀ Voltar aos Resultados",
        "es": "◀ Volver a los Resultados",
        "fr": "◀ Retour aux Résultats",
    },
    "image_search_engine_all": {
        "en": "✨ All Sources (Web + Wikipedia)",
        "pt": "✨ Todas as Fontes (Web + Wikipédia)",
        "es": "✨ Todas las Fuentes (Web + Wikipedia)",
        "fr": "✨ Toutes les sources (Web + Wikipédia)",
    },
    "image_search_engine_google": {
        "en": "🌐 Web (Medical Articles & Journals)",
        "pt": "🌐 Web (Artigos & Revistas Médicas)",
        "es": "🌐 Web (Artículos y Revistas Médicas)",
        "fr": "🌐 Web (Articles et Revues Médicales)",
    },
    "image_search_engine_wikimedia": {
        "en": "🏛️ Wikimedia Commons",
        "pt": "🏛️ Wikimedia Commons",
        "es": "🏛️ Wikimedia Commons",
        "fr": "🏛️ Wikimedia Commons",
    },
    "image_search_engine_wikipedia": {
        "en": "📖 Wikipedia Articles",
        "pt": "📖 Wikipédia Artigos",
        "es": "📖 Artículos de Wikipedia",
        "fr": "📖 Articles Wikipédia",
    },
    "image_search_engine_web": {
        "en": "🌐 Web (Medical Articles & Journals)",
        "pt": "🌐 Web (Artigos & Revistas Médicas)",
        "es": "🌐 Web (Artículos y Revistas Médicas)",
        "fr": "🌐 Web (Articles et Revues Médicales)",
    },
    "image_search_engine_wiki": {
        "en": "Wikimedia Commons (Open Media)",
        "pt": "Wikimedia Commons (Mídia Aberta)",
        "es": "Wikimedia Commons (Medios Abiertos)",
        "fr": "Wikimedia Commons (Médias Libres)",
    },
    "image_search_error": {
        "en": "Error searching or downloading images. Check internet connection.",
        "pt": "Erro ao buscar ou baixar imagens. Verifique a conexão com a internet.",
        "es": "Error al buscar o descargar imágenes. Verifique la conexión a internet.",
        "fr": "Erreur lors de la recherche ou du téléchargement. Vérifiez votre connexion Internet.",
    },
    "image_search_zoom_hint": {
        "en": "Click an image to preview & zoom. Double-click to insert directly.",
        "pt": "Clique em uma imagem para zoom e pré-visualização. Clique duplo para inserir direto.",
        "es": "Haga clic en una imagen para ampliarla. Doble clic para insertarla directamente.",
        "fr": "Cliquez sur une image pour l'agrandir. Double-cliquez pour insérer directement.",
    },
    "image_search_loading_more": {
        "en": "🔄 Loading more images...",
        "pt": "🔄 Carregando mais imagens...",
        "es": "🔄 Cargando más imágenes...",
        "fr": "🔄 Chargement d'autres images...",
    },
    "image_search_end_of_results": {
        "en": "End of results",
        "pt": "Fim dos resultados",
        "es": "Fin de los resultados",
        "fr": "Fin des résultats",
    },
    "image_search_tab_search": {
        "en": "🔍 Search",
        "pt": "🔍 Pesquisa",
        "es": "🔍 Búsqueda",
        "fr": "🔍 Recherche",
    },
    "image_search_tab_recent": {
        "en": "🕒 Recent",
        "pt": "🕒 Recentes",
        "es": "🕒 Recientes",
        "fr": "🕒 Récentes",
    },
    "image_search_recent_hint": {
        "en": "Last 15 images used. Click to preview & zoom or double-click to insert into card.",
        "pt": "Últimas 15 imagens utilizadas. Clique para zoom ou duplo clique para inserir no card.",
        "es": "Últimas 15 imágenes utilizadas. Haga clic para zoom o doble clic para insertar en la tarjeta.",
        "fr": "15 dernières images utilisées. Cliquez pour zoomer ou double-cliquez pour insérer dans la carte.",
    },
    "image_search_recent_empty": {
        "en": "No recent images used yet. Images inserted into cards will appear here.",
        "pt": "Nenhuma imagem recente utilizada ainda. As imagens inseridas nos cards aparecerão aqui.",
        "es": "Aún no se han utilizado imágenes recientes. Las imágenes insertadas en las tarjetas aparecerán aquí.",
        "fr": "Aucune image récente utilisée pour l'instant. Les images insérées dans les cartes apparaîtront ici.",
    },
    "image_search_btn_edit": {
        "en": "✏️ Edit & Insert",
        "pt": "✏️ Editar e Inserir",
        "es": "✏️ Editar e Insertar",
        "fr": "✏️ Modifier et Insérer",
    },
    "image_search_editor_title": {
        "en": "✏️ Image Annotation & Crop Editor",
        "pt": "✏️ Editor de Anotação e Corte de Imagem",
        "es": "✏️ Editor de Anotación y Recorte de Imagen",
        "fr": "✏️ Éditeur d'Annotation et Recadrage d'Image",
    },
    "image_search_tool_arrow": {
        "en": "🏹 Arrow",
        "pt": "🏹 Seta",
        "es": "🏹 Flecha",
        "fr": "🏹 Flèche",
    },
    "image_search_tool_circle": {
        "en": "⭕ Circle",
        "pt": "⭕ Círculo",
        "es": "⭕ Círculo",
        "fr": "⭕ Cercle",
    },
    "image_search_tool_crop": {
        "en": "✂️ Crop",
        "pt": "✂️ Cortar",
        "es": "✂️ Recortar",
        "fr": "✂️ Recadrer",
    },
    "image_search_apply_crop": {
        "en": "Apply Crop",
        "pt": "Aplicar Corte",
        "es": "Aplicar Recorte",
        "fr": "Appliquer Recadrage",
    },
    "image_search_undo": {
        "en": "↩️ Undo",
        "pt": "↩️ Desfazer",
        "es": "↩️ Deshacer",
        "fr": "↩️ Annuler",
    },
    "image_search_reset": {
        "en": "🔄 Reset",
        "pt": "🔄 Redefinir",
        "es": "🔄 Restablecer",
        "fr": "🔄 Réinitialiser",
    },
    "image_search_insert_edited": {
        "en": "⬇️ Insert Edited Image into Card",
        "pt": "⬇️ Inserir Imagem Editada no Card",
        "es": "⬇️ Insertar Imagen Editada en la Tarjeta",
        "fr": "⬇️ Insérer l'Image Modifiée dans la Carte",
    },
    "image_search_stroke_width": {
        "en": "Width",
        "pt": "Espessura",
        "es": "Grosor",
        "fr": "Épaisseur",
    },
    "image_search_editor_hint": {
        "en": "Select a tool (Arrow, Circle, Crop) and drag across the image. Click 'Apply Crop' to execute crop.",
        "pt": "Selecione uma ferramenta (Seta, Círculo, Cortar) e arraste sobre a imagem. Clique em 'Aplicar Corte' para executar o corte.",
        "es": "Seleccione una herramienta (Flecha, Círculo, Recortar) y arrastre sobre la imagen.",
        "fr": "Sélectionnez un outil (Flèche, Cercle, Recadrer) et faites glisser sur l'image.",
    },

    # --- Gamepad & Global Shortcuts ---
    "action_pomo_fullscreen": {
        "en": "Pomodoro: Toggle Fullscreen / Focus Mode",
        "pt": "Pomodoro: Alternar Tela Cheia / Modo Foco",
        "es": "Pomodoro: Alternar Pantalla Completa / Modo Enfoque",
        "fr": "Pomodoro : Basculer Plein Écran / Mode Focus",
    },
    "action_pomo_fullscreen_desc": {
        "en": "Enters or exits fullscreen focus mode during study",
        "pt": "Entra ou sai do modo de foco em tela cheia durante os estudos",
        "es": "Entra o sale del modo de enfoque en pantalla completa durante el estudio",
        "fr": "Active ou désactive le mode plein écran pendant l'étude",
    },
    "action_open_settings": {
        "en": "Settings: Open Settings Hub",
        "pt": "Configurações: Abrir Central de Configurações",
        "es": "Ajustes: Abrir Centro de Ajustes",
        "fr": "Paramètres : Ouvrir le Centre de Configuration",
    },
    "action_open_settings_desc": {
        "en": "Opens the Obsidian Addon Suite Settings Hub dialog",
        "pt": "Abre a Central de Configurações da Obsidian Addon Suite",
        "es": "Abre el Centro de Ajustes de Obsidian Addon Suite",
        "fr": "Ouvre le Centre de Configuration d'Obsidian Addon Suite",
    },

    # --- Pomodoro FAB & Focus Toggle ---
    "fab_btn_focus_enter": {
        "en": "🎯 Focus Mode",
        "pt": "🎯 Modo Foco",
        "es": "🎯 Modo Enfoque",
        "fr": "🎯 Mode Focus",
    },
    "fab_btn_focus_exit": {
        "en": "🗗 Exit Focus",
        "pt": "🗗 Sair Foco",
        "es": "🗗 Salir Enfoque",
        "fr": "🗗 Quitter Focus",
    },
    "fab_btn_focus_enter_tip": {
        "en": "Enter Focus Mode / Fullscreen (F11)",
        "pt": "Entrar no Modo Foco / Tela Cheia (F11)",
        "es": "Entrar al Modo Enfoque / Pantalla Completa (F11)",
        "fr": "Activer le Mode Focus / Plein Écran (F11)",
    },
    "fab_btn_focus_exit_tip": {
        "en": "Exit Focus Mode / Fullscreen (F11)",
        "pt": "Sair do Modo Foco / Tela Cheia (F11)",
        "es": "Salir del Modo Enfoque / Pantalla Completa (F11)",
        "fr": "Quitter le Mode Focus / Plein Écran (F11)",
    },
    "pomo_auto_adv_q_tip": {
        "en": "Auto-Advance: {sec}s remaining to reveal answer",
        "pt": "Passagem Automática: {sec}s restantes para mostrar a resposta",
        "es": "Pase Automático: {sec}s restantes para mostrar la respuesta",
        "fr": "Avance Automatique : {sec}s restantes pour afficher la réponse",
    },
    "pomo_auto_adv_a_tip": {
        "en": "Auto-Advance: {sec}s remaining before grading 'Again' and advancing",
        "pt": "Passagem Automática: {sec}s restantes para marcar 'Errei' automaticamente",
        "es": "Pase Automático: {sec}s restantes para calificar 'Otra vez' automáticamente",
        "fr": "Avance Automatique : {sec}s restantes avant de marquer 'À revoir'",
    },
}


def normalize_language_code(code: Optional[str]) -> str:
    """
    Normalizes any language string (e.g. 'en_US', 'pt_BR', 'pt-PT', 'es-ES', 'fr_FR')
    into one of the 4 supported codes: 'en', 'pt', 'es', 'fr'.
    Any unsupported code (e.g. 'pl', 'de', 'ja') falls back to 'en'.
    """
    if not code or not isinstance(code, str):
        return "en"

    c = code.strip().lower().replace("-", "_")

    if c.startswith("pt"):
        return "pt"
    if c.startswith("es"):
        return "es"
    if c.startswith("fr"):
        return "fr"

    # Polish, German, Italian, or anything else defaults to English
    return "en"


def get_current_language() -> str:
    """
    Returns the effective language code ('en', 'pt', 'es', 'fr').
    Resolution order:
    1. Runtime override (set_language_override)
    2. User explicit selection in Addon Settings (module 'general' -> 'language')
    3. Anki's detected profile language (mw.pm.defaultLang or mw.pm.meta['defaultLang'])
    4. Anki's SQLite prefs database ('_global' profile defaultLang)
    5. System QLocale
    6. Default fallback: 'en'
    """
    global _override_language
    if _override_language:
        return _override_language

    try:
        gen_cfg = get_module_config("general")
        chosen = gen_cfg.get("language", "auto")
        if chosen and chosen != "auto":
            return normalize_language_code(chosen)
    except Exception:
        pass

    detected = None

    # 1. Inspect Anki ProfileManager
    if mw and hasattr(mw, "pm") and mw.pm:
        try:
            if hasattr(mw.pm, "defaultLang"):
                val = mw.pm.defaultLang
                detected = val() if callable(val) else val
            if not detected and hasattr(mw.pm, "meta") and isinstance(mw.pm.meta, dict):
                detected = mw.pm.meta.get("defaultLang") or mw.pm.meta.get("lang")
            if not detected and hasattr(mw.pm, "_meta") and isinstance(mw.pm._meta, dict):
                detected = mw.pm._meta.get("defaultLang") or mw.pm._meta.get("lang")
        except Exception:
            pass

    # 2. Inspect anki.lang module if available
    if not detected:
        try:
            from anki.lang import current_lang
            detected = current_lang
        except Exception:
            pass

    # 3. Direct check in Anki's prefs21.db as robust standalone fallback
    if not detected:
        try:
            import sqlite3, pickle
            db_path = os.path.expanduser(r"~\AppData\Roaming\Anki2\prefs21.db")
            if os.path.exists(db_path):
                with sqlite3.connect(db_path) as conn:
                    row = conn.execute("SELECT data FROM profiles WHERE name='_global'").fetchone()
                    if row and row[0]:
                        meta = pickle.loads(row[0])
                        if isinstance(meta, dict):
                            detected = meta.get("defaultLang") or meta.get("lang")
        except Exception:
            pass

    # 4. Fallback to System QLocale
    if not detected and QLocale:
        try:
            detected = QLocale.system().name()
        except Exception:
            pass

    return normalize_language_code(detected)


def set_language_override(lang_code: Optional[str]):
    """Sets a runtime language override (useful for testing or instant live preview)."""
    global _override_language
    if lang_code is None:
        _override_language = None
    else:
        _override_language = normalize_language_code(lang_code)


def tr(key: str, default: Optional[str] = None, **kwargs) -> str:
    """
    Translates a key into the active language.
    If the key is missing in the current language, falls back to English ('en').
    If completely missing, returns `default` or `key`.
    Supports formatting kwargs, e.g. tr('hello', name='Alice').
    """
    lang = get_current_language()
    trans_map = TRANSLATIONS.get(key)
    if trans_map:
        text = trans_map.get(lang) or trans_map.get("en")
        if text:
            if kwargs:
                try:
                    return text.format(**kwargs)
                except Exception:
                    return text
            return text

    if default is not None:
        if kwargs:
            try:
                return default.format(**kwargs)
            except Exception:
                return default
        return default

    return key
