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
#MainMenu, footer, header { visibility: hidden; }
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

/* ─── Sidebar ─── */
section[data-testid="stSidebar"] { background: rgba(28,28,30,.92) !important; }
section[data-testid="stSidebar"] .stMarkdown p { color: var(--text-2); }
</style>
"""
