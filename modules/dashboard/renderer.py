# -*- coding: utf-8 -*-
"""
HTML/CSS Renderer for the Modern Stats Dashboard & Anki Modern UI Overhaul.
Renders responsive glassmorphic cards with native Anki daily goals, limits, and composition.
"""

from typing import Dict, Any
from .stats_engine import DeckDashboardStats
from ..theme_manager.presets import get_active_theme_colors
try:
    from ...utils.config_manager import get_module_config
    from ...utils.i18n import tr
except (ImportError, ValueError):
    try:
        from utils.config_manager import get_module_config
        from utils.i18n import tr
    except ImportError:
        def tr(key, default=None, **kwargs):
            return default if default is not None else key


try:
    from ..theme_manager.engine import (
        get_accessible_text_color,
        is_light_color,
        get_contrast_ratio,
        get_perceptual_luminance,
    )
except (ImportError, ValueError):
    try:
        from modules.theme_manager.engine import (
            get_accessible_text_color,
            is_light_color,
            get_contrast_ratio,
            get_perceptual_luminance,
        )
    except ImportError:
        def is_light_color(c): return False
        def get_accessible_text_color(bg, dark="#0f172a", light="#ffffff"): return light
        def get_contrast_ratio(a, b): return 5.0
        def get_perceptual_luminance(c): return 0.5


def get_modern_ui_stylesheet(config: Dict[str, Any]) -> str:
    """Returns CSS that modernizes Anki's native Deck Browser and Overview UI."""
    theme_cfg = get_module_config("theme")
    colors = get_active_theme_colors(theme_cfg)

    accent_grad = colors.get("accent_gradient", "linear-gradient(135deg, #38bdf8 0%, #0284c7 100%)")
    accent = colors.get("accent", "#38bdf8")
    bg_card = colors.get("bg_card", "#181825")
    bg_hover = colors.get("bg_card_hover", "#313244")
    border = colors.get("border_color", "#45475a")
    text_pri = colors.get("text_primary", "#cdd6f4")
    new_c = colors.get("new_color", "#89b4fa")
    learn_c = colors.get("learn_color", "#fab387")
    rev_c = colors.get("review_color", "#a6e3a1")

    study_btn_text = get_accessible_text_color(accent)

    return f"""
    <style id="anki-modern-ui-styles">
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }}

        button#study, #study, .study-btn {{
            background: {accent_grad} !important;
            color: {study_btn_text} !important;
            border: none !important;
            border-radius: 24px !important;
            padding: 10px 36px !important;
            font-size: 15px !important;
            font-weight: 700 !important;
            cursor: pointer !important;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3) !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            margin: 12px auto !important;
            display: inline-block !important;
        }}
        button#study:hover, #study:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45) !important;
            filter: brightness(1.1) !important;
        }}

        table#deckbrowser-table, table.deck-table, table#overview-table {{
            width: 100% !important;
            max-width: 980px !important;
            margin: 12px auto !important;
            border-collapse: separate !important;
            border-spacing: 0 4px !important;
        }}
        tr.deck, tr.deck-row {{
            transition: background 0.15s ease, transform 0.08s ease !important;
            border-radius: 8px !important;
            outline: none !important;
        }}
        tr.deck:hover, tr.deck-row:hover {{
            background: {bg_hover} !important;
        }}
        tr.deck.gamepad-focused, tr.deck:focus-visible {{
            outline: 2px solid {accent} !important;
            outline-offset: 2px !important;
            background: rgba(56, 189, 248, 0.18) !important;
            box-shadow: 0 0 16px rgba(56, 189, 248, 0.4) !important;
        }}
        :focus-visible {{
            outline: 2px solid {accent} !important;
            outline-offset: 2px !important;
            border-radius: 6px !important;
        }}

        .count.new-count, .new-count, td.new, span.new-count {{
            color: {new_c} !important;
            font-weight: 700 !important;
        }}
        .count.learn-count, .learn-count, td.learn, span.learn-count {{
            color: {learn_c} !important;
            font-weight: 700 !important;
        }}
        .count.review-count, .review-count, td.review, span.review-count {{
            color: {rev_c} !important;
            font-weight: 700 !important;
        }}
    </style>
    <script id="anki-deck-accessibility-script">
    (function() {{
        if (window._ankiDeckAccessibilityLoaded) return;
        window._ankiDeckAccessibilityLoaded = true;

        function getDecks() {{
            return Array.from(document.querySelectorAll('tr.deck'));
        }}

        function getFocusedIndex() {{
            let decks = getDecks();
            return decks.findIndex(el => el.classList.contains('gamepad-focused') || el === document.activeElement);
        }}

        function focusDeck(index) {{
            let decks = getDecks();
            if (!decks.length) return;
            if (index < 0) index = 0;
            if (index >= decks.length) index = decks.length - 1;

            decks.forEach((el, idx) => {{
                el.setAttribute('role', 'treeitem');
                if (idx === index) {{
                    el.classList.add('gamepad-focused');
                    el.setAttribute('aria-selected', 'true');
                    el.tabIndex = 0;
                    el.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
                }} else {{
                    el.classList.remove('gamepad-focused');
                    el.setAttribute('aria-selected', 'false');
                    el.tabIndex = -1;
                }}
            }});
        }}

        function initAria() {{
            let decks = getDecks();
            let table = document.querySelector('table#deckbrowser-table, table.deck-table, table');
            if (table) table.setAttribute('role', 'tree');

            decks.forEach((el, idx) => {{
                el.setAttribute('role', 'treeitem');
                let isExpanded = el.querySelector('a.collapse') ? true : false;
                el.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
            }});

            let savedDeckId = sessionStorage.getItem('gamepad_focused_deck_id');
            if (savedDeckId) {{
                let savedEl = document.getElementById(savedDeckId) || document.querySelector('tr.deck[id="' + savedDeckId + '"]');
                if (savedEl) {{
                    decks.forEach(el => {{
                        el.classList.remove('gamepad-focused');
                        el.setAttribute('aria-selected', 'false');
                        el.tabIndex = -1;
                    }});
                    savedEl.classList.add('gamepad-focused');
                    savedEl.setAttribute('aria-selected', 'true');
                    savedEl.tabIndex = 0;
                    savedEl.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
                    return;
                }}
            }}

            decks.forEach((el, idx) => {{
                if (idx === 0 && !document.querySelector('tr.deck.gamepad-focused')) {{
                    el.tabIndex = 0;
                }} else if (!el.classList.contains('gamepad-focused')) {{
                    el.tabIndex = -1;
                }}
            }});
        }}

        setTimeout(initAria, 120);

        document.addEventListener('keydown', function(e) {{
            if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;

            let curIdx = getFocusedIndex();
            let decks = getDecks();
            if (!decks.length) return;

            if (e.key === 'ArrowDown') {{
                e.preventDefault();
                let next = (curIdx === -1) ? 0 : Math.min(decks.length - 1, curIdx + 1);
                focusDeck(next);
            }} else if (e.key === 'ArrowUp') {{
                e.preventDefault();
                let prev = (curIdx === -1) ? 0 : Math.max(0, curIdx - 1);
                focusDeck(prev);
            }} else if (e.key === 'ArrowRight') {{
                if (curIdx !== -1) {{
                    let deck = decks[curIdx];
                    let collapseBtn = deck.querySelector('a.collapse') || deck.querySelector('[onclick*="collapse:"]');
                    if (collapseBtn) {{
                        e.preventDefault();
                        collapseBtn.click();
                        setTimeout(initAria, 150);
                    }}
                }}
            }} else if (e.key === 'ArrowLeft') {{
                if (curIdx !== -1) {{
                    let deck = decks[curIdx];
                    let collapseBtn = deck.querySelector('a.collapse') || deck.querySelector('[onclick*="collapse:"]');
                    if (collapseBtn) {{
                        e.preventDefault();
                        collapseBtn.click();
                        setTimeout(initAria, 150);
                    }}
                }}
            }} else if (e.key === 'Enter' || e.key === ' ') {{
                if (curIdx !== -1) {{
                    e.preventDefault();
                    let deck = decks[curIdx];
                    deck.style.transform = 'scale(0.97)';
                    setTimeout(function() {{
                        deck.style.transform = '';
                        let link = deck.querySelector('a.deck');
                        if (link) {{ link.click(); return; }}
                        let openBtn = deck.querySelector('[onclick*="open:"]');
                        if (openBtn) openBtn.click();
                    }}, 80);
                }}
            }} else if (e.key === 'Home') {{
                e.preventDefault();
                focusDeck(0);
            }} else if (e.key === 'End') {{
                e.preventDefault();
                focusDeck(decks.length - 1);
            }}
        }});
    }})();
    </script>
    """


def render_dashboard_html(stats: DeckDashboardStats, config: Dict[str, Any]) -> str:
    """
    Renders the Modern Stats Dashboard with native daily goals, limits, and composition.
    """
    show_today = config.get("show_today_progress", True)
    show_remaining = config.get("show_remaining", True)
    show_done = config.get("show_done_today", True)
    show_goals = config.get("show_daily_goals", True)
    show_comp = config.get("show_deck_composition", True)
    columns = int(config.get("layout_columns", 3))

    theme_cfg = get_module_config("theme")
    colors = get_active_theme_colors(theme_cfg)

    card_bg = colors.get("bg_card", "#181825")
    accent = colors.get("accent", "#38bdf8")
    text_pri = colors.get("text_primary", "#f8fafc")
    text_sec = colors.get("text_secondary", "#94a3b8")
    border = colors.get("border_color", "#27272a")
    new_c = colors.get("new_color", "#38bdf8")
    learn_c = colors.get("learn_color", "#fb923c")
    rev_c = colors.get("review_color", "#4ade80")

    scope_title = f"📁 {stats.deck_name}" if stats.is_per_deck else tr("dash_global_collection", "📊 Coleção Global")
    cards_html = []

    # Card 1: Metas Diárias
    if show_goals:
        cards_html.append(f"""
        <div class="dash-card">
            <div class="dash-card-header">
                <div class="dash-title-wrap">
                    <span class="dash-icon">🎯</span>
                    <span class="dash-card-title">{tr("dash_daily_goals", "Metas Diárias")}</span>
                </div>
                <span class="dash-badge">{tr("dash_native_config", "Config Nativa")}</span>
            </div>
            <div class="dash-goal-row">
                <div class="dash-goal-label-wrap">
                    <span>{tr("dash_new_label", "🌱 Novos:")} <b>{stats.goals.new_done} / {stats.goals.new_limit}</b></span>
                    <span style="color: {new_c}; font-weight: 700;">{stats.goals.new_pct:.0f}%</span>
                </div>
                <div class="dash-progress-track">
                    <div class="dash-progress-fill" style="width: {stats.goals.new_pct}%; background: {new_c};"></div>
                </div>
            </div>
            <div class="dash-goal-row" style="margin-top: 10px;">
                <div class="dash-goal-label-wrap">
                    <span>{tr("dash_rev_label", "📅 Revisões:")} <b>{stats.goals.rev_done} / {stats.goals.rev_limit}</b></span>
                    <span style="color: {rev_c}; font-weight: 700;">{stats.goals.rev_pct:.0f}%</span>
                </div>
                <div class="dash-progress-track">
                    <div class="dash-progress-fill" style="width: {stats.goals.rev_pct}%; background: {rev_c};"></div>
                </div>
            </div>
            <div class="dash-streak-badge">
                {tr("dash_streak", "🔥 Sequência: <b>{days} dias seguidos</b>", days=stats.today.streak_days)}
            </div>
        </div>
        """)

    # Card 2: Progresso de Hoje
    if show_today:
        retention_color = rev_c if stats.today.retention_rate_pct >= 85 else ("#fbbf24" if stats.today.retention_rate_pct >= 75 else "#f87171")
        done_badge_text = tr("dash_done_badge", "{count} feitas", count=stats.today.studied_count)
        cards_html.append(f"""
        <div class="dash-card">
            <div class="dash-card-header">
                <div class="dash-title-wrap">
                    <span class="dash-icon">⚡</span>
                    <span class="dash-card-title">{tr("dash_today_progress", "Progresso de Hoje")}</span>
                </div>
                <span class="dash-badge">{done_badge_text}</span>
            </div>
            <div class="dash-metric-primary">
                <div class="dash-big-number">{stats.today.studied_count}</div>
                <div class="dash-metric-label">{tr("dash_cards_completed_today", "Cartões Concluídos Hoje")}</div>
            </div>
            <div class="dash-metrics-grid">
                <div class="dash-sub-metric">
                    <span class="dash-sub-label">{tr("dash_time_spent", "⏱️ Tempo Gasto")}</span>
                    <span class="dash-sub-val">{stats.today.formatted_time}</span>
                </div>
                <div class="dash-sub-metric">
                    <span class="dash-sub-label">{tr("dash_retention", "🎯 Retenção")}</span>
                    <span class="dash-sub-val" style="color: {retention_color}; font-weight: 700;">{stats.today.retention_rate_pct:.1f}%</span>
                </div>
                <div class="dash-sub-metric">
                    <span class="dash-sub-label">{tr("dash_pace", "🏃 Ritmo")}</span>
                    <span class="dash-sub-val">{stats.today.seconds_per_card:.1f}s / card</span>
                </div>
                <div class="dash-sub-metric">
                    <span class="dash-sub-label">{tr("dash_speed", "📈 Velocidade")}</span>
                    <span class="dash-sub-val">{stats.today.cards_per_minute:.1f} cards/min</span>
                </div>
            </div>
        </div>
        """)

    # Card 3: Fila de Hoje (Para Zerar)
    if show_remaining:
        clear_badge_text = tr("dash_to_clear", "{count} para zerar", count=stats.remaining.total_remaining)
        cards_html.append(f"""
        <div class="dash-card">
            <div class="dash-card-header">
                <div class="dash-title-wrap">
                    <span class="dash-icon">⏳</span>
                    <span class="dash-card-title">{tr("dash_queue_today", "Fila de Hoje")}</span>
                </div>
                <span class="dash-badge remaining-badge">{clear_badge_text}</span>
            </div>
            <div class="dash-metric-primary">
                <div class="dash-big-number" style="color: {new_c};">{stats.remaining.total_remaining}</div>
                <div class="dash-metric-label">{tr("dash_session_pending", "Pendentes na Sessão de Hoje")}</div>
            </div>
            <div class="dash-metrics-grid">
                <div class="dash-sub-metric">
                    <span class="dash-sub-label">{tr("dash_new_today", "🌱 Novos Hoje")}</span>
                    <span class="dash-sub-val" style="color: {new_c}; font-weight: 700;">{stats.remaining.new_cards} <span style="font-size:10px; opacity:0.75;">(de {stats.composition.unseen})</span></span>
                </div>
                <div class="dash-sub-metric">
                    <span class="dash-sub-label">{tr("dash_learning", "🔄 Aprendizado")}</span>
                    <span class="dash-sub-val" style="color: {learn_c}; font-weight: 700;">{stats.remaining.learn_cards}</span>
                </div>
                <div class="dash-sub-metric">
                    <span class="dash-sub-label">{tr("dash_review_today", "📅 Revisão Hoje")}</span>
                    <span class="dash-sub-val" style="color: {rev_c}; font-weight: 700;">{stats.remaining.review_cards} <span style="font-size:10px; opacity:0.75;">(de {stats.composition.due_reviews_total})</span></span>
                </div>
                <div class="dash-sub-metric">
                    <span class="dash-sub-label">{tr("dash_tomorrow", "🔮 Amanhã")}</span>
                    <span class="dash-sub-val">+{stats.remaining.tomorrow_forecast}</span>
                </div>
            </div>
        </div>
        """)

    # Card 4: Acervo Total do Baralho
    if show_comp:
        cards_badge_text = tr("dash_cards_badge", "{count} cards", count=stats.composition.total_cards)
        cards_html.append(f"""
        <div class="dash-card">
            <div class="dash-card-header">
                <div class="dash-title-wrap">
                    <span class="dash-icon">📚</span>
                    <span class="dash-card-title">{tr("dash_deck_library", "Acervo Total")}</span>
                </div>
                <span class="dash-badge done-badge">{cards_badge_text}</span>
            </div>
            <div class="dash-metric-primary">
                <div class="dash-big-number" style="color: {rev_c};">{stats.composition.mature_pct:.1f}%</div>
                <div class="dash-metric-label">{tr("dash_maturity_rate", "Grau de Maturação (≥ 21d)")}</div>
            </div>
            <div class="dash-metrics-grid">
                <div class="dash-sub-metric">
                    <span class="dash-sub-label">{tr("dash_mature", "🌳 Maduros")}</span>
                    <span class="dash-sub-val" style="color: {rev_c}; font-weight: 700;">{stats.composition.mature}</span>
                </div>
                <div class="dash-sub-metric">
                    <span class="dash-sub-label">{tr("dash_young", "🌿 Jovens (&lt;21d)")}</span>
                    <span class="dash-sub-val">{stats.composition.young}</span>
                </div>
                <div class="dash-sub-metric">
                    <span class="dash-sub-label">{tr("dash_unseen", "🌱 Não Vistos")}</span>
                    <span class="dash-sub-val" style="color: {new_c};">{stats.composition.unseen}</span>
                </div>
                <div class="dash-sub-metric">
                    <span class="dash-sub-label">{tr("dash_suspended", "💤 Suspensos")}</span>
                    <span class="dash-sub-val">{stats.composition.suspended + stats.composition.buried}</span>
                </div>
            </div>
        </div>
        """)

    # Card 5: Concluídos Hoje
    if show_done:
        again_color = "#f87171" if stats.done.again_count > 0 else "inherit"
        fail_pct_text = tr("dash_fail_pct", "({rate:.1f}% falhas)", rate=stats.done.fail_rate_pct)
        lapses_text = tr("dash_errors_again", "❌ Erros (Again): <b>{count}</b>", count=stats.done.again_count)
        cards_html.append(f"""
        <div class="dash-card">
            <div class="dash-card-header">
                <div class="dash-title-wrap">
                    <span class="dash-icon">✅</span>
                    <span class="dash-card-title">{tr("dash_completed_today", "Concluídos Hoje")}</span>
                </div>
                <span class="dash-badge done-badge">{tr("dash_breakdown", "Detalhamento")}</span>
            </div>
            <div class="dash-metrics-grid" style="margin-top: 8px;">
                <div class="dash-sub-metric">
                    <span class="dash-sub-label">{tr("dash_new_learned", "🌱 Novos Aprendidos")}</span>
                    <span class="dash-sub-val">{stats.done.new_learned}</span>
                </div>
                <div class="dash-sub-metric">
                    <span class="dash-sub-label">{tr("dash_learn_reps", "🔄 Repetições Aprend.")}</span>
                    <span class="dash-sub-val">{stats.done.learn_reps}</span>
                </div>
                <div class="dash-sub-metric">
                    <span class="dash-sub-label">{tr("dash_reviews_done", "📝 Revisões Feitas")}</span>
                    <span class="dash-sub-val">{stats.done.review_reps}</span>
                </div>
                <div class="dash-sub-metric">
                    <span class="dash-sub-label">{tr("dash_mature_reviewed", "🌳 Maduros Revisados")}</span>
                    <span class="dash-sub-val">{stats.done.mature_reviewed}</span>
                </div>
            </div>
            <div class="dash-error-breakdown">
                <span>{lapses_text}</span>
                <span style="color: {again_color};">{fail_pct_text}</span>
            </div>
        </div>
        """)

    card_is_light = is_light_color(card_bg)

    # High-contrast scope pill styling
    if card_is_light:
        pill_bg = "rgba(0, 0, 0, 0.05)"
        pill_color = accent if get_contrast_ratio(get_perceptual_luminance(accent), get_perceptual_luminance(card_bg)) >= 4.0 else get_accessible_text_color(card_bg)
    else:
        pill_bg = "rgba(255, 255, 255, 0.06)"
        pill_color = accent

    # High-contrast badges according to background luminance
    if card_is_light:
        rem_bg = "rgba(2, 132, 199, 0.12)"
        rem_color = "#0369a1"
        rem_border = "1px solid rgba(2, 132, 199, 0.35)"

        done_bg = "rgba(22, 163, 74, 0.12)"
        done_color = "#15803d"
        done_border = "1px solid rgba(22, 163, 74, 0.35)"

        streak_bg = "rgba(217, 119, 6, 0.12)"
        streak_color = "#b45309"
        streak_border = "1px solid rgba(217, 119, 6, 0.35)"
    else:
        rem_bg = "rgba(56, 189, 248, 0.18)"
        rem_color = new_c
        rem_border = "1px solid rgba(56, 189, 248, 0.35)"

        done_bg = "rgba(74, 222, 128, 0.18)"
        done_color = rev_c
        done_border = "1px solid rgba(74, 222, 128, 0.35)"

        streak_bg = "rgba(251, 146, 60, 0.15)"
        streak_color = "#fb923c"
        streak_border = "1px solid rgba(251, 146, 60, 0.3)"

    text_sec_safe = text_sec if get_contrast_ratio(get_perceptual_luminance(text_sec), get_perceptual_luminance(card_bg)) >= 4.0 else ("#475569" if card_is_light else "#cbd5e1")

    all_cards_str = "\n".join(cards_html)
    actual_cols = min(columns, max(1, len(cards_html)))

    return f"""
    <div id="modern-stats-dashboard-wrapper">
        <style>
            #modern-stats-dashboard-wrapper {{
                display: block !important;
                width: 95% !important;
                max-width: 1040px !important;
                margin: 20px auto 25px auto !important;
                clear: both !important;
                box-sizing: border-box !important;
                text-align: left !important;
                position: relative !important;
                z-index: 50 !important;
                color: {text_pri} !important;
            }}

            .dash-header-row {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 12px;
                padding: 0 4px;
            }}

            .dash-scope-pill {{
                font-size: 13px;
                font-weight: 700;
                color: {pill_color} !important;
                background: {pill_bg} !important;
                padding: 4px 14px;
                border-radius: 20px;
                border: 1px solid {border};
                display: inline-block;
            }}

            .dash-grid {{
                display: grid !important;
                grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)) !important;
                gap: 14px !important;
                width: 100% !important;
                box-sizing: border-box !important;
            }}

            @media (min-width: 900px) {{
                .dash-grid {{
                    grid-template-columns: repeat({actual_cols}, 1fr) !important;
                }}
            }}

            .dash-card {{
                background-color: {card_bg} !important;
                border: 1px solid {border} !important;
                border-radius: 16px !important;
                padding: 16px 18px !important;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15) !important;
                box-sizing: border-box !important;
                transition: transform 0.18s ease, box-shadow 0.18s ease !important;
                color: {text_pri} !important;
            }}

            .dash-card:hover {{
                transform: translateY(-2px) !important;
                box-shadow: 0 10px 28px rgba(0, 0, 0, 0.25) !important;
            }}

            .dash-card-header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 8px;
            }}

            .dash-title-wrap {{
                display: flex;
                align-items: center;
                gap: 6px;
            }}

            .dash-icon {{
                font-size: 17px;
            }}

            .dash-card-title {{
                font-size: 14px;
                font-weight: 700;
                color: {text_pri};
            }}

            .dash-badge {{
                font-size: 11px;
                font-weight: 600;
                padding: 2px 8px;
                border-radius: 10px;
                background: rgba(120, 120, 120, 0.2);
                color: {text_sec_safe};
            }}

            .remaining-badge {{
                background: {rem_bg} !important;
                color: {rem_color} !important;
                border: {rem_border} !important;
            }}

            .done-badge {{
                background: {done_bg} !important;
                color: {done_color} !important;
                border: {done_border} !important;
            }}

            .dash-metric-primary {{
                text-align: center;
                padding: 4px 0 8px 0;
                border-bottom: 1px dashed {border};
                margin-bottom: 8px;
            }}

            .dash-big-number {{
                font-size: 26px;
                font-weight: 800;
                line-height: 1.1;
                color: {accent};
            }}

            .dash-metric-label {{
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                color: {text_sec_safe};
                margin-top: 2px;
            }}

            .dash-metrics-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 6px 10px;
            }}

            .dash-sub-metric {{
                display: flex;
                flex-direction: column;
            }}

            .dash-sub-label {{
                font-size: 11px;
                color: {text_sec_safe};
                margin-bottom: 2px;
            }}

            .dash-sub-val {{
                font-size: 13px;
                font-weight: 600;
                color: {text_pri};
            }}

            .dash-goal-row {{
                margin-top: 6px;
            }}

            .dash-goal-label-wrap {{
                display: flex;
                justify-content: space-between;
                font-size: 12px;
                margin-bottom: 4px;
            }}

            .dash-progress-track {{
                width: 100%;
                height: 8px;
                background: rgba(120, 120, 120, 0.25);
                border-radius: 4px;
                overflow: hidden;
            }}

            .dash-progress-fill {{
                height: 100%;
                border-radius: 4px;
                transition: width 0.3s ease;
            }}

            .dash-streak-badge {{
                margin-top: 10px;
                padding: 4px 8px;
                background: {streak_bg} !important;
                border: {streak_border} !important;
                border-radius: 8px;
                font-size: 11px;
                color: {streak_color} !important;
                text-align: center;
            }}

            .dash-error-breakdown {{
                margin-top: 8px;
                padding-top: 6px;
                border-top: 1px dashed {border};
                display: flex;
                justify-content: space-between;
                font-size: 11px;
                color: {text_sec};
            }}
        </style>

        <div class="dash-header-row">
            <span class="dash-scope-pill">{scope_title}</span>
        </div>
        <div class="dash-grid">
            {all_cards_str}
        </div>
    </div>
    """
