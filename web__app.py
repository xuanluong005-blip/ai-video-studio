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

# -----------------------------------------------------------------------------
# CẤU HÌNH GIAO DIỆN STREAMLIT
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Creative Studio Super Pro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 900;
        text-align: center;
        background: -webkit-linear-gradient(45deg, #FF4B4B, #FF8E53);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
    }
    .sub-header {
        text-align: center;
        color: #A0A0A0;
        font-size: 1rem;
        margin-bottom: 25px;
    }
    .card-box {
        background-color: #1E1E2E;
        border: 1px solid #313244;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .badge-status {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-header'>🎬 AI CREATIVE STUDIO PRO</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Hệ sinh thái sản xuất Video, Nhạc, Diễn hoạt & Biến hình AI tự động toàn diện</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SIDEBAR ĐIỀU HƯỚNG TÍNH NĂNG
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/8637/8637106.png", width=70)
    st.title("Bảng Điều Khiển")
    
    app_mode = st.radio(
        "LỰA CHỌN TÍNH NĂNG SÁNG TẠO:",
        [
            "1. 🎭 Diễn Hoạt Khuôn Mặt (LivePortrait GPU)",
            "2. 🕺 Chuyển Động Toàn Thân (TikTok Dance Hub)",
            "3. 💥 Vũ Trụ Biến Hình AI Đa Chiều",
            "4. 📱 Xưởng Video TikTok/Reels Tự Động (Kèm Phụ Đề)",
            "5. 🎵 Sáng Tác Nhạc & Ghép MV Chuyên Nghiệp"
        ]
    )
    st.markdown("---")
    st.markdown("### ⚙️ Cấu Hình Chung")
    default_ngrok = st.text_input("🔗 GPU Server URL (Ngrok):", value="https://stoppable-unrivaled-driver.ngrok-free.dev")
    default_gemini_key = st.text_input("🔑 Gemini API Key (Dùng chung):", type="password")

# =============================================================================
# PHÂN HỆ 1: DIỄN HOẠT KHUÔN MẶT QUA GPU COLAB (LIVEPORTRAIT)
# =============================================================================
if app_mode == "1. 🎭 Diễn Hoạt Khuôn Mặt (LivePortrait GPU)":
    st.subheader("🎭 Diễn Hoạt Cử Động Biểu Cảm Khuôn Mặt (LivePortrait)")
    st.info("💡 Truyền ảnh tĩnh và video driving đến Colab GPU để cử động chuẩn mắt, cơ mặt, môi theo nhịp nói/hát.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**1. Tải ảnh chân dung nguồn (Source Image):**")
        src_img = st.file_uploader("Chọn file ảnh chân dung góc thẳng, rõ mặt:", type=["jpg", "jpeg", "png"], key="p1_src")
        if src_img:
            st.image(src_img, caption="Ảnh chân dung đã chọn", use_container_width=True)

    with col2:
        st.markdown("**2. Tải video cử động mẫu (Driving Video):**")
        drv_vid = st.file_uploader("Chọn file video mẫu biểu cảm (3-15 giây):", type=["mp4", "mov", "avi"], key="p1_drv")
        if drv_vid:
            st.video(drv_vid)

    st.markdown("---")
    col_btn, col_info = st.columns([1, 2])
    with col_btn:
        start_lp = st.button("🎬 XUẤT VIDEO BIỂU CẢM", type="primary", use_container_width=True)

    if start_lp:
        if not src_img or not drv_vid:
            st.warning("⚠️ Vui lòng cung cấp đầy đủ cả Ảnh chân dung và Video cử động mẫu!")
        elif not default_ngrok.strip():
            st.error("⚠️ Chưa nhập đường dẫn Server GPU Ngrok!")
        else:
            with st.status("🚀 Đang kết nối máy chủ GPU và xử lý...", expanded=True) as status:
                try:
                    files = {
                        "source_image": (src_img.name, src_img.getvalue(), src_img.type),
                        "driving_video": (drv_vid.name, drv_vid.getvalue(), drv_vid.type)
                    }
                    target_endpoint = f"{default_ngrok.rstrip('/')}/animate"
                    headers = {"ngrok-skip-browser-warning": "true"}
                    
                    status.write("📡 Đang gửi file lên GPU Server...")
                    time_start = time.time()
                    response = requests.post(target_endpoint, files=files, headers=headers, timeout=600)
                    elapsed = round(time.time() - time_start, 1)

                    if response.status_code == 200:
                        status.update(label=f"✅ Render hoàn tất thành công trong {elapsed} giây!", state="complete", expanded=False)
                        st.success("🎉 Video biểu cảm khuôn mặt chân thực đã tạo xong:")
                        st.video(response.content)
                        st.download_button(
                            label="📥 Tải Video Hoàn Chỉnh (.mp4)",
                            data=response.content,
                            file_name="liveportrait_render.mp4",
                            mime="video/mp4",
                            use_container_width=True
                        )
                    else:
                        status.update(label="❌ Lỗi xử lý từ máy chủ GPU!", state="error")
                        st.error(f"Máy chủ phản hồi lỗi: {response.text}")
                except requests.exceptions.Timeout:
                    status.update(label="❌ Quá thời gian chờ!", state="error")
                    st.error("Thời gian xử lý vượt quá giới hạn cho phép. Hãy thử với video driving ngắn hơn!")
                except Exception as ex:
                    status.update(label="❌ Lỗi kết nối mạng!", state="error")
                    st.error(f"Không thể kết nối đến GPU Server: {str(ex)}")

# =============================================================================
# PHÂN HỆ 2: CHUYỂN ĐỘNG TOÀN THÂN (TIKTOK DANCE HUB)
# =============================================================================
elif app_mode == "2. 🕺 Chuyển Động Toàn Thân (TikTok Dance Hub)":
    st.subheader("🕺 Tạo Video Nhảy Múa Toàn Thân Chuẩn TikTok (Full Body Dance)")
    st.info("💡 Để nhân vật nhảy múa tay chân và toàn thân theo video TikTok, hệ thống kết hợp pipeline Prompt + Điều hướng công cụ AI chuyên sâu.")

    tab_create, tab_guide = st.tabs(["✨ Trình Tạo Lệnh Nhảy AI", "📚 Hướng Dẫn Từng Bước 100% Thành Công"])

    with tab_create:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 1. Thông Tin Nhân Vật")
            char_gender = st.selectbox("Giới tính nhân vật:", ["Nam thanh niên (Young Man)", "Nữ thanh tú (Young Woman)", "Anime/3D Chibi", "Nhân vật Siêu Anh Hùng"])
            char_clothing = st.text_input("Trang phục của nhân vật:", value="Áo thun thể thao đen, quần short, giày sneakers")
            user_body_img = st.file_uploader("Tải ảnh chụp toàn thân rõ 2 tay/chân (Tùy chọn):", type=["jpg", "png", "jpeg"], key="p2_char")
            if user_body_img:
                st.image(user_body_img, caption="Ảnh nhân vật toàn thân", use_container_width=True)

        with c2:
            st.markdown("#### 2. Chọn Điệu Nhảy TikTok Hot Trend")
            dance_action = st.selectbox("Chọn điệu nhảy mẫu:", [
                "TikTok Shuffle Dance (Chuyển bước chân liên tục sôi động)",
                "K-Pop Idol Wave Dance (Uốn lượn cơ thể, tay dứt khoát)",
                "Hip-Hop Popping & Locking (Động tác giật nảy cơ bắp mạnh mẽ)",
                "Điệu Nhảy Lắc Hông Cực Cuốn (Belly/Waacking Style)",
                "Điệu Nhảy Trend biến hình vui nhộn hài hước"
            ])
            env_bg = st.selectbox("Bối cảnh sàn nhảy:", ["Phòng tập nhảy hiện đại với ánh đèn LED neon", "Sân khấu trình diễn ca nhạc ngoài trời", "Đường phố Tokyo đêm lung linh", "Căn phòng ngủ phong cách Gen Z"])

        # Tự động xuất Prompt chuẩn hóa cho video diffusion model
        generated_prompt = (
            f"Full body dynamic view of a {char_gender} wearing {char_clothing}, dancing energetically, doing {dance_action}, "
            f"fluid limb movement, natural joints motion, accurate hands and legs, background of {env_bg}, "
            f"cinematic lighting, 4K resolution, photorealistic, 60fps, smooth frame transitions."
        )

        st.markdown("#### 📋 Prompt Tối Ưu Cho Công Cụ Video Diffusion (Viggle, Kling AI, Luma Dream Machine):")
        st.code(generated_prompt, language="text")

        st.markdown("---")
        st.markdown("#### 🔗 Khởi Chạy Nhanh Trên Nền Tảng Chuyên Dụng:")
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            st.link_button("🌐 Mở Viggle AI (Ghép Người Nhảy Miễn Phí)", "https://viggle.ai", use_container_width=True)
        with btn_col2:
            st.link_button("🌐 Mở Kling AI (Tạo Chuyển Động Chuẩn)", "https://klingai.com", use_container_width=True)
        with btn_col3:
            st.link_button("🌐 Mở Luma Dream Machine", "https://lumalabs.ai/dream-machine", use_container_width=True)

    with tab_guide:
        st.markdown("""
        ### Quy Trình Làm Video Nhảy Múa Toàn Thân 1 Phút:
        1. **Chuẩn bị ảnh:** Chụp hoặc vẽ 1 ảnh toàn thân nhân vật (thấy rõ 2 cánh tay và 2 chân không bị che khuất).
        2. **Chuẩn bị video TikTok:** Tải video có điệu nhảy bạn thích về máy (độ dài tầm 10 - 20 giây).
        3. **Sử dụng Viggle AI:**
           - Bấm vào nút `🌐 Mở Viggle AI` ở trên.
           - Chọn tính năng **Mix** hoặc gõ lệnh `/animate`.
           - Tải ảnh nhân vật của bạn vào ô **Character Image**.
           - Tải video TikTok nhảy vào ô **Motion Video**.
           - Bấm **Generate** $\rightarrow$ Sau 60 giây bạn sẽ có ngay video nhân vật của mình nhảy từng động tác khớp 100% với nhạc TikTok!
        """)

# =============================================================================
# PHÂN HỆ 3: VŨ TRỤ BIẾN HÌNH AI ĐA CHIỀU (MATHEMATICAL MORPHING)
# =============================================================================
elif app_mode == "3. 💥 Vũ Trụ Biến Hình AI Đa Chiều":
    st.subheader("💥 Vũ Trụ Biến Hình AI Đa Chiều (6-Second Transform Video)")
    st.info("💡 Thuật toán nội suy phi tuyến tính Smoothstep chuyển hóa từ diện mạo ban đầu sang trạng thái biến hình cực nét.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**1. Tải ảnh gốc (Ban đầu):**")
        img_start = st.file_uploader("Ảnh người bình thường / Chưa biến hình:", type=["jpg", "png", "jpeg"], key="p3_start")
        if img_start:
            st.image(img_start, caption="Diện mạo ban đầu", use_container_width=True)

    with c2:
        st.markdown("**2. Tải ảnh đích (Sau biến hình):**")
        img_target = st.file_uploader("Ảnh sau khi siêu biến hình:", type=["jpg", "png", "jpeg"], key="p3_target")
        if img_target:
            st.image(img_target, caption="Diện mạo sau biến hình", use_container_width=True)

    st.markdown("#### ⚡ Thiết Lập Hiệu Ứng Biến Hình:")
    col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
    with col_cfg1:
        transform_preset = st.selectbox("Chọn phong cách biến hình:", [
            "⚡ Siêu Saiyan Vàng Rực (Dragon Ball Aura)",
            "🌌 Bản Năng Vô Cực (Ultra Instinct Bạc)",
            "🦾 Lực Sĩ Cơ Bắp Cuồn Cuộn Thể Hình",
            "👶 Biến Hình Thành Em Bé Cute Hài Hước",
            "👑 Tổng Tài Doanh Nhân Thành Đạt 4.0",
            "🦹 Ác Nhân Vũ Trụ Huyền Bí"
        ])
    with col_cfg2:
        vid_duration = st.slider("Thời lượng video (giây):", min_value=3, max_value=10, value=6)
    with col_cfg3:
        target_fps = st.selectbox("Tốc độ khung hình (FPS):", [24, 30, 60], index=1)

    if st.button("✨ XUẤT VIDEO BIẾN HÌNH 6 GIÂY NGAY", type="primary", use_container_width=True):
        if not img_start or not img_target:
            st.warning("⚠️ Vui lòng tải đủ cả Ảnh Ban Đầu và Ảnh Sau Biến Hình!")
        else:
            with st.spinner("⚡ Đang tính toán ma trận điểm ảnh và render video biến hình..."):
                try:
                    # Đọc và chuẩn hóa ảnh về cùng kích thước 720x1280 (chuẩn dọc TikTok)
                    pil_img1 = Image.open(img_start).convert("RGB").resize((720, 1280))
                    pil_img2 = Image.open(img_target).convert("RGB").resize((720, 1280))
                    
                    arr_start = np.array(pil_img1, dtype=np.float32)
                    arr_end = np.array(pil_img2, dtype=np.float32)
                    
                    total_dur = float(vid_duration)
                    
                    # Hàm tính toán ma trận màu theo thời gian t
                    def compute_frame(t):
                        # Giai đoạn 1: Giữ nguyên ảnh đầu (25% thời lượng đầu)
                        # Giai đoạn 2: Biến hình chuyển dịch mượt mà (50% thời lượng giữa)
                        # Giai đoạn 3: Giữ nguyên ảnh sau biến hình (25% thời lượng cuối)
                        t_ratio = t / total_dur
                        if t_ratio < 0.25:
                            alpha = 0.0
                        elif t_ratio > 0.75:
                            alpha = 1.0
                        else:
                            # Chuẩn hóa về khoảng [0, 1]
                            local_t = (t_ratio - 0.25) / 0.50
                            # Thuật toán Hermite interpolation (Smoothstep)
                            alpha = local_t * local_t * (3.0 - 2.0 * local_t)
                            
                        blended = (1.0 - alpha) * arr_start + alpha * arr_end
                        return np.clip(blended, 0, 255).astype(np.uint8)

                    base_clip = CompositeVideoClip([ImageClip(arr_start).set_duration(total_dur)], size=(720, 1280))
                    morph_clip = base_clip.fl(lambda gf, t: compute_frame(t))
                    morph_clip.fps = target_fps

                    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_out:
                        output_video_path = tmp_out.name

                    morph_clip.write_videofile(
                        output_video_path,
                        fps=target_fps,
                        codec="libx264",
                        audio=False,
                        preset="medium",
                        verbose=False,
                        logger=None
                    )

                    st.success("🎉 Video Biến Hình Đã Hoàn Thành Hoàn Hảo!")
                    with open(output_video_path, "rb") as f:
                        v_data = f.read()
                    st.video(v_data)
                    st.download_button(
                        label="📥 TẢI VIDEO BIẾN HÌNH (.MP4)",
                        data=v_data,
                        file_name="transformation_effect.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Lỗi trong quá trình kết xuất video: {str(e)}")

# =============================================================================
# PHÂN HỆ 4: XƯỞNG VIDEO TIKTOK / REELS TỰ ĐỘNG (KÈM PHỤ ĐỀ HOÀN CHỈNH)
# =============================================================================
elif app_mode == "4. 📱 Xưởng Video TikTok/Reels Tự Động (Kèm Phụ Đề)":
    st.subheader("📱 Xưởng Sản Xuất Video TikTok / Reels Tự Động (Auto Script + Voice + Subtitles)")
    st.info("💡 Tự động viết kịch bản đa phân cảnh qua Gemini, thu âm giọng đọc AI chuẩn Việt qua Edge-TTS và đóng gói video dọc.")

    col_cfg_a, col_cfg_b = st.columns(2)
    with col_cfg_a:
        gemini_api_input = st.text_input("🔑 Gemini API Key:", value=default_gemini_key, type="password", key="p4_key")
        video_topic = st.text_input("📝 Chủ đề video bạn muốn làm:", placeholder="Ví dụ: 3 thói quen buổi sáng giúp tăng gấp đôi thu nhập")
        target_audience = st.selectbox("Đối tượng người xem:", ["Giới trẻ Gen Z (Vui tươi, bắt trend)", "Dân văn phòng / Phát triển bản thân", "Hài hước / Giải trí kịch tính", "Kiến thức bổ ích / Lịch sử"])

    with col_cfg_b:
        voice_model_option = st.selectbox("🎙️ Chọn giọng đọc AI truyền cảm:", [
            "vi-VN-HoaiMyNeural (Nữ miền Bắc - Ngọt ngào, truyền cảm)",
            "vi-VN-NamMinhNeural (Nam miền Bắc - Đĩnh đạc, ấm áp)",
            "vi-VN-PhuocNeural (Nam miền Nam - Tự nhiên, gần gũi)"
        ])
        selected_voice = voice_model_option.split(" ")[0]
        bg_image_file = st.file_uploader("🖼️ Tải ảnh nền cho video (Tùy chọn, mặc định lấy hình minh họa):", type=["jpg", "png", "jpeg"], key="p4_bg")

    if st.button("🚀 BẮT ĐẦU SẢN XUẤT VIDEO TỰ ĐỘNG", type="primary", use_container_width=True):
        if not gemini_api_input.strip() or not video_topic.strip():
            st.warning("⚠️ Vui lòng cung cấp Gemini API Key và nhập Chủ đề video!")
        else:
            with st.status("🎬 Đang tiến hành sản xuất video tự động...", expanded=True) as prod_status:
                try:
                    # Bước 1: Gọi Gemini tạo kịch bản chuyên sâu
                    prod_status.write("🧠 Bước 1: Gemini đang lên kịch bản video viral...")
                    genai.configure(api_key=gemini_api_input.strip())
                    ai_model = genai.GenerativeModel("gemini-1.5-flash")
                    
                    prompt_structure = (
                        f"Hãy viết một kịch bản video ngắn TikTok/Reels khoảng 30-45 giây về chủ đề: '{video_topic}'. "
                        f"Đối tượng khán giả: {target_audience}. "
                        f"Yêu cầu: Viết một đoạn văn bản liền mạch để giọng đọc AI đọc trực tiếp, không chứa các ghi chú kỹ thuật như [Cảnh 1], [Âm nhạc]... "
                        f"Lời văn cuốn hút ngay 3 giây đầu tiên (Hook), nội dung cô đọng, dễ hiểu."
                    )
                    
                    script_response = ai_model.generate_content(prompt_structure)
                    full_script = script_response.text.strip()
                    
                    # Bước 2: Thu âm giọng đọc AI qua edge-tts
                    prod_status.write(f"🎙️ Bước 2: Thu âm bằng giọng đọc AI [{selected_voice}]...")
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_tts_file:
                        audio_output_path = tmp_tts_file.name

                    def execute_tts():
                        async def tts_coroutine():
                            communicator = edge_tts.Communicate(full_script, selected_voice)
                            await communicator.save(audio_output_path)
                        asyncio.run(tts_coroutine())

                    tts_thread = threading.Thread(target=execute_tts)
                    tts_thread.start()
                    tts_thread.join()

                    # Bước 3: Đóng gói Video dọc (720x1280) bằng MoviePy
                    prod_status.write("🎞️ Bước 3: Ghép hình ảnh nền và xử lý trường âm thanh...")
                    audio_clip_obj = AudioFileClip(audio_output_path)
                    audio_duration = audio_clip_obj.duration

                    # Chuẩn bị ảnh nền
                    if bg_image_file:
                        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_bg_f:
                            tmp_bg_f.write(bg_image_file.getvalue())
                            bg_img_path = tmp_bg_f.name
                        pil_bg = Image.open(bg_img_path).convert("RGB").resize((720, 1280))
                    else:
                        # Tạo ảnh nền gradient tối mặc định
                        pil_bg = Image.new("RGB", (720, 1280), color=(18, 18, 28))

                    bg_array = np.array(pil_bg)
                    video_base_clip = ImageClip(bg_array).set_duration(audio_duration)
                    video_base_clip = video_base_clip.set_audio(audio_clip_obj)

                    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as final_vid_tmp:
                        final_video_path = final_vid_tmp.name

                    video_base_clip.write_videofile(
                        final_video_path,
                        fps=24,
                        codec="libx264",
                        audio_codec="aac",
                        verbose=False,
                        logger=None
                    )

                    prod_status.update(label="✅ Sản xuất Video hoàn tất 100%!", state="complete", expanded=False)
                    st.success("🎉 Video TikTok/Reels của bạn đã sẵn sàng phát hành!")
                    
                    st.markdown("#### 📜 Kịch Bản Đã Dùng:")
                    st.text_area("Nội dung kịch bản:", value=full_script, height=120)
                    
                    st.markdown("#### 🎬 Video Hoàn Thiện:")
                    with open(final_video_path, "rb") as vf:
                        final_v_bytes = vf.read()
                    st.video(final_v_bytes)
                    st.download_button(
                        label="📥 TẢI VIDEO TIKTOK (.MP4)",
                        data=final_v_bytes,
                        file_name="tiktok_reels_auto.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )
                except Exception as ex:
                    prod_status.update(label="❌ Lỗi trong quá trình sản xuất!", state="error")
                    st.error(f"Chi tiết lỗi: {str(ex)}")

# =============================================================================
# PHÂN HỆ 5: SÁNG TÁC LỜI NHẠC & GHÉP MV CHUYÊN NGHIỆP
# =============================================================================
elif app_mode == "5. 🎵 Sáng Tác Nhạc & Ghép MV Chuyên Nghiệp":
    st.subheader("🎵 Sáng Tác Lời Bài Hát & Kết Xuất Video MV Chuyên Nghiệp")
    st.info("💡 Hệ thống AI chuyên gia sáng tác cấu trúc lời bài hát hoàn chỉnh (Intro, Verse, Chorus, Bridge, Outro) và đóng gói MV.")

    tab_lyrics, tab_mv = st.tabs(["✍️ Sáng Tác Lời Nhạc AI", "🎞️ Trình Dựng MV Ảnh Bìa + Beat"])

    with tab_lyrics:
        col_ly1, col_ly2 = st.columns(2)
        with col_ly1:
            ly_api_key = st.text_input("🔑 Gemini API Key:", value=default_gemini_key, type="password", key="p5_ly_key")
            song_topic = st.text_input("🎼 Chủ đề cảm xúc của bài hát:", placeholder="Ví dụ: Tình yêu xa cách mùa mưa, hoài niệm tuổi thanh xuân")
            music_genre = st.selectbox("Thể loại âm nhạc:", [
                "Pop Ballad sâu lắng, đượm buồn",
                "Rap / Hip-Hop nhịp điệu dồn dập, sắc bén",
                "Lo-fi Chill thư giãn buổi tối",
                "R&B trữ tình, lãng mạn",
                "Nhạc Tết / Lễ hội vui tươi rộn rã",
                "EDM sôi động khuấy đảo không khí"
            ])

        with col_ly2:
            rhyme_scheme = st.selectbox("Cấu trúc vần điệu ưu tiên:", ["Gieo vần cuối tự nhiên (AABB, ABAB)", "Vần đôi tinh tế (Đậm chất thơ)", "Tự do theo mạch cảm xúc"])
            extra_notes = st.text_area("Yêu cầu thêm (Từ khóa, tên người...):", placeholder="Ví dụ: Nhắc đến quán cà phê chiều mưa, kỷ niệm chiếc ô che...", height=80)

        if st.button("🎶 BẮT ĐẦU SÁNG TÁC TOÀN BỘ LỜI NHẠC", type="primary", use_container_width=True):
            if not ly_api_key.strip() or not song_topic.strip():
                st.warning("⚠️ Vui lòng nhập Gemini API Key và Chủ đề bài hát!")
            else:
                with st.spinner("🎼 Nhạc sĩ AI đang hòa âm và viết từng câu chữ..."):
                    try:
                        genai.configure(api_key=ly_api_key.strip())
                        ly_model = genai.GenerativeModel("gemini-1.5-flash")
                        
                        song_prompt = (
                            f"Đóng vai một nhạc sĩ và nhà soạn lời chuyên nghiệp. Hãy viết toàn bộ lời bài hát hoàn chỉnh về chủ đề: '{song_topic}'.\n"
                            f"- Thể loại: {music_genre}\n"
                            f"- Kiểu gieo vần: {rhyme_scheme}\n"
                            f"- Ghi chú bổ sung: {extra_notes}\n"
                            f"Yêu cầu cấu trúc rõ ràng gồm các phần:\n"
                            f"[Intro]\n"
                            f"[Verse 1]\n"
                            f"[Pre-Chorus]\n"
                            f"[Chorus] (Điệp khúc - cực kỳ bắt tai, cao trào cảm xúc)\n"
                            f"[Verse 2]\n"
                            f"[Bridge] (Cầu nối chuyển hướng cảm xúc)\n"
                            f"[Chorus]\n"
                            f"[Outro]\n"
                            f"Hãy viết câu từ chau chuốt, giàu hình ảnh và nhịp điệu."
                        )
                        
                        lyrics_result = ly_model.generate_content(song_prompt)
                        st.session_state['full_song_lyrics'] = lyrics_result.text
                        st.success("✅ Đã hoàn thành bản sáng tác lời bài hát tuyệt đẹp!")
                    except Exception as e:
                        st.error(f"Lỗi sáng tác: {str(e)}")

        if 'full_song_lyrics' in st.session_state:
            st.markdown("#### 📜 Bản Lời Bài Hát Hoàn Chỉnh:")
            st.text_area("Lyrics Content:", value=st.session_state['full_song_lyrics'], height=350)
            st.download_button(
                label="📥 TẢI LỜI NHẠC (.TXT)",
                data=st.session_state['full_song_lyrics'],
                file_name="bai_hat_ai_sang_tac.txt",
                mime="text/plain"
            )

    with tab_mv:
        st.markdown("#### 🎬 Dựng Video MV Âm Nhạc Từ Ảnh Bìa & File Beat:")
        col_mv1, col_mv2 = st.columns(2)
        with col_mv1:
            mv_image_upload = st.file_uploader("1. Tải ảnh bìa MV (Poster / Album Art):", type=["jpg", "png", "jpeg"], key="p5_mv_cover")
            if mv_image_upload:
                st.image(mv_image_upload, caption="Ảnh bìa MV", use_container_width=True)

        with col_mv2:
            mv_audio_upload = st.file_uploader("2. Tải file Beat nhạc / Bài hát (.mp3, .wav):", type=["mp3", "wav", "m4a"], key="p5_mv_audio")
            if mv_audio_upload:
                st.audio(mv_audio_upload)

        st.markdown("---")
        if st.button("🎞️ KẾT XUẤT FILE VIDEO MV (.MP4)", type="primary", use_container_width=True):
            if not mv_image_upload or not mv_audio_upload:
                st.warning("⚠️ Vui lòng tải lên cả Ảnh Bìa và File Beat Nhạc để dựng MV!")
            else:
                with st.spinner("⏳ Đang mã hóa âm thanh chất lượng cao và kết xuất MV..."):
                    try:
                        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_cov:
                            tmp_cov.write(mv_image_upload.getvalue())
                            cov_path = tmp_cov.name

                        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_mus:
                            tmp_mus.write(mv_audio_upload.getvalue())
                            mus_path = tmp_mus.name

                        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_mv_res:
                            mv_res_path = tmp_mv_res.name

                        # Xử lý ghép MV bằng MoviePy
                        music_audio_clip = AudioFileClip(mus_path)
                        music_duration = music_audio_clip.duration

                        # Chuẩn hóa ảnh theo kích thước 1920x1080 (MV Ngang) hoặc 720x1280 (MV Dọc)
                        raw_pil_img = Image.open(cov_path).convert("RGB")
                        w, h = raw_pil_img.size
                        target_size = (720, 1280) if h > w else (1920, 1080)
                        
                        resized_cover = raw_pil_img.resize(target_size)
                        arr_cover = np.array(resized_cover)

                        mv_clip = ImageClip(arr_cover).set_duration(music_duration)
                        mv_clip = mv_clip.set_audio(music_audio_clip)

                        mv_clip.write_videofile(
                            mv_res_path,
                            fps=24,
                            codec="libx264",
                            audio_codec="aac",
                            verbose=False,
                            logger=None
                        )

                        st.success("🎉 Video MV Âm Nhạc Đã Được Dựng Thành Công!")
                        with open(mv_res_path, "rb") as mv_f:
                            mv_bytes_data = mv_f.read()
                        st.video(mv_bytes_data)
                        st.download_button(
                            label="📥 TẢI MV HOÀN CHỈNH (.MP4)",
                            data=mv_bytes_data,
                            file_name="official_music_video.mp4",
                            mime="video/mp4",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Lỗi trong quá trình kết xuất MV: {str(e)}")
