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
    VideoFileClip,
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

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1976D2;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .scene-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        height: 3em;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. THANH CÔNG CỤ SIDEBAR
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/video-editing.png", width=110)
    st.title("⚙️ TRUNG TÂM ĐIỀU KHIỂN")
    
    st.markdown("### 🔌 Kết Nối Máy Chủ GPU")
    server_url = st.text_input(
        "GPU Server URL (Cloudflare / Ngrok):",
        value="",
        placeholder="https://xxxx.trycloudflare.com hoặc https://xxxx.ngrok-free.app",
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
        if st.button("🧹 Reset App", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.markdown("---")
    st.markdown("### 🔑 Khóa Google AI Studio")
    gemini_key = st.text_input(
        "Gemini API Key:",
        type="password",
        value="",
        help="Nhập API Key để mở khóa trợ lý viết kịch bản thông minh."
    )
    
    st.markdown("---")
    menu_choice = st.radio(
        "📌 CHỌN TÍNH NĂNG HOẠT ĐỘNG:",
        [
            "1. 🎭 Diễn Hoạt Biểu Cảm (LivePortrait GPU)",
            "2. 🎙️ Phòng Thu Giọng Nói AI (Edge-TTS)",
            "3. ✨ Trợ Lý Viết Kịch Bản Phân Cảnh (Gemini)",
            "4. 🎞️ Sản Xuất Video Phân Cảnh (Ảnh & Video Clip)"
        ]
    )

# ==============================================================================
# HÀM BỔ TRỢ GEMINI VỚI MULTI-MODEL AUTO FALLBACK
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
        raise Exception("Mô hình không trả về nội dung.")

# ==============================================================================
# 1. LIVEPORTRAIT GPU
# ==============================================================================
if menu_choice == "1. 🎭 Diễn Hoạt Biểu Cảm (LivePortrait GPU)":
    st.markdown('<div class="main-header">🎭 Diễn Hoạt Cử Động Biểu Cảm Khuôn Mặt (LivePortrait)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Đồng bộ chính xác biểu cảm mắt, khuôn mày, cơ mặt và khẩu hình môi từ video mẫu sang ảnh chân dung bằng Kaggle GPU.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 1. Ảnh Chân Dung Nguồn (Source Image)")
        img_file = st.file_uploader("Tải lên ảnh chân dung sắc nét:", type=["jpg", "jpeg", "png"], key="lp_source_img")
        if img_file:
            st.image(img_file, caption="Ảnh chân dung đã chọn", use_container_width=True)

    with col2:
        st.markdown("#### 2. Video Mẫu Biểu Cảm (Driving Video)")
        vid_file = st.file_uploader("Tải lên video mẫu cử động (3-10 giây):", type=["mp4", "mov", "avi"], key="lp_drive_vid")
        if vid_file:
            st.video(vid_file)

    st.markdown("#### ⚙️ Cấu Hình Thuật Toán LivePortrait")
    with st.expander("Bấm để mở tùy chỉnh nâng cao", expanded=True):
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1:
            lp_flag_eye = st.checkbox("Đồng bộ cử động mắt (Eye Retargeting)", value=True)
            lp_flag_lip = st.checkbox("Đồng bộ khẩu hình môi (Lip Retargeting)", value=True)
        with c_p2:
            lp_flag_head = st.checkbox("Khớp chuyển động xoay đầu (Head Pose)", value=True)
            lp_smooth = st.slider("Độ mượt mà (Smoothing Factor):", min_value=1, max_value=10, value=5)
        with c_p3:
            lp_crop_mode = st.selectbox("Khung hình kết quả:", ["Tập trung khuôn mặt (Face Crop)", "Toàn ảnh gốc (Full Image)"])

    if st.button("🎬 BẮT ĐẦU XUẤT VIDEO BIỂU CẢM", type="primary", use_container_width=True):
        if not img_file or not vid_file:
            st.warning("⚠️ Vui lòng tải lên cả ẢNH NGUỒN và VIDEO MẪU BIỂU CẢM.")
        elif not server_url.strip():
            st.error("❌ Vui lòng cung cấp link GPU Server URL ở cột điều khiển bên trái.")
        else:
            with st.spinner("⏳ Đang gửi dữ liệu tới Kaggle GPU và render..."):
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
                    st.error(f"❌ Không thể kết nối tới GPU Server: {req_err}")

# ==============================================================================
# 2. EDGE-TTS STUDIO
# ==============================================================================
elif menu_choice == "2. 🎙️ Phòng Thu Giọng Nói AI (Edge-TTS)":
    st.markdown('<div class="main-header">🎙️ Phòng Thu Giọng Nói Chuẩn AI (Edge-TTS Studio)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Chuyển đổi văn bản thành giọng đọc tự nhiên, hỗ trợ đa vùng miền và đầy đủ các ngôn ngữ phổ biến.</div>', unsafe_allow_html=True)

    tts_text = st.text_area(
        "Nhập nội dung văn bản cần đọc:",
        height=180,
        value="Chào mừng bạn đến với hệ thống AI Creative Studio. Mọi kịch bản của bạn đều được chuyển đổi thành giọng đọc truyền cảm và sống động nhất."
    )

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
            "🇯🇵 ja-JP-NanamiNeural (Nữ - Nhật Bản)": "ja-JP-NanamiNeural"
        }
        selected_voice_label = st.selectbox("Chọn giọng đọc:", list(voice_dict.keys()))
        selected_voice = voice_dict[selected_voice_label]

    with col_t2:
        voice_rate = st.slider("Tốc độ phát âm (%):", min_value=-50, max_value=50, value=0, step=5)
        rate_str = f"{'+' if voice_rate >= 0 else ''}{voice_rate}%"

    with col_t3:
        voice_pitch = st.slider("Cao độ thanh âm (Hz):", min_value=-30, max_value=30, value=0, step=5)
        pitch_str = f"{'+' if voice_pitch >= 0 else ''}{voice_pitch}Hz"

    if st.button("🔊 TẠO GIỌNG ĐỌC NGAY", type="primary", use_container_width=True):
        if not tts_text.strip():
            st.warning("⚠️ Vui lòng nhập nội dung văn bản.")
        else:
            with st.spinner("Đang tổng hợp âm thanh..."):
                try:
                    async def run_edge_tts():
                        communicate = edge_tts.Communicate(tts_text, selected_voice, rate=rate_str, pitch=pitch_str)
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                        await communicate.save(temp_file.name)
                        return temp_file.name
                    
                    audio_res_path = asyncio.run(run_edge_tts())
                    st.success("🎉 Tạo âm thanh thành công!")
                    st.audio(audio_res_path)
                    
                    with open(audio_res_path, "rb") as af:
                        st.download_button(
                            label="⬇️ TẢI FILE MP3",
                            data=af.read(),
                            file_name="tts_voice_output.mp3",
                            mime="audio/mp3",
                            use_container_width=True
                        )
                except Exception as tts_err:
                    st.error(f"❌ Lỗi xử lý âm thanh: {tts_err}")

# ==============================================================================
# 3. TRỢ LÝ VIẾT KỊCH BẢN PHÂN CẢNH GEMINI
# ==============================================================================
elif menu_choice == "3. ✨ Trợ Lý Viết Kịch Bản Phân Cảnh (Gemini)":
    st.markdown('<div class="main-header">✨ Trợ Lý Sáng Tạo Kịch Bản Phân Cảnh (Gemini Studio)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Tự động biên soạn kịch bản chia rõ từng công đoạn/phân cảnh (Scene 1, Scene 2, Scene 3...) để dễ dàng ghép ảnh hoặc video tương ứng.</div>', unsafe_allow_html=True)

    col_g1, col_g2 = st.columns([2, 1])
    with col_g1:
        topic_input = st.text_input("Chủ đề video của bạn:", value="Quy trình 3 bước tái tạo năng lượng mỗi buổi sáng")
    with col_g2:
        num_scenes = st.slider("Số lượng phân cảnh (Scenes):", min_value=2, max_value=8, value=3)

    col_g3, col_g4 = st.columns(2)
    with col_g3:
        genre_option = st.selectbox(
            "Thể loại kịch bản:",
            ["Truyền cảm hứng & Động lực", "Hài hước & Viral", "Tin tức & Phân tích", "Review & Hướng dẫn", "Kể chuyện ngắn"]
        )
    with col_g4:
        target_audience = st.selectbox("Đối tượng khán giả:", ["Mọi lứa tuổi", "Gen Z & Học sinh - Sinh viên", "Dân công sở / Kinh doanh", "Gia đình"])

    if st.button("✨ TẠO KỊCH BẢN CHIA PHÂN CẢNH BẰNG GEMINI", type="primary", use_container_width=True):
        if not gemini_key.strip():
            st.error("❌ Vui lòng nhập Gemini API Key ở cột điều khiển bên trái.")
        else:
            with st.spinner("Gemini đang thiết kế kịch bản từng phân cảnh..."):
                try:
                    prompt = f"""
                    Bạn là một đạo diễn kiêm biên kịch video chuyên nghiệp.
                    Hãy viết kịch bản video ngắn về chủ đề: "{topic_input}".
                    - Thể loại: {genre_option}
                    - Khán giả: {target_audience}
                    - Hãy chia chính xác thành đúng {num_scenes} phân cảnh theo định dạng chuẩn sau để ứng dụng đọc được:
                    
                    [Cảnh 1] Lời thoại thuyết minh của phân cảnh 1
                    [Cảnh 2] Lời thoại thuyết minh của phân cảnh 2
                    ...
                    [Cảnh {num_scenes}] Lời thoại thuyết minh của phân cảnh {num_scenes}
                    
                    Quy tắc: Mỗi cảnh viết từ 20-35 từ, lời thoại trực tiếp, truyền cảm, không kèm theo mô tả góc quay phức tạp.
                    """
                    script_result, used_model = call_gemini_smart_generator(gemini_key, prompt)
                    st.success(f"🎉 Đã tạo kịch bản {num_scenes} phân cảnh thành công bởi mô hình: {used_model}")
                    st.session_state["saved_scenes_script"] = script_result
                except Exception as e:
                    st.error(f"❌ Lỗi khi tạo kịch bản: {e}")

    generated_script = st.text_area(
        "Nội dung kịch bản phân cảnh đã tạo:",
        value=st.session_state.get("saved_scenes_script", "[Cảnh 1] Thức dậy sớm và uống ngay một ly nước ấm để đánh thức mọi cơ quan trong cơ thể.\n[Cảnh 2] Dành ra mười lăm phút vận động nhẹ nhàng giúp tinh thần sảng khoái và tràn đầy năng lượng.\n[Cảnh 3] Lập danh sách ba việc quan trọng nhất cần hoàn thành trong ngày để làm việc hiệu quả."),
        height=220
    )

# ==============================================================================
# 4. SẢN XUẤT VIDEO PHÂN CẢNH TỪNG CÔNG ĐOẠN (HỖ TRỢ CẢ ẢNH & VIDEO)
# ==============================================================================
elif menu_choice == "4. 🎞️ Sản Xuất Video Phân Cảnh (Ảnh & Video Clip)":
    st.markdown('<div class="main-header">🎞️ Sản Xuất Video Phân Cảnh (Hỗ Trợ Cả Ảnh & Video Clip)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Mỗi phân cảnh cho phép tải lên <b>Hình ảnh</b> hoặc <b>Video ngắn</b> kèm lời thuyết minh riêng. Hệ thống tự động căn chỉnh thời lượng khớp 100% với giọng đọc AI.</div>', unsafe_allow_html=True)

    # 1. Cấu hình chung
    st.markdown("### ⚙️ 1. Cấu Hình Chung Cho Toàn Bộ Video")
    col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
    with col_cfg1:
        prod_voice_choice = st.selectbox(
            "Giọng đọc thuyết minh:",
            ["vi-VN-NamMinhNeural (Nam - Miền Bắc)", "vi-VN-HoaiMyNeural (Nữ - Miền Bắc)", "en-US-JennyNeural (Nữ - Mỹ)", "en-US-GuyNeural (Nam - Mỹ)"]
        )
        selected_prod_voice = prod_voice_choice.split(" ")[0]
        
    with col_cfg2:
        ratio_choice = st.selectbox(
            "Tỷ lệ khung hình video:",
            ["16:9 Ngang (YouTube, Facebook, Web)", "9:16 Dọc (TikTok, Shorts, Reels)", "1:1 Vuông (Instagram Post)"]
        )
        
    with col_cfg3:
        motion_effect = st.selectbox(
            "Hiệu ứng chuyển động (Chỉ áp dụng với Ảnh):",
            ["Không sử dụng hiệu ứng", "Zoom In Nhẹ (Phóng to dần)", "Zoom Out Nhẹ (Thu nhỏ dần)"]
        )

    col_sub1, col_sub2 = st.columns(2)
    with col_sub1:
        sub_toggle = st.checkbox("Chèn phụ đề tiếng Việt tự động cho từng cảnh", value=True)
    with col_sub2:
        if sub_toggle:
            sub_font_size = st.slider("Cỡ chữ phụ đề:", min_value=20, max_value=50, value=30, step=2)
            sub_color = st.color_picker("Màu sắc chữ phụ đề:", "#FFE600")

    st.markdown("---")
    st.markdown("### 🎬 2. Thiết Lập Từng Phân Cảnh (Tải Ảnh Hoặc Video Clip)")

    if "num_scenes_count" not in st.session_state:
        st.session_state["num_scenes_count"] = 3

    col_btn_sc1, col_btn_sc2 = st.columns([1, 4])
    with col_btn_sc1:
        if st.button("➕ Thêm Phân Cảnh"):
            st.session_state["num_scenes_count"] += 1
            st.rerun()
    with col_btn_sc2:
        if st.session_state["num_scenes_count"] > 1:
            if st.button("➖ Giảm Phân Cảnh"):
                st.session_state["num_scenes_count"] -= 1
                st.rerun()

    scenes_data = []
    default_texts = [
        "Thức dậy sớm và uống một ly nước ấm để đánh thức mọi giác quan trong cơ thể.",
        "Dành ra mười lăm phút vận động nhẹ nhàng giúp tinh thần sảng khoái và tràn đầy năng lượng.",
        "Lập danh sách ba việc quan trọng nhất cần hoàn thành trong ngày để làm việc hiệu quả.",
        "Bắt đầu ngày mới với nụ cười và tinh thần quyết tâm chinh phục mọi thử thách."
    ]

    for i in range(st.session_state["num_scenes_count"]):
        st.markdown(f'<div class="scene-box">', unsafe_allow_html=True)
        st.markdown(f"#### 📍 Phân Cảnh {i + 1}")
        
        c_sc1, c_sc2 = st.columns([3, 2])
        with c_sc1:
            def_text = default_texts[i % len(default_texts)]
            sc_text = st.text_area(f"Lời thuyết minh phân cảnh {i + 1}:", value=def_text, key=f"sc_text_{i}", height=100)
        with c_sc2:
            # Cho phép upload cả ảnh và video
            sc_media = st.file_uploader(
                f"Tải Ảnh hoặc Video cho cảnh {i + 1}:",
                type=["jpg", "jpeg", "png", "mp4", "mov", "avi"],
                key=f"sc_media_{i}"
            )
            if sc_media:
                if sc_media.type.startswith("image"):
                    st.image(sc_media, width=160, caption="Hình ảnh minh họa")
                else:
                    st.video(sc_media)
        
        scenes_data.append({"text": sc_text, "media": sc_media})
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🚀 BẮT ĐẦU SẢN XUẤT VIDEO THEO TỪNG CÔNG ĐOẠN", type="primary", use_container_width=True):
        missing_media = [idx + 1 for idx, sc in enumerate(scenes_data) if sc["media"] is None]
        empty_texts = [idx + 1 for idx, sc in enumerate(scenes_data) if not sc["text"].strip()]
        
        if missing_media:
            st.warning(f"⚠️ Vui lòng tải Ảnh hoặc Video cho các phân cảnh: {missing_media}")
        elif empty_texts:
            st.warning(f"⚠️ Vui lòng nhập lời thuyết minh cho các phân cảnh: {empty_texts}")
        else:
            progress_bar = st.progress(0, text="⏳ Đang chuẩn bị các công đoạn...")
            try:
                if "16:9" in ratio_choice:
                    target_w, target_h = 1280, 720
                elif "9:16" in ratio_choice:
                    target_w, target_h = 720, 1280
                else:
                    target_w, target_h = 720, 720

                scene_video_clips = []
                total_scenes = len(scenes_data)

                for idx, scene in enumerate(scenes_data):
                    pct = int(10 + (idx / total_scenes) * 70)
                    progress_bar.progress(pct, text=f"⏳ Đang xử lý Phân Cảnh {idx + 1}/{total_scenes}...")

                    # 1. Tạo audio cho phân cảnh
                    comm = edge_tts.Communicate(scene["text"], selected_prod_voice)
                    t_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    asyncio.run(comm.save(t_audio.name))
                    sc_audio_clip = AudioFileClip(t_audio.name)
                    sc_duration = sc_audio_clip.duration

                    # 2. Xử lý Ảnh hoặc Video tải lên
                    uploaded_file = scene["media"]
                    is_video = uploaded_file.type.startswith("video") or uploaded_file.name.lower().endswith((".mp4", ".mov", ".avi"))

                    if is_video:
                        # Lưu video tạm
                        t_vid = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                        t_vid.write(uploaded_file.getvalue())
                        t_vid.close()

                        raw_vid = VideoFileClip(t_vid.name)
                        # Cắt hoặc lặp để vừa khít thời lượng giọng đọc
                        if raw_vid.duration < sc_duration:
                            loop_count = math.ceil(sc_duration / raw_vid.duration)
                            raw_vid = concatenate_videoclips([raw_vid] * loop_count)
                        
                        raw_vid = raw_vid.subclip(0, sc_duration).resize(newsize=(target_w, target_h))
                        sc_composed = raw_vid.set_audio(sc_audio_clip)
                    else:
                        # Xử lý hình ảnh
                        pil_img = Image.open(uploaded_file).convert("RGB")
                        pil_img = pil_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                        t_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                        pil_img.save(t_img.name, "JPEG", quality=90)
                        t_img.close()

                        sc_img_clip = ImageClip(t_img.name).set_duration(sc_duration)

                        if motion_effect == "Zoom In Nhẹ (Phóng to dần)":
                            sc_img_clip = sc_img_clip.fx(vfx.resize, lambda t: 1.0 + 0.04 * (t / sc_duration))
                        elif motion_effect == "Zoom Out Nhẹ (Thu nhỏ dần)":
                            sc_img_clip = sc_img_clip.fx(vfx.resize, lambda t: 1.04 - 0.04 * (t / sc_duration))

                        sc_composed = sc_img_clip.set_audio(sc_audio_clip)

                    # 3. Chèn phụ đề riêng cho phân cảnh
                    if sub_toggle:
                        current_sub_text = scene["text"].replace("\n", " ")

                        def make_sub_frame(frame, txt=current_sub_text):
                            img = Image.fromarray(frame)
                            draw = ImageDraw.Draw(img)
                            try:
                                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", sub_font_size)
                            except Exception:
                                try:
                                    font = ImageFont.truetype("arial.ttf", sub_font_size)
                                except Exception:
                                    font = ImageFont.load_default()

                            max_chars = max(10, int(target_w / (sub_font_size * 0.65)))
                            words = txt.split()
                            lines = []
                            cur = []
                            for w in words:
                                cur.append(w)
                                if len(" ".join(cur)) > max_chars:
                                    lines.append(" ".join(cur[:-1]))
                                    cur = [w]
                            if cur:
                                lines.append(" ".join(cur))

                            rendered_txt = "\n".join(lines)
                            bbox = draw.multiline_textbbox((0, 0), rendered_txt, font=font, align="center")
                            text_w = bbox[2] - bbox[0]
                            text_h = bbox[3] - bbox[1]
                            pos_x = (target_w - text_w) // 2
                            pos_y = target_h - text_h - 50

                            for ox in range(-2, 3):
                                for oy in range(-2, 3):
                                    draw.multiline_text((pos_x + ox, pos_y + oy), rendered_txt, font=font, fill="black", align="center")

                            draw.multiline_text((pos_x, pos_y), rendered_txt, font=font, fill=sub_color, align="center")
                            return np.array(img)

                        sc_final_clip = sc_composed.fl_image(make_sub_frame)
                    else:
                        sc_final_clip = sc_composed

                    scene_video_clips.append(sc_final_clip)

                # 4. Nối tất cả các phân cảnh
                progress_bar.progress(85, text="⏳ Đang ghép nối các phân cảnh thành video hoàn chỉnh...")
                final_full_video = concatenate_videoclips(scene_video_clips, method="compose")

                out_vid_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                final_full_video.write_videofile(
                    out_vid_path,
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    preset="ultrafast",
                    threads=2,
                    logger=None
                )

                progress_bar.progress(100, text="✅ Render thành công tất cả các phân cảnh!")

                with open(out_vid_path, "rb") as vf:
                    final_bytes = vf.read()

                st.success("🎉 Video hoàn chỉnh từ các phân cảnh (Ảnh/Video) đã xuất bản thành công!")
                st.video(final_bytes)

                st.download_button(
                    label="⬇️ TẢI VIDEO HOÀN CHỈNH (MP4)",
                    data=final_bytes,
                    file_name="multi_scene_final_video.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )
            except Exception as e:
                progress_bar.empty()
                st.error(f"❌ Xảy ra lỗi trong quá trình sản xuất video phân cảnh: {e}")
