# encoding: utf-8
import re

with open('app.py', 'r', encoding='utf-8') as f:
    c = f.read()

# PHASE 4b: Update generate button handler to auto-detect gender before generation
old_btn = '''            if st.button("👤 Generate Face Video", key="fv_generate_btn", use_container_width=True):
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

new_btn = '''            if st.button("👤 Generate Face Video", key="fv_generate_btn", use_container_width=True):
                # Auto-detect gender before generation if toggle is on
                if st.session_state.get("fv_gender_auto", True) and st.session_state.get("face_image_upload"):
                    if not st.session_state.get("fv_detected_gender"):
                        with st.spinner("🔍 Detecting gender from face image..."):
                            detected = detect_gender_from_image(st.session_state["face_image_upload"])
                            if detected:
                                st.session_state["fv_detected_gender"] = detected
                                st.toast(f"✅ Gender detected: {detected.title()}")
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
    print('4b. Updated generate button with auto gender detection!')
else:
    print('4b. ERROR: Could not find generate button!')
    idx = c.find('if st.button("👤 Generate Face Video"')
    if idx >= 0:
        print(f'Found at {idx}')
        print(f'Content: {c[idx:idx+800]}')
    else:
        print('Not found in file!')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('Phase 4 complete!')
