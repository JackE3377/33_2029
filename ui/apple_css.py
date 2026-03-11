# ============================================================
# GEM Protocol — Apple-Style Custom CSS (HIG-Inspired)
# ============================================================
"""
Premium CSS injection for Streamlit, inspired by
Apple Human Interface Guidelines (HIG):

  ✦ San Francisco font stack
  ✦ Glassmorphism cards with backdrop-filter
  ✦ Generous whitespace & visual hierarchy
  ✦ Rounded corners (border-radius: 16px)
  ✦ Subtle drop shadows & depth layers
  ✦ Mobile-friendly responsive layout
  ✦ Dark mode support
  ✦ Smooth animations & transitions
"""

APPLE_CSS = """
<style>
/* ============================================================
   GLOBAL RESET & TYPOGRAPHY (San Francisco Style)
   ============================================================ */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    /* Apple Color Palette */
    --apple-bg:              #f5f5f7;
    --apple-card-bg:         rgba(255, 255, 255, 0.72);
    --apple-card-border:     rgba(0, 0, 0, 0.06);
    --apple-text-primary:    #1d1d1f;
    --apple-text-secondary:  #6e6e73;
    --apple-text-tertiary:   #86868b;
    --apple-accent-blue:     #0071e3;
    --apple-accent-green:    #34c759;
    --apple-accent-red:      #ff3b30;
    --apple-accent-orange:   #ff9500;
    --apple-accent-purple:   #af52de;
    --apple-accent-teal:     #5ac8fa;
    --apple-shadow-soft:     0 2px 12px rgba(0, 0, 0, 0.08);
    --apple-shadow-medium:   0 4px 24px rgba(0, 0, 0, 0.12);
    --apple-shadow-strong:   0 8px 40px rgba(0, 0, 0, 0.16);
    --apple-radius:          16px;
    --apple-radius-sm:       10px;
    --apple-radius-lg:       20px;
    --apple-blur:            20px;
    --apple-transition:      all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1);
}

/* Dark mode variables */
@media (prefers-color-scheme: dark) {
    :root {
        --apple-bg:              #000000;
        --apple-card-bg:         rgba(28, 28, 30, 0.72);
        --apple-card-border:     rgba(255, 255, 255, 0.08);
        --apple-text-primary:    #f5f5f7;
        --apple-text-secondary:  #a1a1a6;
        --apple-text-tertiary:   #6e6e73;
    }
}

/* Streamlit overrides */
.stApp {
    background-color: var(--apple-bg) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', 
                 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
}

/* Hide default Streamlit footer & hamburger */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.block-container {
    padding: 2rem 1.5rem !important;
    max-width: 1400px !important;
}

/* ============================================================
   GLASSMORPHISM CARD
   ============================================================ */
.gem-card {
    background: var(--apple-card-bg);
    backdrop-filter: blur(var(--apple-blur));
    -webkit-backdrop-filter: blur(var(--apple-blur));
    border: 1px solid var(--apple-card-border);
    border-radius: var(--apple-radius);
    padding: 24px 28px;
    margin-bottom: 16px;
    box-shadow: var(--apple-shadow-soft);
    transition: var(--apple-transition);
}

.gem-card:hover {
    box-shadow: var(--apple-shadow-medium);
    transform: translateY(-1px);
}

.gem-card-header {
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    color: var(--apple-text-tertiary);
    margin-bottom: 12px;
}

.gem-card-value {
    font-size: 36px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--apple-text-primary);
    line-height: 1.1;
}

.gem-card-value.positive { color: var(--apple-accent-green); }
.gem-card-value.negative { color: var(--apple-accent-red); }

.gem-card-subtitle {
    font-size: 14px;
    font-weight: 400;
    color: var(--apple-text-secondary);
    margin-top: 6px;
}

/* ============================================================
   ALERT BANNERS
   ============================================================ */
.gem-alert-critical {
    background: linear-gradient(135deg, #ff3b30 0%, #ff6b6b 100%);
    color: white;
    border-radius: var(--apple-radius);
    padding: 18px 24px;
    margin-bottom: 16px;
    font-weight: 500;
    font-size: 15px;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: 0 4px 16px rgba(255, 59, 48, 0.3);
    animation: pulse-glow 2s ease-in-out infinite;
}

.gem-alert-warning {
    background: linear-gradient(135deg, #ff9500 0%, #ffb84d 100%);
    color: white;
    border-radius: var(--apple-radius);
    padding: 16px 24px;
    margin-bottom: 16px;
    font-weight: 500;
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: 0 4px 16px rgba(255, 149, 0, 0.25);
}

.gem-alert-info {
    background: linear-gradient(135deg, #0071e3 0%, #40a0ff 100%);
    color: white;
    border-radius: var(--apple-radius);
    padding: 14px 24px;
    margin-bottom: 16px;
    font-weight: 500;
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: 0 4px 16px rgba(0, 113, 227, 0.2);
}

@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 4px 16px rgba(255, 59, 48, 0.3); }
    50% { box-shadow: 0 4px 24px rgba(255, 59, 48, 0.5); }
}

/* ============================================================
   ENGINE STATUS INDICATORS (Traffic Light)
   ============================================================ */
.gem-status-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 8px;
    vertical-align: middle;
}
.gem-status-dot.green  { background: var(--apple-accent-green); box-shadow: 0 0 8px rgba(52, 199, 89, 0.5); }
.gem-status-dot.yellow { background: var(--apple-accent-orange); box-shadow: 0 0 8px rgba(255, 149, 0, 0.5); }
.gem-status-dot.red    { background: var(--apple-accent-red); box-shadow: 0 0 8px rgba(255, 59, 48, 0.5); }

/* ============================================================
   METRIC GRID
   ============================================================ */
.gem-metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}

.gem-metric-item {
    background: var(--apple-card-bg);
    backdrop-filter: blur(var(--apple-blur));
    -webkit-backdrop-filter: blur(var(--apple-blur));
    border: 1px solid var(--apple-card-border);
    border-radius: var(--apple-radius-sm);
    padding: 20px 22px;
    transition: var(--apple-transition);
}

.gem-metric-item:hover {
    transform: translateY(-2px);
    box-shadow: var(--apple-shadow-medium);
}

.gem-metric-label {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--apple-text-tertiary);
    margin-bottom: 8px;
}

.gem-metric-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--apple-text-primary);
    letter-spacing: -0.02em;
}

.gem-metric-change {
    font-size: 13px;
    font-weight: 500;
    margin-top: 4px;
}
.gem-metric-change.up   { color: var(--apple-accent-green); }
.gem-metric-change.down { color: var(--apple-accent-red); }

/* ============================================================
   SECTION HEADERS
   ============================================================ */
.gem-section-title {
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.015em;
    color: var(--apple-text-primary);
    margin: 32px 0 20px 0;
    padding-bottom: 8px;
}

.gem-section-subtitle {
    font-size: 17px;
    font-weight: 400;
    color: var(--apple-text-secondary);
    margin-top: -12px;
    margin-bottom: 20px;
}

/* ============================================================
   DATA TABLES (Apple Style)
   ============================================================ */
.gem-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    background: var(--apple-card-bg);
    backdrop-filter: blur(var(--apple-blur));
    border-radius: var(--apple-radius);
    overflow: hidden;
    box-shadow: var(--apple-shadow-soft);
    border: 1px solid var(--apple-card-border);
}

.gem-table th {
    background: rgba(0, 0, 0, 0.03);
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--apple-text-tertiary);
    padding: 14px 20px;
    text-align: left;
    border-bottom: 1px solid var(--apple-card-border);
}

.gem-table td {
    font-size: 14px;
    font-weight: 400;
    color: var(--apple-text-primary);
    padding: 14px 20px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.gem-table tr:last-child td {
    border-bottom: none;
}

.gem-table tr:hover td {
    background: rgba(0, 113, 227, 0.04);
}

/* ============================================================
   TAGS / BADGES
   ============================================================ */
.gem-badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.03em;
    padding: 4px 10px;
    border-radius: 20px;
    text-transform: uppercase;
}
.gem-badge.green  { background: rgba(52, 199, 89, 0.12); color: #34c759; }
.gem-badge.red    { background: rgba(255, 59, 48, 0.12); color: #ff3b30; }
.gem-badge.orange { background: rgba(255, 149, 0, 0.12); color: #ff9500; }
.gem-badge.blue   { background: rgba(0, 113, 227, 0.12); color: #0071e3; }
.gem-badge.purple { background: rgba(175, 82, 222, 0.12); color: #af52de; }

/* ============================================================
   NAVIGATION TABS (Streamlit override)
   ============================================================ */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: rgba(0, 0, 0, 0.04);
    border-radius: var(--apple-radius-sm);
    padding: 4px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    font-weight: 500;
    font-size: 14px;
    padding: 8px 20px;
    transition: var(--apple-transition);
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: white;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.stTabs [data-baseweb="tab-highlight"] {
    display: none;
}

/* ============================================================
   BUTTONS (Apple Style)
   ============================================================ */
.stButton > button {
    background: var(--apple-accent-blue) !important;
    color: white !important;
    border: none !important;
    border-radius: 980px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 10px 24px !important;
    transition: var(--apple-transition) !important;
    box-shadow: none !important;
}

.stButton > button:hover {
    background: #0077ed !important;
    transform: scale(1.02);
    box-shadow: 0 4px 12px rgba(0, 113, 227, 0.3) !important;
}

.stButton > button:active {
    transform: scale(0.98);
}

/* Danger button variant */
.danger-btn > button {
    background: var(--apple-accent-red) !important;
}

.danger-btn > button:hover {
    box-shadow: 0 4px 12px rgba(255, 59, 48, 0.3) !important;
}

/* ============================================================
   SIDEBAR (Apple Style)
   ============================================================ */
section[data-testid="stSidebar"] {
    background: rgba(245, 245, 247, 0.95) !important;
    backdrop-filter: blur(20px);
    border-right: 1px solid rgba(0, 0, 0, 0.06);
}

section[data-testid="stSidebar"] .block-container {
    padding-top: 2rem;
}

/* ============================================================
   CHARTS / PLOTS (Minimal Chrome)
   ============================================================ */
.gem-chart-container {
    background: var(--apple-card-bg);
    backdrop-filter: blur(var(--apple-blur));
    border: 1px solid var(--apple-card-border);
    border-radius: var(--apple-radius);
    padding: 24px;
    box-shadow: var(--apple-shadow-soft);
    margin-bottom: 16px;
}

/* ============================================================
   PROGRESS BAR (Goal Tracker)
   ============================================================ */
.gem-progress-container {
    background: rgba(0, 0, 0, 0.06);
    border-radius: 8px;
    height: 8px;
    overflow: hidden;
    margin: 8px 0;
}

.gem-progress-bar {
    height: 100%;
    border-radius: 8px;
    background: linear-gradient(90deg, var(--apple-accent-blue) 0%, var(--apple-accent-teal) 100%);
    transition: width 1s cubic-bezier(0.25, 0.1, 0.25, 1);
}

/* ============================================================
   MOBILE RESPONSIVE
   ============================================================ */
@media (max-width: 768px) {
    .block-container {
        padding: 1rem 0.75rem !important;
    }
    
    .gem-card {
        padding: 18px 20px;
        border-radius: 12px;
    }
    
    .gem-card-value {
        font-size: 28px;
    }
    
    .gem-metric-grid {
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
    }
    
    .gem-metric-value {
        font-size: 22px;
    }
    
    .gem-section-title {
        font-size: 22px;
    }
}

@media (max-width: 480px) {
    .gem-metric-grid {
        grid-template-columns: 1fr;
    }
}

/* ============================================================
   LOADING / SKELETON
   ============================================================ */
.gem-skeleton {
    background: linear-gradient(90deg, 
        rgba(0,0,0,0.06) 25%, 
        rgba(0,0,0,0.1) 50%, 
        rgba(0,0,0,0.06) 75%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s ease-in-out infinite;
    border-radius: 8px;
}

@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

/* ============================================================
   AI INSIGHT CARD
   ============================================================ */
.gem-ai-card {
    background: linear-gradient(135deg, 
        rgba(175, 82, 222, 0.08) 0%, 
        rgba(90, 200, 250, 0.08) 100%
    );
    border: 1px solid rgba(175, 82, 222, 0.15);
    border-radius: var(--apple-radius);
    padding: 24px;
    margin-bottom: 16px;
}

.gem-ai-card .gem-card-header {
    color: var(--apple-accent-purple);
}

/* ============================================================
   STREAMLIT NATIVE OVERRIDES (Clean Up)
   ============================================================ */
div[data-testid="stMetric"] {
    background: var(--apple-card-bg);
    backdrop-filter: blur(var(--apple-blur));
    border: 1px solid var(--apple-card-border);
    border-radius: var(--apple-radius-sm);
    padding: 16px 20px;
    box-shadow: var(--apple-shadow-soft);
}

div[data-testid="stMetric"] label {
    font-size: 12px !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--apple-text-tertiary) !important;
}

div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 28px !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
}

/* Expander */
.streamlit-expanderHeader {
    font-weight: 500 !important;
    font-size: 15px !important;
    border-radius: var(--apple-radius-sm) !important;
}

/* Input fields */
.stTextInput input, .stNumberInput input, .stSelectbox select {
    border-radius: var(--apple-radius-sm) !important;
    border: 1px solid var(--apple-card-border) !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
}

/* Scrollbar */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.15);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 0, 0, 0.3);
}
</style>
"""
