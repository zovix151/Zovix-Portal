import streamlit as st


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
        if st.button("🔑 Login", key="landing_auth_button"):
            st.session_state["landing_auth_requested"] = True
        self._inject_css()
        self._render_navbar()
        self._render_hero()
        self._render_features()
        self._render_how_it_works()
        self._render_stats()
        self._render_testimonials()
        self._render_pricing()
        self._render_faq()
        self._render_cta()
        self._render_footer()
        self._inject_animations()

    def _inject_css(self):
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@100;200;300;400;500;600;700;800;900&family=Orbitron:wght@400;500;600;700;800;900&family=Playfair+Display:wght@700;900&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; }
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
        .hero-section { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 120px 40px 60px; position: relative; z-index: 1; }
        .hero-content { max-width: 1200px; width: 100%; display: grid; grid-template-columns: 1fr 1fr; gap: 60px; align-items: center; }
        .hero-left { animation: fadeInUp 1s ease; }
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(40px); } to { opacity: 1; transform: translateY(0); } }
        .hero-badge { display: inline-block; padding: 6px 18px; background: rgba(69, 243, 255, 0.1); border: 1px solid rgba(69, 243, 255, 0.2); border-radius: 20px; font-size: 12px; color: #45f3ff; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 24px; }
        .hero-title { font-family: 'Orbitron', sans-serif; font-size: 64px; font-weight: 900; line-height: 1.1; margin-bottom: 24px; }
        .hero-title .highlight { background: linear-gradient(135deg, #45f3ff 0%, #EC4899 50%, #8b5cf6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
        .hero-subtitle { font-size: 20px; color: #94a3b8; line-height: 1.6; margin-bottom: 32px; max-width: 500px; }
        .hero-actions { display: flex; gap: 16px; flex-wrap: wrap; }
        .hero-primary-btn { padding: 16px 40px; background: linear-gradient(135deg, #45f3ff, #EC4899); border: none; border-radius: 12px; color: white; font-family: 'Orbitron', sans-serif; font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }
        .hero-secondary-btn { padding: 16px 32px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; color: #ffffff; font-family: 'Orbitron', sans-serif; font-weight: 600; font-size: 14px; backdrop-filter: blur(10px); }
        .hero-stats { display: flex; gap: 40px; margin-top: 40px; }
        .hero-stat .number { font-family: 'Orbitron', sans-serif; font-size: 32px; font-weight: 700; color: #45f3ff; }
        .hero-stat .label { font-size: 13px; color: #94a3b8; margin-top: 4px; }
        .hero-video-container { position: relative; border-radius: 20px; overflow: hidden; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 30px 80px rgba(0,0,0,0.8); }
        .hero-video-container video { width: 100%; display: block; }
        .hero-video-overlay { position: absolute; bottom: 0; left: 0; right: 0; padding: 30px; background: linear-gradient(transparent, rgba(0,0,0,0.8)); }
        .features-section, .how-it-works, .stats-section, .testimonials-section, .pricing-section, .cta-section, .landing-footer { position: relative; z-index: 1; }
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
        .landing-footer { padding: 40px; border-top: 1px solid rgba(255,255,255,0.05); }
        .footer-content { max-width: 1200px; margin: 0 auto; display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 40px; }
        .footer-brand .logo-text { font-family: 'Orbitron', sans-serif; font-size: 24px; font-weight: 700; }
        .footer-brand .logo-text span { color: #45f3ff; }
        .footer-col a { display: block; text-decoration: none; font-size: 14px; padding: 6px 0; }
        .footer-bottom { max-width: 1200px; margin: 30px auto 0; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: #64748b; }
        @media (max-width: 1024px) { .hero-content { grid-template-columns: 1fr; gap: 40px; } .hero-title { font-size: 48px; } .features-grid, .pricing-grid, .testimonials-grid, .stats-grid { grid-template-columns: repeat(2, 1fr); } .steps-container { grid-template-columns: 1fr; } .footer-content { grid-template-columns: 1fr 1fr; } }
        @media (max-width: 768px) { .landing-nav { padding: 12px 20px; flex-wrap: wrap; gap: 12px; } .nav-links { display: none; } .hero-section { padding: 100px 20px 40px; } .hero-title { font-size: 36px; } .hero-subtitle { font-size: 16px; } .features-grid, .pricing-grid, .testimonials-grid, .stats-grid, .footer-content { grid-template-columns: 1fr; } .section-header h2, .cta-container h2 { font-size: 32px; } .hero-stats { flex-wrap: wrap; gap: 20px; } .footer-bottom { flex-direction: column; gap: 12px; text-align: center; } }
        </style>
        """, unsafe_allow_html=True)

    def _render_navbar(self):
        st.markdown("""
        <nav class="landing-nav" id="navbar">
            <a href="#" class="nav-logo">
                <div class="logo-icon">Z</div>
                <div class="logo-text">ZOV<span>IX</span></div>
            </a>
            <div class="nav-links">
                <a href="#features">Features</a>
                <a href="#how-it-works">How It Works</a>
                <a href="#pricing">Pricing</a>
                <a href="#testimonials">Testimonials</a>
                <button class="nav-cta-btn">Get Started</button>
            </div>
        </nav>
        """, unsafe_allow_html=True)

    def _render_hero(self):
        st.markdown("""
        <section class="hero-section">
            <div class="animated-bg"><div class="orb"></div><div class="orb"></div><div class="orb"></div></div>
            <div class="hero-content">
                <div class="hero-left">
                    <div class="hero-badge">🚀 Next-Gen AI Studio</div>
                    <h1 class="hero-title">Create Cinematic<br><span class="highlight">AI Videos</span><br>in Minutes</h1>
                    <p class="hero-subtitle">Transform your ideas into stunning cinematic videos with AI. No technical skills needed. Just describe what you want.</p>
                    <div class="hero-actions">
                        <button class="hero-primary-btn" id="login_btn">🚀 Start Creating Free</button>
                        <button class="hero-secondary-btn" onclick="document.getElementById('features').scrollIntoView()">Watch Demo →</button>
                    </div>
                    <div class="hero-stats">
                        <div class="hero-stat"><div class="number">50K+</div><div class="label">Videos Generated</div></div>
                        <div class="hero-stat"><div class="number">15K+</div><div class="label">Active Creators</div></div>
                        <div class="hero-stat"><div class="number">4.9⭐</div><div class="label">User Rating</div></div>
                    </div>
                </div>
                <div class="hero-right">
                    <div class="hero-video-container">
                        <video autoplay muted loop playsinline><source src="https://cdn.pixabay.com/video/2023/02/15/150962-804104625_large.mp4" type="video/mp4"></video>
                        <div class="hero-video-overlay"><div class="play-btn">▶</div></div>
                    </div>
                </div>
            </div>
        </section>
        """, unsafe_allow_html=True)

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
        st.markdown("<section class='features-section' id='features'><div class='section-header'><div class='tag'>✨ Features</div><h2>Everything You Need to<br><span class='glow-text'>Create Like a Pro</span></h2><p>From script to screen - all AI-powered tools in one platform</p></div><div class='features-grid'>", unsafe_allow_html=True)
        for feature in features:
            st.markdown(f"<div class='feature-card'><span class='icon'>{feature['icon']}</span><h3>{feature['title']}</h3><p>{feature['desc']}</p><span class='feature-tag'>{feature['tag']}</span></div>", unsafe_allow_html=True)
        st.markdown("</div></section>", unsafe_allow_html=True)

    def _render_how_it_works(self):
        steps = [
            {"number": "01", "title": "Describe Your Vision", "desc": "Type what you want to create - a script, a scene, or just an idea. Our AI understands your vision."},
            {"number": "02", "title": "AI Does the Magic", "desc": "Our engines generate script, visuals, voiceovers, and music - all perfectly synchronized."},
            {"number": "03", "title": "Export & Share", "desc": "Download your video in 4K, share directly to social media, or embed on your website."}
        ]
        st.markdown("<section class='how-it-works' id='how-it-works'><div class='section-header'><div class='tag'>⚡ Simple Process</div><h2>How It <span class='glow-text'>Works</span></h2><p>Three simple steps to create cinematic AI videos</p></div><div class='steps-container'>", unsafe_allow_html=True)
        for step in steps:
            st.markdown(f"<div class='step-item'><div class='step-number'>{step['number']}</div><h4>{step['title']}</h4><p>{step['desc']}</p></div>", unsafe_allow_html=True)
        st.markdown("</div></section>", unsafe_allow_html=True)

    def _render_stats(self):
        stats = [{"number": "50,000+", "label": "Videos Generated"}, {"number": "15,000+", "label": "Active Users"}, {"number": "100+", "label": "Countries"}, {"number": "4.9/5", "label": "Average Rating"}]
        st.markdown("<section class='stats-section'><div class='stats-grid'>", unsafe_allow_html=True)
        for stat in stats:
            st.markdown(f"<div class='stat-item'><div class='number'>{stat['number']}</div><div class='label'>{stat['label']}</div></div>", unsafe_allow_html=True)
        st.markdown("</div></section>", unsafe_allow_html=True)

    def _render_testimonials(self):
        testimonials = [
            {"stars": "★★★★★", "text": "ZOVIX completely transformed my content creation. I went from spending 5 hours per video to 15 minutes. The quality is mind-blowing!", "name": "Priya Sharma", "role": "Content Creator, 2M+ Subs"},
            {"stars": "★★★★★", "text": "The face video feature is incredible. I created a professional talking-head video without any equipment. Game changer for my business.", "name": "Rahul Verma", "role": "Startup Founder"},
            {"stars": "★★★★★", "text": "Finally an Indian AI tool that understands our language and culture. Hinglish support with Bhojpuri voices - absolutely phenomenal!", "name": "Anjali Patel", "role": "Digital Marketer"}
        ]
        st.markdown("<section class='testimonials-section' id='testimonials'><div class='section-header'><div class='tag'>💬 Testimonials</div><h2>What Our <span class='glow-text'>Users Say</span></h2><p>Join 15,000+ creators who love ZOVIX</p></div><div class='testimonials-grid'>", unsafe_allow_html=True)
        for test in testimonials:
            initials = ''.join([part[0].upper() for part in test['name'].split()])
            st.markdown(f"<div class='testimonial-card'><div class='stars'>{test['stars']}</div><div class='text'>\"{test['text']}\"</div><div class='author'><div class='avatar'>{initials}</div><div><div class='name'>{test['name']}</div><div class='role'>{test['role']}</div></div></div></div>", unsafe_allow_html=True)
        st.markdown("</div></section>", unsafe_allow_html=True)

    def _render_pricing(self):
        plans = [
            {"name": "Free", "price": "₹0", "period": "/month", "features": ["10 Free Tokens", "Watermarked", "Basic AI Features", "Community Support"], "popular": False, "free": True},
            {"name": "Starter", "price": "₹49", "period": "/month", "features": ["30 Tokens", "No Watermark", "All AI Features", "Email Support", "🎫 Voucher Included"], "popular": False, "free": False},
            {"name": "Standard", "price": "₹99", "period": "/month", "features": ["70 Tokens", "No Watermark", "All AI Features", "Priority Support", "HD Quality"], "popular": True, "free": False},
            {"name": "Cinematic", "price": "₹299", "period": "/month", "features": ["230 Tokens", "No Watermark", "All AI Features", "24/7 Support", "4K Quality"], "popular": False, "free": False}
        ]
        st.markdown("<section class='pricing-section' id='pricing'><div class='section-header'><div class='tag'>💰 Pricing</div><h2>Choose Your <span class='glow-text'>Plan</span></h2><p>Start free, upgrade anytime. No hidden charges.</p></div><div class='pricing-grid'>", unsafe_allow_html=True)
        for plan in plans:
            popular_class = "popular" if plan.get('popular') else ""
            free_class = "free" if plan.get('free') else ""
            st.markdown(f"<div class='pricing-card {popular_class} {free_class}'><div class='plan-name'>{plan['name']}</div><div class='price'>{plan['price']}<span>{plan['period']}</span></div><ul class='features'>", unsafe_allow_html=True)
            for feature in plan['features']:
                st.markdown(f"<li><span class='check'>✅</span> {feature}</li>", unsafe_allow_html=True)
            st.markdown(f"</ul><button class='pricing-btn'>{'Get Started' if plan.get('free') else 'Subscribe Now'}</button></div>", unsafe_allow_html=True)
        st.markdown("</div></section>", unsafe_allow_html=True)

    def _render_faq(self):
        faqs = [
            {"q": "Do I need technical skills to use ZOVIX?", "a": "Not at all! ZOVIX is designed for everyone. Just type what you want to create, and our AI handles everything."},
            {"q": "What languages are supported?", "a": "We support Hindi, Hinglish, Bhojpuri, English, French, Japanese, and more. Voice synthesis works in multiple languages."},
            {"q": "How are payments processed?", "a": "We accept Razorpay (UPI, Cards, Net Banking) and Cryptocurrency (BTC, ETH, USDT, SOL, BNB)."},
            {"q": "Can I cancel my subscription anytime?", "a": "Yes! You can cancel anytime from your profile. No contracts, no hidden fees."}
        ]
        st.markdown("<section class='faq-section' style='padding: 60px 40px; position: relative; z-index: 1; background: rgba(255,255,255,0.02);'><div class='section-header'><div class='tag'>❓ FAQ</div><h2>Frequently Asked <span class='glow-text'>Questions</span></h2></div><div style='max-width: 800px; margin: 0 auto;'>", unsafe_allow_html=True)
        for idx, faq in enumerate(faqs):
            st.markdown(f"""
                <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 20px 24px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; cursor: pointer;" onclick="toggleFaq({idx})">
                        <h4 style="font-family: 'Orbitron', sans-serif; font-size: 16px; font-weight: 600; margin: 0;">{faq['q']}</h4>
                        <span id="faq_icon_{idx}" style="font-size: 20px; color: #45f3ff;">+</span>
                    </div>
                    <div id="faq_ans_{idx}" style="display: none; padding-top: 12px; color: #94a3b8; line-height: 1.6; font-size: 14px;">{faq['a']}</div>
                </div>
                <script>
                    function toggleFaq(idx) {{
                        var ans = document.getElementById('faq_ans_' + idx);
                        var icon = document.getElementById('faq_icon_' + idx);
                        if (ans.style.display === 'none' || ans.style.display === '') {{ ans.style.display = 'block'; icon.textContent = '−'; }} else {{ ans.style.display = 'none'; icon.textContent = '+'; }}
                    }}
                </script>
            """, unsafe_allow_html=True)
        st.markdown("</div></section>", unsafe_allow_html=True)

    def _render_cta(self):
        st.markdown("<section class='cta-section'><div class='cta-container'><h2>Ready to <span class='glow-text'>Create?</span></h2><p>Join 15,000+ creators already using ZOVIX to generate cinematic AI videos.</p><div class='cta-buttons'><button class='hero-primary-btn'>🚀 Start Creating Free</button><button class='hero-secondary-btn' onclick=\"document.getElementById('features').scrollIntoView()\">See Features →</button></div></div></section>", unsafe_allow_html=True)

    def _render_footer(self):
        st.markdown("<footer class='landing-footer'><div class='footer-content'><div class='footer-brand'><div class='logo-text'>ZOV<span>IX</span></div><p>The next-generation AI video creation platform. Create cinematic videos from text in minutes.</p></div><div class='footer-col'><h5>Product</h5><a href='#features'>Features</a><a href='#pricing'>Pricing</a><a href='#'>Changelog</a><a href='#'>Roadmap</a></div><div class='footer-col'><h5>Company</h5><a href='#'>About</a><a href='#'>Careers</a><a href='#'>Blog</a><a href='#'>Contact</a></div><div class='footer-col'><h5>Support</h5><a href='#'>Help Center</a><a href='#'>Documentation</a><a href='#'>Privacy Policy</a><a href='#'>Terms</a></div></div><div class='footer-bottom'><span>© 2026 ZOVIX. All rights reserved.</span><span>Made with ❤️ in India 🇮🇳</span></div></footer>", unsafe_allow_html=True)

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