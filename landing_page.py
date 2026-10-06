import streamlit as st
from html import escape
from plan_catalog import GLOBAL_PLANS

st.set_page_config(
    page_title="Zovix - Create Cinematic AI Videos in Minutes",
    page_icon="🎬",
    layout="wide",
)


class WorldClassLandingPage:
    """Apple-level landing page for ZOVIX"""

    def __init__(self):
        self.init_session_state()

    def init_session_state(self):
        if "landing_animation_played" not in st.session_state:
            st.session_state["landing_animation_played"] = False
        if "landing_video_playing" not in st.session_state:
            st.session_state["landing_video_playing"] = False
        if "current_testimonial" not in st.session_state:
            st.session_state["current_testimonial"] = 0

    def render(self):
        self._inject_css()
        self._render_showcase()
        self._render_cinematic_guide()
        self._render_face_video_guide()
        self._render_expressive_face_guide()
        self._render_creative_workshop_guide()
        self._render_live_emotion_voice_guide()
        self._render_blueprint_engine_guide()
        self._render_ai_upscaler_guide()
        self._render_video_editor_guide()
        self._render_engine_output_gallery()
        self._render_features()
        self._render_about()
        self._render_blog()
        self._render_changelog()
        self._render_roadmap()
        self._render_careers()
        self._render_testimonials()
        self._render_pricing()
        self._render_faq()
        self._render_cta()
        self._render_footer()
        self._inject_animations()

    def _inject_css(self):
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@100;200;300;400;500;600;700;800;900&family=Roboto+Condensed:wght@700;800;900&family=Orbitron:wght@400;500;600;700;800;900&family=Playfair+Display:wght@700;900&family=Caveat:wght@600;700&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,500,1,0&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; }

        /* ===== STREAMLIT DEFAULT UI HIDE ===== */
        [data-testid="stHeader"], header, [data-testid="stToolbar"], #MainMenu, footer {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        /* ===== FULL WIDTH FIX ===== */
        .block-container {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            max-width: 100% !important;
            margin: 0 auto !important;
        }
        section.main > div {
            max-width: 100% !important;
            padding: 0 !important;
        }

        .animated-bg { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; overflow: hidden; pointer-events: none; }
        .animated-bg .orb { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.3; animation: floatOrb 20s infinite ease-in-out; }
        .animated-bg .orb:nth-child(1) { width: 500px; height: 500px; background: #EC4899; top: -100px; left: -100px; animation-delay: 0s; }
        .animated-bg .orb:nth-child(2) { width: 400px; height: 400px; background: #45f3ff; bottom: -50px; right: -50px; animation-delay: -7s; }
        .animated-bg .orb:nth-child(3) { width: 300px; height: 300px; background: #8b5cf6; top: 50%; left: 50%; transform: translate(-50%, -50%); animation-delay: -14s; }
        @keyframes floatOrb { 0%, 100% { transform: translate(0, 0) scale(1); } 25% { transform: translate(50px, -30px) scale(1.1); } 50% { transform: translate(-30px, 50px) scale(0.9); } 75% { transform: translate(30px, 30px) scale(1.05); } }
        .glow-text { background: linear-gradient(135deg, #45f3ff 0%, #EC4899 50%, #8b5cf6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; animation: shimmer 3s ease-in-out infinite; background-size: 200% 200%; }
        @keyframes shimmer { 0%, 100% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } }
        .landing-nav { position: fixed; top: 0; left: 0; right: 0; z-index: 1000; padding: 16px 40px; display: flex; justify-content: space-between; align-items: center; background: rgba(10, 10, 15, 0.8); backdrop-filter: blur(20px) saturate(180%); border-bottom: 1px solid rgba(255,255,255,0.05); transition: all 0.3s ease; }
        .landing-nav.scrolled { background: rgba(10, 10, 15, 0.95); box-shadow: 0 4px 30px rgba(0,0,0,0.5); }
        .nav-logo { display: flex; align-items: center; gap: 12px; text-decoration: none; }
        .nav-logo .logo-icon { width: 40px; height: 40px; background: linear-gradient(135deg, #45f3ff, #EC4899); border-radius: 12px; display: flex; align-items: center; justify-content: center; font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 22px; color: white; }
        .nav-logo .logo-text { font-family: 'Orbitron', sans-serif; font-weight: 700; font-size: 20px; letter-spacing: 1px; }
        .nav-logo .logo-text span { color: #45f3ff; }
        .nav-links { display: flex; align-items: center; gap: 30px; }
        .nav-links a { color: #94a3b8; text-decoration: none; font-size: 13px; font-weight: 500; transition: all 0.3s ease; position: relative; }
        .nav-links a:hover { color: #ffffff; }
        .nav-cta-btn, .hero-primary-btn, .hero-secondary-btn, .pricing-btn { cursor: pointer; }
        .hero-section { min-height: 100svh; display: flex; align-items: center; justify-content: center; padding: 120px 40px 60px; position: relative; z-index: 1; }
        .hero-content { max-width: 1280px; width: min(100%, 1280px); display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: clamp(36px, 5vw, 72px); align-items: center; margin: 0 auto; }
        .hero-left, .hero-right { min-width: 0; }
        .hero-left { animation: fadeInUp 1s ease; }
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(40px); } to { opacity: 1; transform: translateY(0); } }
        .hero-badge { display: inline-block; padding: 6px 18px; background: rgba(69, 243, 255, 0.1); border: 1px solid rgba(69, 243, 255, 0.2); border-radius: 20px; font-size: 12px; color: #45f3ff; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 24px; }
        .hero-topline { display: flex; align-items: center; justify-content: space-between; gap: 16px; width: 100%; max-width: 100%; margin-bottom: 25px; }
        .hero-topline .hero-badge { margin-bottom: 0; }
        .hero-create-btn { display: inline-flex; align-items: center; white-space: nowrap; padding: 10px 14px; border: 1px solid rgba(255,255,255,.2); border-radius: 8px; background: rgba(255,255,255,.08); color: #fff; text-decoration: none !important; font: 700 12px 'Arial', sans-serif; transition: background .2s ease, border-color .2s ease, transform .2s ease; }
        .hero-create-btn:hover { background: #EC4899; border-color: #EC4899; color: #fff; transform: translateY(-2px); }
        .hero-title { font-family: 'Orbitron', sans-serif; font-size: 64px; font-weight: 900; line-height: 1.1; margin-bottom: 24px; }
        .hero-title .highlight { background: linear-gradient(135deg, #45f3ff 0%, #EC4899 50%, #8b5cf6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
        .hero-subtitle { font-size: 20px; color: #94a3b8; line-height: 1.6; margin-bottom: 32px; max-width: 500px; }
        .hero-actions { display: flex; gap: 16px; flex-wrap: wrap; }
        .hero-primary-btn { padding: 16px 40px; background: linear-gradient(135deg, #45f3ff, #EC4899); border: none; border-radius: 12px; color: white; font-family: 'Orbitron', sans-serif; font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }
        .hero-secondary-btn { padding: 16px 32px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; color: #ffffff; font-family: 'Orbitron', sans-serif; font-weight: 600; font-size: 14px; backdrop-filter: blur(10px); }
        .hero-stats { display: flex; gap: 40px; margin-top: 40px; }
        .hero-stat .number { font-family: 'Orbitron', sans-serif; font-size: 32px; font-weight: 700; color: #45f3ff; }
        .hero-stat .label { font-size: 13px; color: #94a3b8; margin-top: 4px; }
        .hero-video-container { position: relative; width: 100%; aspect-ratio: 16 / 10; border-radius: 20px; overflow: hidden; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 30px 80px rgba(0,0,0,0.8); background: #000; }
        .hero-video-container video { width: 100%; height: 100%; object-fit: cover; display: block; }
        .hero-video-overlay { position: absolute; bottom: 0; left: 0; right: 0; padding: 30px; background: linear-gradient(transparent, rgba(0,0,0,0.8)); }
        .features-section, .how-it-works, .stats-section, .testimonials-section, .pricing-section, .cta-section, .landing-footer { position: relative; z-index: 1; padding: 80px 40px; max-width: 1400px; margin: 0 auto; }
        .section-header { text-align: center; max-width: 700px; margin: 0 auto 60px; }
        .section-header .tag { display: inline-block; padding: 6px 18px; background: rgba(236, 72, 153, 0.1); border: 1px solid rgba(236, 72, 153, 0.2); border-radius: 20px; font-size: 12px; color: #EC4899; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px; }
        .section-header h2 { font-family: 'Orbitron', sans-serif; font-size: 48px; font-weight: 800; margin-bottom: 16px; }
        .section-header p { font-size: 18px; color: #94a3b8; line-height: 1.6; }
        .features-grid, .testimonials-grid, .pricing-grid, .stats-grid { display: grid; gap: 30px; }
        .features-grid { grid-template-columns: repeat(3, 1fr); max-width: 1200px; margin: 0 auto; }
        .feature-card, .testimonial-card, .pricing-card, .stat-item { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 16px; }
        .feature-card { padding: 32px; }
        .feature-card h3, .step-item h4, .pricing-card .plan-name, .footer-col h5 { font-family: 'Orbitron', sans-serif; }
        .feature-card p, .step-item p, .testimonial-card .text, .pricing-card .features li, .footer-brand p, .footer-col a, .cta-container p { color: #94a3b8; }
        .feature-card .icon { font-size: 40px; margin-bottom: 16px; display: block; }
        .feature-card .feature-tag { display: inline-block; margin-top: 12px; padding: 4px 12px; background: rgba(69, 243, 255, 0.1); border-radius: 12px; font-size: 11px; color: #45f3ff; font-weight: 600; }
        .steps-container { display: grid; grid-template-columns: repeat(3, 1fr); gap: 40px; max-width: 1000px; margin: 0 auto; }
        .step-item { text-align: center; position: relative; }
        .step-number { width: 60px; height: 60px; border-radius: 50%; background: linear-gradient(135deg, #45f3ff, #EC4899); display: flex; align-items: center; justify-content: center; font-family: 'Orbitron', sans-serif; font-size: 24px; font-weight: 900; color: white; margin: 0 auto 20px; }
        .stats-grid { grid-template-columns: repeat(4, 1fr); max-width: 1000px; margin: 0 auto; }
        .stat-item { text-align: center; padding: 30px; }
        .stat-item .number, .pricing-card .price { font-family: 'Orbitron', sans-serif; font-weight: 900; color: #45f3ff; }
        .stat-item .number { font-size: 48px; }
        .testimonials-grid { grid-template-columns: repeat(3, 1fr); max-width: 1100px; margin: 0 auto; }
        .testimonial-card { padding: 30px; }
        .testimonial-card .author { display: flex; align-items: center; gap: 12px; }
        .testimonial-card .avatar { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #45f3ff, #EC4899); display: flex; align-items: center; justify-content: center; font-weight: 700; color: white; }
        .pricing-grid { grid-template-columns: repeat(4, 1fr); max-width: 1100px; margin: 0 auto; }
        .pricing-card { padding: 32px; text-align: center; position: relative; }
        .pricing-card.popular { border-color: #45f3ff; box-shadow: 0 0 40px rgba(69, 243, 255, 0.1); }
        .pricing-card.popular::before { content: '⭐ POPULAR'; position: absolute; top: -12px; left: 50%; transform: translateX(-50%); padding: 4px 16px; background: #45f3ff; color: #000; font-size: 10px; font-weight: 700; border-radius: 12px; letter-spacing: 1px; }
        .pricing-card .price { font-size: 42px; margin: 16px 0; }
        .pricing-card .price span { font-size: 18px; color: #94a3b8; }
        .pricing-card .features { list-style: none; padding: 0; margin: 20px 0; }
        .pricing-card .features li { padding: 8px 0; font-size: 14px; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .pricing-btn { width: 100%; padding: 14px; background: linear-gradient(135deg, #45f3ff, #EC4899); border: none; border-radius: 10px; color: white; font-family: 'Orbitron', sans-serif; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; }
        .pricing-card.free .pricing-btn { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); }
        .cta-section { padding: 80px 40px; background: linear-gradient(135deg, rgba(69, 243, 255, 0.05), rgba(236, 72, 153, 0.05)); }
        .cta-container { max-width: 800px; margin: 0 auto; text-align: center; }
        .cta-container h2 { font-family: 'Orbitron', sans-serif; font-size: 48px; font-weight: 800; margin-bottom: 16px; }
        .cta-container .cta-buttons { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }
        .landing-footer { display: block !important; visibility: visible !important; opacity: 1 !important; clear: both; min-height: 260px; padding: 40px; border-top: 1px solid rgba(255,255,255,0.05); }
        .footer-content { max-width: 1200px; margin: 0 auto; display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 40px; }
        .footer-brand .logo-text { font-family: 'Orbitron', sans-serif; font-size: 24px; font-weight: 700; }
        .footer-brand .logo-text span { color: #45f3ff; }
        .footer-col a { display: block; text-decoration: none; font-size: 14px; padding: 6px 0; }
        .footer-bottom { max-width: 1200px; margin: 30px auto 0; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: #64748b; }
        @media (min-width: 1600px) { .landing-nav { padding-left: 64px; padding-right: 64px; } .hero-section { padding-left: 64px; padding-right: 64px; } .hero-content { max-width: 1560px; } h1.hero-title { font-size: 68px !important; } .hero-subtitle { font-size: 22px; } .hero-stat .number { font-size: 36px; } }
        @media (max-width: 1024px) { .hero-content { grid-template-columns: 1fr; gap: 40px; } .hero-title { font-size: 48px; } .features-grid, .pricing-grid, .testimonials-grid, .stats-grid { grid-template-columns: repeat(2, 1fr); } .steps-container { grid-template-columns: 1fr; } .footer-content { grid-template-columns: 1fr 1fr; } }
        @media (max-width: 768px) { .landing-nav { padding: 12px 20px; flex-wrap: wrap; gap: 12px; } .nav-links { display: none; } .hero-section { padding: 100px 20px 40px; } .hero-topline { align-items: flex-start; width: 100%; } .hero-create-btn { padding: 9px 10px; font-size: 11px; } .hero-title { font-size: 36px; } .hero-subtitle { font-size: 16px; } .features-grid, .pricing-grid, .testimonials-grid, .stats-grid, .footer-content { grid-template-columns: 1fr; } .section-header h2, .cta-container h2 { font-size: 32px; } .hero-stats { flex-wrap: wrap; gap: 20px; } .footer-bottom { flex-direction: column; gap: 12px; text-align: center; } }

        :root {
            --landing-bg: #101814;
            --landing-surface: #18231d;
            --landing-text: #f1f4ed;
            --landing-muted: #a8b7ad;
            --landing-mint: #91dfb4;
            --landing-coral: #ff9678;
            --landing-line: rgba(226, 239, 229, 0.12);
        }
        .stApp, [data-testid="stAppViewContainer"], section.main {
            color: var(--landing-text) !important;
            background: radial-gradient(ellipse at 18% 8%, rgba(69, 112, 82, 0.22), transparent 38%),
                linear-gradient(155deg, #101814 0%, #17221c 54%, #101814 100%) !important;
        }
        .animated-bg {
            background-image: linear-gradient(rgba(145, 223, 180, 0.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(145, 223, 180, 0.035) 1px, transparent 1px);
            background-size: 48px 48px;
            mask-image: linear-gradient(to bottom, black, transparent 82%);
        }
        .animated-bg .orb { display: none; }
        .landing-nav { background: rgba(16, 24, 20, 0.88); border-bottom-color: var(--landing-line); }
        .landing-nav.scrolled { background: rgba(16, 24, 20, 0.97); }
        .nav-logo .logo-icon, .hero-primary-btn, .pricing-btn, .step-number, .testimonial-card .avatar {
            background: linear-gradient(135deg, var(--landing-mint), var(--landing-coral));
        }
        .nav-logo .logo-text span, .footer-brand .logo-text span { color: var(--landing-mint); }
        .nav-links a, .hero-subtitle, .hero-stat .label, .section-header p,
        .feature-card p, .step-item p, .testimonial-card .text,
        .pricing-card .features li, .footer-brand p, .footer-col a, .cta-container p {
            color: var(--landing-muted);
        }
        .nav-links a:hover, .footer-col a:hover { color: var(--landing-text); }
        .nav-cta-btn {
            padding: 10px 16px;
            border: 0;
            border-radius: 6px;
            background: var(--landing-mint);
            color: #122018;
            font-weight: 700;
        }
        .hero-badge { color: var(--landing-mint); background: rgba(145, 223, 180, 0.09); border-color: rgba(145, 223, 180, 0.22); }
        .hero-create-btn { border-color: var(--landing-line); background: rgba(255, 255, 255, 0.045); }
        .hero-create-btn:hover { background: var(--landing-coral); border-color: var(--landing-coral); }
        .hero-title .highlight, .glow-text {
            background: linear-gradient(110deg, var(--landing-mint) 8%, #d9e7ad 52%, var(--landing-coral) 94%);
            -webkit-background-clip: text;
            background-clip: text;
        }
        h1.hero-title {
            font-family: 'Orbitron', sans-serif !important;
            font-size: 56px !important;
            font-weight: 900 !important;
            line-height: 1.1 !important;
            margin-bottom: 24px !important;
        }
        .section-header h2, .cta-container h2 {
            font-family: 'Orbitron', sans-serif !important;
            font-size: 48px !important;
            font-weight: 800 !important;
            line-height: 1.2 !important;
        }
        .hero-stat .number, .stat-item .number, .pricing-card .price { color: var(--landing-mint); }
        .section-header .tag { color: var(--landing-coral); background: rgba(255, 150, 120, 0.08); border-color: rgba(255, 150, 120, 0.2); }
        .feature-card, .testimonial-card, .pricing-card, .stat-item {
            background: rgba(24, 35, 29, 0.74);
            border-color: var(--landing-line);
            border-radius: 8px;
        }
        .feature-card .feature-tag { color: var(--landing-mint); background: rgba(145, 223, 180, 0.09); }
        .pricing-card.popular { border-color: rgba(145, 223, 180, 0.55); box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2); }
        .pricing-card.popular::before { background: var(--landing-mint); color: #122018; }
        .pricing-card .features li { border-bottom-color: var(--landing-line); }
        .pricing-card.free .pricing-btn, .hero-secondary-btn {
            background: rgba(241, 244, 237, 0.055);
            border-color: var(--landing-line);
        }
        .pricing-card.free .pricing-btn { color: var(--landing-text); }
        .cta-section { background: linear-gradient(115deg, rgba(145, 223, 180, 0.07), rgba(255, 150, 120, 0.055)); }
        .landing-footer, .footer-bottom { border-color: var(--landing-line); }
        .footer-bottom { color: var(--landing-muted); }
        [id^="faq_icon_"] { color: var(--landing-mint) !important; }

        @media (max-width: 1024px) {
            .hero-section { min-height: auto; padding-top: 128px; }
            .hero-content { max-width: 760px; gap: 34px; }
            h1.hero-title { font-size: 48px !important; }
            .hero-video-container { aspect-ratio: 16 / 9; }
            .features-section, .how-it-works, .stats-section, .testimonials-section,
            .pricing-section, .cta-section, .landing-footer { padding: 68px 28px; }
        }
        @media (max-width: 768px) {
            .landing-nav { padding: 10px 18px; }
            .nav-logo .logo-icon { width: 36px; height: 36px; font-size: 19px; }
            .nav-logo .logo-text { font-size: 18px; }
            .hero-section { padding: 104px 20px 44px; }
            .hero-content { gap: 30px; }
            .hero-topline { flex-direction: column; align-items: flex-start; gap: 12px; margin-bottom: 20px; }
            h1.hero-title { font-size: 34px !important; line-height: 1.14 !important; margin-bottom: 18px !important; }
            .hero-subtitle { font-size: 16px; margin-bottom: 24px; }
            .hero-actions { width: 100%; }
            .hero-secondary-btn { min-height: 46px; padding: 12px 18px; }
            .hero-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 28px; }
            .hero-stat .number { font-size: 22px; }
            .hero-stat .label { font-size: 11px; line-height: 1.35; }
            .hero-video-container { border-radius: 12px; }
            .features-section, .how-it-works, .stats-section, .testimonials-section,
            .pricing-section, .cta-section, .landing-footer { padding: 56px 20px; }
            .section-header { margin-bottom: 36px; }
            .section-header h2, .cta-container h2 { font-size: 30px !important; line-height: 1.2 !important; }
            .section-header p, .cta-container p { font-size: 15px; }
            .feature-card, .testimonial-card, .pricing-card { padding: 24px; }
            .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
            .stat-item { padding: 22px 16px; }
            .stat-item .number { font-size: 34px; }
            .faq-section { padding: 52px 20px !important; }
            .landing-footer { min-height: 0; }
            .footer-content { gap: 26px; }
        }
        @media (max-width: 380px) {
            .hero-section { padding-right: 16px; padding-left: 16px; }
            h1.hero-title { font-size: 26px !important; }
            .hero-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .features-section, .how-it-works, .stats-section, .testimonials-section,
            .pricing-section, .cta-section, .landing-footer { padding-right: 16px; padding-left: 16px; }
        }

        :root {
            --landing-bg: #f8f9fa;
            --landing-surface: #ffffff;
            --landing-text: #1a2529;
            --landing-muted: #59676b;
            --landing-mint: #20bdb5;
            --landing-coral: #ed9874;
            --landing-line: rgba(31, 50, 53, 0.14);
        }
        .stApp, [data-testid="stAppViewContainer"], section.main {
            color: var(--landing-text) !important;
            background:
                radial-gradient(ellipse at 18% 8%, rgba(32, 189, 181, .055), transparent 38%),
                radial-gradient(ellipse at 88% 40%, rgba(237, 152, 116, .045), transparent 34%),
                linear-gradient(155deg, #ffffff 0%, #f8f9fa 54%, #ffffff 100%) !important;
        }
        .landing-nav, .landing-nav.scrolled {
            padding: 5px max(5vw, 24px);
            background: rgba(255, 255, 255, 0.94);
            border-bottom: 1px solid var(--landing-line);
            box-shadow: 0 8px 24px rgba(31, 50, 53, .06);
            backdrop-filter: blur(16px);
        }
        .nav-logo { gap: 10px; }
        .nav-logo .logo-icon {
            width: 34px; height: 34px; border-radius: 9px;
            background: linear-gradient(135deg, var(--landing-coral), var(--landing-mint) 70%);
            color: #14393a; font-size: 19px;
        }
        .nav-logo .logo-text { color: var(--landing-text); font: 700 19px 'Inter', sans-serif; letter-spacing: .4px; }
        .nav-logo .logo-text span, .footer-brand .logo-text span { color: var(--landing-mint); }
        .nav-links { gap: clamp(16px, 2.4vw, 34px); }
        .nav-links a { color: #39484c; font-size: 13px; }
        .nav-links a:hover { color: #128f89; }
        .nav-cta-btn { padding: 11px 18px; border-radius: 8px; background: var(--landing-mint); color: #102e2e !important; }
        .hero-section {
            min-height: 548px;
            padding: 222px clamp(32px, 5vw, 80px) 24px;
            align-items: flex-start;
            overflow: hidden;
            background: transparent;
        }
        .hero-section::before {
            position: absolute; z-index: 0; top: 154px; right: -7%; width: 50%; height: 390px;
            content: ""; pointer-events: none;
            background: linear-gradient(130deg, rgba(222, 235, 231, .42), rgba(242, 238, 232, .34));
            border-radius: 58% 0 0 48% / 44% 0 0 58%;
            transform: rotate(-3deg);
        }
        .hero-gallery {
            position: absolute; z-index: 1; top: 18px; left: 0; width: 100%; height: 210px;
            display: block; overflow: visible; padding: 0; pointer-events: none;
        }
        .hero-gallery::before {
            position: absolute; inset: 0 0 10px; content: "";
            background: linear-gradient(105deg, rgba(225, 234, 231, .58), rgba(247, 242, 236, .34));
            border-radius: 0 0 48% 2% / 0 0 34% 2%;
            clip-path: ellipse(87% 76% at 34% 8%);
        }
        .hero-gallery img {
            position: absolute; left: 25%; top: 30px; z-index: 2;
            width: 18%; height: 132px; margin: 0; object-fit: cover;
            border-radius: 12px; border: 1px solid rgba(31, 50, 53, .17);
            background: #e7eeed;
            box-shadow: 0 10px 24px rgba(35, 55, 56, .15);
            filter: saturate(.92) brightness(.97);
            transition: filter .35s ease;
        }
        .hero-gallery img:first-child {
            left: 2%; top: 0; z-index: 1; width: 26%; height: 194px; object-position: center;
            border-radius: 8px 14px 16px 8px;
        }
        .hero-gallery img:nth-child(2) { left: 28%; top: 38px; z-index: 2; width: 17%; height: 136px; border-radius: 11px; }
        .hero-gallery img:nth-child(3) { left: 45.5%; top: 58px; z-index: 3; width: 14.5%; height: 120px; border-radius: 11px; }
        .hero-gallery img:nth-child(4) { left: 60.5%; top: 72px; z-index: 4; width: 15%; height: 108px; border-radius: 11px; }
        .hero-gallery img:nth-child(5) { left: 76%; top: 92px; z-index: 5; width: 8%; height: 78px; object-position: center 42%; border-radius: 11px; }
        .hero-gallery img:hover { filter: saturate(1) brightness(1); }
        .hero-content {
            position: relative; z-index: 2; width: 100%; max-width: 1560px; transform: none;
            grid-template-columns: minmax(0, 1.5fr) minmax(0, .92fr); gap: clamp(32px, 3.5vw, 60px);
            align-items: start;
        }
        .hero-left { margin-left: clamp(112px, 12vw, 190px); }
        .hero-right { width: 100%; max-width: none; justify-self: end; margin-top: -8px; }
        .hero-left { padding-top: 0; }
        .hero-topline { margin-bottom: 10px; }
        .hero-badge { display: none; }
        .hero-create-btn { display: none; }
        h1.hero-title {
            max-width: 700px; margin: 0 0 8px !important;
            color: var(--landing-text); font: 900 clamp(38px, 3.1vw, 52px)/1.08 'Roboto Condensed', sans-serif !important;
            letter-spacing: 0 !important; text-transform: uppercase;
        }
        .hero-title .highlight {
            background: linear-gradient(110deg, var(--landing-mint), #d9e7ad 52%, var(--landing-coral));
            -webkit-background-clip: text; background-clip: text;
        }
        .hero-subtitle {
            max-width: 500px; margin-bottom: 20px; color: var(--landing-muted);
            font-size: clamp(15px, 1.15vw, 18px); line-height: 1.42;
        }
        .hero-actions { gap: 9px; flex-wrap: nowrap; }
        .hero-primary-btn, .hero-secondary-btn {
            display: inline-flex; align-items: center; justify-content: center;
            min-height: 46px; padding: 12px 18px; border-radius: 24px;
            font: 700 12px 'Inter', sans-serif; letter-spacing: .15px; text-transform: uppercase;
            white-space: nowrap;
        }
        .hero-primary-btn {
            background: linear-gradient(120deg, var(--landing-mint), #19aaa2);
            box-shadow: 0 8px 24px rgba(32, 189, 181, .22);
            text-decoration: none !important; color: #102e2e !important;
        }
        .hero-secondary-btn {
            background: rgba(255, 255, 255, .78); color: var(--landing-text) !important;
            border: 1px solid rgba(31, 50, 53, .34); backdrop-filter: blur(10px);
            text-decoration: none !important;
        }
        .hero-demo {
            position: relative; display: grid; place-items: center; width: 100%;
            min-height: 250px; aspect-ratio: 1.71; overflow: hidden;
            border: 1px solid rgba(255, 255, 255, .62); border-radius: 14px;
            background: rgba(28, 42, 43, .28); backdrop-filter: blur(18px) saturate(140%);
            box-shadow: 0 22px 48px rgba(31, 50, 53, .2), inset 0 1px 0 rgba(255,255,255,.36);
            isolation: isolate; text-align: center; color: white !important; text-decoration: none !important;
        }
        .hero-demo::before {
            position: absolute; z-index: -1; inset: -10px; content: "";
            background: linear-gradient(rgba(10, 24, 27, .34), rgba(10, 24, 27, .42)),
                url('https://images.unsplash.com/photo-1492619375914-88005aa9e8fb?auto=format&fit=crop&w=1200&q=85') center/cover;
            filter: blur(4px); transform: scale(1.04);
        }
        .hero-demo::after {
            position: absolute; z-index: -1; inset: 0; content: "";
            background: linear-gradient(135deg, rgba(255,255,255,.16), transparent 44%, rgba(19,38,40,.18));
            pointer-events: none;
        }
        .demo-label { color: #fff !important; font-size: 18px; line-height: 1.25; font-weight: 700; }
        .demo-label span { display: block; color: var(--landing-mint) !important; }
        .demo-play {
            display: grid; place-items: center; width: 54px; height: 54px; margin: 14px auto 0;
            border-radius: 50%; color: white; background: rgba(16, 48, 51, .76);
            border: 1px solid rgba(79, 224, 210, .48);
            font-size: 21px; padding-left: 3px;
        }
        .stats-section {
            position: relative; z-index: 2; width: 100%; max-width: 1560px;
            padding: 0 clamp(32px, 5vw, 80px) 48px; margin: 0 auto; transform: none;
        }
        .stats-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; max-width: none; }
        .stat-item {
            display: grid; grid-template-columns: 54px 1fr; grid-template-rows: auto auto;
            align-content: center; align-items: center; column-gap: 12px; row-gap: 4px;
            min-height: 118px; padding: 18px 24px;
            text-align: left; background: rgba(255, 255, 255, .94); border: 1px solid rgba(31, 50, 53, .13);
            border-radius: 12px; box-shadow: 0 14px 28px rgba(31, 50, 53, .11);
        }
        .stat-icon {
            grid-column: 1; grid-row: 1 / 3; color: #20383d;
            font: 42px 'Material Symbols Rounded'; font-variation-settings: 'FILL' 1, 'wght' 600;
        }
        .stat-item .number { color: var(--landing-text); font: 900 clamp(30px, 2.25vw, 38px)/1.05 'Inter', sans-serif; }
        .stat-item .label { color: var(--landing-muted); font: 600 clamp(14px, 1vw, 16px)/1.3 'Inter', sans-serif; }
        .features-section, .how-it-works, .testimonials-section, .pricing-section,
        .cta-section, .landing-footer { color: var(--landing-text); }
        .section-header h2, .cta-container h2, .feature-card h3, .step-item h4,
        .pricing-card .plan-name, .footer-col h5 { color: var(--landing-text); }
        .feature-card, .testimonial-card, .pricing-card, .stat-item {
            background: rgba(255, 255, 255, .92); border-color: var(--landing-line); color: var(--landing-text);
        }
        .feature-card p, .step-item p, .testimonial-card .text, .pricing-card .features li,
        .footer-brand p, .footer-col a, .cta-container p, .section-header p { color: var(--landing-muted); }
        .payment-methods {
            max-width: 1000px;
            margin: 34px auto 0;
            padding: 24px;
            text-align: center;
            background: rgba(255, 255, 255, .94);
            border: 1px solid var(--landing-line);
            border-radius: 12px;
            box-shadow: 0 12px 26px rgba(31, 50, 53, .08);
        }
        .payment-methods h3 {
            margin: 0 0 6px;
            color: var(--landing-text);
            font: 700 18px 'Inter', sans-serif;
        }
        .payment-methods p {
            margin: 0 0 16px;
            color: var(--landing-muted);
            font: 14px/1.5 'Inter', sans-serif;
        }
        .payment-method-list {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 9px;
        }
        .payment-method {
            display: inline-flex;
            align-items: center;
            min-height: 36px;
            padding: 7px 13px;
            color: #126964;
            background: rgba(32, 189, 181, .10);
            border: 1px solid rgba(32, 189, 181, .28);
            border-radius: 20px;
            font: 700 12px/1.25 'Inter', sans-serif;
        }
        .payment-method:nth-child(3n) {
            background: rgba(237, 152, 116, .10);
            border-color: rgba(237, 152, 116, .3);
        }
        .faq-section { padding: 60px 40px; position: relative; z-index: 1; }
        .faq-list { max-width: 800px; margin: 0 auto; }
        .faq-item {
            margin-bottom: 12px; padding: 20px 24px;
            background: rgba(255,255,255,.92); border: 1px solid var(--landing-line);
            border-radius: 12px; box-shadow: 0 8px 22px rgba(31,50,53,.06);
        }
        .faq-item summary {
            display: flex; justify-content: space-between; align-items: center;
            gap: 20px; cursor: pointer; list-style: none;
        }
        .faq-item summary::-webkit-details-marker { display: none; }
        .faq-question {
            margin: 0; color: var(--landing-text);
            font: 600 16px 'Orbitron', sans-serif;
        }
        .faq-toggle { color: #168e89; font-size: 20px; line-height: 1; }
        .faq-toggle::before { content: '+'; }
        .faq-item[open] .faq-toggle::before { content: '−'; }
        .faq-answer { padding-top: 12px; color: var(--landing-muted); font-size: 14px; line-height: 1.6; }
        @media (max-width: 900px) {
            .hero-section { min-height: auto; padding-top: 185px; }
            .hero-content { max-width: 760px; transform: none; grid-template-columns: 1fr 0.85fr; gap: 26px; }
            .hero-left { margin-left: 0; }
            .hero-gallery { top: 18px; height: 290px; }
            .hero-gallery img:first-child { left: 2%; top: 0; width: 30%; height: 165px; }
            .hero-gallery img:nth-child(2) { left: 25%; top: 24px; width: 24%; height: 126px; }
            .hero-gallery img:nth-child(3) { left: 43%; top: 42px; width: 19%; height: 102px; }
            .hero-gallery img:nth-child(4) { left: 57%; top: 66px; width: 15%; height: 82px; }
            .hero-gallery img:nth-child(5) { left: 68%; top: 96px; width: 13%; height: 68px; }
            .hero-right { margin-top: 0; }
            h1.hero-title { font-size: 38px !important; }
            .hero-demo { min-height: 190px; }
            .stats-section { max-width: 1120px; padding-bottom: 40px; transform: none; }
            .stat-item { padding: 14px; grid-template-columns: 42px 1fr; }
            .stat-icon { font-size: 32px; }
            .stat-item .number { font-size: 27px; }
            .stat-item .label { font-size: 14px; }
        }
        @media (max-width: 640px) {
            .landing-nav { padding: 10px 18px; }
            .nav-links { display: flex; gap: 0; }
            .nav-links a { display: none; }
            .nav-cta-btn { padding: 9px 14px; font-size: 12px; }
            .hero-section { padding: 158px 20px 24px; }
            .hero-gallery { top: 14px; left: 0; width: 100%; height: 126px; mask-image: none; }
            .hero-gallery img:first-child { left: 0; top: 0; width: 39%; height: 116px; }
            .hero-gallery img:nth-child(2) { left: 24%; top: 14px; width: 31%; height: 94px; }
            .hero-gallery img:nth-child(3) { left: 48%; top: 28px; width: 25%; height: 76px; }
            .hero-gallery img:nth-child(4) { left: 67%; top: 48px; width: 19%; height: 59px; }
            .hero-gallery img:nth-child(5) { left: 82%; top: 74px; width: 15%; height: 46px; }
            .hero-content { transform: none; margin: 0 auto; grid-template-columns: 1fr; gap: 18px; }
            .hero-left { margin-left: 0; }
            h1.hero-title { font-size: 37px !important; line-height: 1.08 !important; }
            .hero-subtitle { font-size: 15px; }
            .hero-actions { gap: 8px; }
            .hero-primary-btn, .hero-secondary-btn { min-height: 44px; padding: 11px 16px; font-size: 11px; }
            .hero-demo { min-height: 190px; aspect-ratio: 1.7; }
            .stats-section { max-width: 1120px; padding: 0 20px 34px; transform: none; }
            .stats-grid { grid-template-columns: 1fr; gap: 10px; }
            .stat-item { min-height: 76px; }
            .stat-item .number { font-size: 26px; }
            .stat-item .label { font-size: 14px; }
            .faq-section { padding: 52px 20px; }
            .faq-item { padding: 18px 20px; }
            .faq-question { font-size: 14px; }
        }
        @media (min-width: 901px) and (max-width: 1200px) {
            .hero-section { padding-right: 32px; padding-left: 32px; }
            .hero-content { grid-template-columns: minmax(0, 1.1fr) minmax(360px, .9fr); gap: 32px; }
            .hero-left { margin-left: clamp(92px, 11vw, 130px); }
            h1.hero-title { font-size: clamp(36px, 3.4vw, 42px) !important; }
            .hero-demo { min-height: 240px; }
            .stats-section { padding-right: 32px; padding-left: 32px; }
            .hero-primary-btn, .hero-secondary-btn { padding-right: 14px; padding-left: 14px; font-size: 11px; }
        }
        @media (min-width: 901px) {
            .hero-left { margin-left: clamp(112px, 12vw, 190px) !important; }
            .hero-actions { flex-wrap: nowrap; }
        }
        @media (min-width: 1600px) {
            .hero-section { min-height: 690px; padding-top: 235px; }
        }
        .nav-logo { gap: 9px; }
        .nav-logo .logo-mark {
            display: grid; place-items: center; width: 34px; height: 34px;
            border-radius: 9px; color: #fff; font: 800 19px 'Inter', sans-serif;
            background: linear-gradient(135deg, #06c9cb, #5865f2);
            box-shadow: 0 5px 14px rgba(32, 189, 181, .22);
        }
        .nav-brand-copy { display: grid; gap: 1px; }
        .nav-brand-copy .logo-text { line-height: 1; }
        .nav-brand-copy small {
            color: var(--landing-muted); font: 700 7px/1.2 'Inter', sans-serif;
            letter-spacing: .85px;
        }
        .nav-links { gap: clamp(12px, 1.7vw, 24px); }
        .nav-links a { font-size: 12px; }
        .nav-links .nav-cta-btn {
            padding: 10px 17px; color: #fff !important;
            background: linear-gradient(115deg, #13c9cb, #5273f5);
            box-shadow: 0 6px 16px rgba(42, 150, 215, .2);
        }
        .hero-badge {
            display: inline-flex; align-items: center; gap: 7px;
            padding: 6px 11px; margin: 0; color: #176c84;
            background: rgba(18, 190, 204, .08); border-color: rgba(18, 190, 204, .19);
            font-size: 10px; letter-spacing: .25px; text-transform: none;
        }
        .hero-topline { justify-content: flex-start; margin-bottom: 12px; }
        .hero-create-btn { display: none; }
        h1.hero-title { color: #102a52; }
        .hero-title .highlight {
            background: linear-gradient(100deg, #10bfc9 5%, #258eea 52%, #7656ed 95%);
            -webkit-background-clip: text; background-clip: text;
        }
        .hero-primary-btn {
            color: #fff !important;
            background: linear-gradient(110deg, #11c4c7, #397dea 68%, #7554ee);
            box-shadow: 0 8px 22px rgba(53, 147, 221, .25);
        }
        .hero-demo .demo-label {
            position: absolute; top: 16px; left: 18px; right: 18px; text-align: left;
        }
        .hero-demo .demo-play {
            position: absolute; top: 50%; left: 50%;
            margin: 0; transform: translate(-50%, -50%);
        }
        .hero-demo::before {
            background: linear-gradient(rgba(10, 24, 27, .22), rgba(10, 24, 27, .38)),
                url('https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=90') center/cover;
            filter: none;
        }
        .hero-benefits {
            display: flex; flex-wrap: wrap; gap: 16px; margin-top: 14px;
            color: #44586e; font: 500 11px/1.4 'Inter', sans-serif;
        }
        .hero-benefits span { display: inline-flex; align-items: center; gap: 5px; }
        .hero-benefits span::before {
            content: "✓"; display: grid; place-items: center; width: 15px; height: 15px;
            border: 1px solid #21b6c5; border-radius: 50%; color: #159fb0;
            font-size: 9px; font-weight: 800;
        }
        .stats-section { max-width: 1240px; padding-bottom: 18px; }
        .stats-grid {
            grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0;
            padding: 10px 8px; overflow: hidden;
            background: rgba(255, 255, 255, .9); border: 1px solid var(--landing-line);
            border-radius: 14px; box-shadow: 0 12px 30px rgba(31, 67, 86, .09);
        }
        .stat-item {
            min-height: 70px; grid-template-columns: 40px 1fr; column-gap: 10px;
            padding: 10px 16px; border: 0; border-radius: 0; box-shadow: none;
            background: transparent;
        }
        .stat-item + .stat-item { border-left: 1px solid rgba(31, 50, 53, .11); }
        .stat-icon {
            display: grid; place-items: center; width: 38px; height: 38px;
            border-radius: 50%; color: #11aeca; background: rgba(25, 186, 207, .1);
            font-size: 22px;
        }
        .stat-item .number { font-size: clamp(23px, 2vw, 30px); color: #17335b; }
        .stat-item .label { font-size: 11px; }
        .how-it-works {
            display: grid; grid-template-columns: minmax(190px, .78fr) minmax(0, 2fr);
            align-items: center; gap: clamp(24px, 4vw, 54px);
            max-width: 1240px; padding: 38px clamp(32px, 5vw, 80px) 32px;
        }
        .section-header .tag {
            color: #148ba7; background: rgba(18, 190, 204, .08);
            border-color: rgba(18, 190, 204, .19);
        }
        .process-intro .section-header { margin: 0; text-align: left; }
        .process-intro .section-header .tag { margin-bottom: 10px; }
        .process-intro .section-header h2 {
            margin-bottom: 9px; font-family: 'Inter', sans-serif !important;
            font-size: clamp(20px, 1.75vw, 23px) !important;
            font-weight: 800 !important; line-height: 1.18 !important;
        }
        .process-intro .section-header p { font-size: 12px; line-height: 1.5; }
        .process-link {
            display: inline-flex; align-items: center; gap: 7px; margin-top: 12px;
            color: #078eaa; font: 700 11px 'Inter', sans-serif;
            text-decoration: none; border-bottom: 1px solid rgba(8, 142, 170, .35);
        }
        .steps-container {
            grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; max-width: none;
        }
        .step-item {
            min-width: 0; padding: 17px 15px 15px; text-align: left;
            background: rgba(255, 255, 255, .83); border: 1px solid var(--landing-line);
            border-radius: 12px; box-shadow: 0 8px 22px rgba(31, 67, 86, .055);
        }
        .step-number {
            width: 27px; height: 27px; margin: 0 0 10px; border-radius: 9px;
            color: #148ba7; background: rgba(24, 181, 203, .11);
            font: 800 11px 'Inter', sans-serif;
        }
        .step-item h4 { margin-bottom: 6px; font: 700 13px 'Inter', sans-serif; }
        .step-item p { font-size: 11px; line-height: 1.45; }
        .features-section { max-width: 1240px; padding-top: 28px; }
        .features-section .section-header { margin-bottom: 28px; }
        .features-section .section-header h2 {
            font: 800 clamp(28px, 3vw, 38px)/1.1 'Roboto Condensed', sans-serif !important;
        }
        .glow-text {
            background: linear-gradient(100deg, #10bfc9, #287fe7 58%, #7656ed);
            -webkit-background-clip: text; background-clip: text;
        }
        @media (max-width: 900px) {
            .how-it-works { grid-template-columns: 1fr; gap: 22px; }
            .process-intro .section-header { max-width: 560px; }
            .stats-section { padding-bottom: 18px; }
        }
        @media (max-width: 640px) {
            .nav-brand-copy small { display: none; }
            .hero-badge { font-size: 9px; }
            .hero-benefits { gap: 8px 12px; font-size: 10px; }
            .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0; }
            .stat-item { padding: 10px 8px; grid-template-columns: 32px 1fr; column-gap: 8px; }
            .stat-item:nth-child(odd) { border-left: 0; }
            .stat-item:nth-child(n+3) { border-top: 1px solid rgba(31, 50, 53, .11); }
            .stat-icon { width: 30px; height: 30px; font-size: 18px; }
            .stat-item .number { font-size: 21px; }
            .stat-item .label { font-size: 10px; }
            .how-it-works { padding-top: 34px; padding-bottom: 22px; }
            .steps-container { grid-template-columns: 1fr; }
            .step-item { padding: 15px; }
            .features-section { padding-top: 34px; }
        }
        /* ===== ZOVIX showcase: pixel-matched to the reference design ===== */
        .landing-nav, .landing-nav.scrolled {
            height: max(52px, 4.1vw); padding: 0 6.6vw;
            display: flex; align-items: center; justify-content: space-between;
            background: rgba(255, 255, 255, .97); border-bottom: 1px solid rgba(20, 40, 80, .06);
            box-shadow: 0 2px 16px rgba(30, 60, 120, .05);
        }
        .nav-logo { gap: 10px; align-items: center; }
        .zx-logo-mark {
            width: clamp(30px, 2.5vw, 42px); aspect-ratio: 1; border-radius: 26%;
            background: linear-gradient(135deg, #ff4fa3 0%, #ff9d3d 34%, #2fe0c0 66%, #3b82f6 100%);
            box-shadow: 0 4px 12px rgba(80, 120, 255, .3), inset 0 0 0 1.5px rgba(255, 255, 255, .4);
        }
        .nav-brand-copy { gap: 3px; }
        .zx-logo-text { font: 800 clamp(20px, 1.75vw, 29px)/1 'Inter', sans-serif; letter-spacing: .07em; color: #14284b; }
        .nav-brand-copy small { font: 700 clamp(6px, .52vw, 9px)/1 'Inter', sans-serif; letter-spacing: .2em; color: #3b4c6b; }
        .landing-nav .nav-links { gap: clamp(14px, 2.1vw, 34px); align-items: center; }
        .landing-nav .nav-links a {
            display: inline-flex; align-items: center; color: #25365a;
            font: 500 clamp(11px, .84vw, 14px)/1 'Inter', sans-serif;
        }
        .landing-nav .nav-links a:hover { color: #1f6fe0; }
        .zx-caret {
            display: inline-block; width: .38em; height: .38em; margin-left: .55em;
            border-right: 1.6px solid currentColor; border-bottom: 1.6px solid currentColor;
            transform: rotate(45deg) translate(-10%, -10%);
        }
        .zx-nav-sep { width: 1px; height: 1.7em; margin: 0 -.3vw; background: rgba(20, 40, 80, .16); }
        .zx-lang { display: inline-flex; align-items: center; gap: .4em; color: #25365a; font: 600 clamp(11px, .84vw, 14px)/1 'Inter', sans-serif; }
        .zx-lang .zx-i { font-size: 1.55em; }
        .landing-nav .nav-links a.zx-login { padding: .62em 1.55em; border: 1.4px solid #15284b; border-radius: 99px; color: #15284b; font-weight: 600; }
        .landing-nav .nav-links a.nav-cta-btn {
            padding: .78em 1.6em; border-radius: 8px; color: #fff !important; font-weight: 700;
            background: linear-gradient(100deg, #10d6cf 0%, #3b82f6 100%); box-shadow: 0 6px 16px rgba(46, 140, 240, .28);
        }
        .zx-i {
            font-family: 'Material Symbols Rounded'; font-weight: normal; font-style: normal; line-height: 1;
            letter-spacing: normal; text-transform: none; white-space: nowrap; direction: ltr;
            -webkit-font-feature-settings: 'liga'; font-feature-settings: 'liga'; user-select: none;
        }

        .zx-landing { position: relative; width: 100%; padding-inline: clamp(8px, .7vw, 12px); overflow: hidden; container-type: inline-size; }
        [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] { gap: 0; }
        html { scroll-behavior: smooth; scroll-padding-top: 64px; }
        #how-it-works, #engines, #features, #pricing, #testimonials, #support,
        #engine-output-gallery, #about, #changelog, #roadmap {
            scroll-margin-top: 64px;
        }
        .landing-nav a:focus-visible, .zx-root a:focus-visible {
            outline: 3px solid #397dea;
            outline-offset: 4px;
        }
        .zx-root { --p: calc(100cqw / 1184); position: relative; color: #14284b; font-family: 'Inter', sans-serif; }
        .zx-root a { text-decoration: none; }
        .zx-stage {
            --y-scale: min(calc(var(--p) * 1.25), calc((100svh - 100px) * 0.0017));
            position: relative;
            height: calc(max(calc(100svh - 65px), calc(var(--p) * 554)) + calc(var(--p) * 460));
        }
        .zx-followup {
            --y-scale: var(--p);
            position: absolute;
            top: max(calc(100svh - 65px), calc(var(--p) * 530));
            left: 0;
            width: 100%;
            height: calc(var(--p) * 460);
        }
        .zx-a {
            position: absolute; left: calc(var(--p) * var(--x)); top: calc(var(--y-scale) * var(--y));
            width: calc(var(--p) * var(--w)); height: var(--hh, auto);
        }
        .zx-waves { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
        .zx-strip {
            --frame-top: calc(var(--p) * 34);
            position: absolute;
            top: var(--frame-top);
            left: 0;
            width: 100%;
            height: calc(var(--p) * 350);
            border: 1px solid rgba(255, 255, 255, .88);
            border-radius: 0 0 calc(var(--p) * 118) calc(var(--p) * 118) / 0 0 calc(var(--p) * 54) calc(var(--p) * 54);
            background: linear-gradient(115deg, rgba(255, 255, 255, .58), rgba(227, 241, 255, .32) 48%, rgba(237, 231, 255, .4));
            box-shadow: 0 calc(var(--p) * 15) calc(var(--p) * 42) rgba(66, 119, 194, .12), inset 0 1px 0 rgba(255, 255, 255, .9);
            isolation: isolate;
            z-index: 1;
        }
        .zx-strip::before {
            content: "";
            position: absolute;
            inset: 0;
            border-radius: inherit;
            background: radial-gradient(ellipse at 25% 0%, rgba(116, 203, 255, .18), transparent 50%),
                radial-gradient(ellipse at 80% 10%, rgba(164, 142, 255, .15), transparent 48%);
            pointer-events: none;
            z-index: 0;
        }
        .zx-strip .zx-tile { top: calc(var(--y-scale) * var(--y) - var(--frame-top)); }
        .zx-tile {
            margin: 0; overflow: hidden; z-index: 1; background: #dfe8f5;
            transform: perspective(calc(var(--p) * 900)) rotateY(var(--ry, 0deg)) rotate(var(--r, 0deg));
            border: calc(var(--p) * 1.6) solid rgba(255, 255, 255, .9); border-radius: calc(var(--p) * 10);
            box-shadow: 0 calc(var(--p) * 10) calc(var(--p) * 24) rgba(40, 70, 140, .22);
            transition: filter .2s ease, box-shadow .2s ease;
        }
        .zx-tile:hover { z-index: 4; filter: saturate(1.08); box-shadow: 0 calc(var(--p) * 14) calc(var(--p) * 28) rgba(40, 70, 140, .28); }
        .zx-tile img { display: block; width: 100%; height: 100%; object-fit: cover; }
        .zx-tile figcaption {
            position: absolute; left: calc(var(--p) * 9); bottom: calc(var(--p) * 8); color: #fff;
            font: 600 calc(var(--p) * 7.2)/1 'Inter', sans-serif; text-shadow: 0 1px 5px rgba(0, 0, 0, .7);
        }

        .zx-badge {
            z-index: 3; display: flex; align-items: center; gap: calc(var(--p) * 6); height: calc(var(--p) * 21);
            padding: 0 calc(var(--p) * 9); background: rgba(255, 255, 255, .92); white-space: nowrap;
            border: 1px solid rgba(40, 80, 160, .12); border-radius: 99px; box-shadow: 0 2px 10px rgba(40, 80, 160, .06);
            font: 500 calc(var(--p) * 7.4)/1 'Inter', sans-serif; color: #5a6a86; width: auto !important;
        }
        .zx-badge .zx-i { color: #fff; font-size: calc(var(--p) * 8); width: calc(var(--p) * 12); height: calc(var(--p) * 12); display: grid; place-items: center; border-radius: 50%; background: linear-gradient(135deg, #17c6e0, #3b6df0); }
        .zx-badge b { color: #1a5fd0; font-weight: 700; padding-right: calc(var(--p) * 7); border-right: 1px solid rgba(40, 80, 160, .16); }
        .zx-h1 {
            z-index: 3; margin: 0; padding: 0 !important; font: 800 calc(var(--p) * 40)/1 'Inter', sans-serif !important; line-height: calc(var(--p) * 37.5) !important;
            letter-spacing: -.035em; text-transform: uppercase; color: #0f2147; white-space: nowrap;
        }
        .zx-h1 [data-testid="stHeaderActionElements"] { display: none !important; }
        .zx-grad { background: linear-gradient(100deg, #12c9e4 0%, #2f86f2 60%, #4f6bf0 100%); -webkit-background-clip: text; background-clip: text; color: transparent; -webkit-text-fill-color: transparent; }
        .zx-sub { z-index: 3; font: 400 calc(var(--p) * 11.2)/1.45 'Inter', sans-serif; color: #2c3d5c; }
        .zx-cta { z-index: 3; display: flex; align-items: center; gap: calc(var(--p) * 16); }
        .zx-btn {
            display: inline-flex; align-items: center; justify-content: center; gap: calc(var(--p) * 7); white-space: nowrap;
            font: 700 calc(var(--p) * 8.6)/1 'Inter', sans-serif; letter-spacing: .06em; text-transform: uppercase; border-radius: 99px;
        }
        .zx-btn .zx-i { font-size: calc(var(--p) * 12); }
        .zx-btn-primary {
            height: calc(var(--p) * 35); width: calc(var(--p) * 193); color: #fff !important;
            background: linear-gradient(100deg, #12d8cc 0%, #3d86f3 58%, #6c4df0 100%);
            box-shadow: 0 calc(var(--p) * 8) calc(var(--p) * 20) rgba(70, 110, 240, .32);
        }
        .zx-btn-ghost { height: calc(var(--p) * 33); width: calc(var(--p) * 172); color: #14284b !important; background: rgba(255, 255, 255, .7); border: 1.3px solid #1a2c50; }
        .zx-checks { z-index: 3; display: flex; align-items: center; gap: calc(var(--p) * 20); font: 500 calc(var(--p) * 7.6)/1 'Inter', sans-serif; color: #31425f; white-space: nowrap; }
        .zx-checks span { display: inline-flex; align-items: center; gap: calc(var(--p) * 5); }
        .zx-checks span::before {
            content: "✓"; display: grid; place-items: center; width: calc(var(--p) * 11); height: calc(var(--p) * 11);
            border: 1.2px solid #1fb3d4; border-radius: 50%; color: #139ec4; font-size: calc(var(--p) * 7); font-weight: 800;
        }

        .zx-demo {
            z-index: 3; display: block; overflow: hidden; color: #fff !important;
            background-size: cover; background-position: center; border-radius: calc(var(--p) * 12);
            border: calc(var(--p) * 2.5) solid rgba(255, 255, 255, .92);
            box-shadow: 0 calc(var(--p) * 16) calc(var(--p) * 40) rgba(60, 100, 200, .32), 0 0 0 calc(var(--p) * 6) rgba(170, 200, 255, .22);
        }
        .zx-demo::before { content: ""; position: absolute; inset: 0; background: linear-gradient(180deg, rgba(8, 20, 50, .38), rgba(8, 20, 50, .02) 42%, rgba(5, 10, 30, .62)); }
        .zx-demo-title { position: absolute; left: calc(var(--p) * 20); top: calc(var(--p) * 17); font: 800 calc(var(--p) * 21)/1.1 'Inter', sans-serif; letter-spacing: .02em; }
        .zx-demo-title small { display: block; margin-top: calc(var(--p) * 3); color: #fff; font: 700 calc(var(--p) * 14.5)/1.2 'Inter', sans-serif; letter-spacing: .03em; }
        .zx-play {
            position: absolute; left: 50%; top: 52%; display: grid; place-items: center; width: calc(var(--p) * 46); height: calc(var(--p) * 46);
            transform: translate(-50%, -50%); border-radius: 50%; background: rgba(22, 30, 48, .62); border: 1px solid rgba(255, 255, 255, .4); backdrop-filter: blur(6px);
        }
        .zx-play .zx-i { font-size: calc(var(--p) * 26); color: #fff; }
        .zx-demo-cap { position: absolute; left: calc(var(--p) * 14); bottom: calc(var(--p) * 11); font: 600 calc(var(--p) * 8)/1 'Inter', sans-serif; }
        .zx-demo-time { position: absolute; right: calc(var(--p) * 12); bottom: calc(var(--p) * 9); display: inline-flex; align-items: center; gap: calc(var(--p) * 3); padding: calc(var(--p) * 3) calc(var(--p) * 6); border-radius: 99px; background: rgba(10, 20, 40, .5); font: 600 calc(var(--p) * 7.6)/1 'Inter', sans-serif; }
        .zx-demo-time .zx-i { font-size: calc(var(--p) * 9); }

        .zx-stats {
            z-index: 2; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)) minmax(0, .78fr); align-items: center;
            background: rgba(255, 255, 255, .96); border: 1px solid rgba(40, 80, 160, .08);
            border-radius: calc(var(--p) * 11); box-shadow: 0 calc(var(--p) * 10) calc(var(--p) * 28) rgba(50, 90, 170, .13);
        }
        .zx-stat { display: flex; align-items: center; gap: calc(var(--p) * 9); height: calc(var(--p) * 38); padding-left: calc(var(--p) * 14); }
        .zx-stat + .zx-stat { border-left: 1px solid rgba(40, 80, 160, .1); }
        .zx-stat .zx-stat-ico {
            position: relative !important;
            display: grid !important;
            flex: none !important;
            place-items: center !important;
            width: calc(var(--p) * 38) !important;
            height: calc(var(--p) * 38) !important;
            margin: 0 !important;
            padding: 0 !important;
            box-sizing: border-box !important;
            border-radius: 50% !important;
            background: #eaf0ff;
        }
        .zx-stat .zx-stat-ico .zx-i {
            position: static !important;
            display: block !important;
            width: auto !important;
            height: auto !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1 !important;
            transform: none !important;
            font-size: calc(var(--p) * 19) !important;
        }
        .zx-stat b { display: block; font: 800 calc(var(--p) * 19)/1.05 'Inter', sans-serif; color: #14284b; }
        .zx-stat span { display: block; margin-top: calc(var(--p) * 2); font: 500 calc(var(--p) * 7.6)/1.2 'Inter', sans-serif; color: #5a6a86; }
        .zx-tagline { position: relative; padding-left: calc(var(--p) * 22); font: 700 calc(var(--p) * 13.5)/1.1 'Caveat', cursive; color: #1d4f9c; transform: rotate(-4deg); }
        .zx-tagline svg { display: block; width: 78%; height: calc(var(--p) * 8); margin-top: calc(var(--p) * 2); }

        .zx-pill {
            z-index: 3; display: inline-flex; align-items: center; gap: calc(var(--p) * 5); height: calc(var(--p) * 15); width: auto !important;
            padding: 0 calc(var(--p) * 8) 0 calc(var(--p) * 3); border-radius: 99px; background: #fff; border: 1px solid rgba(40, 80, 160, .12);
            font: 700 calc(var(--p) * 6.4)/1 'Inter', sans-serif; letter-spacing: .1em; color: #1a73d6; white-space: nowrap;
        }
        .zx-pill .zx-i { display: grid; place-items: center; width: calc(var(--p) * 9); height: calc(var(--p) * 9); border-radius: 50%; background: linear-gradient(135deg, #17c6e0, #3b6df0); color: #fff; font-size: calc(var(--p) * 6); }
        .zx-hiw-title { z-index: 3; font: 800 clamp(22px, calc(var(--p) * 23), 26px)/1.16 'Inter', sans-serif; color: #0f2147; letter-spacing: -.025em; }
        .zx-hiw-text { z-index: 3; font: 400 calc(var(--p) * 8.2)/1.5 'Inter', sans-serif; color: #3f4f6c; }
        .zx-hiw-text b { color: #14284b; font-weight: 700; }
        .zx-watch { z-index: 3; display: inline-flex; align-items: center; gap: calc(var(--p) * 8); width: auto !important; color: #1f78e0 !important; font: 700 calc(var(--p) * 8.4)/1 'Inter', sans-serif; }
        .zx-watch .zx-i { display: grid; place-items: center; width: calc(var(--p) * 26); height: calc(var(--p) * 26); border-radius: 50%; color: #fff; font-size: calc(var(--p) * 16); background: linear-gradient(135deg, #16cbd8, #3b6df0); box-shadow: 0 calc(var(--p) * 5) calc(var(--p) * 12) rgba(50, 110, 240, .35); }
        .zx-watch span { border-bottom: 1px solid currentColor; padding-bottom: 1px; }
        .zx-step {
            z-index: 3; display: flex; flex-direction: column; padding: calc(var(--p) * 11) calc(var(--p) * 13);
            background: rgba(255, 255, 255, .96); border: 1px solid rgba(40, 80, 160, .1); border-radius: calc(var(--p) * 9);
            box-shadow: 0 calc(var(--p) * 8) calc(var(--p) * 22) rgba(40, 70, 140, .1);
        }
        .zx-num { align-self: flex-start; padding: calc(var(--p) * 3) calc(var(--p) * 5); margin-bottom: calc(var(--p) * 5); border-radius: calc(var(--p) * 4); background: #e8f2ff; color: #1a73d6; font: 700 calc(var(--p) * 7)/1 'Inter', sans-serif; }
        .zx-ficon { position: absolute; left: 50%; top: calc(var(--p) * -8); display: grid; place-items: center; width: calc(var(--p) * 22); height: calc(var(--p) * 22); border-radius: 50%; background: #eaf3ff; border: 1px solid rgba(40, 80, 160, .1); color: #2a86f0; box-shadow: 0 calc(var(--p) * 4) calc(var(--p) * 10) rgba(50, 110, 240, .18); }
        .zx-ficon .zx-i { font-size: calc(var(--p) * 13); }
        .zx-step-t { font: 800 calc(var(--p) * 10.4)/1.2 'Inter', sans-serif; color: #14284b; }
        .zx-step-d { margin-top: calc(var(--p) * 3); font: 400 calc(var(--p) * 7.6)/1.42 'Inter', sans-serif; color: #4a5a76; }
        .zx-mock { margin-top: auto; }
        .zx-mock-input { padding: calc(var(--p) * 5) calc(var(--p) * 7); border: 1px solid #d5e0f2; border-radius: calc(var(--p) * 5); background: #fbfdff; font: italic 400 calc(var(--p) * 6.6)/1.2 'Inter', sans-serif; color: #7b8aa6; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; box-shadow: inset 0 -2px 0 rgba(59, 130, 246, .35); }
        .zx-mock-icons { display: flex; gap: calc(var(--p) * 6); }
        .zx-mock-icons span { display: grid; place-items: center; width: calc(var(--p) * 20); height: calc(var(--p) * 20); border-radius: calc(var(--p) * 6); }
        .zx-mock-icons .zx-i { font-size: calc(var(--p) * 12); }
        .zx-mock-thumb { position: relative; height: calc(var(--p) * 30); border-radius: calc(var(--p) * 5); background-size: cover; background-position: center; }
        .zx-mock-thumb span { position: absolute; left: 50%; top: 50%; display: grid; place-items: center; width: calc(var(--p) * 16); height: calc(var(--p) * 16); transform: translate(-50%, -50%); border-radius: 50%; background: rgba(15, 25, 45, .72); color: #fff; }
        .zx-mock-thumb .zx-i { font-size: calc(var(--p) * 11); }
        .zx-arrow { z-index: 3; display: grid; place-items: center; color: #18a9e6; }
        .zx-arrow .zx-i { font-size: calc(var(--p) * 17); }
        .zx-cube { z-index: 1; filter: drop-shadow(0 calc(var(--p) * 8) calc(var(--p) * 14) rgba(40, 110, 255, .35)); }

        .zx-eng-title { z-index: 3; font: 800 calc(var(--p) * 8.6)/1 'Inter', sans-serif; letter-spacing: .05em; text-transform: uppercase; color: #14284b; }
        .zx-eng-sub { z-index: 3; font: 400 calc(var(--p) * 8)/1 'Inter', sans-serif; color: #5a6a86; }
        .zx-eng { z-index: 3; display: grid; grid-template-columns: repeat(9, 1fr); gap: calc(var(--p) * 8); }
        .zx-eng-card {
            display: flex; flex-direction: column; gap: calc(var(--p) * 3); min-width: 0; padding: calc(var(--p) * 8) calc(var(--p) * 9);
            background: rgba(255, 255, 255, .96); border: 1px solid rgba(40, 80, 160, .08); border-radius: calc(var(--p) * 8);
            box-shadow: 0 calc(var(--p) * 6) calc(var(--p) * 16) rgba(40, 70, 140, .08);
        }
        .zx-eico { display: grid; place-items: center; width: calc(var(--p) * 20); height: calc(var(--p) * 20); margin-bottom: calc(var(--p) * 2); border-radius: calc(var(--p) * 6); }
        .zx-eico .zx-i { font-size: calc(var(--p) * 13); }
        .zx-eng-card b { font: 700 calc(var(--p) * 8.2)/1.15 'Inter', sans-serif; color: #14284b; white-space: nowrap; }
        .zx-eng-card span { font: 400 calc(var(--p) * 6.5)/1.25 'Inter', sans-serif; color: #6a7a96; }

        .zx-hiw-text { font-size: clamp(12px, calc(var(--p) * 8.2), 15px); }
        .zx-watch { font-size: clamp(12px, calc(var(--p) * 8.4), 14px); }
        .zx-step { min-height: calc(var(--p) * 130); }
        .zx-step-t { font-size: clamp(13px, calc(var(--p) * 10.4), 16px); }
        .zx-step-d { font-size: clamp(11px, calc(var(--p) * 7.6), 14px); }
        .zx-eng-title { font-size: clamp(12px, calc(var(--p) * 8.6), 14px); }
        .zx-eng-sub { font-size: clamp(11px, calc(var(--p) * 8), 13px); }
        .zx-eng-card b { font-size: clamp(11px, calc(var(--p) * 8.2), 14px); white-space: normal; }
        .zx-eng-card span { font-size: clamp(10px, calc(var(--p) * 6.5), 12px); }

        @media (max-width: 900px) {
            .landing-nav .nav-links a:not(.nav-cta-btn), .zx-nav-sep, .zx-lang { display: none !important; }
            .landing-nav .nav-links { display: flex !important; }
            .landing-nav .nav-links a.nav-cta-btn { display: inline-flex !important; }
            .zx-root { --p: min(1.15px, calc(100cqw / 400)); }
            .zx-stage { display: flex; flex-direction: column; align-items: flex-start; gap: calc(var(--p) * 16); height: auto; padding: calc(var(--p) * 70) calc(var(--p) * 18) calc(var(--p) * 28); }
            .zx-a { position: static; width: auto; height: auto; }
            .zx-waves, .zx-cube, .zx-arrow, .zx-tile.zx-sm { display: none; }
            .zx-strip {
                position: relative;
                top: auto;
                display: flex;
                gap: 8px;
                align-self: stretch;
                width: calc(100% + var(--p) * 36);
                height: calc(var(--p) * 104);
                margin: 0 calc(var(--p) * -18);
                padding: calc(var(--p) * 6);
                overflow: hidden;
                border-radius: calc(var(--p) * 28);
                background: linear-gradient(115deg, rgba(255, 255, 255, .72), rgba(227, 241, 255, .52) 48%, rgba(237, 231, 255, .58));
                box-shadow: 0 8px 24px rgba(66, 119, 194, .12), inset 0 0 0 1px rgba(255, 255, 255, .9);
            }
            .zx-strip::before { border-radius: inherit; }
            .zx-tile { position: static; flex: 0 0 38%; width: auto; height: 100%; transform: none; }
            .zx-h1 { white-space: normal; }
            .zx-sub, .zx-hiw-text { width: 100% !important; }
            .zx-cta { flex-wrap: wrap; }
            .zx-checks { flex-wrap: wrap; gap: calc(var(--p) * 8) calc(var(--p) * 14); white-space: normal; }
            .zx-demo {
                position: relative !important;
                left: auto !important;
                top: auto !important;
                align-self: stretch;
                width: 100%;
                height: clamp(120px, 34vw, 155px);
                aspect-ratio: auto;
                flex: none;
            }
            .zx-stats { align-self: stretch; grid-template-columns: 1fr 1fr; row-gap: calc(var(--p) * 6); padding: calc(var(--p) * 8) 0; }
            .zx-stat + .zx-stat { border-left: 0; }
            .zx-tagline { grid-column: 1 / -1; padding: calc(var(--p) * 4) calc(var(--p) * 14); }
            .zx-step, .zx-eng { align-self: stretch; }
            .zx-step { min-height: calc(var(--p) * 120); }
            .zx-ficon { left: auto; right: calc(var(--p) * 14); }
            .zx-eng { grid-template-columns: repeat(3, 1fr); }
        }
        @media (max-width: 480px) { .zx-eng { grid-template-columns: repeat(2, 1fr); } }
        .features-section, .testimonials-section, .pricing-section, .faq-section,
        .cta-section, .landing-footer {
            width: 100%;
            max-width: 1800px;
            padding-left: clamp(16px, 2vw, 32px);
            padding-right: clamp(16px, 2vw, 32px);
        }
        .features-grid, .testimonials-grid, .pricing-grid {
            width: 100%;
            max-width: none;
        }
        .payment-methods { max-width: 1400px; }
        .faq-list { max-width: 1100px; }
        .footer-content, .footer-bottom { max-width: none; }
        .landing-footer {
            width: 100%;
            max-width: 1920px;
            margin: 0 auto;
            padding-right: clamp(20px, 4vw, 64px);
            padding-left: clamp(20px, 4vw, 64px);
        }
        .footer-content {
            display: grid;
            grid-template-columns: minmax(0, 1.6fr) repeat(3, minmax(140px, 1fr));
            align-items: start;
            gap: clamp(24px, 4vw, 64px);
            width: min(100%, 1640px);
            margin: 0 auto;
        }
        .footer-brand { max-width: 380px; }
        .footer-brand p { max-width: 340px; line-height: 1.6; }
        .footer-col { min-width: 0; }
        .footer-col h5 { margin: 0 0 12px; }
        .footer-col a { padding: 7px 0; }
        .footer-bottom {
            width: min(100%, 1640px);
            margin: 30px auto 0;
        }
        @media (max-width: 900px) {
            .footer-content { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 30px 40px; }
            .footer-brand { grid-column: 1 / -1; max-width: 560px; }
        }
        @media (max-width: 520px) {
            .footer-content { gap: 24px 18px; }
            .footer-brand { grid-column: 1 / -1; }
            .footer-col:last-child { grid-column: 1 / -1; }
        }
        .engine-gallery-section {
            position: relative;
            z-index: 1;
            width: 100%;
            max-width: 1920px;
            margin: 0 auto;
            padding: clamp(48px, 6vw, 88px) clamp(12px, 1.2vw, 24px);
        }
        .engine-gallery-section .section-header {
            max-width: 820px;
            margin: 0 auto 34px;
        }
        .engine-gallery-section .section-header h2 {
            font: 800 clamp(32px, 4vw, 50px)/1.08 'Roboto Condensed', sans-serif;
        }
        .engine-gallery-section .section-header p { font-size: 16px; }
        .engine-gallery-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: clamp(12px, 1.5vw, 22px);
        }
        .engine-gallery-card {
            min-width: 0;
            overflow: hidden;
            border: 1px solid rgba(226, 239, 229, .12);
            border-radius: 16px;
            background: linear-gradient(155deg, rgba(255, 255, 255, .055), rgba(255, 255, 255, .018));
            box-shadow: 0 16px 38px rgba(0, 0, 0, .16);
            transition: transform .25s ease, border-color .25s ease, box-shadow .25s ease;
        }
        .engine-gallery-card:hover {
            transform: translateY(-4px);
            border-color: rgba(145, 223, 180, .38);
            box-shadow: 0 22px 44px rgba(0, 0, 0, .24);
        }
        .engine-gallery-card img {
            display: block;
            width: 100%;
            aspect-ratio: 16 / 11;
            object-fit: cover;
            background: #18231d;
        }
        .engine-gallery-card-copy { padding: 16px; }
        .engine-gallery-engine {
            display: inline-block;
            margin-bottom: 9px;
            color: var(--landing-mint);
            font: 700 10px/1.3 'Inter', sans-serif;
            letter-spacing: .1em;
            text-transform: uppercase;
        }
        .engine-gallery-card h3 {
            margin: 0 0 7px;
            color: var(--landing-text);
            font: 700 17px/1.25 'Inter', sans-serif;
        }
        .engine-gallery-card p {
            margin: 0;
            color: var(--landing-muted);
            font: 400 13px/1.5 'Inter', sans-serif;
        }
        .engine-gallery-note {
            margin: 20px 0 0;
            color: var(--landing-muted);
            font: 400 12px/1.5 'Inter', sans-serif;
            text-align: center;
        }
        .about-section {
            position: relative;
            z-index: 1;
            width: 100%;
            max-width: 1920px;
            margin: 0 auto;
            padding: clamp(52px, 6vw, 88px) clamp(16px, 2vw, 32px);
        }
        .about-hero {
            position: relative;
            display: flex;
            min-height: clamp(280px, 34vw, 420px);
            flex-direction: column;
            justify-content: flex-end;
            overflow: hidden;
            margin-bottom: 30px;
            padding: clamp(26px, 5vw, 60px);
            border-radius: 24px 100px 24px 100px;
            background:
                linear-gradient(90deg, rgba(11, 20, 27, .86), rgba(11, 20, 27, .42) 72%, rgba(11, 20, 27, .2)),
                linear-gradient(0deg, rgba(8, 13, 18, .58), transparent 75%),
                url('https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1800&q=88') center 48%/cover;
            box-shadow: 0 26px 60px rgba(20, 42, 57, .2);
        }
        .about-section .section-header {
            max-width: 920px;
            margin: 0 0 14px;
            text-align: left;
        }
        .about-hero .section-header .tag {
            color: #d4fff0;
            background: rgba(10, 30, 31, .42);
            border-color: rgba(212, 255, 240, .3);
        }
        .about-section .section-header h2 {
            color: #fff;
            font: 800 clamp(32px, 4vw, 50px)/1.08 'Roboto Condensed', sans-serif;
        }
        .about-intro {
            max-width: 920px;
            margin: 0;
            color: rgba(255, 255, 255, .9);
            font: 400 clamp(15px, 1.25vw, 18px)/1.7 'Inter', sans-serif;
            text-align: left;
        }
        .about-pillars {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: clamp(14px, 2vw, 24px);
        }
        .about-pillar {
            padding: clamp(20px, 2.2vw, 30px);
            border: 1px solid var(--landing-line);
            border-radius: 16px;
            background: rgba(255, 255, 255, .72);
            box-shadow: 0 14px 32px rgba(31, 50, 53, .07);
        }
        .about-pillar-icon {
            display: grid;
            width: 44px;
            height: 44px;
            margin-bottom: 16px;
            place-items: center;
            border-radius: 13px;
            background: rgba(32, 189, 181, .12);
            font-size: 22px;
        }
        .about-pillar h3 {
            margin: 0 0 9px;
            color: var(--landing-text);
            font: 700 18px/1.3 'Inter', sans-serif;
        }
        .about-pillar p {
            margin: 0;
            color: var(--landing-muted);
            font: 400 14px/1.6 'Inter', sans-serif;
        }
        .about-workflow {
            margin: 28px auto 0;
            padding: clamp(20px, 3vw, 34px);
            border: 1px solid var(--landing-line);
            border-radius: 16px;
            background: linear-gradient(110deg, rgba(32, 189, 181, .08), rgba(237, 152, 116, .08));
            text-align: center;
        }
        .about-workflow h3 {
            margin: 0 0 8px;
            color: var(--landing-text);
            font: 700 20px/1.3 'Inter', sans-serif;
        }
        .about-workflow p {
            max-width: 800px;
            margin: 0 auto;
            color: var(--landing-muted);
            font: 400 14px/1.65 'Inter', sans-serif;
        }
        .about-workflow a {
            display: inline-flex;
            margin-top: 17px;
            color: #15847f;
            font: 700 13px/1.4 'Inter', sans-serif;
            text-decoration: none;
        }
        .about-workflow a:hover { text-decoration: underline; }
        .blog-section {
            position: relative;
            z-index: 1;
            width: 100%;
            max-width: 1920px;
            margin: 0 auto;
            padding: clamp(46px, 5vw, 76px) clamp(12px, 1.2vw, 24px);
        }
        .blog-hero {
            position: relative;
            display: flex;
            min-height: clamp(280px, 34vw, 420px);
            align-items: flex-end;
            overflow: hidden;
            margin-bottom: 30px;
            padding: clamp(26px, 5vw, 60px);
            border-radius: 24px 100px 24px 100px;
            background:
                linear-gradient(90deg, rgba(11, 20, 27, .86), rgba(11, 20, 27, .38) 70%, rgba(11, 20, 27, .16)),
                linear-gradient(0deg, rgba(8, 13, 18, .58), transparent 75%),
                url('https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1800&q=88') center 48%/cover;
            box-shadow: 0 26px 60px rgba(20, 42, 57, .2);
        }
        .blog-hero-copy { position: relative; max-width: 760px; }
        .blog-hero .eyebrow {
            margin-bottom: 12px;
            color: #baf4da;
            font: 700 11px/1.3 'Inter', sans-serif;
            letter-spacing: .16em;
            text-transform: uppercase;
        }
        .blog-hero h2 {
            margin: 0 0 12px;
            color: #fff;
            font: 800 clamp(34px, 5vw, 58px)/1.04 'Roboto Condensed', sans-serif;
        }
        .blog-hero p {
            max-width: 660px;
            margin: 0;
            color: rgba(255, 255, 255, .88);
            font: 400 clamp(14px, 1.2vw, 17px)/1.6 'Inter', sans-serif;
        }
        .blog-post-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: clamp(14px, 2vw, 24px);
        }
        .blog-post {
            min-width: 0;
            overflow: hidden;
            border: 1px solid var(--landing-line);
            border-radius: 16px;
            background: rgba(255, 255, 255, .84);
            box-shadow: 0 14px 32px rgba(31, 50, 53, .07);
        }
        .blog-post img {
            display: block;
            width: 100%;
            aspect-ratio: 16 / 10;
            object-fit: cover;
            background: #18231d;
        }
        .blog-post-copy { padding: clamp(16px, 2vw, 24px); }
        .blog-post-topic {
            display: inline-block;
            margin-bottom: 9px;
            color: #168e89;
            font: 700 10px/1.3 'Inter', sans-serif;
            letter-spacing: .1em;
            text-transform: uppercase;
        }
        .blog-post h3 {
            margin: 0 0 8px;
            color: var(--landing-text);
            font: 700 18px/1.3 'Inter', sans-serif;
        }
        .blog-post p {
            margin: 0;
            color: var(--landing-muted);
            font: 400 13px/1.6 'Inter', sans-serif;
        }
        .blog-studio-link {
            display: flex;
            width: fit-content;
            margin: 24px auto 0;
            padding: 12px 18px;
            border-radius: 99px;
            background: linear-gradient(110deg, #20bdb5, #397dea 72%, #7656ed);
            color: #fff !important;
            font: 700 12px/1.2 'Inter', sans-serif;
            text-decoration: none !important;
            text-transform: uppercase;
        }
        .changelog-section, .roadmap-section {
            position: relative;
            z-index: 1;
            width: 100%;
            max-width: 1920px;
            margin: 0 auto;
            padding: clamp(46px, 5vw, 76px) clamp(12px, 1.2vw, 24px);
        }
        .changelog-hero, .roadmap-hero {
            position: relative;
            display: flex;
            min-height: clamp(280px, 34vw, 420px);
            align-items: flex-end;
            overflow: hidden;
            margin-bottom: 30px;
            padding: clamp(26px, 5vw, 60px);
            border-radius: 24px 100px 24px 100px;
            background:
                linear-gradient(90deg, rgba(11, 20, 27, .86), rgba(11, 20, 27, .38) 70%, rgba(11, 20, 27, .16)),
                linear-gradient(0deg, rgba(8, 13, 18, .58), transparent 75%),
                url('https://images.unsplash.com/photo-1553877522-43269d4ea984?auto=format&fit=crop&w=1800&q=88') center 48%/cover;
            box-shadow: 0 26px 60px rgba(20, 42, 57, .2);
        }
        .changelog-hero-copy, .roadmap-hero-copy { position: relative; max-width: 760px; }
        .changelog-hero .eyebrow, .roadmap-hero .eyebrow {
            margin-bottom: 12px;
            color: #c9dcff;
            font: 700 11px/1.3 'Inter', sans-serif;
            letter-spacing: .16em;
            text-transform: uppercase;
        }
        .changelog-hero h2, .roadmap-hero h2 {
            margin: 0 0 12px;
            color: #fff;
            font: 800 clamp(34px, 5vw, 58px)/1.04 'Roboto Condensed', sans-serif;
        }
        .changelog-hero p, .roadmap-hero p {
            max-width: 660px;
            margin: 0;
            color: rgba(255, 255, 255, .9);
            font: 400 clamp(14px, 1.2vw, 17px)/1.6 'Inter', sans-serif;
        }
        .changelog-grid, .roadmap-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: clamp(14px, 2vw, 24px);
        }
        .changelog-card, .roadmap-card {
            min-width: 0;
            overflow: hidden;
            border: 1px solid var(--landing-line);
            border-radius: 16px;
            background: rgba(255, 255, 255, .84);
            box-shadow: 0 14px 32px rgba(31, 50, 53, .07);
        }
        .changelog-card img, .roadmap-card img {
            display: block;
            width: 100%;
            aspect-ratio: 16 / 10;
            object-fit: cover;
            background: #18231d;
        }
        .changelog-card-copy, .roadmap-card-copy { padding: clamp(16px, 2vw, 24px); }
        .changelog-card-label, .roadmap-card-label {
            display: inline-block;
            margin-bottom: 9px;
            color: #168e89;
            font: 700 10px/1.3 'Inter', sans-serif;
            letter-spacing: .1em;
            text-transform: uppercase;
        }
        .changelog-card h3, .roadmap-card h3 {
            margin: 0 0 8px;
            color: var(--landing-text);
            font: 700 18px/1.3 'Inter', sans-serif;
        }
        .changelog-card p, .roadmap-card p {
            margin: 0;
            color: var(--landing-muted);
            font: 400 13px/1.6 'Inter', sans-serif;
        }
        .changelog-studio-link, .roadmap-studio-link {
            display: flex;
            width: fit-content;
            margin: 24px auto 0;
            padding: 12px 18px;
            border-radius: 99px;
            background: linear-gradient(110deg, #20bdb5, #397dea 72%, #7656ed);
            color: #fff !important;
            font: 700 12px/1.2 'Inter', sans-serif;
            text-decoration: none !important;
            text-transform: uppercase;
        }
        .roadmap-card-label { color: #397dea; }
        .roadmap-note {
            max-width: 920px;
            margin: 18px auto 0;
            color: var(--landing-muted);
            font: 400 12px/1.6 'Inter', sans-serif;
            text-align: center;
        }
        @media (max-width: 700px) {
            .blog-post-grid, .changelog-grid, .roadmap-grid { grid-template-columns: 1fr; }
            .blog-hero, .about-hero, .careers-hero, .changelog-hero, .roadmap-hero { min-height: 300px; border-radius: 20px 70px 20px 70px; }
        }
        .careers-section {
            position: relative;
            z-index: 1;
            width: 100%;
            max-width: 1920px;
            margin: 0 auto;
            padding: clamp(46px, 5vw, 76px) clamp(12px, 1.2vw, 24px);
        }
        .careers-hero {
            position: relative;
            display: flex;
            min-height: clamp(290px, 36vw, 440px);
            align-items: flex-end;
            overflow: hidden;
            margin-bottom: 30px;
            padding: clamp(26px, 5vw, 60px);
            border-radius: 24px 100px 24px 100px;
            background:
                linear-gradient(90deg, rgba(12, 19, 30, .86), rgba(12, 19, 30, .40) 70%, rgba(12, 19, 30, .18)),
                linear-gradient(0deg, rgba(8, 13, 18, .58), transparent 75%),
                url('https://images.unsplash.com/photo-1521737711867-e3b97375f902?auto=format&fit=crop&w=1800&q=88') center 48%/cover;
            box-shadow: 0 26px 60px rgba(20, 42, 57, .2);
        }
        .careers-hero-copy { position: relative; max-width: 760px; }
        .careers-hero .eyebrow {
            margin-bottom: 12px;
            color: #c9dcff;
            font: 700 11px/1.3 'Inter', sans-serif;
            letter-spacing: .16em;
            text-transform: uppercase;
        }
        .careers-hero h2 {
            margin: 0 0 12px;
            color: #fff;
            font: 800 clamp(34px, 5vw, 58px)/1.04 'Roboto Condensed', sans-serif;
        }
        .careers-hero p {
            max-width: 660px;
            margin: 0;
            color: rgba(255, 255, 255, .9);
            font: 400 clamp(14px, 1.2vw, 17px)/1.6 'Inter', sans-serif;
        }
        .careers-focus-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: clamp(14px, 2vw, 24px);
        }
        .careers-focus-card {
            min-width: 0;
            padding: clamp(18px, 2.3vw, 28px);
            border: 1px solid var(--landing-line);
            border-radius: 16px;
            background: rgba(255, 255, 255, .84);
            box-shadow: 0 14px 32px rgba(31, 50, 53, .07);
        }
        .careers-focus-card span {
            display: block;
            margin-bottom: 10px;
            color: #168e89;
            font: 700 10px/1.3 'Inter', sans-serif;
            letter-spacing: .1em;
            text-transform: uppercase;
        }
        .careers-focus-card h3 {
            margin: 0 0 8px;
            color: var(--landing-text);
            font: 700 18px/1.3 'Inter', sans-serif;
        }
        .careers-focus-card p {
            margin: 0;
            color: var(--landing-muted);
            font: 400 13px/1.6 'Inter', sans-serif;
        }
        .careers-note {
            margin: 20px 0 0;
            color: var(--landing-muted);
            font: 400 12px/1.55 'Inter', sans-serif;
            text-align: center;
        }
        .careers-studio-link {
            display: flex;
            width: fit-content;
            margin: 22px auto 0;
            padding: 12px 18px;
            border-radius: 99px;
            background: linear-gradient(110deg, #3b6cf6, #20bdb5 72%, #7656ed);
            color: #fff !important;
            font: 700 12px/1.2 'Inter', sans-serif;
            text-decoration: none !important;
            text-transform: uppercase;
        }
        @media (max-width: 700px) {
            .careers-focus-grid { grid-template-columns: 1fr; }
        }
        .ready-create-section { width: 100%; }
        .ready-create-section .cta-container { max-width: 1040px; }
        .ready-create-section .cta-container > p {
            max-width: 720px;
            margin: 0 auto 28px;
            line-height: 1.65;
        }
        .ready-create-steps {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 16px;
            margin: 0 auto 28px;
            text-align: left;
        }
        .ready-create-step {
            padding: 18px;
            border: 1px solid rgba(226, 239, 229, .13);
            border-radius: 14px;
            background: rgba(255, 255, 255, .035);
        }
        .ready-create-step span {
            display: block;
            margin-bottom: 8px;
            color: var(--landing-mint);
            font: 700 11px/1.2 'Inter', sans-serif;
            letter-spacing: .12em;
        }
        .ready-create-step h3 {
            margin: 0 0 6px;
            color: var(--landing-text);
            font: 700 15px/1.3 'Inter', sans-serif;
        }
        .ready-create-step p {
            margin: 0;
            font: 400 13px/1.5 'Inter', sans-serif;
        }
        @media (max-width: 1100px) {
            .engine-gallery-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        }
        @media (max-width: 700px) {
            .engine-gallery-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
            .engine-gallery-card-copy { padding: 13px; }
            .engine-gallery-card h3 { font-size: 15px; }
            .engine-gallery-card p { font-size: 12px; }
            .ready-create-steps { grid-template-columns: 1fr; }
            .about-pillars { grid-template-columns: 1fr; }
        }
        @media (max-width: 380px) {
            .engine-gallery-grid { grid-template-columns: 1fr; }
        }
        .cinematic-guide {
            position: relative;
            width: 100%;
            max-width: 1920px;
            margin: 0 auto;
            padding: clamp(36px, 5vw, 76px) clamp(12px, 1.2vw, 24px);
            overflow: hidden;
        }
        @media (min-width: 561px) {
            section.cinematic-guide#cinematic-engine {
                padding-top: clamp(34px, 3vw, 48px);
            }
        }
        .cinematic-guide::before {
            position: absolute;
            top: 12%;
            left: 50%;
            width: min(70vw, 1000px);
            height: 80%;
            content: "";
            background: radial-gradient(ellipse, rgba(32, 189, 181, .10), transparent 68%);
            transform: translateX(-50%);
            pointer-events: none;
        }
        .cinematic-guide-inner {
            position: relative;
            display: grid;
            grid-template-columns: minmax(0, 1.02fr) minmax(0, 1fr);
            align-items: center;
            gap: clamp(28px, 4vw, 64px);
            width: min(100%, 1700px);
            margin: 0 auto;
        }
        .cinematic-guide-visual {
            position: relative;
            min-height: clamp(330px, 36vw, 520px);
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, .58);
            border-radius: 28px 120px 28px 120px;
            background:
                linear-gradient(180deg, rgba(9, 20, 31, .08) 10%, rgba(9, 20, 31, .22) 42%, rgba(9, 20, 31, .88) 100%),
                url('https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?auto=format&fit=crop&w=1500&q=90') center 48%/cover;
            box-shadow: 0 34px 70px rgba(20, 42, 57, .24), 0 0 0 10px rgba(255, 255, 255, .28);
            transform: perspective(1200px) rotateY(-7deg) rotateX(2deg);
            transition: transform .4s ease, box-shadow .4s ease;
            isolation: isolate;
        }
        .cinematic-guide-visual:hover {
            box-shadow: 0 42px 90px rgba(20, 42, 57, .3), 0 0 0 10px rgba(255, 255, 255, .4);
            transform: perspective(1200px) rotateY(-2deg) rotateX(0);
        }
        .face-video-guide::before { background: radial-gradient(ellipse, rgba(236, 72, 153, .11), transparent 68%); }
        .face-video-guide .glow-text {
            background: linear-gradient(100deg, #ec4899, #7656ed 70%, #397dea);
            -webkit-background-clip: text;
            background-clip: text;
        }
        .face-video-guide .cinematic-guide-visual {
            background:
                linear-gradient(180deg, rgba(18, 15, 29, .06) 8%, rgba(18, 15, 29, .18) 42%, rgba(18, 15, 29, .9) 100%),
                url('https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=1500&q=90') center 34%/cover;
            box-shadow: 0 34px 70px rgba(96, 36, 78, .2), 0 0 0 10px rgba(255, 255, 255, .28);
        }
        .face-video-guide .cinematic-visual-copy .eyebrow { color: #ffd0e7; }
        .face-video-guide .cinematic-flow-number {
            background: linear-gradient(135deg, #ec4899, #7656ed);
        }
        .face-video-guide .cinematic-guide-cta {
            background: linear-gradient(110deg, #ec4899, #7656ed 72%, #397dea);
            box-shadow: 0 8px 22px rgba(190, 75, 164, .24);
        }
        .expressive-face-guide::before { background: radial-gradient(ellipse, rgba(124, 77, 240, .12), transparent 68%); }
        .expressive-face-guide .glow-text {
            background: linear-gradient(100deg, #7656ed, #ec4899 72%, #ff9678);
            -webkit-background-clip: text;
            background-clip: text;
        }
        .expressive-face-guide .cinematic-guide-visual {
            background:
                linear-gradient(180deg, rgba(17, 16, 36, .04) 8%, rgba(17, 16, 36, .18) 42%, rgba(17, 16, 36, .91) 100%),
                url('https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?auto=format&fit=crop&w=1500&q=90') center 30%/cover;
            box-shadow: 0 34px 70px rgba(78, 48, 129, .22), 0 0 0 10px rgba(255, 255, 255, .28);
        }
        .expressive-face-guide .cinematic-visual-copy .eyebrow { color: #ded0ff; }
        .expressive-face-guide .cinematic-flow-number {
            background: linear-gradient(135deg, #7656ed, #ec4899);
        }
        .expressive-face-guide .cinematic-guide-cta {
            background: linear-gradient(110deg, #7656ed, #ec4899 72%, #ff9678);
            box-shadow: 0 8px 22px rgba(124, 77, 240, .24);
        }
        .creative-workshop-guide::before { background: radial-gradient(ellipse, rgba(249, 115, 22, .12), transparent 68%); }
        .creative-workshop-guide .glow-text {
            background: linear-gradient(100deg, #f97316, #ec4899 58%, #7656ed);
            -webkit-background-clip: text;
            background-clip: text;
        }
        .creative-workshop-guide .cinematic-guide-visual {
            background:
                linear-gradient(180deg, rgba(25, 18, 18, .04) 8%, rgba(25, 18, 18, .16) 42%, rgba(25, 18, 18, .9) 100%),
                url('https://images.unsplash.com/photo-1549490349-8643362247b5?auto=format&fit=crop&w=1500&q=90') center 50%/cover;
            box-shadow: 0 34px 70px rgba(141, 83, 44, .2), 0 0 0 10px rgba(255, 255, 255, .28);
        }
        .creative-workshop-guide .cinematic-visual-copy .eyebrow { color: #ffdfbd; }
        .creative-workshop-guide .cinematic-flow-number {
            background: linear-gradient(135deg, #f97316, #ec4899);
        }
        .creative-workshop-guide .cinematic-guide-cta {
            background: linear-gradient(110deg, #f97316, #ec4899 72%, #7656ed);
            box-shadow: 0 8px 22px rgba(220, 105, 54, .24);
        }
        .live-emotion-voice-guide::before { background: radial-gradient(ellipse, rgba(32, 189, 181, .12), transparent 68%); }
        .live-emotion-voice-guide .glow-text {
            background: linear-gradient(100deg, #20bdb5, #397dea 58%, #7656ed);
            -webkit-background-clip: text;
            background-clip: text;
        }
        .live-emotion-voice-guide .cinematic-guide-visual {
            background:
                linear-gradient(180deg, rgba(9, 18, 33, .06) 8%, rgba(9, 18, 33, .18) 42%, rgba(9, 18, 33, .91) 100%),
                url('https://images.unsplash.com/photo-1590602847861-f357a9332bbc?auto=format&fit=crop&w=1500&q=90') center 48%/cover;
            box-shadow: 0 34px 70px rgba(40, 68, 130, .22), 0 0 0 10px rgba(255, 255, 255, .28);
        }
        .live-emotion-voice-guide .cinematic-visual-copy .eyebrow { color: #b5fff0; }
        .live-emotion-voice-guide .cinematic-flow-number {
            background: linear-gradient(135deg, #20bdb5, #397dea);
        }
        .live-emotion-voice-guide .cinematic-guide-cta {
            background: linear-gradient(110deg, #20bdb5, #397dea 72%, #7656ed);
            box-shadow: 0 8px 22px rgba(53, 147, 221, .24);
        }
        .blueprint-engine-guide::before { background: radial-gradient(ellipse, rgba(59, 108, 246, .12), transparent 68%); }
        .blueprint-engine-guide .glow-text {
            background: linear-gradient(100deg, #3b6cf6, #20bdb5 58%, #7656ed);
            -webkit-background-clip: text;
            background-clip: text;
        }
        .blueprint-engine-guide .cinematic-guide-visual {
            background:
                linear-gradient(180deg, rgba(8, 20, 42, .06) 8%, rgba(8, 20, 42, .18) 42%, rgba(8, 20, 42, .92) 100%),
                url('https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1500&q=90') center 50%/cover;
            box-shadow: 0 34px 70px rgba(40, 68, 130, .22), 0 0 0 10px rgba(255, 255, 255, .28);
        }
        .blueprint-engine-guide .cinematic-visual-copy .eyebrow { color: #c7ddff; }
        .blueprint-engine-guide .cinematic-flow-number {
            background: linear-gradient(135deg, #3b6cf6, #20bdb5);
        }
        .blueprint-engine-guide .cinematic-guide-cta {
            background: linear-gradient(110deg, #3b6cf6, #20bdb5 72%, #7656ed);
            box-shadow: 0 8px 22px rgba(53, 105, 221, .24);
        }
        .ai-upscaler-guide::before { background: radial-gradient(ellipse, rgba(245, 158, 11, .12), transparent 68%); }
        .ai-upscaler-guide .glow-text {
            background: linear-gradient(100deg, #f59e0b, #f97316 58%, #ec4899);
            -webkit-background-clip: text;
            background-clip: text;
        }
        .ai-upscaler-guide .cinematic-guide-visual {
            background:
                linear-gradient(180deg, rgba(30, 23, 14, .04) 8%, rgba(30, 23, 14, .18) 42%, rgba(30, 23, 14, .91) 100%),
                url('https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?auto=format&fit=crop&w=1500&q=90') center 50%/cover;
            box-shadow: 0 34px 70px rgba(141, 83, 44, .2), 0 0 0 10px rgba(255, 255, 255, .28);
        }
        .ai-upscaler-guide .cinematic-visual-copy .eyebrow { color: #ffe0a3; }
        .ai-upscaler-guide .cinematic-flow-number {
            background: linear-gradient(135deg, #f59e0b, #f97316);
        }
        .ai-upscaler-guide .cinematic-guide-cta {
            background: linear-gradient(110deg, #f59e0b, #f97316 72%, #ec4899);
            box-shadow: 0 8px 22px rgba(220, 105, 54, .24);
        }
        .video-editor-guide::before { background: radial-gradient(ellipse, rgba(139, 92, 246, .12), transparent 68%); }
        .video-editor-guide .glow-text {
            background: linear-gradient(100deg, #8b5cf6, #ec4899 58%, #f97316);
            -webkit-background-clip: text;
            background-clip: text;
        }
        .video-editor-guide .cinematic-guide-visual {
            background:
                linear-gradient(180deg, rgba(20, 13, 34, .04) 8%, rgba(20, 13, 34, .2) 42%, rgba(20, 13, 34, .92) 100%),
                url('https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?auto=format&fit=crop&w=1500&q=90') center 50%/cover;
            box-shadow: 0 34px 70px rgba(94, 52, 130, .22), 0 0 0 10px rgba(255, 255, 255, .28);
        }
        .video-editor-guide .cinematic-visual-copy .eyebrow { color: #e3d2ff; }
        .video-editor-guide .cinematic-flow-number {
            background: linear-gradient(135deg, #8b5cf6, #ec4899);
        }
        .video-editor-guide .cinematic-guide-cta {
            background: linear-gradient(110deg, #8b5cf6, #ec4899 72%, #f97316);
            box-shadow: 0 8px 22px rgba(144, 75, 190, .24);
        }
        .cinematic-guide-visual::after {
            position: absolute;
            z-index: -1;
            inset: 0;
            content: "";
            background: linear-gradient(115deg, rgba(16, 30, 43, .32), transparent 55%);
        }
        .cinematic-visual-top {
            position: absolute;
            top: 24px;
            left: 26px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 9px 13px;
            border: 1px solid rgba(255, 255, 255, .35);
            border-radius: 99px;
            background: rgba(9, 22, 34, .42);
            color: #fff;
            font: 700 11px/1 'Inter', sans-serif;
            letter-spacing: .08em;
            text-transform: uppercase;
            backdrop-filter: blur(12px);
        }
        .cinematic-visual-copy {
            position: absolute;
            right: clamp(24px, 4vw, 52px);
            bottom: clamp(28px, 4vw, 52px);
            left: clamp(24px, 4vw, 52px);
            color: #fff;
        }
        .cinematic-visual-copy .eyebrow {
            margin-bottom: 10px;
            color: #b5fff0;
            font: 700 12px/1.2 'Inter', sans-serif;
            letter-spacing: .14em;
            text-transform: uppercase;
        }
        .cinematic-visual-copy h3 {
            max-width: 560px;
            margin: 0 0 12px;
            color: #fff;
            font: 800 clamp(30px, 4vw, 54px)/1.02 'Roboto Condensed', sans-serif;
            letter-spacing: -.02em;
        }
        .cinematic-visual-copy p {
            max-width: 500px;
            margin: 0;
            color: rgba(255, 255, 255, .86);
            font: 500 clamp(14px, 1.2vw, 17px)/1.55 'Inter', sans-serif;
        }
        .cinematic-guide-copy .section-header {
            max-width: none;
            margin: 0 0 24px;
            text-align: left;
        }
        .cinematic-guide-copy .section-header h2 {
            margin: 0 0 12px;
            font: 800 clamp(30px, 3.4vw, 46px)/1.08 'Roboto Condensed', sans-serif !important;
        }
        .cinematic-guide-copy .section-header p { font-size: 16px; }
        .cinematic-flow {
            display: grid;
            gap: 12px;
        }
        .cinematic-flow-step {
            display: grid;
            grid-template-columns: 42px minmax(0, 1fr);
            align-items: start;
            gap: 14px;
            padding: 15px 17px;
            border: 1px solid rgba(31, 50, 53, .1);
            border-radius: 14px;
            background: rgba(255, 255, 255, .76);
            box-shadow: 0 8px 22px rgba(31, 50, 53, .055);
        }
        .cinematic-flow-number {
            display: grid;
            width: 38px;
            height: 38px;
            place-items: center;
            border-radius: 12px;
            background: linear-gradient(135deg, #20bdb5, #4188ef);
            color: #fff;
            font: 800 13px/1 'Inter', sans-serif;
        }
        .cinematic-flow-step h3 {
            margin: 0 0 4px;
            color: var(--landing-text);
            font: 700 15px/1.3 'Inter', sans-serif;
        }
        .cinematic-flow-step p {
            margin: 0;
            color: var(--landing-muted);
            font: 400 13px/1.5 'Inter', sans-serif;
        }
        .cinematic-guide-cta {
            display: inline-flex;
            align-items: center;
            gap: 9px;
            margin-top: 20px;
            padding: 13px 19px;
            border-radius: 99px;
            background: linear-gradient(110deg, #11c4c7, #397dea 68%, #7554ee);
            box-shadow: 0 8px 22px rgba(53, 147, 221, .22);
            color: #fff !important;
            font: 700 12px/1 'Inter', sans-serif;
            letter-spacing: .04em;
            text-decoration: none !important;
            text-transform: uppercase;
        }
        .cinematic-guide-cta:hover { transform: translateY(-2px); }
        @media (max-width: 900px) {
            .cinematic-guide-inner { grid-template-columns: 1fr; gap: 30px; }
            .cinematic-guide-visual { min-height: clamp(310px, 58vw, 470px); transform: none; }
        }
        @media (max-width: 560px) {
            .cinematic-guide { padding-top: 28px; padding-bottom: 36px; }
            .cinematic-guide-visual {
                min-height: 340px;
                border-radius: 22px 72px 22px 72px;
            }
            .cinematic-visual-top { top: 16px; left: 16px; font-size: 9px; }
            .cinematic-visual-copy { right: 22px; bottom: 26px; left: 22px; }
            .cinematic-visual-copy h3 { font-size: 34px; }
            .cinematic-guide-copy .section-header p { font-size: 14px; }
            .cinematic-flow-step { grid-template-columns: 36px minmax(0, 1fr); gap: 11px; padding: 13px; }
            .cinematic-flow-number { width: 34px; height: 34px; }
        }
        @media (prefers-reduced-motion: reduce) {
            .cinematic-guide-visual, .cinematic-guide-cta { transition: none; }
        }
        .pricing-section .pricing-subsection { margin-top: 32px; }
        .pricing-subsection-title {
            margin: 0 0 18px;
            color: var(--landing-text);
            text-align: center;
            font: 700 clamp(19px, 2vw, 25px)/1.2 'Inter', sans-serif;
        }
        .pricing-section .subscription-plans-grid { grid-template-columns: repeat(6, minmax(0, 1fr)); }
        .pricing-section .one-time-plans-grid { grid-template-columns: repeat(5, minmax(0, 1fr)); }
        .plan-badge {
            display: inline-block;
            margin-bottom: 12px;
            padding: 5px 10px;
            border-radius: 20px;
            background: rgba(32, 189, 181, .12);
            color: #118782;
            font: 700 10px/1.2 'Inter', sans-serif;
            letter-spacing: .04em;
        }
        .pricing-card .plan-description {
            min-height: 36px;
            color: var(--landing-muted);
            font: 13px/1.4 'Inter', sans-serif;
        }
        .pricing-section .pricing-card {
            display: flex;
            flex-direction: column;
            min-width: 0;
            padding: 20px 16px;
        }
        .pricing-section .pricing-card .price {
            font: 800 clamp(22px, 1.8vw, 28px)/1.1 'Inter', sans-serif;
            white-space: nowrap;
        }
        .pricing-section .pricing-card .price span {
            display: block;
            margin-top: 4px;
            font: 500 13px/1.2 'Inter', sans-serif;
        }
        .pricing-card .features { flex: 1; }
        .pricing-card .pricing-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            color: #fff !important;
        }
        .pricing-card.free .pricing-btn { color: var(--landing-text) !important; }
        .pricing-card.featured-plan {
            border-color: rgba(32, 189, 181, .65);
            box-shadow: 0 12px 32px rgba(32, 189, 181, .12);
        }
        @media (max-width: 1100px) {
            .pricing-section .subscription-plans-grid,
            .pricing-section .one-time-plans-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        }
        @media (max-width: 720px) {
            .pricing-section .subscription-plans-grid,
            .pricing-section .one-time-plans-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        @media (max-width: 480px) {
            .pricing-section .subscription-plans-grid,
            .pricing-section .one-time-plans-grid { grid-template-columns: 1fr; }
        }
        @media (prefers-reduced-motion: reduce) {
            html { scroll-behavior: auto; }
            *, *::before, *::after {
                animation-duration: .01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: .01ms !important;
            }
        }
        /* Keep the landing navigation and hero composition aligned across screens. */
        .landing-nav, .landing-nav.scrolled {
            height: 68px;
            padding: 0 clamp(20px, 6.6vw, 88px);
            background: rgba(255, 255, 255, .94);
            border-bottom: 1px solid rgba(20, 40, 80, .08);
            box-shadow: 0 4px 18px rgba(30, 60, 120, .07);
            backdrop-filter: blur(18px) saturate(160%);
        }
        .nav-logo { flex: 0 0 auto; gap: 10px; }
        .zx-logo-mark { width: 36px; }
        .landing-nav .nav-links { gap: clamp(12px, 1.6vw, 24px); }
        .landing-nav .nav-links a { white-space: nowrap; }
        .landing-nav .nav-links a.zx-login {
            min-height: 38px;
            padding: 0 18px;
            align-items: center;
        }
        .landing-nav .nav-links a.nav-cta-btn {
            min-height: 40px;
            padding: 0 20px;
            justify-content: center;
            border-radius: 999px;
            box-shadow: 0 6px 16px rgba(42, 150, 215, .2);
        }
        .zx-badge {
            height: calc(var(--p) * 25);
            font-size: clamp(11px, calc(var(--p) * 8.5), 14px);
        }
        .zx-btn {
            font-size: clamp(11px, calc(var(--p) * 8.6), 13px);
            letter-spacing: .035em;
            transition: transform .18s ease, box-shadow .18s ease;
        }
        .zx-btn:hover { transform: translateY(-2px); }
        .zx-btn-primary:hover { box-shadow: 0 calc(var(--p) * 10) calc(var(--p) * 24) rgba(70, 110, 240, .38); }
        .zx-demo {
            border-radius: calc(var(--p) * 16);
            box-shadow: 0 calc(var(--p) * 14) calc(var(--p) * 34) rgba(40, 75, 150, .24);
        }
        .zx-h1 {
            width: calc(var(--p) * 400) !important;
            font-size: clamp(32px, calc(var(--p) * 46), 58px) !important;
            line-height: 1.04 !important;
        }
        .zx-sub {
            width: calc(var(--p) * 390) !important;
            font-size: clamp(11px, calc(var(--p) * 13.3), 18px);
            line-height: 1.55;
        }
        .zx-btn-primary { width: calc(var(--p) * 210); min-height: calc(var(--p) * 40); }
        .zx-btn-ghost { width: calc(var(--p) * 190); min-height: calc(var(--p) * 40); }
        .zx-checks {
            font-size: clamp(9px, calc(var(--p) * 8.5), 11px);
            gap: calc(var(--p) * 16);
        }
        .zx-stat { height: calc(var(--p) * 42); gap: calc(var(--p) * 10); }
        .zx-stat-ico { width: calc(var(--p) * 38); height: calc(var(--p) * 38); }
        .zx-stat b { font-size: clamp(22px, calc(var(--p) * 21.5), 28px); }
        .zx-stat span { font-size: clamp(9px, calc(var(--p) * 8.8), 11px); }
        .zx-tagline { font-size: clamp(17px, calc(var(--p) * 15), 21px); }
        .zx-hiw-title {
            width: calc(var(--p) * 330);
            font-size: clamp(23px, calc(var(--p) * 30), 36px);
            line-height: 1.16;
        }
        .zx-hiw-text {
            width: calc(var(--p) * 330);
            font-size: clamp(12px, calc(var(--p) * 10), 16px);
        }
        .zx-pill { font-size: clamp(9px, calc(var(--p) * 7.4), 11px); }
        .zx-watch { font-size: clamp(12px, calc(var(--p) * 9.5), 14px); }
        .zx-step { min-height: calc(var(--p) * 132); padding: calc(var(--p) * 13) calc(var(--p) * 15); }
        .zx-num { font-size: clamp(10px, calc(var(--p) * 8), 12px); }
        .zx-step-t { font-size: clamp(10px, calc(var(--p) * 11.5), 16px); }
        .zx-step-d { font-size: clamp(9px, calc(var(--p) * 9), 14px); }
        .zx-mock-input { font-size: clamp(10px, calc(var(--p) * 7.4), 12px); }
        .zx-eng-title { font-size: clamp(11px, calc(var(--p) * 10), 16px); }
        .zx-eng-sub { font-size: clamp(10px, calc(var(--p) * 9), 14px); }
        .zx-eng-card { padding: calc(var(--p) * 10) calc(var(--p) * 11); }
        .zx-eng-card b { font-size: clamp(12px, calc(var(--p) * 9), 15px); }
        .zx-eng-card span { font-size: clamp(11px, calc(var(--p) * 7.8), 13px); }
        .zx-stage .zx-h1 {
            width: calc(var(--p) * 450) !important;
            font-size: clamp(42px, min(calc(var(--p) * 58), calc(var(--y-scale) * 52)), 78px) !important;
        }
        .zx-stage .zx-sub {
            width: calc(var(--p) * 450) !important;
            font-size: clamp(17px, calc(var(--p) * 17), 23px);
        }
        .zx-stage > .zx-badge,
        .zx-stage > .zx-h1,
        .zx-stage > .zx-sub,
        .zx-stage > .zx-cta,
        .zx-stage > .zx-checks,
        .zx-stage > .zx-demo,
        .zx-stage > .zx-stats {
            left: calc(var(--p) * var(--x) - clamp(18px, 2vw, 32px));
        }
        .zx-stage .zx-stats { top: max(calc(var(--y-scale) * 553), calc(100svh - 150px)); }
        .zx-stage .zx-badge { font-size: clamp(12px, calc(var(--p) * 9.2), 15px); }
        .zx-stage .zx-btn { font-size: clamp(12px, calc(var(--p) * 9.5), 15px); }
        .zx-stage .zx-btn-primary { width: calc(var(--p) * 225); }
        .zx-stage .zx-btn-ghost { width: calc(var(--p) * 205); }
        .zx-stage .zx-checks { font-size: clamp(10px, calc(var(--p) * 8.8), 13px); }
        .zx-stage .zx-stat b { font-size: clamp(24px, calc(var(--p) * 23.5), 31px); }
        .zx-stage .zx-stat span { font-size: clamp(10px, calc(var(--p) * 9.6), 13px); }
        .zx-stage .zx-tagline { font-size: clamp(19px, calc(var(--p) * 16.5), 23px); }
        .zx-followup {
            left: clamp(-32px, -2vw, -18px);
            width: calc(100% + 32px);
        }
        .zx-followup .zx-hiw-title { width: calc(var(--p) * 360); font-size: clamp(26px, calc(var(--p) * 31), 41px); }
        .zx-followup .zx-hiw-text { font-size: clamp(13px, calc(var(--p) * 11.5), 17px); }
        .zx-followup .zx-pill { font-size: clamp(10px, calc(var(--p) * 8), 13px); }
        .zx-followup .zx-watch { font-size: clamp(13px, calc(var(--p) * 10.5), 16px); }
        .zx-followup .zx-step-t { font-size: clamp(14px, calc(var(--p) * 13.5), 19px); }
        .zx-followup .zx-step-d { font-size: clamp(12px, calc(var(--p) * 10.8), 16px); }
        .zx-followup .zx-num { font-size: clamp(12px, calc(var(--p) * 9), 14px); }
        .zx-followup .zx-mock-input { font-size: clamp(12px, calc(var(--p) * 8.3), 14px); }
        .zx-followup .zx-eng-title { font-size: clamp(13px, calc(var(--p) * 11), 17px); }
        .zx-followup .zx-eng-sub { font-size: clamp(12px, calc(var(--p) * 10), 16px); }
        .zx-followup .zx-eng-card b { font-size: clamp(14px, calc(var(--p) * 10.8), 18px); }
        .zx-followup .zx-eng-card span { font-size: clamp(12px, calc(var(--p) * 9.2), 15px); }
        @media (max-width: 900px) {
            .landing-nav, .landing-nav.scrolled {
                height: 60px;
                padding: 0 18px;
            }
            .zx-followup { position: static; left: auto; width: 100%; height: auto; }
            .zx-stage .zx-sub { width: 100% !important; }
            .zx-stage .zx-stats { top: auto; }
            .zx-followup .zx-hiw-title { width: auto; font-size: clamp(26px, calc(var(--p) * 30), 38px); }
            .zx-logo-mark { width: 32px; }
            .landing-nav .nav-links a.nav-cta-btn {
                min-height: 38px;
                padding: 0 16px;
                font-size: 12px;
            }
            .zx-stage { gap: calc(var(--p) * 13); }
            .zx-stage .zx-h1 {
                width: auto !important;
                font-size: clamp(38px, calc(var(--p) * 46), 52px) !important;
                line-height: 1.04 !important;
            }
            .zx-sub {
                font-size: clamp(14px, calc(var(--p) * 11.2), 16px);
                line-height: 1.55;
            }
            .zx-cta { gap: 10px; }
            .zx-btn {
                width: auto;
                min-height: 44px;
                height: auto;
                padding: 0 16px;
                font-size: clamp(11px, calc(var(--p) * 8.6), 13px);
            }
            .zx-btn-primary, .zx-btn-ghost { width: auto; }
            .zx-hiw-title { width: auto; }
            .zx-hiw-text { width: 100% !important; }
        }
        @media (max-aspect-ratio: 3/4) {
            .landing-nav, .landing-nav.scrolled {
                height: 60px;
                padding: 0 12px;
            }
            .landing-nav .nav-links {
                gap: 8px;
            }
            .landing-nav .nav-links > a:not(.zx-login):not(.nav-cta-btn),
            .landing-nav .zx-nav-sep,
            .landing-nav .zx-lang {
                display: none !important;
            }
            .landing-nav .nav-links a.zx-login {
                min-height: 34px;
                padding: 0 11px;
                font-size: 11px;
            }
            .landing-nav .nav-links a.nav-cta-btn {
                min-height: 34px;
                padding: 0 12px;
                font-size: 11px;
            }
            .zx-stage {
                height: calc(var(--p) * 1110) !important;
            }
            .zx-stage .zx-stats {
                top: calc(var(--p) * 553) !important;
            }
            .zx-followup {
                top: calc(var(--p) * 650) !important;
                left: 0 !important;
                width: 100% !important;
                height: calc(var(--p) * 460) !important;
            }
        }
        </style>
        """, unsafe_allow_html=True)

    def _navbar_html(self):
        return (
            "<nav class='landing-nav' id='navbar'>"
            "<a href='#' class='nav-logo'><span class='zx-logo-mark'></span><span class='nav-brand-copy'><span class='zx-logo-text'>ZOVIX</span><small>AI CREATIVE STUDIO</small></span></a>"
            "<div class='nav-links'>"
            "<a href='#features'>Features</a><a href='#engines'>Engines<i class='zx-caret'></i></a><a href='#pricing'>Pricing</a>"
            "<a href='#engine-output-gallery'>Gallery</a><a href='#how-it-works'>Resources<i class='zx-caret'></i></a><a href='#about'>About</a>"
            "<span class='zx-nav-sep'></span><span class='zx-lang'><i class='zx-i'>language</i>EN<i class='zx-caret'></i></span>"
            "<a class='zx-login' href='?page=studio' target='_self'>Login</a>"
            "<a class='nav-cta-btn' href='?page=studio' target='_self'>Get Started</a>"
            "</div></nav>"
        )

    def _render_showcase(self):
        def photo(photo_id, width=700):
            return f"https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&w={width}&q=80"

        def pos(x, y, w, h=None):
            height = f";--hh:calc(var(--p)*{h})" if h else ""
            return f"--x:{x};--y:{y};--w:{w}{height}"

        # label, photo, x, y, w, h, rotation, 3D tilt, small
        tiles = [
            ("Cinematic", "1506905925346-21bda4d32df4", 0, 54, 358, 156, "-6deg", "0deg", False),
            ("Face Studio", "1524504388940-b1c1722653e1", 358, 60, 162, 106, "5deg", "-8deg", False),
            ("Creative Workshop", "1497366754035-f200968a6e72", 526, 80, 146, 94, "2.5deg", "-6deg", False),
            ("Blueprint", "1518709268805-4e9042af9f23", 680, 72, 175, 102, "1deg", "-4deg", False),
            ("Draw", "1460661419201-fd4cecdf8a8b", 858, 84, 160, 96, "6deg", "-6deg", False),
            ("", "1517502884422-41eaead166d4", 1026, 142, 160, 96, "9deg", "-10deg", False),
            ("", "1494790108377-be9c29b29330", 1075, 258, 56, 64, "4deg", "-8deg", True),
            ("", "1469474968028-56623f02e42e", 1136, 274, 52, 48, "6deg", "-8deg", True),
            ("", "1472214103451-9374bd1c798e", 1075, 326, 56, 56, "4deg", "-8deg", True),
            ("", "1480714378408-67cf0d13bc1b", 1136, 330, 52, 54, "6deg", "-8deg", True),
        ]
        tile_html = "".join(
            f"<figure class='zx-a zx-tile{' zx-sm' if small else ''}' style='{pos(x, y, w, h)};--r:{rot};--ry:{ry}'>"
            f"<img src='{photo(pid, 900 if w > 300 else 600)}' alt='{label or 'AI generated artwork'}'>"
            f"{f'<figcaption>{label}</figcaption>' if label else ''}</figure>"
            for label, pid, x, y, w, h, rot, ry, small in tiles
        )

        stats = [
            ("smart_display", "#2f6bff", "50K+", "Videos Created"),
            ("groups", "#2f6bff", "15K+", "Active Creators"),
            ("public", "#1d8fe8", "180+", "Countries Supported"),
            ("star", "#6a4cf2", "4.9/5", "User Rating"),
        ]
        stats_html = "".join(
            f"<div class='zx-stat'><span class='zx-stat-ico'><i class='zx-i' style='color:{color}'>{icon}</i></span><div><b>{number}</b><span>{label}</span></div></div>"
            for icon, color, number, label in stats
        )
        tagline = (
            "<div class='zx-tagline'>More than a tool,<br>it's your creative partner."
            "<svg viewBox='0 0 120 10' preserveAspectRatio='none' aria-hidden='true'><defs><linearGradient id='zxu' x1='0' x2='1'>"
            "<stop offset='0' stop-color='#17c6e0'/><stop offset='1' stop-color='#3b6df0'/></linearGradient></defs>"
            "<path d='M2 7 C30 1 80 1 118 6' fill='none' stroke='url(#zxu)' stroke-width='2.2' stroke-linecap='round'/></svg></div>"
        )

        steps = [
            (458, 182, "lightbulb", "01", "Your Idea", "Type a prompt or upload an image. Be as creative as you want.",
             "<div class='zx-mock zx-mock-input'>A cinematic scene with a futuristic city...</div>"),
            (673, 180, "settings", "02", "ZOVIX AI Engines", "Our specialized engines work together — generating characters, scenes, voice, motion and more.",
             "<div class='zx-mock zx-mock-icons'>"
             "<span style='background:#e5efff;color:#2f6bff'><i class='zx-i'>movie</i></span>"
             "<span style='background:#fff0e3;color:#f0782a'><i class='zx-i'>face</i></span>"
             "<span style='background:#efe9ff;color:#7c4df0'><i class='zx-i'>edit</i></span>"
             "<span style='background:#e1f6f3;color:#12a89a'><i class='zx-i'>layers</i></span>"
             "<span style='background:#ffe6ec;color:#ef4468'><i class='zx-i'>favorite</i></span></div>"),
            (886, 192, "auto_awesome", "03", "Your Masterpiece", "Get studio-quality images, videos and content — ready to use, edit or publish.",
             f"<div class='zx-mock zx-mock-thumb' style=\"background-image:url('{photo('1470071459604-3b5ec3a7fe05', 600)}')\"><span><i class='zx-i'>play_arrow</i></span></div>"),
        ]
        steps_html = "".join(
            f"<div class='zx-a zx-step' style='{pos(x + 42, 20, w, 168)}'><span class='zx-ficon'><i class='zx-i'>{icon}</i></span>"
            f"<span class='zx-num'>{num}</span><div class='zx-step-t'>{title}</div><div class='zx-step-d'>{desc}</div>{mock}</div>"
            for x, w, icon, num, title, desc, mock in steps
        )
        arrows_html = "".join(
            f"<div class='zx-a zx-arrow' style='{pos(x + 42, 58, 18, 18)}'><i class='zx-i'>arrow_forward</i></div>" for x in (648, 861)
        )

        engines = [
            ("movie", "#2f6bff", "#e5efff", "Cinematic", "Epic videos &amp; stories"),
            ("face", "#8b5cf6", "#efe9ff", "Face Studio", "Talking characters"),
            ("auto_awesome", "#ec4899", "#ffe6f2", "Creative Workshop", "Unique creative visuals"),
            ("view_in_ar", "#3b6cf6", "#e5edff", "Blueprint", "Design &amp; plan"),
            ("brush", "#f97316", "#fff0e2", "Draw", "Art &amp; illustrations"),
            ("tune", "#ef4444", "#ffe8e8", "Editor", "Edit &amp; assemble"),
            ("smart_toy", "#3b82f6", "#e4f0ff", "AI Agent", "Automate &amp; create"),
            ("campaign", "#f59e0b", "#fff3da", "Sales Video", "Business &amp; marketing"),
            ("favorite", "#ec4899", "#ffe6ef", "Live Emotions", "Real character emotions"),
        ]
        engines_html = "".join(
            f"<div class='zx-eng-card'><span class='zx-eico' style='background:{bg}'><i class='zx-i' style='color:{color}'>{icon}</i></span><b>{name}</b><span>{desc}</span></div>"
            for icon, color, bg, name, desc in engines
        )

        waves = (
            "<svg class='zx-waves' viewBox='0 0 1184 800' preserveAspectRatio='none' aria-hidden='true'><defs>"
            "<linearGradient id='zxw1' x1='0' y1='0' x2='1' y2='0'><stop offset='0' stop-color='#9fd8ff' stop-opacity='0'/><stop offset='.45' stop-color='#8fbaff' stop-opacity='.75'/><stop offset='1' stop-color='#b9a4ff' stop-opacity='.4'/></linearGradient>"
            "<linearGradient id='zxw2' x1='0' y1='0' x2='1' y2='0'><stop offset='0' stop-color='#dff1ff' stop-opacity='0'/><stop offset='.5' stop-color='#e2ecff' stop-opacity='.8'/><stop offset='1' stop-color='#eee6ff' stop-opacity='.6'/></linearGradient></defs>"
            "<path d='M0 205 C260 240 560 215 850 160 S1130 100 1184 118 L1184 300 C1000 270 760 215 520 232 S200 262 0 235 Z' fill='url(#zxw2)'/>"
            "<path d='M0 205 C260 240 560 215 850 160 S1130 100 1184 118' fill='none' stroke='url(#zxw1)' stroke-width='2'/>"
            "<path d='M0 235 C200 262 380 232 520 232 S760 215 1000 270 S1150 290 1184 285' fill='none' stroke='url(#zxw1)' stroke-width='1.5'/></svg>"
        )
        cube = (
            f"<svg class='zx-a zx-cube' style='{pos(1128, 540, 64, 64)}' viewBox='0 0 60 60' aria-hidden='true'><defs>"
            "<linearGradient id='zxc1' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#8cc4ff'/><stop offset='1' stop-color='#5a8dff'/></linearGradient>"
            "<linearGradient id='zxc2' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='#3d7bf2'/><stop offset='1' stop-color='#1f4fd0'/></linearGradient>"
            "<linearGradient id='zxc3' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='#2a5fe0'/><stop offset='1' stop-color='#6a4cf2'/></linearGradient></defs>"
            "<polygon points='30,4 56,18 30,32 4,18' fill='url(#zxc1)'/><polygon points='4,18 30,32 30,58 4,44' fill='url(#zxc2)'/>"
            "<polygon points='56,18 30,32 30,58 56,44' fill='url(#zxc3)'/><polyline points='4,18 30,32 56,18' fill='none' stroke='#d6ebff' stroke-width='1' opacity='.8'/></svg>"
        )

        hero = (
            f"<div class='zx-a zx-badge' style='{pos(160, 190, 306)}'><i class='zx-i'>auto_awesome</i><b>Next Gen AI Creative Platform</b>9 Powerful Engines. Endless Possibilities.</div>"
            f"<h1 class='zx-a zx-h1' style='{pos(160, 216, 340)}'>Zovix AI Studio.<br>Every <span class='zx-grad'>Creative</span><br>Possibility.</h1>"
            f"<div class='zx-a zx-sub' style='{pos(160, 378, 390)}'>Create cinematic videos, characters, images, voices, designs and more — powered by specialized AI engines in one workspace.</div>"
            f"<div class='zx-a zx-cta' style='{pos(160, 465, 440)}'>"
            "<a class='zx-btn zx-btn-primary' href='?page=studio' target='_self'><i class='zx-i'>rocket_launch</i>Start Creating Free<i class='zx-i'>arrow_forward</i></a>"
            "<a class='zx-btn zx-btn-ghost' href='#how-it-works'><i class='zx-i'>play_arrow</i>Watch ZOVIX in Action</a></div>"
            f"<div class='zx-a zx-checks' style='{pos(160, 518, 440)}'><span>No Credit Card Required</span><span>Instant Access</span><span>Free Plan Available</span></div>"
            f"<a class='zx-a zx-demo' href='#how-it-works' aria-label='Watch the ZOVIX cinematic demo' style=\"{pos(690, 213, 394, 220)};background-image:url('{photo('1493246507139-91e8fad9978e', 1200)}');\">"
            "<div class='zx-demo-title'><span class='zx-grad'>ZOVIX</span><small>CINEMATIC DEMO</small></div>"
            "<span class='zx-play'><i class='zx-i'>play_arrow</i></span>"
            "<span class='zx-demo-cap'>Real AI Generated Content</span>"
            "<span class='zx-demo-time'><i class='zx-i'>schedule</i>2:18</span></a>"
            f"<div class='zx-a zx-stats' style='{pos(160, 545, 905, 65)}'>{stats_html}{tagline}</div>"
        )
        how_it_works = (
            f"<div class='zx-a zx-pill' id='how-it-works' style='{pos(35, 0, 90)}'><i class='zx-i'>bolt</i>HOW IT WORKS</div>"
            f"<div class='zx-a zx-hiw-title' style='{pos(35, 20, 360)}'>From a Simple Idea to<br>a Stunning Masterpiece</div>"
            f"<div class='zx-a zx-hiw-text' style='{pos(35, 100, 360)}'><b>Just describe your vision.</b> ZOVIX's AI engines do the rest — turning your imagination into high-quality visuals, videos, and complete creative experiences.</div>"
            f"<a class='zx-a zx-watch' href='#engines' style='{pos(35, 205, 200)}'><i class='zx-i'>play_arrow</i><span>Watch How It Works</span></a>"
            f"{steps_html}{arrows_html}"
        )
        explore = (
            f"<div class='zx-a zx-eng-title' id='engines' style='{pos(35, 260, 400)}'>Explore ZOVIX Engines</div>"
            f"<div class='zx-a zx-eng-sub' style='{pos(35, 282, 500)}'>Multiple specialized engines. Endless creative possibilities.</div>"
            f"<div class='zx-a zx-eng' style='{pos(35, 310, 1110)}'>{engines_html}</div>"
        )
        st.markdown(
            f"{self._navbar_html()}<div class='zx-landing'><div class='zx-root'><div class='zx-stage'>{waves}"
            f"<div class='zx-strip'>{tile_html}</div>{hero}{cube}<div class='zx-followup'>{how_it_works}{explore}</div></div></div></div>",
            unsafe_allow_html=True,
        )

    def _render_cinematic_guide(self):
        st.markdown(
            """
            <section class="cinematic-guide" id="cinematic-engine">
                <div class="cinematic-guide-inner">
                    <div class="cinematic-guide-visual" role="img" aria-label="Cinematic sunset landscape">
                        <div class="cinematic-visual-top"><span>🎬</span> Cinematic Engine</div>
                        <div class="cinematic-visual-copy">
                            <div class="eyebrow">From your imagination to the screen</div>
                            <h3>Your story.<br>Your cinematic world.</h3>
                            <p>Describe an idea. ZOVIX turns it into a scene-by-scene video with visuals, voice and music.</p>
                        </div>
                    </div>
                    <div class="cinematic-guide-copy">
                        <div class="section-header">
                            <div class="tag">🎥 How cinematic generation works</div>
                            <h2>From a simple prompt<br><span class="glow-text">to a complete video</span></h2>
                            <p>Choose how to start, shape your video, and let the Cinematic Engine build the story with you.</p>
                        </div>
                        <div class="cinematic-flow">
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">01</span>
                                <div><h3>Start with an idea or script</h3><p>Use an AI topic, write your own script, or create a scene blueprint from your concept.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">02</span>
                                <div><h3>Choose your video settings</h3><p>Pick a format and duration, then set voice language and render quality for your project.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">03</span>
                                <div><h3>AI builds the scenes</h3><p>Your story is shaped into scenes with generated visuals, narration and optional background music.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">04</span>
                                <div><h3>Generate and review</h3><p>Start the render and preview your finished cinematic video when it is ready.</p></div>
                            </article>
                        </div>
                        <a class="cinematic-guide-cta" href="?page=studio" target="_self">Try the Cinematic Engine <span aria-hidden="true">→</span></a>
                    </div>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    def _render_face_video_guide(self):
        st.markdown(
            """
            <section class="cinematic-guide face-video-guide" id="face-video-studio">
                <div class="cinematic-guide-inner">
                    <div class="cinematic-guide-visual" role="img" aria-label="Portrait for an AI talking face video">
                        <div class="cinematic-visual-top"><span>👤</span> Face Video Studio</div>
                        <div class="cinematic-visual-copy">
                            <div class="eyebrow">A photo that speaks your script</div>
                            <h3>One photo.<br>A voice of your own.</h3>
                            <p>Turn a portrait and your dialogue into a talking-face video with natural voice and lip-sync.</p>
                        </div>
                    </div>
                    <div class="cinematic-guide-copy">
                        <div class="section-header">
                            <div class="tag">👤 How Face Video Studio works</div>
                            <h2>Bring a portrait<br><span class="glow-text">to life with AI</span></h2>
                            <p>Choose a face photo, write what you want it to say, and let the studio create a voiced, lip-synced clip.</p>
                        </div>
                        <div class="cinematic-flow">
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">01</span>
                                <div><h3>Upload a clear face photo</h3><p>Choose a well-lit portrait with the face clearly visible for the best talking-video result.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">02</span>
                                <div><h3>Write the dialogue</h3><p>Enter the words for your character to speak. Keep the script concise for a natural delivery.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">03</span>
                                <div><h3>Pick voice and video quality</h3><p>Choose a male or female voice, then select the available duration and Standard, HD or 4K quality.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">04</span>
                                <div><h3>Generate and preview</h3><p>The AI creates speech and synchronizes the portrait's lip movements. Preview the finished clip in your studio.</p></div>
                            </article>
                        </div>
                        <a class="cinematic-guide-cta" href="?page=studio" target="_self">Try Face Video Studio <span aria-hidden="true">→</span></a>
                    </div>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    def _render_expressive_face_guide(self):
        st.markdown(
            """
            <section class="cinematic-guide expressive-face-guide" id="expressive-face-video">
                <div class="cinematic-guide-inner">
                    <div class="cinematic-guide-visual" role="img" aria-label="Expressive portrait for an AI animated face video">
                        <div class="cinematic-visual-top"><span>🧬</span> Expressive Face Video</div>
                        <div class="cinematic-visual-copy">
                            <div class="eyebrow">More than lip-sync</div>
                            <h3>Every word.<br>Every expression.</h3>
                            <p>Animate a portrait with speech-driven facial movement, expressive eyes and natural head motion.</p>
                        </div>
                    </div>
                    <div class="cinematic-guide-copy">
                        <div class="section-header">
                            <div class="tag">🧬 How Expressive Face Video works</div>
                            <h2>Make a still portrait<br><span class="glow-text">feel alive</span></h2>
                            <p>Pair a face image with spoken dialogue. Expressive animation models bring the eyes, brows and jaw into the performance.</p>
                        </div>
                        <div class="cinematic-flow">
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">01</span>
                                <div><h3>Upload a portrait</h3><p>Choose a clear, front-facing image so the animation model can track facial features.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">02</span>
                                <div><h3>Write the dialogue</h3><p>Enter up to 120 words. The script guides generated speech and the character's lip movement.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">03</span>
                                <div><h3>Set voice, duration and quality</h3><p>Choose a voice language and model, clip length, video quality, and preferred animation backend.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">04</span>
                                <div><h3>Animate and preview</h3><p>LivePortrait or SadTalker drives facial expressions and speech motion; preview and download your finished clip.</p></div>
                            </article>
                        </div>
                        <a class="cinematic-guide-cta" href="?page=studio" target="_self">Try Expressive Face Video <span aria-hidden="true">→</span></a>
                    </div>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    def _render_creative_workshop_guide(self):
        st.markdown(
            """
            <section class="cinematic-guide creative-workshop-guide" id="creative-workshop">
                <div class="cinematic-guide-inner">
                    <div class="cinematic-guide-visual" role="img" aria-label="Colorful AI art created for a creative project">
                        <div class="cinematic-visual-top"><span>🎨</span> Creative Workshop</div>
                        <div class="cinematic-visual-copy">
                            <div class="eyebrow">Your idea, made visual</div>
                            <h3>Dream it.<br>Design it.</h3>
                            <p>Create original artwork for thumbnails, posters, banners and concepts with AI image generation.</p>
                        </div>
                    </div>
                    <div class="cinematic-guide-copy">
                        <div class="section-header">
                            <div class="tag">🎨 How Creative Workshop works</div>
                            <h2>Turn a text prompt<br><span class="glow-text">into striking artwork</span></h2>
                            <p>Describe the image you want, choose its shape and quality, then let AI create a ready-to-use visual.</p>
                        </div>
                        <div class="cinematic-flow">
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">01</span>
                                <div><h3>Describe your image</h3><p>Write a prompt with the subject, style, colors and details you want in your artwork.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">02</span>
                                <div><h3>Choose an aspect ratio</h3><p>Select a format such as 16:9 for banners, 9:16 for stories, or square for social posts.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">03</span>
                                <div><h3>Refine and set quality</h3><p>Optionally exclude unwanted details with a negative prompt, then choose Standard, HD or Pro quality.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">04</span>
                                <div><h3>Generate and use your image</h3><p>Generate the artwork, preview the result, and save it for thumbnails, posters, banners or concepts.</p></div>
                            </article>
                        </div>
                        <a class="cinematic-guide-cta" href="?page=studio" target="_self">Try Creative Workshop <span aria-hidden="true">→</span></a>
                    </div>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    def _render_live_emotion_voice_guide(self):
        st.markdown(
            """
            <section class="cinematic-guide live-emotion-voice-guide" id="live-emotion-voice">
                <div class="cinematic-guide-inner">
                    <div class="cinematic-guide-visual" role="img" aria-label="Studio microphone for expressive AI voice generation">
                        <div class="cinematic-visual-top"><span>🎤</span> Live Emotion Voice</div>
                        <div class="cinematic-visual-copy">
                            <div class="eyebrow">Give every line a feeling</div>
                            <h3>Feel the words.<br>Hear the emotion.</h3>
                            <p>Turn written text into expressive voice audio, with an emotion and voice that fit your message.</p>
                        </div>
                    </div>
                    <div class="cinematic-guide-copy">
                        <div class="section-header">
                            <div class="tag">🎤 How Live Emotion Voice works</div>
                            <h2>Your words,<br><span class="glow-text">with feeling</span></h2>
                            <p>Choose a voice and an emotion, then generate an audio performance for your script.</p>
                        </div>
                        <div class="cinematic-flow">
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">01</span>
                                <div><h3>Write what you want to say</h3><p>Enter the text for your voiceover, narration, character or creative project.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">02</span>
                                <div><h3>Choose an emotion</h3><p>Select a tone such as happy, sad, excited, angry, fearful, mysterious, serious or neutral.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">03</span>
                                <div><h3>Pick a voice</h3><p>Filter available voices by gender, then select the voice that best suits your words.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">04</span>
                                <div><h3>Generate and listen</h3><p>Create your emotional voice audio, preview the result, and use it in your project.</p></div>
                            </article>
                        </div>
                        <a class="cinematic-guide-cta" href="?page=studio" target="_self">Try Live Emotion Voice <span aria-hidden="true">→</span></a>
                    </div>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    def _render_blueprint_engine_guide(self):
        st.markdown(
            """
            <section class="cinematic-guide blueprint-engine-guide" id="blueprint-engine">
                <div class="cinematic-guide-inner">
                    <div class="cinematic-guide-visual" role="img" aria-label="Architectural blueprint and technical drawing">
                        <div class="cinematic-visual-top"><span>📐</span> Blueprint Engine</div>
                        <div class="cinematic-visual-copy">
                            <div class="eyebrow">Turn a design idea into a plan</div>
                            <h3>Plan the details.<br>See the structure.</h3>
                            <p>Describe a building or technical concept and create a clear visual blueprint to explore your idea.</p>
                        </div>
                    </div>
                    <div class="cinematic-guide-copy">
                        <div class="section-header">
                            <div class="tag">📐 How Blueprint Engine works</div>
                            <h2>From your design idea<br><span class="glow-text">to a detailed blueprint</span></h2>
                            <p>Create architectural concepts and technical drawings with controls for drawing type, visual style and view.</p>
                        </div>
                        <div class="cinematic-flow">
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">01</span>
                                <div><h3>Describe your design</h3><p>Explain the building, space or technical object and include the rooms, components and details you want shown.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">02</span>
                                <div><h3>Choose a drawing type</h3><p>Select a floor plan, elevation, site plan, section, or mechanical, electrical and structural drawing.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">03</span>
                                <div><h3>Set the style and view</h3><p>Pick a visual style, choose a 2D technical plan or 3D concept view, and select Standard or HD quality. Quick templates can help you get started.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">04</span>
                                <div><h3>Generate and review</h3><p>Generate your blueprint, inspect the result in the viewer, and refine your description for another version. Have technical plans checked by a qualified professional before construction.</p></div>
                            </article>
                        </div>
                        <a class="cinematic-guide-cta" href="?page=studio" target="_self">Try Blueprint Engine <span aria-hidden="true">→</span></a>
                    </div>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    def _render_ai_upscaler_guide(self):
        st.markdown(
            """
            <section class="cinematic-guide ai-upscaler-guide" id="ai-upscaler">
                <div class="cinematic-guide-inner">
                    <div class="cinematic-guide-visual" role="img" aria-label="Detailed landscape photo prepared for high-resolution image upscaling">
                        <div class="cinematic-visual-top"><span>⚡</span> AI Upscaler</div>
                        <div class="cinematic-visual-copy">
                            <div class="eyebrow">More pixels. A polished finish.</div>
                            <h3>Bring details<br>into focus.</h3>
                            <p>Enlarge an image for sharper-looking, high-resolution visuals ready to preview and download.</p>
                        </div>
                    </div>
                    <div class="cinematic-guide-copy">
                        <div class="section-header">
                            <div class="tag">⚡ How AI Upscaler works</div>
                            <h2>Give your image<br><span class="glow-text">room to shine</span></h2>
                            <p>Upload an image, choose how far to enlarge it and select a finish. Compare the result with your original before downloading.</p>
                        </div>
                        <div class="cinematic-flow">
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">01</span>
                                <div><h3>Upload an image</h3><p>Start with a PNG, JPG, JPEG or WEBP image and see the original in the workspace.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">02</span>
                                <div><h3>Choose the enlargement</h3><p>Select 2×, 4× or 8× scaling to increase the image dimensions to suit your project.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">03</span>
                                <div><h3>Pick a finish and quality</h3><p>Choose Standard, Sharp, Smooth, Enhance, Cinematic or Neon, then set Standard, HD or 4K output quality.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">04</span>
                                <div><h3>Compare and download</h3><p>Generate your enlarged image, compare it side by side with the original, check its resolution and download the result.</p></div>
                            </article>
                        </div>
                        <a class="cinematic-guide-cta" href="?page=studio" target="_self">Try AI Upscaler <span aria-hidden="true">→</span></a>
                    </div>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    def _render_video_editor_guide(self):
        st.markdown(
            """
            <section class="cinematic-guide video-editor-guide" id="video-editor">
                <div class="cinematic-guide-inner">
                    <div class="cinematic-guide-visual" role="img" aria-label="Video editing setup ready for a multi-clip project">
                        <div class="cinematic-visual-top"><span>🎞️</span> Video Editor</div>
                        <div class="cinematic-visual-copy">
                            <div class="eyebrow">Bring every clip together</div>
                            <h3>Shape the story.<br>Set the rhythm.</h3>
                            <p>Combine your video and image files with transitions, visual effects, music and optional narration.</p>
                        </div>
                    </div>
                    <div class="cinematic-guide-copy">
                        <div class="section-header">
                            <div class="tag">🎞️ How Video Editor works</div>
                            <h2>From separate clips<br><span class="glow-text">to one finished video</span></h2>
                            <p>Bring your media together, choose a look and soundtrack, then process a polished video ready to preview and download.</p>
                        </div>
                        <div class="cinematic-flow">
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">01</span>
                                <div><h3>Upload your media</h3><p>Add multiple video clips, images and audio files to build your project from the assets you already have.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">02</span>
                                <div><h3>Choose transitions and effects</h3><p>Select a transition between clips and add a visual style such as cinematic, vintage, neon, dreamy or grayscale.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">03</span>
                                <div><h3>Add music or AI voiceover</h3><p>Upload custom background music and set its volume. Optionally enter a narration script and choose an AI voice profile.</p></div>
                            </article>
                            <article class="cinematic-flow-step">
                                <span class="cinematic-flow-number">04</span>
                                <div><h3>Process and export</h3><p>Choose 720p, 1080p or 4K resolution and Standard, HD or 4K quality, then process, preview and download your edited video.</p></div>
                            </article>
                        </div>
                        <a class="cinematic-guide-cta" href="?page=studio" target="_self">Try Video Editor <span aria-hidden="true">→</span></a>
                    </div>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    def _render_engine_output_gallery(self):
        outputs = [
            (
                "Cinematic Engine",
                "Mountain film scene",
                "A cinematic landscape frame to set the mood for a travel story or short film.",
                "1506905925346-21bda4d32df4",
                "Cinematic mountain landscape",
            ),
            (
                "Face Video Studio",
                "Talking-head portrait",
                "A portrait concept for a presenter-style clip with spoken dialogue and lip-sync.",
                "1534528741775-53994a69daeb",
                "Portrait for a talking-head video",
            ),
            (
                "Expressive Face Video",
                "Expressive character",
                "A character portrait concept for a voice-led performance with expressive facial motion.",
                "1508214751196-bcfd4ca60f91",
                "Expressive character portrait",
            ),
            (
                "Creative Workshop",
                "Colorful poster artwork",
                "An art-forward visual direction for a poster, thumbnail, banner or social post.",
                "1549490349-8643362247b5",
                "Colorful abstract poster artwork",
            ),
            (
                "Live Emotion Voice",
                "Voiceover mood",
                "A studio-inspired voice concept for narration that carries a chosen emotional tone.",
                "1590602847861-f357a9332bbc",
                "Audio recording setup for voiceover",
            ),
            (
                "Blueprint Engine",
                "Architectural concept",
                "A visual reference for exploring building layouts and technical design concepts.",
                "1518709268805-4e9042af9f23",
                "Architectural design concept",
            ),
            (
                "AI Upscaler",
                "High-detail landscape",
                "A detailed photo concept suited to enlarging and preparing visuals for larger displays.",
                "1470252649378-9c29740c9fa8",
                "High-detail landscape image",
            ),
            (
                "Video Editor",
                "Edited film sequence",
                "A production still representing how clips, effects and music come together in a finished edit.",
                "1574717024653-61fd2cf4d44d",
                "Video editing production setup",
            ),
            (
                "Cinematic Engine",
                "City story frame",
                "An urban establishing-shot idea for a documentary, promo or cinematic sequence.",
                "1480714378408-67cf0d13bc1b",
                "City skyline cinematic frame",
            ),
            (
                "Creative Workshop",
                "Creative campaign visual",
                "A polished campaign image direction for a brand banner or promotional creative.",
                "1497366754035-f200968a6e72",
                "Creative workspace campaign visual",
            ),
        ]
        cards = "".join(
            "<article class='engine-gallery-card'>"
            f"<img src='https://images.unsplash.com/photo-{photo_id}?auto=format&amp;fit=crop&amp;w=720&amp;q=82' "
            f"alt='{escape(alt)}' loading='lazy'>"
            "<div class='engine-gallery-card-copy'>"
            f"<span class='engine-gallery-engine'>{escape(engine)}</span>"
            f"<h3>{escape(title)}</h3><p>{escape(description)}</p>"
            "</div></article>"
            for engine, title, description, photo_id, alt in outputs
        )
        st.markdown(
            "<section class='engine-gallery-section' id='engine-output-gallery'>"
            "<div class='section-header'><div class='tag'>🖼️ Engine output gallery</div>"
            "<h2>Ideas made visible.<br><span class='glow-text'>Your next creation starts here.</span></h2>"
            "<p>Explore visual examples inspired by ZOVIX engines, from cinematic scenes and portraits to blueprints and finished edits.</p></div>"
            f"<div class='engine-gallery-grid'>{cards}</div>"
            "<p class='engine-gallery-note'>Illustrative inspiration images only. Your generated results will depend on your prompt and selected settings.</p>"
            "</section>",
            unsafe_allow_html=True,
        )

    def _render_features(self):
        features = [
            {"icon": "🎬", "title": "Cinematic Engine", "desc": "Generate full cinematic videos from text prompts. Script → Visuals → Voice → Final video in one click.", "tag": "AI Generated"},
            {"icon": "👤", "title": "Face Video Studio", "desc": "Create talking face videos with perfect lip-sync. 20+ voices, multiple languages, emotion control.", "tag": "Lip-Sync AI"},
            {"icon": "🧬", "title": "Expressive Face Video", "desc": "Natural eye blinks, eyebrow movement, jaw motion. Powered by LivePortrait & SadTalker.", "tag": "Premium"},
            {"icon": "🎨", "title": "Creative Workshop", "desc": "Generate stunning images for thumbnails, posters, and banners. 8K resolution with AI.", "tag": "Image Gen"},
            {"icon": "🤖", "title": "AI Agent", "desc": "Auto-pilot your business. Generate content, manage orders, collect payments - all AI-powered.", "tag": "Automation"},
            {"icon": "🎤", "title": "Live Emotion Voice", "desc": "Hyper-realistic voice with human emotional dynamics. Happy, sad, excited, angry - any emotion.", "tag": "Voice AI"},
            {"icon": "📐", "title": "Blueprint Engine", "desc": "Professional architectural blueprints and technical drawings. Perfect for designers.", "tag": "Design"},
            {"icon": "⚡", "title": "AI Upscaler", "desc": "Upscale images up to 8K with detail restoration. Perfect for print and professional use.", "tag": "Enhance"},
            {"icon": "🎬", "title": "Video Editor", "desc": "Multi-track video editing with transitions, effects, BGM, and voiceover. Unlimited media files.", "tag": "Pro Editor"}
        ]
        feature_cards = "".join(
            f"<div class='feature-card'><span class='icon'>{feature['icon']}</span><h3>{feature['title']}</h3><p>{feature['desc']}</p><span class='feature-tag'>{feature['tag']}</span></div>"
            for feature in features
        )
        st.markdown(
            "<section class='features-section' id='features'><div class='section-header'><div class='tag'>✨ Features</div><h2>Everything You Need to<br><span class='glow-text'>Create Like a Pro</span></h2><p>From script to screen - all AI-powered tools in one platform</p></div>"
            f"<div class='features-grid'>{feature_cards}</div></section>",
            unsafe_allow_html=True,
        )

    def _render_about(self):
        st.markdown(
            "<section class='about-section' id='about'><div class='about-hero'>"
            "<div class='section-header'><div class='tag'>✨ About ZOVIX</div>"
            "<h2>One creative studio.<br><span class='glow-text'>Many ways to bring ideas to life.</span></h2></div>"
            "<p class='about-intro'>ZOVIX is an AI-powered creative platform that brings video, image, voice, design and editing tools together in one workspace. Start with an idea or your own media, choose an engine, and shape the result for your project.</p>"
            "</div>"
            "<div class='about-pillars'>"
            "<article class='about-pillar'><span class='about-pillar-icon' aria-hidden='true'>🎬</span>"
            "<h3>Create stories and characters</h3><p>Build cinematic videos from concepts, turn portraits into talking or expressive face videos, and assemble multiple clips with the Video Editor.</p></article>"
            "<article class='about-pillar'><span class='about-pillar-icon' aria-hidden='true'>🎨</span>"
            "<h3>Make visuals and sound</h3><p>Generate creative artwork, upscale images, and create expressive voice audio with controls for style, quality and emotion.</p></article>"
            "<article class='about-pillar'><span class='about-pillar-icon' aria-hidden='true'>📐</span>"
            "<h3>Explore design ideas</h3><p>Use the Blueprint Engine to create architectural and technical drawing concepts, with options for drawing type, style and 2D or 3D view.</p></article>"
            "</div><div class='about-workflow'><h3>Made for a simple creative workflow</h3>"
            "<p>Choose the engine that fits your goal, describe your vision or upload media, set the options you need, then generate, review and refine your output. You stay in control of the prompt and creative direction.</p>"
            "<a href='?page=studio' target='_self'>Explore the ZOVIX Studio →</a></div></section>",
            unsafe_allow_html=True,
        )

    def _render_blog(self):
        posts = [
            (
                "Creative workflow",
                "From a simple idea to a stronger prompt",
                "Name your subject, setting, mood and visual style. A few specific details can help guide an image or video generation toward the result you have in mind.",
                "photo-1455390582262-044cdead277a",
                "Creator writing down an idea",
            ),
            (
                "Engine guide",
                "Choose the right engine for your project",
                "Start with the output you need: use Cinematic for story-led video, Creative Workshop for artwork, Live Emotion Voice for expressive audio, or Blueprint for design concepts.",
                "photo-1497366754035-f200968a6e72",
                "Creative studio workspace",
            ),
            (
                "Finishing touches",
                "Make your final video feel complete",
                "Bring clips together in Video Editor, choose transitions and effects, then add background music or optional narration before reviewing the export.",
                "photo-1574717024653-61fd2cf4d44d",
                "Video creator editing a project",
            ),
        ]
        cards = "".join(
            "<article class='blog-post'>"
            f"<img src='https://images.unsplash.com/{photo_id}?auto=format&amp;fit=crop&amp;w=900&amp;q=84' "
            f"alt='{escape(alt)}' loading='lazy'>"
            f"<div class='blog-post-copy'><span class='blog-post-topic'>{escape(topic)}</span>"
            f"<h3>{escape(title)}</h3><p>{escape(description)}</p></div></article>"
            for topic, title, description, photo_id, alt in posts
        )
        st.markdown(
            "<section class='blog-section' id='blog'>"
            "<div class='blog-hero'><div class='blog-hero-copy'>"
            "<div class='eyebrow'>ZOVIX Creator Journal</div>"
            "<h2>Ideas, workflows<br>and creative tips.</h2>"
            "<p>Explore practical notes on prompting, choosing an AI engine and polishing the images, voices and videos you create.</p>"
            "</div></div>"
            f"<div class='blog-post-grid'>{cards}</div>"
            "<a class='blog-studio-link' href='?page=studio' target='_self'>Put an idea into practice →</a>"
            "</section>",
            unsafe_allow_html=True,
        )

    def _render_changelog(self):
        updates = [
            (
                "AI creation suite",
                "More ways to bring an idea to life",
                "Explore dedicated tools for cinematic video, expressive faces and voices, image creation, blueprints, upscaling and video editing.",
                "photo-1516321318423-f06f85e504b3",
                "Creative team reviewing digital work",
            ),
            (
                "Engine walkthroughs",
                "A clearer path from prompt to result",
                "Step-by-step guides explain what each engine does, what to prepare and how to refine an output for your project.",
                "photo-1516321497487-e288fb19713f",
                "Creator planning a digital project",
            ),
            (
                "Output inspiration",
                "See what each tool can help create",
                "Browse visual examples across video, portraits, artwork, voice and design, then choose an engine to start your own work.",
                "photo-1497366754035-f200968a6e72",
                "Bright creative studio workspace",
            ),
        ]
        cards = "".join(
            "<article class='changelog-card'>"
            f"<img src='https://images.unsplash.com/{photo_id}?auto=format&amp;fit=crop&amp;w=900&amp;q=84' "
            f"alt='{escape(alt)}' loading='lazy'>"
            f"<div class='changelog-card-copy'><span class='changelog-card-label'>{escape(label)}</span>"
            f"<h3>{escape(title)}</h3><p>{escape(description)}</p></div></article>"
            for label, title, description, photo_id, alt in updates
        )
        st.markdown(
            "<section class='changelog-section' id='changelog'>"
            "<div class='changelog-hero'><div class='changelog-hero-copy'>"
            "<div class='eyebrow'>The ZOVIX Changelog</div>"
            "<h2>New ways to turn<br>ideas into creations.</h2>"
            "<p>See what ZOVIX brings together for creators: more AI-powered engines, practical guides for each workflow and visual examples to spark your next project.</p>"
            "</div></div>"
            f"<div class='changelog-grid'>{cards}</div>"
            "<a class='changelog-studio-link' href='?page=studio' target='_self'>Explore the creative studio →</a>"
            "</section>",
            unsafe_allow_html=True,
        )

    def _render_roadmap(self):
        priorities = [
            (
                "NOW · EXPERIENCE",
                "Make every engine easier to use",
                "Keep improving the path from choosing an engine to getting a polished result, with clearer guidance, useful defaults and simpler workflows.",
                "photo-1454165804606-c3d57bc86b40",
                "Team organizing plans around a workspace",
            ),
            (
                "NEXT · CREATION",
                "Bring more creative controls together",
                "Explore smoother ways to refine generated video, image and voice outputs, and make it easier to continue a project across creation tools.",
                "photo-1516321318423-f06f85e504b3",
                "Creative team collaborating on digital work",
            ),
            (
                "EXPLORING · PLATFORM",
                "Build a more connected creator studio",
                "Look at ways to improve project organization, previews and handoffs, so creators can move from first idea to finished work with less friction.",
                "photo-1497366754035-f200968a6e72",
                "Bright modern creative studio",
            ),
        ]
        cards = "".join(
            "<article class='roadmap-card'>"
            f"<img src='https://images.unsplash.com/{photo_id}?auto=format&amp;fit=crop&amp;w=900&amp;q=84' "
            f"alt='{escape(alt)}' loading='lazy'>"
            f"<div class='roadmap-card-copy'><span class='roadmap-card-label'>{escape(stage)}</span>"
            f"<h3>{escape(title)}</h3><p>{escape(description)}</p></div></article>"
            for stage, title, description, photo_id, alt in priorities
        )
        st.markdown(
            "<section class='roadmap-section' id='roadmap'>"
            "<div class='roadmap-hero'><div class='roadmap-hero-copy'>"
            "<div class='eyebrow'>The ZOVIX Roadmap</div>"
            "<h2>See what we're<br>working toward.</h2>"
            "<p>A quick look at the product priorities shaping ZOVIX — from making each engine simpler to use, to connecting more of the creative journey in one studio.</p>"
            "</div></div>"
            f"<div class='roadmap-grid'>{cards}</div>"
            "<p class='roadmap-note'>These are product priorities, not promised delivery dates. Scope and timing may change as we learn from creators and improve the platform.</p>"
            "<a class='roadmap-studio-link' href='?page=studio' target='_self'>Explore the creative studio →</a>"
            "</section>",
            unsafe_allow_html=True,
        )

    def _render_careers(self):
        focus_areas = [
            (
                "01 · Engineering",
                "Build creative AI tools",
                "Work across AI workflows, media processing, video pipelines and reliable product experiences that help turn ideas into finished outputs.",
            ),
            (
                "02 · Product and design",
                "Make creation feel natural",
                "Shape clear studio workflows, accessible interfaces and visual systems for people creating videos, images, voice and design concepts.",
            ),
            (
                "03 · Creative technology",
                "Connect stories and media",
                "Explore how storytelling, editing, sound and generative tools can work together in a practical creator-focused platform.",
            ),
        ]
        cards = "".join(
            "<article class='careers-focus-card'>"
            f"<span>{escape(number)}</span><h3>{escape(title)}</h3><p>{escape(description)}</p>"
            "</article>"
            for number, title, description in focus_areas
        )
        st.markdown(
            "<section class='careers-section' id='careers'>"
            "<div class='careers-hero'><div class='careers-hero-copy'>"
            "<div class='eyebrow'>Careers at ZOVIX</div>"
            "<h2>Build tools that<br>help ideas take shape.</h2>"
            "<p>ZOVIX brings AI, design and media creation into one studio. We value thoughtful problem-solving, useful technology and experiences that keep creators in control.</p>"
            "</div></div>"
            f"<div class='careers-focus-grid'>{cards}</div>"
            "<p class='careers-note'>These are areas of work that shape the product, not a list of currently open positions. No specific vacancies are published here.</p>"
            "<a class='careers-studio-link' href='?page=studio' target='_self'>Explore what we are building →</a>"
            "</section>",
            unsafe_allow_html=True,
        )

    def _render_testimonials(self):
        testimonials = [
            {"stars": "★★★★★", "text": "ZOVIX completely transformed my content creation. I went from spending 5 hours per video to 15 minutes. The quality is mind-blowing!", "name": "Priya Sharma", "role": "Content Creator, 2M+ Subs"},
            {"stars": "★★★★★", "text": "The face video feature is incredible. I created a professional talking-head video without any equipment. Game changer for my business.", "name": "Rahul Verma", "role": "Startup Founder"},
            {"stars": "★★★★★", "text": "Finally an Indian AI tool that understands our language and culture. Hinglish support with Bhojpuri voices - absolutely phenomenal!", "name": "Anjali Patel", "role": "Digital Marketer"}
        ]
        testimonial_cards = []
        for test in testimonials:
            initials = ''.join([part[0].upper() for part in test['name'].split()])
            testimonial_cards.append(
                f"<div class='testimonial-card'><div class='stars'>{test['stars']}</div><div class='text'>\"{test['text']}\"</div><div class='author'><div class='avatar'>{initials}</div><div><div class='name'>{test['name']}</div><div class='role'>{test['role']}</div></div></div></div>"
            )
        st.markdown(
            "<section class='testimonials-section' id='testimonials'><div class='section-header'><div class='tag'>💬 Testimonials</div><h2>What Our <span class='glow-text'>Users Say</span></h2><p>Join 15,000+ creators who love ZOVIX</p></div>"
            f"<div class='testimonials-grid'>{''.join(testimonial_cards)}</div></section>",
            unsafe_allow_html=True,
        )

    def _render_pricing(self):
        def plan_card(plan, one_time=False):
            name = escape(plan["name"])
            description = escape(plan.get("description", ""))
            badge = escape(plan.get("badge", ""))
            features = "".join(
                f"<li><span class='check'>✅</span> {escape(str(feature))}</li>"
                for feature in plan.get("features", [])
            )
            if one_time:
                title = f"{int(plan['tokens']):,} Tokens"
                period = "one-time"
            else:
                title = name
                period = "/month"
            badge_html = f"<span class='plan-badge'>{badge}</span>" if badge else ""
            free_class = " free" if int(plan["price"]) == 0 else ""
            featured_class = (
                " featured-plan" if badge in {"POPULAR", "⭐ BEST VALUE"} else ""
            )
            button_label = "Get started" if int(plan["price"]) == 0 else "View plan"
            return (
                f"<article class='pricing-card{free_class}{featured_class}'>"
                f"{badge_html}<div class='plan-name'>{escape(title)}</div>"
                f"<p class='plan-description'>{description}</p>"
                f"<div class='price'>₹{int(plan['price']):,}<span>{period}</span></div>"
                f"<ul class='features'>{features}</ul>"
                f"<a class='pricing-btn' href='?page=studio' target='_self'>{button_label}</a>"
                "</article>"
            )

        subscription_cards = "".join(
            plan_card(plan) for plan in GLOBAL_PLANS["subscriptions"].values()
        )
        topup_cards = "".join(
            plan_card(plan, one_time=True) for plan in GLOBAL_PLANS["one_time"].values()
        )
        payment_methods = [
            "Credit/Debit Cards",
            "UPI",
            "Net Banking",
            "Bitcoin",
            "Ethereum",
            "USDT",
            "USDC",
            "Solana",
            "BNB",
            "DOGE",
            "Binance Pay",
            "Crypto",
            "Cards",
        ]
        methods_html = "".join(
            f"<span class='payment-method'>{method}</span>"
            for method in payment_methods
        )
        st.markdown(
            "<section class='pricing-section' id='pricing'><div class='section-header'><div class='tag'>💰 Pricing</div><h2>Choose Your <span class='glow-text'>Plan</span></h2><p>Start free, upgrade anytime. No hidden charges.</p></div>"
            "<div class='pricing-subsection'><h3 class='pricing-subsection-title'>Monthly subscriptions</h3>"
            f"<div class='pricing-grid subscription-plans-grid'>{subscription_cards}</div></div>"
            "<div class='pricing-subsection'><h3 class='pricing-subsection-title'>One-time token top-ups</h3>"
            f"<div class='pricing-grid one-time-plans-grid'>{topup_cards}</div></div>"
            "<div class='payment-methods'><h3>Flexible payment options</h3>"
            "<p>Choose from cards, UPI, net banking, or your preferred cryptocurrency.</p>"
            f"<div class='payment-method-list'>{methods_html}</div></div></section>",
            unsafe_allow_html=True,
        )

    def _render_faq(self):
        faqs = [
            {"q": "Do I need technical skills to use ZOVIX?", "a": "Not at all! ZOVIX is designed for everyone. Just type what you want to create, and our AI handles everything."},
            {"q": "What languages are supported?", "a": "We support Hindi, Hinglish, Bhojpuri, English, French, Japanese, and more. Voice synthesis works in multiple languages."},
            {"q": "How are payments processed?", "a": "We accept Razorpay (UPI, Cards, Net Banking) and Cryptocurrency (BTC, ETH, USDT, SOL, BNB)."},
            {"q": "Can I cancel my subscription anytime?", "a": "Yes! You can cancel anytime from your profile. No contracts, no hidden fees."}
        ]
        faq_cards = "".join(
            f"<details class='faq-item'><summary><span class='faq-question'>{faq['q']}</span><span class='faq-toggle' aria-hidden='true'></span></summary><div class='faq-answer'>{faq['a']}</div></details>"
            for faq in faqs
        )
        st.markdown(
            "<section class='faq-section'><div class='section-header'><div class='tag'>❓ FAQ</div><h2>Frequently Asked <span class='glow-text'>Questions</span></h2></div>"
            f"<div class='faq-list'>{faq_cards}</div></section>",
            unsafe_allow_html=True,
        )

    def _render_cta(self):
        st.markdown(
            "<section class='cta-section ready-create-section' id='ready-to-create'><div class='cta-container'>"
            "<div class='tag'>🚀 Your next idea starts here</div>"
            "<h2>Ready to <span class='glow-text'>Create?</span></h2>"
            "<p>Turn your idea into a video, image, voice, blueprint or polished edit. Pick an engine, describe what you want, and let ZOVIX help bring it to life.</p>"
            "<div class='ready-create-steps'>"
            "<article class='ready-create-step'><span>01 · CHOOSE</span><h3>Pick your engine</h3><p>Start with the tool that matches your idea, from cinematic video to image creation and editing.</p></article>"
            "<article class='ready-create-step'><span>02 · DESCRIBE</span><h3>Share your vision</h3><p>Write a prompt or add your media, then choose the style and settings that fit your project.</p></article>"
            "<article class='ready-create-step'><span>03 · CREATE</span><h3>Generate and refine</h3><p>Review your result, adjust your approach and download when it is ready to use.</p></article>"
            "</div><div class='cta-buttons'><a class='hero-primary-btn' href='?page=studio' target='_self'>Start creating free →</a>"
            "<a class='hero-secondary-btn' href='#engine-output-gallery'>Explore output ideas →</a></div></div></section>",
            unsafe_allow_html=True,
        )

    def _render_footer(self):
        st.markdown("""
        <footer class="landing-footer" id="support">
            <div class="footer-content">
                <div class="footer-brand">
                    <div class="logo-text">ZOV<span>IX</span></div>
                    <p>The next-generation AI video creation platform. Create cinematic videos from text in minutes.</p>
                </div>
                <div class="footer-col" id="product">
                    <h5>Product</h5>
                    <a href="#features">Features</a>
                    <a href="#pricing">Pricing</a>
                    <a href="#changelog">Changelog</a>
                    <a href="#roadmap">Roadmap</a>
                </div>
                <div class="footer-col" id="company">
                    <h5>Company</h5>
                    <a href="#about">About</a>
                    <a href="#careers">Careers</a>
                    <a href="#blog">Blog</a>
                    <a href="#">Contact</a>
                </div>
                <div class="footer-col">
                    <h5>Support</h5>
                    <a href="#">Help Center</a>
                    <a href="#">Documentation</a>
                    <a href="#">Privacy Policy</a>
                    <a href="#">Terms</a>
                </div>
            </div>
            <div class="footer-bottom">
                <span>© 2026 ZOVIX. All rights reserved.</span>
                <span>Made with ❤️ in India 🇮🇳</span>
            </div>
        </footer>
        """, unsafe_allow_html=True)

    def _inject_animations(self):
        st.markdown("""
        <script>
        window.addEventListener('scroll', function() {
            var nav = document.getElementById('navbar');
            if (nav) {
                if (window.scrollY > 50) nav.classList.add('scrolled');
                else nav.classList.remove('scrolled');
            }
        });
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                var target = document.querySelector(this.getAttribute('href'));
                if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        });
        </script>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    WorldClassLandingPage().render()