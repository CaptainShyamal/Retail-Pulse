"""
Enterprise High-Contrast Design System & Animation Engine for RetailPulse
- Canvas: Ultra-deep Navy / Charcoal (#080C14 / #0B1120)
- Cards & Panels: Elevated Dark Slate (#111827 / #0F172A) with crisp borders (#1E293B / #334155)
- Color System:
    * Primary Actions / Actuals: Electric Blue (#2563EB / #3B82F6)
    * ML Forecasts / Demand Spikes: Cyan (#06B6D4 / #22D3EE)
    * Healthy / Resolved: Emerald Green (#10B981 / #059669)
    * Critical / Stockouts: Crimson Red (#EF4444 / #DC2626)
    * Shelf Sensors / Medium: Amber Orange (#F59E0B / #D97706)
    * Secondary / Graph: Purple (#8B5CF6 / #A855F7)
- Smooth CSS Transitions, Card Elevations, Staggered Feed Animations, and Accessible Contrast
"""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

:root {
    --bg-canvas: #080C14;
    --bg-panel: #111827;
    --bg-panel-hover: #162032;
    --border-subtle: #1E293B;
    --border-bright: #334155;
    
    --accent-blue: #2563EB;
    --accent-blue-light: #3B82F6;
    --accent-cyan: #06B6D4;
    --accent-cyan-light: #22D3EE;
    --accent-green: #10B981;
    --accent-red: #EF4444;
    --accent-amber: #F59E0B;
    --accent-purple: #8B5CF6;
    
    --text-primary: #FFFFFF;
    --text-body: #E2E8F0;
    --text-muted: #94A3B8;
    --text-subtle: #64748B;
}

/* Base Canvas */
html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    background-color: var(--bg-canvas) !important;
    color: var(--text-body) !important;
    -webkit-font-smoothing: antialiased;
}

/* Hide default Streamlit sidebar & deploy toolbar */
[data-testid="stSidebar"], .stDeployButton, [data-testid="stToolbar"], #MainMenu, footer, header {
    display: none !important;
    visibility: hidden !important;
}

.main .block-container {
    padding-top: 1rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 1380px !important;
    animation: fadeInPage 0.35s ease-out;
}

@keyframes fadeInPage {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Top Header Bar */
.top-header-bar {
    background: linear-gradient(135deg, #111827 0%, #0F172A 100%);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    padding: 0.9rem 1.4rem;
    margin-bottom: 1.3rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.45);
    transition: border-color 0.25s ease;
}

.top-header-bar:hover {
    border-color: var(--border-bright);
}

.header-brand {
    display: flex;
    align-items: center;
    gap: 12px;
}

.header-logo-icon {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
    color: #FFFFFF;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
    font-weight: 800;
    box-shadow: 0 0 20px rgba(37, 99, 235, 0.55);
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.header-logo-icon:hover {
    transform: scale(1.05);
    box-shadow: 0 0 26px rgba(37, 99, 235, 0.75);
}

.header-brand-title {
    font-size: 1.3rem;
    font-weight: 800;
    color: #FFFFFF !important;
    letter-spacing: -0.025em;
    margin: 0;
}

.header-status-pill {
    background-color: rgba(37, 99, 235, 0.12);
    color: #93C5FD;
    border: 1px solid rgba(59, 130, 246, 0.35);
    font-weight: 700;
    font-size: 0.78rem;
    padding: 0.35rem 0.85rem;
    border-radius: 9999px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    letter-spacing: 0.02em;
}

/* Pulsing Live Telemetry Indicator */
.live-pulse-dot {
    width: 8px;
    height: 8px;
    background-color: #10B981;
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
    animation: livePulse 2s infinite;
}

@keyframes livePulse {
    0% {
        transform: scale(0.95);
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
    }
    70% {
        transform: scale(1);
        box-shadow: 0 0 0 7px rgba(16, 185, 129, 0);
    }
    100% {
        transform: scale(0.95);
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
    }
}

.live-pulse-cyan {
    background-color: #06B6D4 !important;
    box-shadow: 0 0 0 0 rgba(6, 182, 212, 0.7) !important;
    animation: livePulseCyan 2s infinite !important;
}

@keyframes livePulseCyan {
    0% {
        transform: scale(0.95);
        box-shadow: 0 0 0 0 rgba(6, 182, 212, 0.7);
    }
    70% {
        transform: scale(1);
        box-shadow: 0 0 0 7px rgba(6, 182, 212, 0);
    }
    100% {
        transform: scale(0.95);
        box-shadow: 0 0 0 0 rgba(6, 182, 212, 0);
    }
}

/* Plotly Graph Container Animation Styling */
.js-plotly-plot .plotly .modebar {
    background: transparent !important;
}

.js-plotly-plot .plotly .updatemenu-button {
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}

.js-plotly-plot .plotly .updatemenu-button:hover {
    fill: #2563EB !important;
}

/* Top Navigation Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background-color: #0F172A;
    padding: 6px;
    border-radius: 14px;
    border: 1px solid var(--border-subtle);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
    margin-bottom: 1.4rem;
}

.stTabs [data-baseweb="tab"] {
    height: 44px;
    border-radius: 10px;
    color: var(--text-muted) !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    padding: 0 1.3rem !important;
    background-color: transparent !important;
    border: 1px solid transparent !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

.stTabs [data-baseweb="tab"]:hover {
    color: #FFFFFF !important;
    background-color: #1E293B !important;
    border-color: #334155 !important;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    border-color: #3B82F6 !important;
    box-shadow: 0 4px 16px rgba(37, 99, 235, 0.45) !important;
}

.stTabs [data-baseweb="tab-panel"] {
    animation: tabFadeIn 0.25s ease-out;
}

@keyframes tabFadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}

/* High-Contrast Stat Cards */
.stat-card-clean {
    background: linear-gradient(180deg, #111827 0%, #0F172A 100%);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    padding: 1.3rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.25);
    position: relative;
    overflow: hidden;
    transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.25s ease, border-color 0.25s ease;
}

.stat-card-clean:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 28px rgba(0, 0, 0, 0.45);
    border-color: var(--border-bright);
}

.stat-card-clean::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 4px;
    background: var(--accent-blue);
    transition: height 0.2s ease;
}

.stat-card-clean:hover::before {
    height: 5px;
}

.stat-card-clean.blue-top::before { background: var(--accent-blue); }
.stat-card-clean.cyan-top::before { background: var(--accent-cyan); }
.stat-card-clean.white-top::before { background: #E2E8F0; }
.stat-card-clean.green-top::before { background: var(--accent-green); }
.stat-card-clean.red-top::before { background: var(--accent-red); }
.stat-card-clean.amber-top::before { background: var(--accent-amber); }

.stat-eyebrow-clean {
    font-size: 0.76rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    margin-bottom: 0.4rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.stat-val-clean {
    font-size: 2.1rem;
    font-weight: 800;
    color: #FFFFFF !important;
    line-height: 1.15;
    letter-spacing: -0.025em;
}

.stat-sub-clean {
    font-size: 0.84rem;
    color: var(--text-muted);
    margin-top: 0.45rem;
    font-weight: 500;
}

/* Panels & Cards */
.panel-card-clean {
    background: linear-gradient(180deg, #111827 0%, #0F172A 100%);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    padding: 1.4rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    margin-bottom: 1.2rem;
    transition: border-color 0.25s ease, box-shadow 0.25s ease;
}

.panel-card-clean:hover {
    border-color: var(--border-bright);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}

/* Action Rows */
.action-row-item {
    background: #0F172A;
    border: 1px solid var(--border-subtle);
    border-left: 4px solid var(--accent-blue);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: transform 0.2s ease, border-color 0.2s ease, background-color 0.2s ease;
}

.action-row-item:hover {
    transform: translateX(3px);
    background: #131E33;
    border-color: var(--border-bright);
}

.action-row-item.danger {
    border-left-color: var(--accent-red);
}

.action-row-item.warning {
    border-left-color: var(--accent-amber);
}

/* Staggered Incident Feed Animation */
.incident-card {
    background: linear-gradient(180deg, #111827 0%, #0F172A 100%);
    border: 1px solid var(--border-subtle);
    border-radius: 14px;
    padding: 14px 18px;
    margin-bottom: 12px;
    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    animation: slideUpFade 0.3s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.incident-card:hover {
    transform: translateY(-2px);
    border-color: var(--border-bright);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
}

@keyframes slideUpFade {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Buttons */
.stButton>button {
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
    color: #FFFFFF !important;
    border: 1px solid #3B82F6 !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
    border-radius: 10px !important;
    padding: 0.52rem 1.4rem !important;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    cursor: pointer;
}

.stButton>button:hover {
    background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
    border-color: #60A5FA !important;
    box-shadow: 0 6px 20px rgba(37, 99, 235, 0.55) !important;
    transform: translateY(-1px);
}

.stButton>button:active {
    transform: scale(0.98) !important;
}

.stDownloadButton>button {
    background-color: #0F172A !important;
    color: #F8FAFC !important;
    border: 1px solid var(--border-bright) !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    border-radius: 10px !important;
    padding: 0.48rem 1.25rem !important;
    transition: all 0.2s ease !important;
}

.stDownloadButton>button:hover {
    background-color: #1E293B !important;
    border-color: var(--accent-blue-light) !important;
    color: #93C5FD !important;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25) !important;
    transform: translateY(-1px);
}

/* Form Controls & Inputs */
.stSelectbox div[data-baseweb="select"] > div {
    background-color: #0F172A !important;
    border: 1px solid var(--border-bright) !important;
    color: #FFFFFF !important;
    border-radius: 10px !important;
    transition: border-color 0.2s ease;
}

.stSelectbox div[data-baseweb="select"] > div:hover {
    border-color: var(--accent-blue-light) !important;
}

/* Headings & Text */
h1, h2, h3, h4, h5, h6 {
    color: #FFFFFF !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
}

p {
    color: var(--text-body) !important;
}

/* Streamlit Metrics */
[data-testid="stMetric"] {
    background: #0F172A;
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 12px 16px;
    transition: border-color 0.2s ease, transform 0.2s ease;
}

[data-testid="stMetric"]:hover {
    border-color: var(--border-bright);
    transform: translateY(-2px);
}

[data-testid="stMetricLabel"] {
    color: var(--text-muted) !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

[data-testid="stMetricValue"] {
    color: #FFFFFF !important;
    font-weight: 800 !important;
    font-size: 1.5rem !important;
}

/* Reduced Motion Support */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}

/* Mobile Responsiveness */
@media (max-width: 768px) {
    .main .block-container {
        padding: 0.5rem !important;
    }
    .top-header-bar {
        flex-direction: column;
        gap: 12px;
        align-items: flex-start;
        padding: 1rem;
    }
    .stat-val-clean {
        font-size: 1.65rem;
    }
}
</style>
"""
