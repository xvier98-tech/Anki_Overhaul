# -*- coding: utf-8 -*-
"""
Floating Action Button (FAB) HTML/CSS/JS Injection for Reviewer and Anki screens.
Expanded, comfortable typography, progress bar, focus mode (fullscreen) button and resilient event dispatching.
"""

from typing import Dict, Any, Optional

try:
    from aqt import mw
except ImportError:
    mw = None

from .timer_engine import PomodoroEngine, PomodoroState


def get_reviewer_fab_html(
    engine: PomodoroEngine,
    config: Dict[str, Any],
    rem_cards: int = 0,
    is_fullscreen: Optional[bool] = None,
) -> str:
    """
    Generates floating HTML/CSS/JS widget for Anki screens.
    """
    if not config.get("enabled", True):
        return ""

    if is_fullscreen is None:
        is_fullscreen = mw.isFullScreen() if mw else False

    formatted_time = engine.get_formatted_time()
    rem_sec = engine.remaining_seconds
    total_sec = max(1, engine.total_phase_seconds)
    progress_pct = max(0.0, min(100.0, ((total_sec - rem_sec) / total_sec) * 100.0))

    completed_cycles = engine.completed_cycles
    is_running = engine.is_running
    is_started = engine.is_started

    eta_data = engine.fatigue_tracker.compute_eta(rem_cards)
    eta_str = eta_data["formatted_eta"] if rem_cards > 0 else "0m"

    if not is_started or not is_running:
        state_label = "Pausado" if is_started else "Pronto"
        state_class = "state-paused"
        play_btn_icon = "▶️"
        play_btn_title = "Iniciar Pomodoro (Alt+P)"
        icon_symbol = "⏸️" if is_started else "🍅"
    elif engine.state == PomodoroState.SOFT_BREAK:
        state_label = "Pausa Suave"
        state_class = "state-soft-break"
        play_btn_icon = "⏸️"
        play_btn_title = "Pausar (Alt+P)"
        icon_symbol = "⏸️"
    elif engine.state in (PomodoroState.BREAK, PomodoroState.LONG_BREAK):
        state_label = "Intervalo"
        state_class = "state-break"
        play_btn_icon = "⏸️"
        play_btn_title = "Pausar (Alt+P)"
        icon_symbol = "☕"
    else:
        state_label = "Foco"
        state_class = "state-work"
        play_btn_icon = "⏸️"
        play_btn_title = "Pausar (Alt+P)"
        icon_symbol = "🍅"

    focus_btn_text = "🗗 Sair Foco" if is_fullscreen else "🎯 Modo Foco"
    focus_btn_title = "Modo Foco em Tela Cheia (Pressione Esc para sair)"

    def make_btn_onclick(cmd_name: str) -> str:
        return f"event.preventDefault(); event.stopPropagation(); pomoExec('{cmd_name}', this);"

    play_onclick = make_btn_onclick("pomo_toggle_pause")
    focus_onclick = make_btn_onclick("pomo_toggle_fullscreen")
    skip_onclick = make_btn_onclick("pomo_skip_break")
    reset_onclick = make_btn_onclick("pomo_reset_phase")
    cfg_onclick = make_btn_onclick("pomo_open_config")

    return f"""
    <div id="pomo-fab-container" class="{state_class}">
        <style>
            #pomo-fab-container {{
                position: fixed !important;
                bottom: 24px !important;
                right: 24px !important;
                z-index: 2147483647 !important;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
                -webkit-font-smoothing: antialiased;
                box-sizing: border-box !important;
                user-select: none !important;
                pointer-events: auto !important;
                transform: none !important;
                isolation: isolate !important;
            }}

            #pomo-fab-card {{
                background: rgba(15, 17, 24, 0.95) !important;
                backdrop-filter: blur(20px) !important;
                -webkit-backdrop-filter: blur(20px) !important;
                border: 1.5px solid rgba(80, 100, 140, 0.5) !important;
                border-radius: 22px !important;
                box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6), 0 0 1px rgba(255, 255, 255, 0.15) !important;
                padding: 10px 18px !important;
                display: flex !important;
                flex-direction: column !important;
                color: #f8fafc !important;
                transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
                min-width: 250px !important;
                box-sizing: border-box !important;
                pointer-events: auto !important;
            }}

            #pomo-fab-container.pomo-expanded #pomo-fab-card {{
                min-width: 360px !important;
                max-width: 400px !important;
                padding: 14px 20px !important;
            }}

            .pomo-header-row {{
                display: flex !important;
                align-items: center !important;
                justify-content: space-between !important;
                gap: 10px !important;
                pointer-events: auto !important;
            }}

            .pomo-left-group {{
                display: flex !important;
                align-items: center !important;
                gap: 9px !important;
            }}

            .pomo-icon {{
                font-size: 20px !important;
                line-height: 1 !important;
            }}

            .pomo-timer-display {{
                font-size: 20px !important;
                font-weight: 800 !important;
                font-family: "SF Mono", "Roboto Mono", Consolas, monospace !important;
                color: #ffffff !important;
                min-width: 62px !important;
                text-align: center !important;
                letter-spacing: 0.5px !important;
            }}

            .pomo-badge {{
                font-size: 12px !important;
                font-weight: 700 !important;
                padding: 3px 9px !important;
                border-radius: 12px !important;
                text-transform: uppercase !important;
                letter-spacing: 0.5px !important;
            }}

            .state-work .pomo-badge {{
                background: rgba(239, 68, 68, 0.25) !important;
                color: #fca5a5 !important;
                border: 1px solid rgba(239, 68, 68, 0.4) !important;
            }}
            .state-break .pomo-badge, .state-soft-break .pomo-badge {{
                background: rgba(34, 197, 94, 0.25) !important;
                color: #86efac !important;
                border: 1px solid rgba(34, 197, 94, 0.4) !important;
            }}
            .state-paused .pomo-badge {{
                background: rgba(234, 179, 8, 0.25) !important;
                color: #fde047 !important;
                border: 1px solid rgba(234, 179, 8, 0.4) !important;
            }}

            .pomo-cycles {{
                font-size: 13px !important;
                font-weight: 700 !important;
                color: #94a3b8 !important;
            }}

            .pomo-btn-group {{
                display: flex !important;
                align-items: center !important;
                gap: 6px !important;
                pointer-events: auto !important;
            }}

            .pomo-btn-icon {{
                background: rgba(255, 255, 255, 0.08) !important;
                border: 1px solid rgba(255, 255, 255, 0.15) !important;
                color: #ffffff !important;
                border-radius: 10px !important;
                width: 32px !important;
                height: 32px !important;
                font-size: 14px !important;
                cursor: pointer !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                transition: all 0.15s ease !important;
                pointer-events: auto !important;
            }}

            .pomo-btn-icon:hover {{
                background: rgba(255, 255, 255, 0.2) !important;
                transform: scale(1.06) !important;
            }}

            /* Expanded View */
            #pomo-expanded-section {{
                display: none !important;
                margin-top: 12px !important;
                padding-top: 10px !important;
                border-top: 1px solid rgba(148, 163, 184, 0.2) !important;
                flex-direction: column !important;
                gap: 10px !important;
                pointer-events: auto !important;
            }}

            #pomo-fab-container.pomo-expanded #pomo-expanded-section {{
                display: flex !important;
            }}

            .pomo-progress-track {{
                width: 100% !important;
                height: 6px !important;
                background: rgba(255, 255, 255, 0.12) !important;
                border-radius: 6px !important;
                overflow: hidden !important;
            }}

            .pomo-progress-fill {{
                height: 100% !important;
                background: linear-gradient(90deg, #38bdf8 0%, #0284c7 100%) !important;
                width: {progress_pct:.1f}% !important;
                border-radius: 6px !important;
                transition: width 0.3s ease !important;
            }}

            .pomo-eta-row {{
                font-size: 13px !important;
                text-align: center !important;
                color: #cbd5e1 !important;
                display: flex !important;
                justify-content: space-between !important;
                padding: 2px 4px !important;
            }}

            .pomo-actions-bar {{
                display: flex !important;
                gap: 6px !important;
                justify-content: center !important;
                margin-top: 4px !important;
                flex-wrap: wrap !important;
                pointer-events: auto !important;
            }}

            .pomo-action-btn {{
                background: rgba(56, 189, 248, 0.16) !important;
                border: 1px solid rgba(56, 189, 248, 0.4) !important;
                border-radius: 10px !important;
                padding: 7px 11px !important;
                font-size: 12px !important;
                font-weight: 700 !important;
                cursor: pointer !important;
                color: #f8fafc !important;
                transition: all 0.18s ease !important;
                display: flex !important;
                align-items: center !important;
                gap: 4px !important;
                flex: 1 1 auto !important;
                justify-content: center !important;
                min-width: 75px !important;
                pointer-events: auto !important;
            }}

            .pomo-action-btn:hover {{
                background: rgba(56, 189, 248, 0.35) !important;
                border-color: #38bdf8 !important;
                transform: translateY(-1px) !important;
            }}

            .pomo-action-btn.pomo-focus-btn {{
                background: rgba(168, 85, 247, 0.2) !important;
                border-color: rgba(168, 85, 247, 0.5) !important;
            }}
            .pomo-action-btn.pomo-focus-btn:hover {{
                background: rgba(168, 85, 247, 0.4) !important;
                border-color: #c084fc !important;
            }}
        </style>

        <div id="pomo-fab-card">
            <div class="pomo-header-row">
                <div class="pomo-left-group">
                    <span id="pomo-state-icon" class="pomo-icon">{icon_symbol}</span>
                    <span id="pomo-timer-text" class="pomo-timer-display">{formatted_time}</span>
                    <span id="pomo-badge-text" class="pomo-badge">{state_label}</span>
                </div>
                <div class="pomo-btn-group">
                    <span class="pomo-cycles">🍅x{completed_cycles}</span>
                    <button type="button" id="pomo-play-btn" class="pomo-btn-icon" tabindex="-1" title="{play_btn_title}" onpointerdown="event.stopPropagation();" onmousedown="event.stopPropagation();" onclick="{play_onclick}">{play_btn_icon}</button>
                    <button type="button" id="pomo-expand-btn" class="pomo-btn-icon" tabindex="-1" title="Expandir / Minimizar" onpointerdown="event.stopPropagation();" onmousedown="event.stopPropagation();" onclick="event.preventDefault(); event.stopPropagation(); var el = document.getElementById('pomo-fab-container'); if (el) el.classList.toggle('pomo-expanded');">⛶</button>
                </div>
            </div>

            <div id="pomo-expanded-section">
                <div class="pomo-progress-track">
                    <div id="pomo-progress-bar" class="pomo-progress-fill"></div>
                </div>
                <div class="pomo-eta-row">
                    <span>Restantes: <b>{rem_cards}</b></span>
                    <span>ETA: <b>{eta_str}</b></span>
                </div>
                <div class="pomo-actions-bar">
                    <button type="button" id="pomo-focus-btn" class="pomo-action-btn pomo-focus-btn" tabindex="-1" title="{focus_btn_title}" onpointerdown="event.stopPropagation();" onmousedown="event.stopPropagation();" onclick="{focus_onclick}">{focus_btn_text}</button>
                    <button type="button" id="pomo-skip-btn" class="pomo-action-btn" tabindex="-1" onpointerdown="event.stopPropagation();" onmousedown="event.stopPropagation();" onclick="{skip_onclick}">⏩ Intervalo</button>
                    <button type="button" id="pomo-reset-btn" class="pomo-action-btn" tabindex="-1" onpointerdown="event.stopPropagation();" onmousedown="event.stopPropagation();" onclick="{reset_onclick}">🔄 Reset</button>
                    <button type="button" id="pomo-cfg-btn" class="pomo-action-btn" tabindex="-1" onpointerdown="event.stopPropagation();" onmousedown="event.stopPropagation();" onclick="{cfg_onclick}">⚙️ Config</button>
                </div>
            </div>
        </div>

        <img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" style="display:none;" onload="(function(){{
            window.pomoTotalSec = {rem_sec};
            window.pomoMaxSec = {total_sec};
            window.pomoIsRunning = {'true' if is_running else 'false'};

            window.pomoExec = function(cmd, btnEl) {{
                if (btnEl) {{
                    btnEl.style.outline = '2px solid #eab308';
                    setTimeout(function() {{ btnEl.style.outline = ''; }}, 250);
                }}
                try {{
                    if (typeof window.pycmd === 'function') {{
                        window.pycmd(cmd);
                        return;
                    }}
                }} catch(e) {{}}
                try {{
                    if (typeof pycmd === 'function') {{
                        pycmd(cmd);
                        return;
                    }}
                }} catch(e) {{}}
                try {{
                    if (typeof window.bridgeCommand === 'function') {{
                        window.bridgeCommand(cmd);
                        return;
                    }}
                }} catch(e) {{}}
                try {{
                    if (typeof bridgeCommand === 'function') {{
                        bridgeCommand(cmd);
                        return;
                    }}
                }} catch(e) {{}}
                try {{
                    if (typeof qt !== 'undefined' && qt.webChannelTransport && typeof QWebChannel !== 'undefined') {{
                        new QWebChannel(qt.webChannelTransport, function(channel) {{
                            channel.objects.py.cmd(cmd, function(){{}});
                        }});
                        return;
                    }}
                }} catch(e) {{}}
                if (btnEl) {{
                    btnEl.style.outline = '2px solid #ef4444';
                }}
                console.error('pomoExec failed for:', cmd);
            }};

            if (window._pomoIntervalInstance) {{
                clearInterval(window._pomoIntervalInstance);
            }}

            window._pomoIntervalInstance = setInterval(function() {{
                if (window.pomoIsRunning && window.pomoTotalSec > 0) {{
                    window.pomoTotalSec--;
                    var m = Math.floor(window.pomoTotalSec / 60);
                    var s = window.pomoTotalSec % 60;
                    var formatted = (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
                    var timerEl = document.getElementById('pomo-timer-text');
                    if (timerEl) {{
                        timerEl.innerText = formatted;
                    }}
                    var bar = document.getElementById('pomo-progress-bar');
                    if (bar && window.pomoMaxSec > 0) {{
                        var pct = Math.max(0, Math.min(100, ((window.pomoMaxSec - window.pomoTotalSec) / window.pomoMaxSec) * 100));
                        bar.style.width = pct + '%';
                    }}
                }}
            }}, 1000);
        }})();" />
    </div>
    """
