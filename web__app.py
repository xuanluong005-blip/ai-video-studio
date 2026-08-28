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

# --- PATCH LỖI PILLOW CHO MOVIEPY ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
# ------------------------------------

import streamlit as st
import google.generativeai as genai
import edge_tts
from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
    vfx
)

# ==============================================================================
# 1. CẤU HÌNH GIAO DIỆN HỆ THỐNG
# ==============================================================================
st.set_page_config(
    page_title="AI Creative Studio Super Pro Max",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Áp dụng Custom CSS tăng tính thẩm mỹ cho UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #555555;
        margin-bottom: 1.5rem;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        height: 3em;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. THANH CÔNG CỤ SIDEBAR & CẤU HÌNH TOÀN CỤC
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/video-editing.png", width=120)
    st.title("⚙️ CẤU HÌNH HỆ THỐNG")
    
    st.markdown("### 🔌 Máy Chủ Xử Lý GPU")
    server_url = st.text_input(
        "GPU Server URL (Cloudflare / Ngrok):",
        value="",
        placeholder="https://xxxx.trycloudflare.com hoặc https://xxxx.ngrok-free.app",
        help="Dán URL tunnel được cấp từ phiên chạy Kaggle GPU vào đây."
    )
    
    if st.button("🔍 Kiểm Tra Kết Nối GPU", use_container_width=True):
        if not server_url.strip():
            st.warning("⚠️ Vui lòng nhập link Server GPU trước!")
        else:
            with st.spinner("Đang ping tới máy chủ..."):
                try:
                    headers = {
                        "User-Agent": "Mozilla/5.0",
                        "ngrok-skip-browser-warning": "true",
                        "Bypass-Tunnel-Reminder": "true"
                    }
                    test_res = requests.get(server_url.strip().rstrip('/'), headers=headers, timeout=10)
                    if test_res.status_code == 200:
                        st.success("🟢 Kết nối thành công! Máy chủ GPU đã sẵn sàng.")
                    else:
                        st.warning(f"🟡 Phản hồi máy chủ: Mã {test_res.status_code}")
                except Exception as ping_err:
                    st.error(f"🔴 Không thể kết nối: {ping_err}")

    st.markdown("---")
    st.markdown("### 🔑 Khóa API Google AI")
    gemini_key = st.text_input(
        "Google Gemini API Key:",
        type="password",
        value="",
        help="Nhập API Key để mở khóa trợ lý viết kịch bản thông minh."
    )
    
    st.markdown("---")
    menu_choice = st.radio(
        "📌 ĐIỀU HƯỚNG TÍNH NĂNG:",
        [
            "1. 🎭 Diễn Hoạt Biểu Cảm (LivePortrait GPU)",
            "2. 🎙️ Phòng Thu Giọng Nói AI (Edge-TTS)",
            "3. ✨ Trợ Lý Viết Kịch Bản AI (Gemini Studio)",
            "4. 🎞️ Xưởng Sản Xuất Video Đa Năng (All-In-One)"
        ]
    )

# ==============================================================================
# HÀM HỖ TRỢ XỬ LÝ GEMINI VỚI CƠ CHẾ MULTI-MODEL FALLBACK
# ==============================================================================
def call_gemini_smart_generator(api_key, prompt_text):
    genai.configure(api_key=api_key)
    
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
    except Exception:
        pass

    priority_order = [
        "models/gemini-3.6-flash",
        "models/gemini-3.6-pro",
        "models/gemini-2.5-flash",
        "models/gemini-1.5-flash",
        "gemini-3.6-flash",
        "gemini-1.5-flash"
    ]
    
    target_model = None
    for p in priority_order:
        if p in available_models:
            target_model = p
            break
            
    if not target_model and available_models:
        target_model = available_models[0]
        
    if not target_model:
        target_model = "models/gemini-3.6-flash"

    model = genai.GenerativeModel(target_model)
    response = model.generate_content(prompt_text)
    
    if response and response.text:
        return response.text, target_model
    else:
        raise Exception("Mô hình không trả về nội dung văn bản.")

# ==============================================================================
# CHỨC NĂNG 1: LIVEPORTRAIT (GPU SERVER)
# ==============================================================================
if menu_choice == "1. 🎭 Diễn Hoạt Biểu Cảm (LivePortrait GPU)":
    st.markdown('<div class="main-header">🎭 Diễn Hoạt Cử Động Biểu Cảm Khuôn Mặt (LivePortrait)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Truyền cử động mắt, cơ mặt, nhép môi từ video driving sang ảnh chân dung bằng sức mạnh Kaggle GPU.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 1. Ảnh Chân Dung Nguồn (Source Image)")
        img_file = st.file_uploader("Tải lên ảnh khuôn mặt rõ nét:", type=["jpg", "jpeg", "png"], key="lp_img")
        if img_file:
            st.image(img_file, caption="Ảnh chân dung đã chọn", use_container_width=True)

    with col2:
        st.markdown("#### 2. Video Mẫu Biểu Cảm (Driving Video)")
        vid_file = st.file_uploader("Tải lên video mẫu cử động (Khuyên dùng 3-10 giây):", type=["mp4", "mov", "avi"], key="lp_vid")
        if vid_file:
            st.video(vid_file)

    st.markdown("#### ⚙️ Tùy Chỉnh Nâng Cao Cho LivePortrait")
    with st.expander("Bấm để mở các tùy chọn thuật toán LivePortrait", expanded=False):
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1:
            lp_flag_eye = st.checkbox("Khớp chuyển động nhắm/mở mắt (Eye Retargeting)", value=True)
            lp_flag_lip = st.checkbox("Khớp chuyển động khẩu hình môi (Lip Retargeting)", value=True)
        with c_p2:
            lp_flag_head = st.checkbox("Đồng bộ xoay góc đầu (Head Pose)", value=True)
            lp_smooth = st.slider("Độ mượt mà chuyển động (Smoothness):", min_value=1, max_value=10, value=5)
        with c_p3:
            lp_crop_mode = st.selectbox("Chế độ khung hình:", ["Tập trung khuôn mặt (Face Crop)", "Toàn thân/Bối cảnh (Full Image)"])

   if st.button("🎬 BẮT ĐẦU SẢN XUẤT VIDEO TỰ ĐỘNG", type="primary", use_container_width=True):
        if not prod_script.strip():
            st.warning("⚠️ Vui lòng nhập nội dung kịch bản thuyết minh.")
        elif not uploaded_imgs:
            st.warning("⚠️ Vui lòng tải lên ít nhất 1 hình ảnh minh họa.")
        else:
            progress_bar = st.progress(0, text="⏳ Bước 1/4: Đang tạo giọng đọc AI...")
            try:
                # 1. Tạo file âm thanh bằng Edge-TTS
                comm = edge_tts.Communicate(prod_script, selected_prod_voice)
                temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                asyncio.run(comm.save(temp_audio_file.name))
                
                audio_clip = AudioFileClip(temp_audio_file.name)
                total_duration = audio_clip.duration
                
                # 2. Xác định kích thước video
                progress_bar.progress(30, text="⏳ Bước 2/4: Đang tối ưu hóa hình ảnh...")
                if "16:9" in ratio_choice:
                    target_w, target_h = 1280, 720
                elif "9:16" in ratio_choice:
                    target_w, target_h = 720, 1280
                else:
                    target_w, target_h = 720, 720

                # 3. Xử lý ảnh chuẩn hóa bằng PIL trước khi nạp vào MoviePy
                num_images = len(uploaded_imgs)
                duration_per_image = total_duration / num_images
                clips_list = []
                
                for idx, img_item in enumerate(uploaded_imgs):
                    # Đọc và ép kích thước ảnh chuẩn ngay từ đầu bằng PIL để tiết kiệm RAM
                    pil_img = Image.open(img_item).convert("RGB")
                    pil_img = pil_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    
                    t_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                    pil_img.save(t_img.name, "JPEG", quality=90)
                    t_img.close()
                    
                    img_clip = ImageClip(t_img.name).set_duration(duration_per_image)
                    
                    if motion_effect == "Zoom In Nhẹ (Phóng to dần)":
                        img_clip = img_clip.fx(vfx.resize, lambda t: 1.0 + 0.04 * (t / duration_per_image))
                    elif motion_effect == "Zoom Out Nhẹ (Thu nhỏ dần)":
                        img_clip = img_clip.fx(vfx.resize, lambda t: 1.04 - 0.04 * (t / duration_per_image))
                        
                    clips_list.append(img_clip)
                    
                composed_base_video = concatenate_videoclips(clips_list, method="compose").set_audio(audio_clip)
                
                # 4. Thêm phụ đề nhẹ nhàng
                progress_bar.progress(60, text="⏳ Bước 3/4: Đang vẽ phụ đề...")
                if sub_toggle:
                    def add_subtitle_to_frame(frame):
                        img = Image.fromarray(frame)
                        draw = ImageDraw.Draw(img)
                        
                        try:
                            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", sub_font_size)
                        except Exception:
                            try:
                                font = ImageFont.truetype("arial.ttf", sub_font_size)
                            except Exception:
                                font = ImageFont.load_default()
                        
                        text = prod_script.replace("\n", " ")
                        max_chars = max(10, int(target_w / (sub_font_size * 0.65)))
                        words = text.split()
                        lines = []
                        cur_line = []
                        for w in words:
                            cur_line.append(w)
                            if len(" ".join(cur_line)) > max_chars:
                                lines.append(" ".join(cur_line[:-1]))
                                cur_line = [w]
                        if cur_line:
                            lines.append(" ".join(cur_line))
                        
                        rendered_text = "\n".join(lines)
                        bbox = draw.multiline_textbbox((0, 0), rendered_text, font=font, align="center")
                        text_w = bbox[2] - bbox[0]
                        text_h = bbox[3] - bbox[1]
                        pos_x = (target_w - text_w) // 2
                        pos_y = target_h - text_h - 50

                        # Viền chữ đen
                        stroke_w = 2
                        for ox in range(-stroke_w, stroke_w + 1):
                            for oy in range(-stroke_w, stroke_w + 1):
                                draw.multiline_text((pos_x + ox, pos_y + oy), rendered_text, font=font, fill="black", align="center")

                        draw.multiline_text((pos_x, pos_y), rendered_text, font=font, fill=sub_color, align="center")
                        return np.array(img)

                    final_video_clip = composed_base_video.fl_image(add_subtitle_to_frame)
                else:
                    final_video_clip = composed_base_video

                # 5. Xuất video MP4
                progress_bar.progress(80, text="⏳ Bước 4/4: Đang encode video MP4 hoàn thiện...")
                out_vid_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                
                final_video_clip.write_videofile(
                    out_vid_path,
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    preset="ultrafast",   # Dùng preset ultrafast để encode cực nhanh, tiết kiệm RAM
                    threads=2,
                    logger=None
                )
                
                # Đóng các clip để giải phóng tài nguyên
                audio_clip.close()
                final_video_clip.close()
                
                progress_bar.progress(100, text="✅ Hoàn tất!")
                
                # Đọc dữ liệu video vào bộ nhớ để hiển thị chắc chắn 100%
                with open(out_vid_path, "rb") as vf:
                    video_bytes = vf.read()
                
                st.success("🎉 Video của bạn đã render hoàn tất thành công!")
                st.video(video_bytes)
                
                st.download_button(
                    label="⬇️ BẤM VÀO ĐÂY ĐỂ TẢI VIDEO (MP4)",
                    data=video_bytes,
                    file_name="ai_production_video.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )
            except Exception as prod_err:
                progress_bar.empty()
                st.error(f"❌ Xảy ra lỗi trong quá trình dựng video: {prod_err}")
