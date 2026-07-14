# encoding: utf-8
import re

with open('app.py', 'r', encoding='utf-8') as f:
    c = f.read()

# ============================================================
# 1. ADD GENDER DETECTION FUNCTIONS before run_face_video_mode
# ============================================================
gender_funcs = '''
# ========================================================
# GENDER DETECTION UTILITY FOR FACE VIDEO MODE
# ========================================================
def detect_gender_from_image(image_path):
    """Detect gender (male/female) from a face image using DeepFace AI."""
    if not image_path or not os.path.exists(image_path):
        return None
    
    try:
        from deepface import DeepFace
        os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
        result = DeepFace.analyze(image_path, actions=['gender'], enforce_detection=False, prog_bar=False)
        if isinstance(result, list) and len(result) > 0:
            gender_data = result[0].get('gender', {})
        elif isinstance(result, dict):
            gender_data = result.get('gender', {})
        else:
            return None
        
        if isinstance(gender_data, dict) and gender_data:
            detected_gender = max(gender_data, key=gender_data.get)
            return detected_gender.lower().strip()
        elif isinstance(gender_data, str):
            return gender_data.lower().strip()
    except Exception as e:
        logger.warning(f'Gender detection failed: {e}')
    
    return None


def get_gender_based_voice_recommendation(detected_gender, language='English'):
    """Get recommended voice profiles based on detected gender."""
    if detected_gender == 'male':
        if language == 'Hindi':
            return [v for v, m in ELEVENLABS_VOICES.items() if m.get('gender') == 'male' and m.get('language') in ['Hindi', 'English']]
        elif language == 'English':
            return [v for v, m in ELEVENLABS_VOICES.items() if m.get('gender') == 'male' and m.get('language') == 'English']
        return [v for v, m in ELEVENLABS_VOICES.items() if m.get('gender') == 'male']
    elif detected_gender == 'female':
        if language == 'Hindi':
            return [v for v, m in ELEVENLABS_VOICES.items() if m.get('gender') == 'female' and m.get('language') in ['Hindi', 'English']]
        elif language == 'English':
            return [v for v, m in ELEVENLABS_VOICES.items() if m.get('gender') == 'female' and m.get('language') == 'English']
        return [v for v, m in ELEVENLABS_VOICES.items() if m.get('gender') == 'female']
    return []

'''

pos = c.find('def run_face_video_mode():')
c = c[:pos] + gender_funcs + '\n' + c[pos:]
print('1. Gender detection functions added')

# ============================================================
# 2. REPLACE VOICE SECTION WITH GENDER AUTO-DETECT UI
# ============================================================
old_voice_section = '''            fv_voice_language = st.selectbox(
                "Voice Language",
                ["Hindi", "English", "All Voices"],
                key="fv_voice_language",
            )
            fv_voice_options = _resolve_face_voice_config(voice_language=fv_voice_language).get("available_voices", [])
            fv_current_voice = st.session_state.get("face_voice_model")
            if fv_current_voice not in fv_voice_options:
                fv_current_voice = fv_voice_options[0] if fv_voice_options else "Adam (Premium Male)"
            fv_voice_model = st.selectbox(
                "Voice Model",
                fv_voice_options,
                index=fv_voice_options.index(fv_current_voice) if fv_voice_options and fv_current_voice in fv_voice_options else 0,
                key="fv_voice_model",
            )'''

new_voice_section = '''            fv_voice_language = st.selectbox(
                "Voice Language",
                ["Hindi", "English", "All Voices"],
                key="fv_voice_language",
            )
            
            # ---- Gender Auto-Detect Feature ----
            if "fv_gender_auto" not in st.session_state:
                st.session_state["fv_gender_auto"] = True
            
            face_uploaded = st.session_state.get("face_image_upload")
            face_available = bool(face_uploaded and os.path.exists(face_uploaded))
            
            col_g1, col_g2 = st.columns([1, 1])
            with col_g1:
                gender_auto = st.toggle(
                    "\U0001f3ad Auto-Detect Gender",
                    value=st.session_state.get("fv_gender_auto", True),
                    key="fv_gender_auto_toggle",
                    help="Automatically detect gender from face image and suggest matching voice",
                )
            
            if gender_auto and face_available:
                with col_g2:
                    if st.button("\U0001f50d Detect Now", key="fv_detect_gender_btn", use_container_width=True):
                        with st.spinner("Analyzing face image for gender..."):
                            detected = detect_gender_from_image(face_uploaded)
                            if detected:
                                st.session_state["fv_detected_gender"] = detected
                                st.session_state["fv_gender_auto"] = True
                                st.toast(f"Gender detected: {detected.title()}")
                                st.rerun()
                            else:
                                st.warning("Could not detect gender. Please select manually.")
                                st.session_state["fv_gender_auto"] = False
            
            detected_gender = st.session_state.get("fv_detected_gender")
            if gender_auto and detected_gender and face_available:
                emoji = "\U0001f468" if detected_gender == 'male' else "\U0001f469"
                st.markdown(f"""<div style='background: rgba(69,243,255,0.08); border: 1px solid rgba(69,243,255,0.2); 
                    border-radius: 8px; padding: 8px 12px; margin: 5px 0; display: flex; align-items: center; gap: 8px;'>
                    <span style='font-size: 18px;'>{emoji}</span>
                    <span style='color: #45f3ff; font-size: 13px; font-weight: 500;'>
                        Detected: <strong>{detected_gender.title()}</strong>
                    </span>
                </div>""", unsafe_allow_html=True)
                
                recommended_voices = get_gender_based_voice_recommendation(detected_gender, fv_voice_language)
                if recommended_voices:
                    fv_voice_options = recommended_voices
                else:
                    fv_voice_options = _resolve_face_voice_config(voice_language=fv_voice_language).get("available_voices", [])
            else:
                if gender_auto and not face_available:
                    st.caption("\U0001f4f7 Upload a face image first to enable auto gender detection")
                fv_voice_options = _resolve_face_voice_config(voice_language=fv_voice_language).get("available_voices", [])
            
            fv_current_voice = st.session_state.get("face_voice_model")
            if fv_current_voice not in fv_voice_options:
                fv_current_voice = fv_voice_options[0] if fv_voice_options else "Adam (Premium Male)"
            
            manual_label = "Voice Model (Manual Override)" if (gender_auto and detected_gender and face_available) else "Voice Model"
            fv_voice_model = st.selectbox(
                manual_label,
                fv_voice_options,
                index=fv_voice_options.index(fv_current_voice) if fv_voice_options and fv_current_voice in fv_voice_options else 0,
                key="fv_voice_model",
            )
            
            if gender_auto != st.session_state.get("fv_gender_auto", True):
                st.session_state["fv_gender_auto"] = gender_auto'''

if old_voice_section in c:
    c = c.replace(old_voice_section, new_voice_section)
    print('2. Voice section updated with gender auto-detect')
else:
    print('2. ERROR: Could not find old voice section!')
    # debug
    idx = c.find('fv_voice_language = st.selectbox')
    if idx >= 0:
        print(f'Found at {idx}')
        print(c[idx:idx+800])

# ============================================================
# 3. UPDATE GENERATE BUTTON to auto-detect gender
# ============================================================
old_btn = '''            if st.button("\U0001f464 Generate Face Video", key="fv_generate_btn", use_container_width=True):
                success, required_tokens, message = validate_and_deduct_tokens("Face Video Generator", quality)
                if not success:
                    st.error(message)
                else:
                    st.success(message)
                    if not face_prompt.strip():
                        st.error("Please enter a video description for lip sync.")
                    elif not st.session_state.get("face_image_upload") or not os.path.exists(st.session_state["face_image_upload"]):
                        st.error("Please upload a face image or take a photo using camera mode.")
                    else:
                        with st.spinner(f"Generating {quality} lip-sync face video (motion locked)..."):
                            video_path = generate_face_video(
                                face_prompt,
                                st.session_state["face_image_upload"],
                                video_duration,
                                quality=quality,
                                voice_language=fv_voice_language,
                                voice_label=fv_voice_model,
                            )
                            if video_path and os.path.exists(video_path):'''

new_btn = '''            if st.button("\U0001f464 Generate Face Video", key="fv_generate_btn", use_container_width=True):
                if st.session_state.get("fv_gender_auto", True) and st.session_state.get("face_image_upload"):
                    if not st.session_state.get("fv_detected_gender"):
                        with st.spinner("\U0001f50d Detecting gender from face image..."):
                            detected = detect_gender_from_image(st.session_state["face_image_upload"])
                            if detected:
                                st.session_state["fv_detected_gender"] = detected
                                st.toast(f"Gender detected: {detected.title()}")
                            else:
                                st.warning("Gender detection failed. Using default voice.")
                
                success, required_tokens, message = validate_and_deduct_tokens("Face Video Generator", quality)
                if not success:
                    st.error(message)
                else:
                    st.success(message)
                    if not face_prompt.strip():
                        st.error("Please enter a video description for lip sync.")
                    elif not st.session_state.get("face_image_upload") or not os.path.exists(st.session_state["face_image_upload"]):
                        st.error("Please upload a face image or take a photo using camera mode.")
                    else:
                        with st.spinner(f"Generating {quality} lip-sync face video (motion locked)..."):
                            video_path = generate_face_video(
                                face_prompt,
                                st.session_state["face_image_upload"],
                                video_duration,
                                quality=quality,
                                voice_language=fv_voice_language,
                                voice_label=fv_voice_model,
                            )
                            if video_path and os.path.exists(video_path):'''

if old_btn in c:
    c = c.replace(old_btn, new_btn)
    print('3. Generate button updated with auto gender detection')
else:
    print('3. ERROR: Generate button not found!')
    idx = c.find('if st.button')
    if idx >= 0:
        print(f'First st.button at {idx}: {c[idx:idx+100]}')

# ============================================================
# 4. UPDATE generate_face_video to pass gender state
# ============================================================
old_gen = 'voice_cfg = _resolve_face_voice_config(voice_language=voice_language, voice_label=voice_label)'
new_gen = "voice_cfg = _resolve_face_voice_config(voice_language=voice_language, voice_label=voice_label, preferred_gender=st.session_state.get('fv_detected_gender') if st.session_state.get('fv_gender_auto', False) else None)"

if old_gen in c:
    c = c.replace(old_gen, new_gen)
    print('4. generate_face_video updated with gender pass')
else:
    print('4. ERROR: Voice config line not found!')

# Also update the expressive one
old_exp = "voice_cfg = _resolve_face_voice_config(voice_language=voice_language, voice_label=voice_label)"
new_exp = "voice_cfg = _resolve_face_voice_config(voice_language=voice_language, voice_label=voice_label, preferred_gender=st.session_state.get('fv_detected_gender') if st.session_state.get('fv_gender_auto', False) else None)"

# Only replace if found (might be same text as above which was already replaced if in generate_face_video)
# Let's count and replace all remaining instances
count = c.count(old_exp)
if count > 0:
    c = c.replace(old_exp, new_exp)
    print(f'5. Updated {count} more voice config calls')

# ============================================================
# 5. UPDATE _resolve_face_voice_config to accept gender
# ============================================================
old_sig = 'def _resolve_face_voice_config(voice_language=None, voice_label=None):'
new_sig = 'def _resolve_face_voice_config(voice_language=None, voice_label=None, preferred_gender=None):'

if old_sig in c:
    c = c.replace(old_sig, new_sig)
    print('6. _resolve_face_voice_config signature updated')
else:
    print('6. ERROR: Function signature not found!')

# Add gender filtering in the body
old_body = '''    if not available_voices:
        available_voices = ["Adam (Premium Male)"]'''

new_body = '''    # Filter by gender preference if provided
    if preferred_gender and available_voices:
        gender_filtered = []
        for v in available_voices:
            meta = ELEVENLABS_VOICES.get(v, {})
            if meta.get('gender') == preferred_gender:
                gender_filtered.append(v)
        if gender_filtered:
            available_voices = gender_filtered

    if not available_voices:
        available_voices = ["Adam (Premium Male)"]'''

if old_body in c:
    c = c.replace(old_body, new_body)
    print('7. Gender filtering added to _resolve_face_voice_config')
else:
    print('7. ERROR: Body section not found!')

# ============================================================
# WRITE AND VERIFY
# ============================================================
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('\n--- File written ---')

try:
    compile(c, 'app.py', 'exec')
    print('Syntax check: PASSED')
except SyntaxError as e:
    print(f'Syntax error: {e}')

# Verify all components
for kw in ['detect_gender_from_image', 'get_gender_based_voice_recommendation', 
           'fv_gender_auto_toggle', 'fv_detected_gender', 'fv_detect_gender_btn',
           'preferred_gender', 'Auto-Detect Gender', 'Manual Override']:
    cnt = c.count(kw)
    status = 'OK' if cnt > 0 else 'MISSING'
    print(f'  {kw}: {cnt} ({status})')
