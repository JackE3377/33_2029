# ============================================================
# GEM Protocol v2 — Dark-Mode Glassmorphism CSS
# ============================================================
DARK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --bg:            #000000;
    --card-bg:       rgba(28, 28, 30, 0.75);
    --card-border:   rgba(255, 255, 255, 0.08);
    --text-1:        #f5f5f7;
    --text-2:        #a1a1a6;
    --text-3:        #6e6e73;
    --blue:          #0a84ff;
    --green:         #30d158;
    --red:           #ff453a;
    --orange:        #ff9f0a;
    --purple:        #bf5af2;
    --teal:          #64d2ff;
    --shadow:        0 2px 16px rgba(0,0,0,0.5);
    --radius:        16px;
    --radius-sm:     10px;
    --blur:          24px;
    --transition:    all 0.25s cubic-bezier(.25,.1,.25,1);
}

.stApp {
    background: var(--bg) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display',
                 'Segoe UI', Roboto, sans-serif !important;
    color: var(--text-1) !important;
}
/* Hide ALL Streamlit branding / chrome */
#MainMenu { visibility: hidden !important; }
footer { visibility: hidden !important; }
header { visibility: hidden !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
.stDeployButton { display: none !important; }
.styles_viewerBadge__CvC9N { display: none !important; }  /* Made with Streamlit */
.viewerBadge_container__r5tak { display: none !important; }
.viewerBadge_link__qRIco { display: none !important; }
a[href="https://streamlit.io"] { display: none !important; }
[data-testid="manage-app-button"] { display: none !important; }
[data-testid="stHeader"] { display: none !important; }
.stActionButton { display: none !important; }
.block-container { padding: 1.5rem 2rem !important; max-width: 1440px !important; }

/* ─── Glass Card ─── */
.gc {
    background: var(--card-bg);
    backdrop-filter: blur(var(--blur));
    -webkit-backdrop-filter: blur(var(--blur));
    border: 1px solid var(--card-border);
    border-radius: var(--radius);
    padding: 24px;
    margin-bottom: 16px;
    box-shadow: var(--shadow);
    transition: var(--transition);
}
.gc:hover { border-color: rgba(255,255,255,0.14); transform: translateY(-1px); }

/* ─── Metric ─── */
.gc-label { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; color: var(--text-3); margin-bottom: 6px; }
.gc-value { font-size: 36px; font-weight: 800; letter-spacing: -0.03em; color: var(--text-1); line-height: 1.1; }
.gc-value.big { font-size: 48px; }
.gc-sub   { font-size: 13px; color: var(--text-2); margin-top: 4px; }
.gc-value.up   { color: var(--green); }
.gc-value.down { color: var(--red); }

/* ─── Alert Banners ─── */
.al-crit { background: linear-gradient(135deg, #ff453a 0%, #ff6961 100%); color: #fff; border-radius: var(--radius); padding: 16px 20px; margin-bottom: 14px; font-weight: 500; font-size: 15px; display: flex; align-items: center; gap: 10px; box-shadow: 0 4px 20px rgba(255,69,58,.35); animation: glow 2s ease-in-out infinite; }
.al-warn { background: linear-gradient(135deg, #ff9f0a 0%, #ffb340 100%); color: #fff; border-radius: var(--radius); padding: 14px 20px; margin-bottom: 14px; font-weight: 500; font-size: 14px; display: flex; align-items: center; gap: 10px; }
.al-info { background: linear-gradient(135deg, #0a84ff 0%, #409cff 100%); color: #fff; border-radius: var(--radius); padding: 14px 20px; margin-bottom: 14px; font-weight: 500; font-size: 14px; display: flex; align-items: center; gap: 10px; }
.al-scout { background: linear-gradient(135deg, #30d158 0%, #63e68b 100%); color: #fff; border-radius: var(--radius); padding: 16px 20px; margin-bottom: 14px; font-weight: 600; font-size: 15px; display: flex; align-items: center; gap: 10px; box-shadow: 0 4px 20px rgba(48,209,88,.3); animation: glow-green 2s ease-in-out infinite; }
@keyframes glow { 0%,100%{box-shadow:0 4px 20px rgba(255,69,58,.35)} 50%{box-shadow:0 4px 32px rgba(255,69,58,.55)} }
@keyframes glow-green { 0%,100%{box-shadow:0 4px 20px rgba(48,209,88,.3)} 50%{box-shadow:0 4px 32px rgba(48,209,88,.5)} }

/* ─── Grid ─── */
.mg { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 20px; }
.mg .gc { margin-bottom: 0; }

/* ─── Traffic Light ─── */
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
.dot.g { background: var(--green); box-shadow: 0 0 8px rgba(48,209,88,.5); }
.dot.y { background: var(--orange); box-shadow: 0 0 8px rgba(255,159,10,.5); }
.dot.r { background: var(--red); box-shadow: 0 0 8px rgba(255,69,58,.5); }

/* ─── Table ─── */
.gt { width: 100%; border-collapse: collapse; margin: 12px 0; }
.gt th { text-align: left; padding: 10px 14px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--text-3); border-bottom: 1px solid var(--card-border); }
.gt td { padding: 10px 14px; font-size: 14px; color: var(--text-1); border-bottom: 1px solid rgba(255,255,255,.04); }
.gt tr:hover td { background: rgba(255,255,255,.03); }

/* ─── Section Title ─── */
.st { font-size: 26px; font-weight: 700; letter-spacing: -0.015em; color: var(--text-1); margin: 28px 0 16px; }
.st-sub { font-size: 14px; color: var(--text-2); margin-top: -10px; margin-bottom: 16px; }

/* ─── Score Badge ─── */
.badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; }
.badge.buy  { background: rgba(48,209,88,.18); color: var(--green); }
.badge.hold { background: rgba(255,159,10,.18); color: var(--orange); }
.badge.avoid{ background: rgba(255,69,58,.18); color: var(--red); }

/* ─── Analysis Card ─── */
.ac { background: rgba(191,90,242,.08); border: 1px solid rgba(191,90,242,.15); border-radius: var(--radius); padding: 20px; margin-bottom: 14px; }
.ac-title { font-size: 14px; font-weight: 700; color: var(--purple); margin-bottom: 8px; }
.ac-body  { font-size: 13px; line-height: 1.7; color: var(--text-2); }

/* ─── Signal Card — Compact with GO/WAIT badge ─── */
.sc {
    background: rgba(40, 40, 42, 0.45);
    border-left: 4px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 10px 14px;
    transition: var(--transition);
    display: flex;
    align-items: center;
    gap: 10px;
    min-height: 0;
}
.sc-left { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.sc-left .sc-icon { font-size: 20px; line-height: 1; }
.sc-body { flex: 1; min-width: 0; }
.sc-body .sc-title { font-size: 11px; font-weight: 700; color: var(--text-3); text-transform: uppercase; letter-spacing: .04em; }
.sc-body .sc-label { font-size: 13px; color: var(--text-2); margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sc-body .sc-detail { font-size: 11px; color: var(--text-3); margin-top: 2px; line-height: 1.4; }
.sc-badge { flex-shrink: 0; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; }
.sc-badge-wait { background: rgba(110,110,115,0.25); color: var(--text-3); }
.sc-badge-go { background: rgba(48,209,88,0.2); color: #30d158; }
.sc-badge-go-urgent { background: #30d158; color: #000; animation: badge-blink 1.5s ease-in-out infinite; }
@keyframes badge-blink { 0%,100%{opacity:1} 50%{opacity:.6} }

/* ON state — colored left border + brighter text */
.sc-on { border-left-color: var(--sc-clr, var(--blue)); background: rgba(var(--sc-rgb, 10,132,255), 0.06); }
.sc-on .sc-title { color: var(--text-2); }
.sc-on .sc-label { color: var(--text-1); font-weight: 600; }
.sc-on .sc-detail { color: var(--text-2); }

/* URGENT — strong colored border + glow */
.sc-urgent { border-left-color: var(--sc-clr, var(--red)); background: rgba(var(--sc-rgb, 255,69,58), 0.1); box-shadow: 0 0 16px rgba(var(--sc-rgb, 255,69,58), 0.25); }
.sc-urgent .sc-title { color: var(--text-1); }
.sc-urgent .sc-label { color: #fff; font-weight: 700; }
.sc-urgent .sc-detail { color: var(--text-2); }

/* Color themes */
.sc-tether  { --sc-clr: #ff9f0a; --sc-rgb: 255,159,10; }
.sc-dollar  { --sc-clr: #30d158; --sc-rgb: 48,209,88; }
.sc-yen     { --sc-clr: #5e5ce6; --sc-rgb: 94,92,230; }
.sc-bank    { --sc-clr: #0a84ff; --sc-rgb: 10,132,255; }
.sc-stock   { --sc-clr: #bf5af2; --sc-rgb: 191,90,242; }
.sc-rebal   { --sc-clr: #64d2ff; --sc-rgb: 100,210,255; }

/* ─── Signal Card Grid (2-per-row, compact) ─── */
.sc-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    margin-bottom: 16px;
}
@media (max-width: 768px) {
    .sc-grid { grid-template-columns: 1fr; gap: 6px; }
}

/* ─── Hide sidebar completely ─── */
section[data-testid="stSidebar"] { display: none !important; }

/* ─── Entry Gauge Bar ─── */
.eg-wrap {
    background: var(--card-bg);
    backdrop-filter: blur(var(--blur));
    border: 1px solid var(--card-border);
    border-radius: var(--radius-sm);
    padding: 14px 18px;
    margin-bottom: 8px;
}
.eg-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
}
.eg-label {
    font-size: 13px;
    font-weight: 700;
    color: var(--text-2);
}
.eg-score {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.02em;
}
.eg-score.eg-low  { color: var(--red); }
.eg-score.eg-mid  { color: var(--orange); }
.eg-score.eg-high { color: var(--green); }
.eg-track {
    width: 100%;
    height: 8px;
    background: rgba(255,255,255,0.06);
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 6px;
}
.eg-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.6s ease;
}
.eg-fill.eg-low  { background: linear-gradient(90deg, #ff453a, #ff6961); }
.eg-fill.eg-mid  { background: linear-gradient(90deg, #ff9f0a, #ffb340); }
.eg-fill.eg-high { background: linear-gradient(90deg, #30d158, #63e68b); }
.eg-rationale {
    font-size: 11px;
    color: var(--text-3);
    line-height: 1.4;
}
.eg-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    margin-bottom: 16px;
}
@media (max-width: 768px) {
    .eg-grid { grid-template-columns: 1fr; }
}

/* ─── AI Analysis Card v2 ─── */
.ac2 {
    background: rgba(28, 28, 30, 0.6);
    border: 1px solid var(--card-border);
    border-radius: var(--radius);
    overflow: hidden;
    margin-bottom: 14px;
}
.ac2-header {
    padding: 14px 18px;
    border-bottom: 1px solid var(--card-border);
    font-size: 14px;
    font-weight: 700;
    color: var(--text-1);
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}
.ac2-sections {
    display: flex;
    flex-direction: column;
}
.ac2-sec {
    padding: 12px 18px;
    border-left: 4px solid transparent;
}
.ac2-sec + .ac2-sec {
    border-top: 1px solid rgba(255,255,255,0.04);
}
.ac2-bull {
    border-left-color: var(--green);
    background: rgba(48,209,88,0.04);
}
.ac2-bear {
    border-left-color: var(--red);
    background: rgba(255,69,58,0.04);
}
.ac2-synth {
    border-left-color: var(--purple);
    background: rgba(191,90,242,0.06);
}
.ac2-sec-title {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 4px;
}
.ac2-bull .ac2-sec-title { color: var(--green); }
.ac2-bear .ac2-sec-title { color: var(--red); }
.ac2-synth .ac2-sec-title { color: var(--purple); }
.ac2-sec-body {
    font-size: 13px;
    line-height: 1.7;
    color: var(--text-2);
}
/* Bullet list inside analysis card */
.ac2-list {
    list-style: none;
    margin: 0;
    padding: 0;
}
.ac2-list li {
    position: relative;
    padding: 5px 0 5px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.ac2-list li:last-child { border-bottom: none; }
.ac2-list li::before {
    content: '▸';
    position: absolute;
    left: 0;
    color: var(--text-3);
    font-size: 11px;
}
.ac2-bull .ac2-list li::before { color: var(--green); }
.ac2-bear .ac2-list li::before { color: var(--red); }
.ac2-synth .ac2-list li::before { color: var(--purple); }
/* Sentence blocks (legacy prose fallback) */
.ac2-sent {
    margin: 0 0 6px 0;
    padding-left: 10px;
    border-left: 2px solid rgba(255,255,255,0.06);
}
.ac2-sent:last-child { margin-bottom: 0; }
/* Keyword highlights */
.ac2-num {
    display: inline;
    background: rgba(100,210,255,0.12);
    color: var(--teal);
    padding: 1px 5px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 12px;
    font-family: 'SF Mono', 'Fira Code', monospace;
}
.ac2-pos {
    color: var(--green);
    font-weight: 600;
}
.ac2-neg {
    color: var(--red);
    font-weight: 600;
}
.ac2-footer {
    padding: 8px 18px;
    border-top: 1px solid var(--card-border);
    font-size: 11px;
    color: var(--text-3);
}
</style>
"""
