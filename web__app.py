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
    
    # Nút kiểm tra nhanh trạng thái server
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
    # Danh sách các tên model tương thích cao nhất
    model_names = [
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-1.5-pro-latest",
        "gemini-1.5-pro",
        "gemini-pro"
    ]
    last_err = None
    for m in model_names:
        try:
            model = genai.GenerativeModel(m)
            response = model.generate_content(prompt_text)
            if response and response.text:
                return response.text, m
        except Exception as e:
            last_err = e
            continue
    raise Exception(f"Không thể gọi model nào trong danh sách. Lỗi cuối: {last_err}")

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

    if st.button("🎬 BẮT ĐẦU XUẤT VIDEO BIỂU CẢM", type="primary", use_container_width=True):
        if not img_file or not vid_file:
            st.warning("⚠️ Vui lòng tải lên đầy đủ cả ẢNH CHÂN DUNG và VIDEO MẪU BIỂU CẢM.")
        elif not server_url.strip():
            st.error("❌ Vui lòng nhập link kết nối GPU Server URL ở cột bên trái.")
        else:
            with st.spinner("⏳ Đang truyền dữ liệu sang máy chủ Kaggle GPU và render... (Quá trình mất 30–90 giây)"):
                try:
                    target_endpoint = f"{server_url.strip().rstrip('/')}/process"
                    
                    files = {
                        "image": (img_file.name, img_file.getvalue(), img_file.type or "image/jpeg"),
                        "video": (vid_file.name, vid_file.getvalue(), vid_file.type or "video/mp4")
                    }
                    
                    # Headers chống chặn kết nối qua Tunnel
                    headers = {
                        "User-Agent": "Mozilla/5.0",
                        "ngrok-skip-browser-warning": "true",
                        "Bypass-Tunnel-Reminder": "true"
                    }
                    
                    response = requests.post(target_endpoint, files=files, headers=headers, timeout=600)
                    
                    if response.status_code == 200:
                        st.success("🎉 Xuất video biểu cảm khuôn mặt thành công!")
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
                    st.error(f"❌ Không thể gửi yêu cầu tới máy chủ GPU. Chi tiết: {req_err}")

# ==============================================================================
# CHỨC NĂNG 2: EDGE-TTS STUDIO (PHÒNG THU GIỌNG NÓI AI)
# ==============================================================================
elif menu_choice == "2. 🎙️ Phòng Thu Giọng Nói AI (Edge-TTS)":
    st.markdown('<div class="main-header">🎙️ Phòng Thu Giọng Nói Chuẩn AI (Edge-TTS Studio)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Chuyển đổi văn bản thành giọng đọc tự nhiên, hỗ trợ đa vùng miền và đầy đủ các ngôn ngữ phổ biến.</div>', unsafe_allow_html=True)

    tts_text = st.text_area(
        "Nhập nội dung văn bản cần chuyển thành giọng đọc:",
        height=180,
        value="Chào mừng bạn đến với hệ thống AI Creative Studio. Mọi kịch bản của bạn đều được chuyển đổi thành giọng đọc truyền cảm và sống động nhất."
    )

    st.markdown("#### 🎛️ Bảng Điều Khiển Âm Thanh")
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
        selected_voice_label = st.selectbox("Chọn giọng đọc AI:", list(voice_dict.keys()))
        selected_voice = voice_dict[selected_voice_label]

    with col_t2:
        voice_rate = st.slider("Tốc độ đọc (Rate %):", min_value=-50, max_value=50, value=0, step=5)
        rate_str = f"{'+' if voice_rate >= 0 else ''}{voice_rate}%"

    with col_t3:
        voice_pitch = st.slider("Cao độ giọng (Pitch Hz):", min_value=-30, max_value=30, value=0, step=5)
        pitch_str = f"{'+' if voice_pitch >= 0 else ''}{voice_pitch}Hz"

    if st.button("🔊 TẠO GIỌNG ĐỌC AI NGAY", type="primary", use_container_width=True):
        if not tts_text.strip():
            st.warning("⚠️ Vui lòng nhập nội dung văn bản cần đọc.")
        else:
            with st.spinner("Đang xử lý tổng hợp giọng nói chất lượng cao..."):
                try:
                    async def run_edge_tts():
                        communicate = edge_tts.Communicate(tts_text, selected_voice, rate=rate_str, pitch=pitch_str)
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                        await communicate.save(temp_file.name)
                        return temp_file.name
                    
                    audio_res_path = asyncio.run(run_edge_tts())
                    st.success("🎉 Tạo giọng đọc thành công!")
                    st.audio(audio_res_path)
                    
                    with open(audio_res_path, "rb") as af:
                        st.download_button(
                            label="⬇️ TẢI FILE ÂM THANH MP3",
                            data=af.read(),
                            file_name="tts_voice_output.mp3",
                            mime="audio/mp3",
                            use_container_width=True
                        )
                except Exception as tts_err:
                    st.error(f"❌ Lỗi khi tạo giọng nói: {tts_err}")

# ==============================================================================
# CHỨC NĂNG 3: TRỢ LÝ VIẾT KỊCH BẢN GEMINI STUDIO
# ==============================================================================
elif menu_choice == "3. ✨ Trợ Lý Viết Kịch Bản AI (Gemini Studio)":
    st.markdown('<div class="main-header">✨ Trợ Lý Sáng Tạo Kịch Bản AI (Gemini Studio)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Tự động sinh kịch bản video ngắn, quảng cáo, review hoặc câu chuyện truyền cảm hứng chỉ trong vài giây.</div>', unsafe_allow_html=True)

    col_g1, col_g2 = st.columns([2, 1])
    with col_g1:
        topic_input = st.text_input("Chủ đề hoặc ý tưởng video của bạn:", value="5 thói quen buổi sáng của những người thành công")
    with col_g2:
        genre_option = st.selectbox(
            "Thể loại kịch bản:",
            [
                "Truyền cảm hứng & Động lực",
                "Hài hước & Viral giải trí",
                "Tin tức & Kiến thức tổng hợp",
                "Review & Giới thiệu sản phẩm",
                "Kể chuyện & Triết lý sâu sắc"
            ]
        )

    col_g3, col_g4 = st.columns(2)
    with col_g3:
        target_audience = st.selectbox("Đối tượng khán giả:", ["Mọi lứa tuổi", "Gen Z & Giới trẻ", "Dân văn phòng / Kinh doanh", "Phụ huynh & Gia đình"])
    with col_g4:
        word_count = st.slider("Độ dài kịch bản mong muốn (khoảng số từ):", min_value=50, max_value=400, value=120, step=10)

    if st.button("✨ BẮT ĐẦU TẠO KỊCH BẢN BẰNG GEMINI", type="primary", use_container_width=True):
        if not gemini_key.strip():
            st.error("❌ Vui lòng nhập Google Gemini API Key ở thanh điều khiển bên trái để sử dụng tính năng này.")
        else:
            with st.spinner("Gemini đang phân tích và sáng tạo kịch bản..."):
                try:
                    prompt = f"""
                    Bạn là một biên kịch video ngắn chuyên nghiệp.
                    Hãy viết kịch bản thuyết minh video ngắn về chủ đề: "{topic_input}".
                    - Thể loại: {genre_option}
                    - Khán giả mục tiêu: {target_audience}
                    - Độ dài yêu cầu: Khoảng {word_count} từ.
                    - Quy tắc quan trọng: Chỉ viết lời thuyết minh trực tiếp, mạch lạc, lôi cuốn, không chèn các chú thích đạo diễn hay ký hiệu phức tạp để có thể đọc thẳng vào công cụ TTS.
                    """
                    script_result, used_model = call_gemini_smart_generator(gemini_key, prompt)
                    st.success(f"🎉 Kịch bản đã được tạo thành công bởi mô hình: {used_model}")
                    st.session_state["saved_script"] = script_result
                except Exception as e:
                    st.error(f"❌ Lỗi khi tạo kịch bản: {e}")

    generated_script = st.text_area(
        "Nội dung kịch bản đã tạo (Có thể chỉnh sửa trực tiếp):",
        value=st.session_state.get("saved_script", ""),
        height=220
    )

# ==============================================================================
# CHỨC NĂNG 4: XƯỞNG SẢN XUẤT VIDEO ĐA NĂNG (ALL-IN-ONE)
# ==============================================================================
elif menu_choice == "4. 🎞️ Xưởng Sản Xuất Video Đa Năng (All-In-One)":
    st.markdown('<div class="main-header">🎞️ Xưởng Sản Xuất Video Toàn Diện (All-In-One Video Studio)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Tự động hợp nhất kịch bản, giọng đọc AI, hiệu ứng chuyển động và phụ đề chuyên nghiệp thành video MP4 hoàn chỉnh.</div>', unsafe_allow_html=True)

    st.markdown("### 📝 Bước 1: Kịch Bản Thuyết Minh & Giọng Đọc")
    col_v1, col_v2 = st.columns([2, 1])
    with col_v1:
        prod_script = st.text_area(
            "Nhập kịch bản video:",
            value="Hành trình vạn dặm luôn bắt đầu từ một bước chân đầu tiên. Hãy kiên trì theo đuổi đam mê, thành công nhất định sẽ mỉm cười với bạn.",
            height=130
        )
    with col_v2:
        prod_voice_choice = st.selectbox(
            "Giọng đọc thuyết minh:",
            [
                "vi-VN-NamMinhNeural (Nam Bắc)",
                "vi-VN-HoaiMyNeural (Nữ Bắc)",
                "en-US-JennyNeural (Nữ Mỹ)",
                "en-US-GuyNeural (Nam Mỹ)"
            ]
        )
        selected_prod_voice = prod_voice_choice.split(" ")[0]

    st.markdown("---")
    st.markdown("### 🖼️ Bước 2: Tải Lên Danh Sách Ảnh Minh Họa")
    uploaded_imgs = st.file_uploader(
        "Tải lên các hình ảnh (Hệ thống sẽ tự động phân bổ đều theo thời lượng giọng đọc):",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    st.markdown("---")
    st.markdown("### ⚙️ Bước 3: Cấu Hình Định Dạng & Hiệu Ứng Chuyên Nghiệp")
    col_c1, col_c2, col_c3 = st.columns(3)
    
    with col_c1:
        ratio_choice = st.selectbox(
            "Tỷ lệ khung hình video:",
            [
                "16:9 Ngang (YouTube, Facebook, Web)",
                "9:16 Dọc (TikTok, Shorts, Reels)",
                "1:1 Vuông (Instagram Post)"
            ]
        )
    
    with col_c2:
        motion_effect = st.selectbox(
            "Hiệu ứng chuyển động hình ảnh (Ken Burns):",
            [
                "Không sử dụng hiệu ứng",
                "Zoom In Nhẹ (Phóng to dần)",
                "Zoom Out Nhẹ (Thu nhỏ dần)"
            ]
        )
        
    with col_c3:
        sub_toggle = st.checkbox("Chèn phụ đề thuyết minh tự động", value=True)
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
            with st.spinner("⏳ Đang tổng hợp giọng nói, căn chỉnh tỷ lệ và render video hoàn chỉnh..."):
                try:
                    # 1. Tạo file âm thanh bằng Edge-TTS
                    comm = edge_tts.Communicate(prod_script, selected_prod_voice)
                    temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    asyncio.run(comm.save(temp_audio_file.name))
                    
                    audio_clip = AudioFileClip(temp_audio_file.name)
                    total_duration = audio_clip.duration
                    
                    # 2. Xác định kích thước video dựa vào tỉ lệ đã chọn
                    if "16:9" in ratio_choice:
                        target_w, target_h = 1280, 720
                    elif "9:16" in ratio_choice:
                        target_w, target_h = 720, 1280
                    else:
                        target_w, target_h = 1080, 1080

                    # 3. Xử lý các clip hình ảnh
                    num_images = len(uploaded_imgs)
                    duration_per_image = total_duration / num_images
                    clips_list = []
                    
                    for idx, img_item in enumerate(uploaded_imgs):
                        t_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                        t_img.write(img_item.getvalue())
                        t_img.close()
                        
                        img_clip = ImageClip(t_img.name).set_duration(duration_per_image)
                        
                        # Cắt và ép kích thước chuẩn
                        img_clip = img_clip.resize(newsize=(target_w, target_h))
                        
                        # Thêm hiệu ứng chuyển động Ken Burns
                        if motion_effect == "Zoom In Nhẹ (Phóng to dần)":
                            img_clip = img_clip.fx(vfx.resize, lambda t: 1.0 + 0.05 * (t / duration_per_image))
                        elif motion_effect == "Zoom Out Nhẹ (Thu nhỏ dần)":
                            img_clip = img_clip.fx(vfx.resize, lambda t: 1.05 - 0.05 * (t / duration_per_image))
                            
                        clips_list.append(img_clip)
                        
                    composed_base_video = concatenate_videoclips(clips_list, method="compose").set_audio(audio_clip)
                    
                    # 4. Thêm phụ đề (nếu người dùng kích hoạt)
                    if sub_toggle:
                        clean_sub_text = prod_script.replace("\n", " ")
                        text_clip = (
                            TextClip(
                                clean_sub_text,
                                fontsize=sub_font_size,
                                color=sub_color,
                                font='Liberation-Sans-Bold',
                                method='caption',
                                size=(target_w - 100, None)
                            )
                            .set_position(('center', target_h - 150))
                            .set_duration(total_duration)
                        )
                        final_video_clip = CompositeVideoClip([composed_base_video, text_clip])
                    else:
                        final_video_clip = composed_base_video

                    # 5. Xuất video MP4 chất lượng cao
                    out_vid_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                    final_video_clip.write_videofile(
                        out_vid_path,
                        fps=24,
                        codec="libx264",
                        audio_codec="aac",
                        logger=None
                    )
                    
                    st.success("🎉 Video của bạn đã được xuất bản thành công!")
                    st.video(out_vid_path)
                    
                    with open(out_vid_path, "rb") as vf:
                        st.download_button(
                            label="⬇️ TẢI VIDEO THÀNH PHẨM (MP4)",
                            data=vf.read(),
                            file_name="ai_studio_full_production.mp4",
                            mime="video/mp4",
                            use_container_width=True
                        )
                except Exception as prod_err:
                    st.error(f"❌ Xảy ra lỗi trong quá trình dựng video: {prod_err}")
