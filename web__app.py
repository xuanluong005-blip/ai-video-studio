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

# ==============================================================================
# BẢN VÁ TƯƠNG THÍCH PILLOW CHO MOVIEPY (TRÁNH LỖI ANTIALIAS)
# ==============================================================================
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS

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
# 1. CẤU HÌNH GIAO DIỆN & TỐI ƯU GIAO DIỆN STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="AI Creative Studio Super Pro Max",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 800;
        color: #1976D2;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        height: 3em;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        border-color: #1976D2;
        color: #1976D2;
    }
    .status-card {
        padding: 12px 18px;
        border-radius: 8px;
        background-color: #F3F4F6;
        border-left: 5px solid #1976D2;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. THANH CÔNG CỤ SIDEBAR & CẤU HÌNH KẾT NỐI
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/video-editing.png", width=110)
    st.title("⚙️ TRUNG TÂM ĐIỀU KHIỂN")
    
    st.markdown("### 🔌 Kết Nối Máy Chủ GPU")
    server_url = st.text_input(
        "GPU Server URL (Cloudflare / Ngrok):",
        value="",
        placeholder="https://xxxx.trycloudflare.com hoặc https://xxxx.ngrok-free.app",
        help="Dán URL tunnel được cung cấp từ phiên chạy Kaggle Notebook vào đây."
    )
    
    col_ping1, col_ping2 = st.columns([1, 1])
    with col_ping1:
        if st.button("🔍 Kiểm Tra GPU", use_container_width=True):
            if not server_url.strip():
                st.warning("Chưa nhập link GPU!")
            else:
                with st.spinner("Đang ping..."):
                    try:
                        headers = {
                            "User-Agent": "Mozilla/5.0",
                            "ngrok-skip-browser-warning": "true",
                            "Bypass-Tunnel-Reminder": "true"
                        }
                        test_res = requests.get(server_url.strip().rstrip('/'), headers=headers, timeout=10)
                        if test_res.status_code == 200:
                            st.success("🟢 GPU Online!")
                        else:
                            st.warning(f"🟡 Phản hồi: {test_res.status_code}")
                    except Exception as err:
                        st.error(f"🔴 Mất kết nối: {err}")

    with col_ping2:
        if st.button("🧹 Xóa Bộ Nhớ", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.markdown("---")
    st.markdown("### 🔑 Khóa Google AI Studio")
    gemini_key = st.text_input(
        "Gemini API Key:",
        type="password",
        value="",
        help="Nhập API Key để kích hoạt tính năng viết kịch bản thông minh."
    )
    
    st.markdown("---")
    menu_choice = st.radio(
        "📌 CHỌN PHÂN HỆ LÀM VIỆC:",
        [
            "1. 🎭 Diễn Hoạt Biểu Cảm (LivePortrait GPU)",
            "2. 🎙️ Phòng Thu Giọng Nói AI (Edge-TTS)",
            "3. ✨ Trợ Lý Viết Kịch Bản AI (Gemini Studio)",
            "4. 🎞️ Xưởng Sản Xuất Video Toàn Diện (All-In-One)"
        ]
    )

# ==============================================================================
# HÀM BỔ TRỢ: TỰ ĐỘNG BẮT ĐÚNG MODEL GEMINI TƯƠNG THÍCH
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
        "models/gemini-1.5-flash-latest",
        "models/gemini-1.5-flash",
        "models/gemini-1.5-pro",
        "gemini-3.6-flash",
        "gemini-1.5-flash",
        "gemini-pro"
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
# PHÂN HỆ 1: LIVEPORTRAIT (GPU SERVER)
# ==============================================================================
if menu_choice == "1. 🎭 Diễn Hoạt Biểu Cảm (LivePortrait GPU)":
    st.markdown('<div class="main-header">🎭 Diễn Hoạt Cử Động Biểu Cảm Khuôn Mặt (LivePortrait)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Đồng bộ chính xác biểu cảm mắt, khuôn mày, cơ mặt và khẩu hình môi từ video mẫu sang hình ảnh chân dung tĩnh.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 1. Ảnh Chân Dung Gốc (Source Image)")
        img_file = st.file_uploader("Tải lên ảnh chân dung sắc nét:", type=["jpg", "jpeg", "png"], key="lp_source_img")
        if img_file:
            st.image(img_file, caption="Ảnh nguồn chân dung", use_container_width=True)

    with col2:
        st.markdown("#### 2. Video Mẫu Biểu Cảm (Driving Video)")
        vid_file = st.file_uploader("Tải lên video cử động mẫu (Nên từ 3 đến 10 giây):", type=["mp4", "mov", "avi"], key="lp_drive_vid")
        if vid_file:
            st.video(vid_file)

    st.markdown("#### ⚙️ Cấu Hình Thuật Toán LivePortrait")
    with st.expander("Bấm để tùy chỉnh các tham số nâng cao", expanded=True):
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1:
            lp_flag_eye = st.checkbox("Đồng bộ nhắm/mở mắt (Eye Retargeting)", value=True)
            lp_flag_lip = st.checkbox("Đồng bộ khẩu hình môi (Lip Retargeting)", value=True)
        with c_p2:
            lp_flag_head = st.checkbox("Khớp chuyển động xoay đầu (Head Pose)", value=True)
            lp_smooth = st.slider("Độ mượt mà chuyển động (Smoothing Factor):", min_value=1, max_value=10, value=5)
        with c_p3:
            lp_crop_mode = st.selectbox("Phạm vi khung hình kết quả:", ["Cắt khuôn mặt (Face Crop)", "Toàn ảnh gốc (Full Image)"])

    if st.button("🎬 BẮT ĐẦU XUẤT VIDEO BIỂU CẢM", type="primary", use_container_width=True):
        if not img_file or not vid_file:
            st.warning("⚠️ Vui lòng tải lên cả ẢNH NGUỒN và VIDEO MẪU BIỂU CẢM.")
        elif not server_url.strip():
            st.error("❌ Vui lòng cung cấp link GPU Server URL ở cột điều khiển bên trái.")
        else:
            with st.spinner("⏳ Đang truyền dữ liệu sang máy chủ Kaggle GPU và tiến hành render... (Vui lòng chờ khoảng 30–90 giây)"):
                try:
                    target_endpoint = f"{server_url.strip().rstrip('/')}/process"
                    files = {
                        "image": (img_file.name, img_file.getvalue(), img_file.type or "image/jpeg"),
                        "video": (vid_file.name, vid_file.getvalue(), vid_file.type or "video/mp4")
                    }
                    headers = {
                        "User-Agent": "Mozilla/5.0",
                        "ngrok-skip-browser-warning": "true",
                        "Bypass-Tunnel-Reminder": "true"
                    }
                    
                    response = requests.post(target_endpoint, files=files, headers=headers, timeout=600)
                    
                    if response.status_code == 200:
                        st.success("🎉 Xuất video biểu cảm LivePortrait thành công!")
                        st.video(response.content)
                        st.download_button(
                            label="⬇️ TẢI VIDEO THÀNH PHẨM (MP4)",
                            data=response.content,
                            file_name="liveportrait_animated_result.mp4",
                            mime="video/mp4",
                            use_container_width=True
                        )
                    else:
                        st.error(f"❌ Máy chủ GPU báo lỗi (Mã {response.status_code}):")
                        try:
                            st.json(response.json())
                        except Exception:
                            st.write(response.text)
                except requests.exceptions.RequestException as req_err:
                    st.error(f"❌ Không thể kết nối tới GPU Server. Chi tiết: {req_err}")

# ==============================================================================
# PHÂN HỆ 2: EDGE-TTS STUDIO (PHÒNG THU GIỌNG NÓI ĐA NGÔN NGỮ)
# ==============================================================================
elif menu_choice == "2. 🎙️ Phòng Thu Giọng Nói AI (Edge-TTS)":
    st.markdown('<div class="main-header">🎙️ Phòng Thu Giọng Nói Chuẩn AI (Edge-TTS Studio)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Chuyển văn bản thành giọng đọc tự nhiên với đầy đủ hệ thống giọng đọc vùng miền và đa ngôn ngữ quốc tế.</div>', unsafe_allow_html=True)

    tts_text = st.text_area(
        "Nhập nội dung kịch bản văn bản cần chuyển thành giọng đọc:",
        height=180,
        value="Chào mừng bạn đến với hệ thống AI Creative Studio. Mọi kịch bản của bạn đều được chuyển đổi thành giọng đọc truyền cảm và sống động nhất."
    )

    st.markdown("#### 🎛️ Bảng Điều Khiển Âm Thanh & Giọng Đọc")
    col_t1, col_t2, col_t3 = st.columns(3)
    
    with col_t1:
        voice_dict = {
            "🇻🇳 vi-VN-NamMinhNeural (Nam - Miền Bắc)": "vi-VN-NamMinhNeural",
            "🇻🇳 vi-VN-HoaiMyNeural (Nữ - Miền Bắc)": "vi-VN-HoaiMyNeural",
            "🇺🇸 en-US-GuyNeural (Nam - Mỹ)": "en-US-GuyNeural",
            "🇺🇸 en-US-JennyNeural (Nữ - Mỹ)": "en-US-JennyNeural",
            "🇬🇧 en-GB-RyanNeural (Nam - Anh)": "en-GB-RyanNeural",
            "🇬🇧 en-GB-SoniaNeural (Nữ - Anh)": "en-GB-SoniaNeural",
            "🇨🇳 zh-CN-YunxiNeural (Nam - Trung Quốc)": "zh-CN-YunxiNeural",
            "🇨🇳 zh-CN-XiaoxiaoNeural (Nữ - Trung Quốc)": "zh-CN-XiaoxiaoNeural",
            "🇯🇵 ja-JP-KeitaNeural (Nam - Nhật Bản)": "ja-JP-KeitaNeural",
            "🇯🇵 ja-JP-NanamiNeural (Nữ - Nhật Bản)": "ja-JP-NanamiNeural",
            "🇰🇷 ko-KR-InJoonNeural (Nam - Hàn Quốc)": "ko-KR-InJoonNeural",
            "🇫🇷 fr-FR-HenriNeural (Nam - Pháp)": "fr-FR-HenriNeural"
        }
        selected_voice_label = st.selectbox("Chọn nhân vật giọng đọc:", list(voice_dict.keys()))
        selected_voice = voice_dict[selected_voice_label]

    with col_t2:
        voice_rate = st.slider("Tốc độ phát âm (Speed Rate %):", min_value=-50, max_value=50, value=0, step=5)
        rate_str = f"{'+' if voice_rate >= 0 else ''}{voice_rate}%"

    with col_t3:
        voice_pitch = st.slider("Cao độ thanh âm (Pitch Hz):", min_value=-30, max_value=30, value=0, step=5)
        pitch_str = f"{'+' if voice_pitch >= 0 else ''}{voice_pitch}Hz"

    if st.button("🔊 TỔNG HỢP ÂM THANH NGAY", type="primary", use_container_width=True):
        if not tts_text.strip():
            st.warning("⚠️ Vui lòng nhập nội dung văn bản.")
        else:
            with st.spinner("Đang tổng hợp giọng nói chất lượng cao..."):
                try:
                    async def run_edge_tts():
                        communicate = edge_tts.Communicate(tts_text, selected_voice, rate=rate_str, pitch=pitch_str)
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                        await communicate.save(temp_file.name)
                        return temp_file.name
                    
                    audio_res_path = asyncio.run(run_edge_tts())
                    st.success("🎉 Đã tạo giọng nói thành công!")
                    st.audio(audio_res_path)
                    
                    with open(audio_res_path, "rb") as af:
                        st.download_button(
                            label="⬇️ TẢI FILE ÂM THANH (MP3)",
                            data=af.read(),
                            file_name="tts_voice_output.mp3",
                            mime="audio/mp3",
                            use_container_width=True
                        )
                except Exception as tts_err:
                    st.error(f"❌ Lỗi xử lý âm thanh: {tts_err}")

# ==============================================================================
# PHÂN HỆ 3: TRỢ LÝ VIẾT KỊCH BẢN GEMINI STUDIO
# ==============================================================================
elif menu_choice == "3. ✨ Trợ Lý Viết Kịch Bản AI (Gemini Studio)":
    st.markdown('<div class="main-header">✨ Trợ Lý Sáng Tạo Kịch Bản AI (Gemini Studio)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Tự động biên soạn nội dung video ngắn, kịch bản quảng cáo, tóm tắt tin tức hay bài học truyền động lực.</div>', unsafe_allow_html=True)

    col_g1, col_g2 = st.columns([2, 1])
    with col_g1:
        topic_input = st.text_input("Chủ đề video muốn sáng tạo:", value="5 bài học đắt giá về sự kỷ luật bản thân")
    with col_g2:
        genre_option = st.selectbox(
            "Thể loại kịch bản:",
            [
                "Truyền cảm hứng & Động lực sống",
                "Hài hước & Viral giải trí",
                "Tin tức & Phân tích tổng hợp",
                "Review & Giới thiệu tính năng",
                "Kể chuyện & Triết lý sâu sắc"
            ]
        )

    col_g3, col_g4 = st.columns(2)
    with col_g3:
        target_audience = st.selectbox("Khán giả mục tiêu:", ["Mọi lứa tuổi", "Gen Z & Học sinh - Sinh viên", "Dân công sở / Doanh nhân", "Gia đình & Phụ huynh"])
    with col_g4:
        word_count = st.slider("Số lượng từ mong muốn (khoảng):", min_value=50, max_value=400, value=120, step=10)

    if st.button("✨ BẮT ĐẦU TẠO KỊCH BẢN BẰNG GEMINI", type="primary", use_container_width=True):
        if not gemini_key.strip():
            st.error("❌ Vui lòng nhập Gemini API Key ở thanh sidebar bên trái để sử dụng chức năng này.")
        else:
            with st.spinner("Gemini đang phân tích và sáng tác kịch bản..."):
                try:
                    prompt = f"""
                    Bạn là một biên kịch video ngắn chuyên nghiệp.
                    Hãy viết kịch bản thuyết minh cho video ngắn về chủ đề: "{topic_input}".
                    - Thể loại: {genre_option}
                    - Đối tượng người xem: {target_audience}
                    - Độ dài yêu cầu: Khoảng {word_count} từ.
                    - Quy tắc quan trọng: Chỉ viết nội dung lời đọc trực tiếp mạch lạc, giàu cảm xúc, không kèm theo các ghi chú đạo diễn hay ký hiệu dư thừa để người dùng có thể chuyển thẳng sang giọng đọc AI.
                    """
                    script_result, used_model = call_gemini_smart_generator(gemini_key, prompt)
                    st.success(f"🎉 Kịch bản đã được khởi tạo thành công bởi mô hình: {used_model}")
                    st.session_state["saved_script"] = script_result
                except Exception as e:
                    st.error(f"❌ Lỗi khi gọi Gemini: {e}")

    generated_script = st.text_area(
        "Nội dung kịch bản đã tạo (Có thể tùy biến sửa chữa trực tiếp):",
        value=st.session_state.get("saved_script", ""),
        height=220
    )

# ==============================================================================
# PHÂN HỆ 4: XƯỞNG SẢN XUẤT VIDEO TOÀN DIỆN (ALL-IN-ONE)
# ==============================================================================
elif menu_choice == "4. 🎞️ Xưởng Sản Xuất Video Toàn Diện (All-In-One)":
    st.markdown('<div class="main-header">🎞️ Xưởng Sản Xuất Video Toàn Diện (All-In-One Studio)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Tự động liên kết kịch bản văn bản, giọng đọc AI, hình ảnh minh họa, hiệu ứng Ken Burns và phụ đề tiếng Việt thành video MP4 sắc nét.</div>', unsafe_allow_html=True)

    st.markdown("### 📝 Bước 1: Kịch Bản Thuyết Minh & Giọng Đọc")
    col_v1, col_v2 = st.columns([2, 1])
    with col_v1:
        prod_script = st.text_area(
            "Nội dung kịch bản video:",
            value="Hành trình vạn dặm luôn bắt đầu từ một bước chân đầu tiên. Hãy kiên trì theo đuổi đam mê, thành công nhất định sẽ mỉm cười với bạn.",
            height=130
        )
    with col_v2:
        prod_voice_choice = st.selectbox(
            "Giọng đọc thuyết minh:",
            [
                "vi-VN-NamMinhNeural (Nam - Miền Bắc)",
                "vi-VN-HoaiMyNeural (Nữ - Miền Bắc)",
                "en-US-JennyNeural (Nữ - Mỹ)",
                "en-US-GuyNeural (Nam - Mỹ)"
            ]
        )
        selected_prod_voice = prod_voice_choice.split(" ")[0]

    st.markdown("---")
    st.markdown("### 🖼️ Bước 2: Tải Lên Danh Sách Ảnh Minh Họa")
    uploaded_imgs = st.file_uploader(
        "Tải lên các hình ảnh (Hệ thống sẽ tự động căn chỉnh thời lượng mỗi ảnh khớp 100% với giọng đọc):",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    st.markdown("---")
    st.markdown("### ⚙️ Bước 3: Định Dạng Video, Chuyển Cảnh & Phụ Đề")
    col_c1, col_c2, col_c3 = st.columns(3)
    
    with col_c1:
        ratio_choice = st.selectbox(
            "Tỷ lệ khung hình video:",
            [
                "16:9 Ngang (YouTube, Web)",
                "9:16 Dọc (TikTok, Shorts, Reels)",
                "1:1 Vuông (Instagram Post)"
            ]
        )
    
    with col_c2:
        motion_effect = st.selectbox(
            "Hiệu ứng chuyển động (Ken Burns):",
            [
                "Không sử dụng hiệu ứng",
                "Zoom In Nhẹ (Phóng to dần)",
                "Zoom Out Nhẹ (Thu nhỏ dần)"
            ]
        )
        
    with col_c3:
        sub_toggle = st.checkbox("Chèn phụ đề tiếng Việt tự động", value=True)
        if sub_toggle:
            sub_font_size = st.slider("Cỡ chữ phụ đề:", min_value=20, max_value=60, value=32, step=2)
            sub_color = st.color_picker("Màu sắc chữ phụ đề:", "#FFE600")

    st.markdown("---")
    if st.button("🎬 BẮT ĐẦU SẢN XUẤT VIDEO TỰ ĐỘNG", type="primary", use_container_width=True):
        if not prod_script.strip():
            st.warning("⚠️ Vui lòng nhập nội dung kịch bản thuyết minh.")
        elif not uploaded_imgs:
            st.warning("⚠️ Vui lòng tải lên ít nhất 1 hình ảnh minh họa.")
        else:
            progress_bar = st.progress(0, text="⏳ Bước 1/4: Đang tạo giọng đọc AI...")
            try:
                # 1. Tạo âm thanh giọng đọc bằng Edge-TTS
                comm = edge_tts.Communicate(prod_script, selected_prod_voice)
                temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                asyncio.run(comm.save(temp_audio_file.name))
                
                audio_clip = AudioFileClip(temp_audio_file.name)
                total_duration = audio_clip.duration
                
                # 2. Xác định độ phân giải video
                progress_bar.progress(25, text="⏳ Bước 2/4: Đang tối ưu hóa hình ảnh...")
                if "16:9" in ratio_choice:
                    target_w, target_h = 1280, 720
                elif "9:16" in ratio_choice:
                    target_w, target_h = 720, 1280
                else:
                    target_w, target_h = 720, 720

                # 3. Chuẩn hóa hình ảnh bằng PIL trước để giải phóng RAM
                num_images = len(uploaded_imgs)
                duration_per_image = total_duration / num_images
                clips_list = []
                
                for idx, img_item in enumerate(uploaded_imgs):
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
                
                # 4. Thêm phụ đề tiếng Việt bằng PIL (Không phụ thuộc ImageMagick)
                progress_bar.progress(55, text="⏳ Bước 3/4: Đang dựng lớp phụ đề...")
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

                        # Vẽ viền đen sắc nét
                        stroke_w = 2
                        for ox in range(-stroke_w, stroke_w + 1):
                            for oy in range(-stroke_w, stroke_width if 'stroke_width' in locals() else 1 + 1):
                                draw.multiline_text((pos_x + ox, pos_y + oy), rendered_text, font=font, fill="black", align="center")

                        draw.multiline_text((pos_x, pos_y), rendered_text, font=font, fill=sub_color, align="center")
                        return np.array(img)

                    final_video_clip = composed_base_video.fl_image(add_subtitle_to_frame)
                else:
                    final_video_clip = composed_base_video

                # 5. Xuất video MP4 tối ưu tốc độ và dung lượng
                progress_bar.progress(80, text="⏳ Bước 4/4: Đang mã hóa file video MP4...")
                out_vid_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                
                final_video_clip.write_videofile(
                    out_vid_path,
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    preset="ultrafast",
                    threads=2,
                    logger=None
                )
                
                audio_clip.close()
                final_video_clip.close()
                
                progress_bar.progress(100, text="✅ Render thành công!")
                
                # Đọc byte trực tiếp để tránh lỗi mất file tạm trên giao diện web
                with open(out_vid_path, "rb") as vf:
                    video_bytes = vf.read()
                
                st.success("🎉 Video đã được hoàn tất thành công!")
                st.video(video_bytes)
                
                st.download_button(
                    label="⬇️ TẢI VIDEO THÀNH PHẨM (MP4)",
                    data=video_bytes,
                    file_name="ai_studio_full_production.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )
            except Exception as prod_err:
                progress_bar.empty()
                st.error(f"❌ Đã xảy ra lỗi trong quá trình render video: {prod_err}")
