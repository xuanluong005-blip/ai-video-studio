import os
import re
import sys
import time
import math
import shutil
import tempfile
import asyncio
import threading
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import PIL.Image

# Patch MoviePy
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS

import streamlit as st
import google.generativeai as genai
import edge_tts
from moviepy.editor import (
    ImageClip,
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
    vfx
)

st.set_page_config(
    page_title="AI Creative Studio Super Pro Max",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 800; color: #1976D2; margin-bottom: 0.2rem; }
    .sub-header { font-size: 1.05rem; color: #4B5563; margin-bottom: 1.5rem; }
    .scene-box { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 15px; margin-bottom: 15px; }
    .stButton>button { border-radius: 8px; font-weight: 600; height: 3em; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/video-editing.png", width=110)
    st.title("⚙️ TRUNG TÂM ĐIỀU KHIỂN")
    
    server_url = st.text_input(
        "GPU Server URL (Cloudflare / Ngrok):",
        value="",
        placeholder="https://xxxx.ngrok-free.app",
        help="Dán URL tunnel được cung cấp từ Kaggle Notebook vào đây."
    )
    
    col_ping1, col_ping2 = st.columns([1, 1])
    with col_ping1:
        if st.button("🔍 Kiểm Tra GPU", use_container_width=True):
            if not server_url.strip():
                st.warning("Chưa nhập link GPU!")
            else:
                with st.spinner("Đang ping..."):
                    try:
                        headers = {"User-Agent": "Mozilla/5.0", "ngrok-skip-browser-warning": "true"}
                        test_res = requests.get(server_url.strip().rstrip('/'), headers=headers, timeout=10)
                        if test_res.status_code == 200:
                            st.success("🟢 GPU SVD Online!")
                        else:
                            st.warning(f"🟡 Phản hồi: {test_res.status_code}")
                    except Exception as err:
                        st.error(f"🔴 Mất kết nối: {err}")

    with col_ping2:
        if st.button("🧹 Reset App", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.markdown("---")
    gemini_key = st.text_input("Gemini API Key:", type="password", value="")
    
    st.markdown("---")
    menu_choice = st.radio(
        "📌 CHỌN TÍNH NĂNG HOẠT ĐỘNG:",
        [
            "1. 🎙️ Phòng Thu Giọng Nói AI (Edge-TTS)",
            "2. ✨ Trợ Lý Viết Kịch Bản Phân Cảnh (Gemini)",
            "3. 🎞️ Sản Xuất Video Phân Cảnh (Chuyển Động Toàn Thân SVD Miễn Phí)"
        ]
    )

# Hàm gọi Gemini
def call_gemini_smart_generator(api_key, prompt_text):
    genai.configure(api_key=api_key)
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
    except Exception:
        pass

    priority_order = ["models/gemini-2.5-flash", "models/gemini-1.5-flash", "gemini-1.5-flash"]
    target_model = next((p for p in priority_order if p in available_models), "gemini-1.5-flash")

    model = genai.GenerativeModel(target_model)
    response = model.generate_content(prompt_text)
    return response.text, target_model

# 1. PHÒNG THU GIỌNG NÓI
if menu_choice == "1. 🎙️ Phòng Thu Giọng Nói AI (Edge-TTS)":
    st.markdown('<div class="main-header">🎙️ Phòng Thu Giọng Nói Chuẩn AI (Edge-TTS)</div>', unsafe_allow_html=True)
    tts_text = st.text_area("Nhập nội dung văn bản:", height=180, value="Chào mừng bạn đến với hệ thống AI Creative Studio.")
    
    voice_dict = {
        "🇻🇳 vi-VN-NamMinhNeural (Nam Bắc)": "vi-VN-NamMinhNeural",
        "🇻🇳 vi-VN-HoaiMyNeural (Nữ Bắc)": "vi-VN-HoaiMyNeural",
        "🇺🇸 en-US-GuyNeural (Nam Mỹ)": "en-US-GuyNeural"
    }
    selected_voice = voice_dict[st.selectbox("Chọn giọng đọc:", list(voice_dict.keys()))]

    if st.button("🔊 TẠO GIỌNG ĐỌC NGAY", type="primary", use_container_width=True):
        if tts_text.strip():
            async def run_edge_tts():
                comm = edge_tts.Communicate(tts_text, selected_voice)
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                await comm.save(temp_file.name)
                return temp_file.name
            audio_path = asyncio.run(run_edge_tts())
            st.success("🎉 Tạo âm thanh thành công!")
            st.audio(audio_path)

# 2. TRỢ LÝ GEMINI
elif menu_choice == "2. ✨ Trợ Lý Viết Kịch Bản Phân Cảnh (Gemini)":
    st.markdown('<div class="main-header">✨ Trợ Lý Sáng Tạo Kịch Bản Phân Cảnh</div>', unsafe_allow_html=True)
    topic = st.text_input("Chủ đề video:", value="3 bài học về sự nỗ lực")
    num_scenes = st.slider("Số lượng phân cảnh:", 2, 6, 3)

    if st.button("✨ TẠO KỊCH BẢN", type="primary", use_container_width=True):
        if gemini_key.strip():
            prompt = f"Viết kịch bản ngắn chủ đề '{topic}' chia đúng {num_scenes} phân cảnh dạng [Cảnh 1]..., [Cảnh 2]..."
            res, m_used = call_gemini_smart_generator(gemini_key, prompt)
            st.session_state["saved_scenes"] = res
            st.success("Tạo kịch bản thành công!")
    st.text_area("Kịch bản:", value=st.session_state.get("saved_scenes", ""), height=200)

# 3. SẢN XUẤT VIDEO SVD
elif menu_choice == "3. 🎞️ Sản Xuất Video Phân Cảnh (Chuyển Động Toàn Thân SVD Miễn Phí)":
    st.markdown('<div class="main-header">🎞️ Sản Xuất Video Chuyển Động Toàn Thân SVD (Miễn Phí)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI tự động tạo chuyển động mượt mà toàn thân cho con vật/nhân vật và bối cảnh theo từng phân cảnh.</div>', unsafe_allow_html=True)

    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        voice_choice = st.selectbox("Giọng đọc:", ["vi-VN-NamMinhNeural (Nam Bắc)", "vi-VN-HoaiMyNeural (Nữ Bắc)"]).split(" ")[0]
    with col_cfg2:
        sub_toggle = st.checkbox("Chèn phụ đề tự động", value=True)

    if "scenes_count" not in st.session_state:
        st.session_state["scenes_count"] = 2

    col_b1, col_b2 = st.columns([1, 4])
    with col_b1:
        if st.button("➕ Thêm Cảnh"):
            st.session_state["scenes_count"] += 1
            st.rerun()
    with col_b2:
        if st.session_state["scenes_count"] > 1:
            if st.button("➖ Giảm Cảnh"):
                st.session_state["scenes_count"] -= 1
                st.rerun()

    scenes_data = []
    for i in range(st.session_state["scenes_count"]):
        st.markdown('<div class="scene-box">', unsafe_allow_html=True)
        st.markdown(f"#### 📍 Phân Cảnh {i + 1}")
        c1, c2, c3 = st.columns([3, 2, 2])
        with c1:
            t = st.text_area(f"Lời thoại cảnh {i + 1}:", value=f"Nội dung thuyết minh phân cảnh số {i + 1}.", key=f"t_{i}", height=100)
        with c2:
            m = st.file_uploader(f"Ảnh cảnh {i + 1}:", type=["jpg", "png", "jpeg"], key=f"m_{i}")
            if m:
                st.image(m, width=140)
        with c3:
            opt = st.selectbox(f"Kiểu chuyển động:", ["🌟 Chuyển động toàn thân AI (SVD)", "🖼️ Ảnh tĩnh"], key=f"opt_{i}")
        scenes_data.append({"text": t, "media": m, "opt": opt})
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🚀 BẮT ĐẦU SẢN XUẤT VIDEO", type="primary", use_container_width=True):
        if any(sc["media"] is None for sc in scenes_data):
            st.warning("⚠️ Vui lòng tải đủ hình ảnh cho các phân cảnh!")
        else:
            prog = st.progress(0, text="⏳ Bắt đầu xử lý...")
            try:
                target_w, target_h = 1024, 576
                scene_clips = []
                total = len(scenes_data)

                for idx, sc in enumerate(scenes_data):
                    prog.progress(int((idx / total) * 80), text=f"⏳ Đang xử lý cảnh {idx + 1}/{total}...")
                    
                    # 1. Tạo giọng đọc
                    comm = edge_tts.Communicate(sc["text"], voice_choice)
                    t_aud = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    asyncio.run(comm.save(t_aud.name))
                    aud_clip = AudioFileClip(t_aud.name)
                    dur = aud_clip.duration

                    # 2. Xử lý video cử động qua SVD
                    if "SVD" in sc["opt"] and server_url.strip():
                        prog.progress(int((idx / total) * 80) + 10, text=f"⏳ GPU đang sinh chuyển động mượt mà cho Cảnh {idx + 1}...")
                        files = {"image": (sc["media"].name, sc["media"].getvalue(), sc["media"].type or "image/jpeg")}
                        res = requests.post(f"{server_url.strip().rstrip('/')}/animate_scene", files=files, headers={"ngrok-skip-browser-warning": "true"}, timeout=600)
                        
                        if res.status_code == 200:
                            t_vid = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                            t_vid.write(res.content)
                            t_vid.close()
                            
                            raw_vid = VideoFileClip(t_vid.name)
                            if raw_vid.duration < dur:
                                loop_cnt = math.ceil(dur / raw_vid.duration)
                                raw_vid = concatenate_videoclips([raw_vid] * loop_cnt)
                            sc_clip = raw_vid.subclip(0, dur).resize((target_w, target_h)).set_audio(aud_clip)
                        else:
                            st.error(f"Lỗi render GPU cảnh {idx + 1}: {res.text}")
                            st.stop()
                    else:
                        # Ảnh tĩnh
                        pil_img = Image.open(sc["media"]).convert("RGB").resize((target_w, target_h))
                        t_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                        pil_img.save(t_img.name, "JPEG")
                        sc_clip = ImageClip(t_img.name).set_duration(dur).set_audio(aud_clip)

                    # 3. Vẽ phụ đề
                    if sub_toggle:
                        def make_sub(frame, txt=sc["text"]):
                            img = Image.fromarray(frame)
                            draw = ImageDraw.Draw(img)
                            try:
                                font = ImageFont.truetype("arial.ttf", 28)
                            except:
                                font = ImageFont.load_default()
                            bbox = draw.textbbox((0, 0), txt, font=font)
                            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                            px, py = (target_w - tw) // 2, target_h - th - 40
                            draw.text((px, py), txt, font=font, fill="#FFE600", stroke_width=2, stroke_fill="black")
                            return np.array(img)
                        sc_clip = sc_clip.fl_image(make_sub)

                    scene_clips.append(sc_clip)

                prog.progress(90, text="⏳ Đang ghép nối toàn bộ video...")
                final_video = concatenate_videoclips(scene_clips, method="compose")
                out_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                final_video.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)

                prog.progress(100, text="✅ Hoàn thành!")
                with open(out_path, "rb") as vf:
                    v_bytes = vf.read()

                st.success("🎉 Xuất video chuyển động SVD thành công!")
                st.video(v_bytes)
                st.download_button("⬇️ TẢI VIDEO (MP4)", data=v_bytes, file_name="svd_full_motion_video.mp4", mime="video/mp4", use_container_width=True)
            except Exception as e:
                prog.empty()
                st.error(f"Lỗi: {e}")
