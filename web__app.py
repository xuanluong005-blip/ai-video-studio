import os
import re
import sys
import time
import shutil
import tempfile
import asyncio
import threading
import requests
import numpy as np
from PIL import Image
import streamlit as st
import google.generativeai as genai
import edge_tts
from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
    vfx
)

# ---------------------------------------------------------
# CẤU HÌNH GIAO DIỆN STREAMLIT
# ---------------------------------------------------------
st.set_page_config(
    page_title="AI Creative Studio Super Pro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# THANH ĐIỀU KHIỂN BÊN TRÁI (SIDEBAR)
# ---------------------------------------------------------
with st.sidebar:
    st.title("⚙️ Cấu Hình Hệ Thống")
    
    server_url = st.text_input(
        "🔗 GPU Server URL (Cloudflare / Ngrok):",
        value="https://bacterial-sec-key-sunday.trycloudflare.com",
        help="Dán link trycloudflare.com lấy từ Kaggle Notebook vào đây"
    )
    
    gemini_key = st.text_input(
        "🔑 Google Gemini API Key:",
        type="password",
        value="",
        help="Nhập API Key để dùng tính năng tạo kịch bản tự động"
    )
    
    st.divider()
    menu_choice = st.radio(
        "📌 Chọn Chức Năng Hoạt Động:",
        [
            "1. 🎭 Diễn Hoạt Khuôn Mặt (LivePortrait GPU)",
            "2. 🎙️ Chuyển Văn Bản Thành Giọng Nói (Edge-TTS)",
            "3. 🎞️ Sản Xuất Video Kịch Bản Tự Động"
        ]
    )

# ---------------------------------------------------------
# CHỨC NĂNG 1: LIVEPORTRAIT (GỬI ĐẾN KAGGLE GPU)
# ---------------------------------------------------------
if menu_choice == "1. 🎭 Diễn Hoạt Khuôn Mặt (LivePortrait GPU)":
    st.header("🎭 Diễn Hoạt Cử Động Biểu Cảm Khuôn Mặt (LivePortrait)")
    st.caption("Truyền ảnh tĩnh và video driving đến Kaggle GPU để cử động chuẩn mắt, cơ mặt, môi theo nhịp.")

    col1, col2 = st.columns(2)
    with col1:
        img_file = st.file_uploader("1. Tải ảnh chân dung nguồn (Source Image):", type=["jpg", "jpeg", "png"])
        if img_file:
            st.image(img_file, caption="Ảnh chân dung đã chọn", use_container_width=True)

    with col2:
        vid_file = st.file_uploader("2. Tải video cử động mẫu (Driving Video - ngắn 3-10s):", type=["mp4", "mov", "avi"])
        if vid_file:
            st.video(vid_file)

    if st.button("🎬 XUẤT VIDEO BIỂU CẢM", type="primary", use_container_width=True):
        if not img_file or not vid_file:
            st.warning("⚠️ Vui lòng tải lên cả ẢNH NGUỒN và VIDEO MẪU.")
        elif not server_url.strip():
            st.error("❌ Vui lòng nhập link GPU Server URL ở cột bên trái.")
        else:
            with st.spinner("⏳ Đang truyền dữ liệu sang máy chủ Kaggle GPU và render... (Thường mất 30-90 giây)"):
                try:
                    target_endpoint = f"{server_url.strip().rstrip('/')}/process"
                    
                    files = {
                        "image": (img_file.name, img_file.getvalue(), img_file.type or "image/jpeg"),
                        "video": (vid_file.name, vid_file.getvalue(), vid_file.type or "video/mp4")
                    }
                    
                    # Headers vượt qua màn hình chặn xác thực của Cloudflare & Ngrok
                    headers = {
                        "User-Agent": "Mozilla/5.0",
                        "ngrok-skip-browser-warning": "true",
                        "Bypass-Tunnel-Reminder": "true"
                    }
                    
                    response = requests.post(target_endpoint, files=files, headers=headers, timeout=600)
                    
                    if response.status_code == 200:
                        st.success("🎉 Xuất video biểu cảm thành công!")
                        st.video(response.content)
                        st.download_button(
                            label="⬇️ TẢI VIDEO THÀNH PHẨM (MP4)",
                            data=response.content,
                            file_name="liveportrait_result.mp4",
                            mime="video/mp4"
                        )
                    else:
                        st.error(f"❌ Lỗi xử lý từ máy chủ GPU (Mã lỗi {response.status_code}):")
                        try:
                            st.json(response.json())
                        except Exception:
                            st.write(response.text)
                except requests.exceptions.RequestException as req_err:
                    st.error(f"❌ Không thể kết nối tới Server GPU. Chi tiết: {req_err}")

# ---------------------------------------------------------
# CHỨC NĂNG 2: EDGE-TTS (GIỌNG NÓI AI)
# ---------------------------------------------------------
elif menu_choice == "2. 🎙️ Chuyển Văn Bản Thành Giọng Nói (Edge-TTS)":
    st.header("🎙️ Chuyển Văn Bản Thành Giọng Nói Chuẩn AI")
    st.caption("Tạo giọng đọc thuyết minh chất lượng cao đa ngôn ngữ.")

    tts_text = st.text_area("Nhập văn bản cần đọc:", height=150, value="Chào mừng bạn đến với hệ thống AI Video Studio chuyên nghiệp.")
    
    col_voice1, col_voice2 = st.columns(2)
    with col_voice1:
        voice_option = st.selectbox(
            "Chọn giọng đọc:",
            [
                "vi-VN-NamMinhNeural (Nam - Miền Bắc)",
                "vi-VN-HoaiMyNeural (Nữ - Miền Bắc)",
                "en-US-GuyNeural (Nam - Tiếng Anh)",
                "en-US-JennyNeural (Nữ - Tiếng Anh)"
            ]
        )
        selected_voice = voice_option.split(" ")[0]
        
    with col_voice2:
        voice_rate = st.slider("Tốc độ đọc (%):", min_value=-50, max_value=50, value=0, step=5)
        rate_str = f"{'+' if voice_rate >= 0 else ''}{voice_rate}%"

    if st.button("🔊 TẠO GIỌNG ĐỌC", use_container_width=True):
        if not tts_text.strip():
            st.warning("⚠️ Vui lòng nhập văn bản cần đọc.")
        else:
            with st.spinner("Đang tổng hợp giọng nói..."):
                async def generate_audio():
                    communicate = edge_tts.Communicate(tts_text, selected_voice, rate=rate_str)
                    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    await communicate.save(temp_audio.name)
                    return temp_audio.name
                
                audio_path = asyncio.run(generate_audio())
                st.audio(audio_path)
                with open(audio_path, "rb") as f:
                    st.download_button("⬇️ Tải file âm thanh (.mp3)", f.read(), file_name="voice_output.mp3", mime="audio/mp3")

# ---------------------------------------------------------
# CHỨC NĂNG 3: SẢN XUẤT VIDEO TỰ ĐỘNG
# ---------------------------------------------------------
elif menu_choice == "3. 🎞️ Sản Xuất Video Kịch Bản Tự Động":
    st.header("🎞️ Sản Xuất Video Toàn Diện Từ Kịch Bản")
    st.caption("Ghép hình ảnh, giọng đọc AI và phụ đề thành video hoàn chỉnh.")
    
    topic = st.text_input("Nhập chủ đề video:", value="Khám phá vẻ đẹp kỳ vĩ của thiên nhiên Việt Nam")
    
    if st.button("✨ Tạo kịch bản mẫu bằng Gemini", use_container_width=True):
        if not gemini_key:
            st.error("❌ Vui lòng nhập Gemini API Key ở cột bên trái.")
        else:
            try:
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = f"Hãy viết một kịch bản video ngắn (dưới 100 từ) về chủ đề: {topic}. Văn phong truyền cảm hứng."
                res = model.generate_content(prompt)
                st.session_state["script_content"] = res.text
            except Exception as e:
                st.error(f"Lỗi gọi Gemini API: {e}")

    script_text = st.text_area("Nội dung kịch bản thuyết minh:", value=st.session_state.get("script_content", "Việt Nam với hàng ngàn cảnh quan thiên nhiên tráng lệ từ non cao tới biển bạc."), height=120)
    bg_images = st.file_uploader("Tải lên các hình ảnh minh họa cho video:", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

    if st.button("🎬 BẮT ĐẦU RENDER VIDEO HOÀN CHỈNH", type="primary", use_container_width=True):
        if not script_text.strip() or not bg_images:
            st.warning("⚠️ Vui lòng cung cấp đầy đủ kịch bản và ít nhất 1 hình ảnh.")
        else:
            with st.spinner("Đang xử lý âm thanh, hình ảnh và dựng video..."):
                try:
                    # 1. Tạo audio
                    communicate = edge_tts.Communicate(script_text, "vi-VN-NamMinhNeural")
                    temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    asyncio.run(communicate.save(temp_audio_file.name))
                    
                    audio_clip = AudioFileClip(temp_audio_file.name)
                    total_duration = audio_clip.duration
                    
                    # 2. Tạo visual clips từ hình ảnh
                    clips = []
                    duration_per_image = total_duration / len(bg_images)
                    
                    for img_item in bg_images:
                        t_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                        t_img.write(img_item.getvalue())
                        t_img.close()
                        
                        ic = ImageClip(t_img.name).set_duration(duration_per_image).resize(width=1080)
                        clips.append(ic)
                        
                    final_video = concatenate_videoclips(clips, method="compose").set_audio(audio_clip)
                    
                    out_vid_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                    final_video.write_videofile(out_vid_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
                    
                    st.success("🎉 Video đã hoàn thành!")
                    st.video(out_vid_path)
                    with open(out_vid_path, "rb") as vf:
                        st.download_button("⬇️ TẢI VIDEO XUỐNG", vf.read(), file_name="final_composed_video.mp4", mime="video/mp4")
                except Exception as comp_err:
                    st.error(f"❌ Lỗi trong quá trình render video: {comp_err}")
