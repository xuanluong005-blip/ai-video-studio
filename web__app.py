import streamlit as st
import os
import tempfile
import asyncio
import threading
import requests
import numpy as np
from PIL import Image
import google.generativeai as genai
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, TextClip, CompositeVideoClip

# Cấu hình giao diện Streamlit
st.set_page_config(page_title="AI Creative Studio All-in-One", page_icon="🎬", layout="wide")

st.markdown("""
    <style>
    .main-title {font-size: 2.2rem; font-weight: 800; color: #FF4B4B; text-align: center; margin-bottom: 20px;}
    .feature-card {background: #1E1E2E; padding: 20px; border-radius: 12px; border: 1px solid #313244; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>🎬 AI CREATIVE STUDIO ALL-IN-ONE</div>", unsafe_allow_html=True)

# Thanh điều hướng phân hệ
menu = st.sidebar.radio(
    "🌟 CHỌN TÍNH NĂNG SÁNG TẠO:",
    [
        "1. 🎭 Biểu Cảm Khuôn Mặt (LivePortrait)",
        "2. 🕺 Chuyển Động Toàn Thân (TikTok Dance)",
        "3. 💥 Vũ Trụ Biến Hình AI",
        "4. 📱 Tạo Video TikTok/Reels Tự Động",
        "5. 🎵 Sáng Tác Nhạc & Ghép MV"
    ]
)

# -----------------------------------------------------------------------------
# PHÂN HỆ 1: LIVEPORTRAIT (COLAB GPU SERVER)
# -----------------------------------------------------------------------------
if menu == "1. 🎭 Biểu Cảm Khuôn Mặt (LivePortrait)":
    st.subheader("🎭 Diễn Hoạt Cử Động Khuôn Mặt Qua GPU")
    st.info("💡 Tính năng này truyền ảnh chân dung và video biểu cảm đến máy chủ Colab GPU để render chuyển động mắt, miệng, đầu.")
    
    col1, col2 = st.columns(2)
    with col1:
        src_file = st.file_uploader("1. Tải ảnh chân dung (Rõ mặt):", type=["jpg", "png", "jpeg"], key="lp_src")
        if src_file:
            st.image(src_file, caption="Ảnh Chân Dung", use_container_width=True)
    with col2:
        drv_file = st.file_uploader("2. Tải video biểu cảm mẫu (3-8 giây):", type=["mp4", "mov"], key="lp_drv")
        if drv_file:
            st.video(drv_file)

    gpu_url = st.text_input("🔗 Đường dẫn Ngrok Server:", value="https://stoppable-unrivaled-driver.ngrok-free.dev")

    if st.button("🚀 BẮT ĐẦU RENDER BIỂU CẢM", type="primary", use_container_width=True):
        if not src_file or not drv_file:
            st.warning("⚠️ Vui lòng tải đủ ảnh chân dung và video mẫu!")
        else:
            with st.status("🧠 Đang gửi dữ liệu đến GPU Server...", expanded=True) as status:
                try:
                    files = {
                        "source_image": (src_file.name, src_file.getvalue(), src_file.type),
                        "driving_video": (drv_file.name, drv_file.getvalue(), drv_file.type)
                    }
                    target_api = f"{gpu_url.rstrip('/')}/animate"
                    headers = {"ngrok-skip-browser-warning": "true"}
                    
                    status.write("⚡ GPU đang phân tích ngũ quan và render video...")
                    response = requests.post(target_api, files=files, headers=headers, timeout=600)
                    
                    if response.status_code == 200:
                        status.update(label="✅ Render thành công 100%!", state="complete", expanded=False)
                        st.success("🎉 Video biểu cảm đã sẵn sàng!")
                        st.video(response.content)
                        st.download_button("📥 TẢI VIDEO (.MP4)", data=response.content, file_name="liveportrait_result.mp4", mime="video/mp4")
                    else:
                        status.update(label="❌ Lỗi từ máy chủ!", state="error")
                        st.error(f"Máy chủ phản hồi: {response.text}")
                except Exception as e:
                    status.update(label="❌ Lỗi kết nối!", state="error")
                    st.error(f"Không thể kết nối đến GPU: {str(e)}")

# -----------------------------------------------------------------------------
# PHÂN HỆ 2: NHẢY MÚA TOÀN THÂN (TIKTOK DANCE)
# -----------------------------------------------------------------------------
elif menu == "2. 🕺 Chuyển Động Toàn Thân (TikTok Dance)":
    st.subheader("🕺 Tạo Video Nhảy Múa Toàn Thân (Full Body Pose)")
    st.markdown("""
        Mô hình khuếch tán toàn thân (như *Viggle AI, Kling AI*) yêu cầu hạ tầng siêu máy tính chuyên dụng để bóc tách khung xương và đắp chuyển động nhân vật.
    """)
    
    tab1, tab2 = st.tabs(["🚀 Xuất Lệnh Nhanh (Viggle/Kling)", "📖 Hướng Dẫn Từng Bước"])
    
    with tab1:
        st.markdown("**1. Tải ảnh nhân vật của bạn:**")
        char_img = st.file_uploader("Chọn ảnh toàn thân:", type=["jpg", "png", "jpeg"], key="dance_char")
        
        st.markdown("**2. Điệu nhảy TikTok mong muốn:**")
        dance_style = st.selectbox("Chọn phong cách điệu nhảy:", [
            "Điệu nhảy TikTok Shuffle Dance sôi động",
            "Điệu nhảy Hip-hop tay chân dứt khoát",
            "Điệu nhảy K-Pop idol quyến rũ",
            "Điệu múa lượn sóng Wave Body mềm mại"
        ])
        
        prompt_generated = f"Full body character dancing gracefully, doing {dance_style}, high quality, realistic motion, 4k 60fps."
        st.text_area("📋 Prompt tối ưu cho Kling AI / Luma / Haiper:", value=prompt_generated, height=100)
        st.markdown("[👉 Mở Viggle AI để tạo ngay miễn phí](https://viggle.ai) | [👉 Mở Kling AI](https://klingai.com)")

    with tab2:
        st.markdown("""
        * **Bước 1:** Chuẩn bị ảnh chụp thấy rõ 2 tay và 2 chân của bạn.
        * **Bước 2:** Tải video nhảy mẫu từ TikTok về máy.
        * **Bước 3:** Đưa cả hai vào **Viggle AI** (chọn lệnh `/animate` hoặc nút `Mix`).
        * **Bước 4:** Hệ thống sẽ xuất ra file video nhân vật của bạn nhảy y hệt điệu nhảy mẫu chỉ sau 1 phút.
        """)

# -----------------------------------------------------------------------------
# PHÂN HỆ 3: VŨ TRỤ BIẾN HÌNH AI
# -----------------------------------------------------------------------------
elif menu == "3. 💥 Vũ Trụ Biến Hình AI":
    st.subheader("💥 Vũ Trụ Biến Hình Đa Chiều (Mathematical Morphing)")
    
    c1, c2 = st.columns(2)
    with c1:
        img_original = st.file_uploader("1. Tải ảnh gốc ban đầu:", type=["jpg", "png", "jpeg"], key="morph_orig")
        if img_original:
            st.image(img_original, caption="Ảnh Gốc", use_container_width=True)
    with c2:
        img_target = st.file_uploader("2. Tải ảnh sau biến hình:", type=["jpg", "png", "jpeg"], key="morph_targ")
        if img_target:
            st.image(img_target, caption="Ảnh Đã Biến Hình", use_container_width=True)

    transform_style = st.selectbox("Chọn hiệu ứng biến hình:", [
        "Siêu Saiyan Cấp 3 (Hào quang vàng rực)",
        "Bản Năng Vô Cực (Hào quang bạc Ultra Instinct)",
        "Thể Hình Lực Sĩ Cơ Bắp Cuồn Cuộn",
        "Biến Hình Thành Em Bé Cute Hài Hước",
        "Tổng Tài Doanh Nhân Thành Đạt"
    ])

    if st.button("✨ TẠO VIDEO BIẾN HÌNH 6 GIÂY", type="primary", use_container_width=True):
        if not img_original or not img_target:
            st.warning("⚠️ Vui lòng tải đủ cả ảnh gốc và ảnh đích biến hình!")
        else:
            with st.spinner("⚡ Đang tính toán ma trận điểm ảnh và render video biến hình..."):
                try:
                    # Đọc và chuẩn hóa kích thước 2 ảnh
                    im1 = Image.open(img_original).convert("RGB").resize((720, 1280))
                    im2 = Image.open(img_target).convert("RGB").resize((720, 1280))
                    arr1 = np.array(im1, dtype=np.float32)
                    arr2 = np.array(im2, dtype=np.float32)
                    
                    fps = 24
                    duration = 6.0
                    total_frames = int(fps * duration)
                    
                    def make_frame(t):
                        alpha = t / duration
                        # Áp dụng hàm Smoothstep để hiệu ứng chuyển cảnh mượt mà
                        smooth_alpha = alpha * alpha * (3 - 2 * alpha)
                        frame = (1 - smooth_alpha) * arr1 + smooth_alpha * arr2
                        return np.clip(frame, 0, 255).astype(np.uint8)

                    video_clip = CompositeVideoClip([ImageClip(arr1).set_duration(duration)], size=(720, 1280))
                    video_clip = video_clip.fl(lambda gf, t: make_frame(t))
                    video_clip.fps = fps
                    
                    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_vid:
                        output_path = tmp_vid.name
                        
                    video_clip.write_videofile(output_path, codec="libx264", audio=False, verbose=False, logger=None)
                    
                    st.success("🎉 Video biến hình đã hoàn tất!")
                    with open(output_path, "rb") as f:
                        vid_bytes = f.read()
                    st.video(vid_bytes)
                    st.download_button("📥 TẢI VIDEO BIẾN HÌNH (.MP4)", data=vid_bytes, file_name="transformation_video.mp4", mime="video/mp4")
                except Exception as e:
                    st.error(f"Lỗi khi render video: {str(e)}")

# -----------------------------------------------------------------------------
# PHÂN HỆ 4: TẠO VIDEO TIKTOK / REELS TỰ ĐỘNG
# -----------------------------------------------------------------------------
elif menu == "4. 📱 Tạo Video TikTok/Reels Tự Động":
    st.subheader("📱 Xưởng Sản Xuất Video Ngắn Tự Động")
    
    api_key = st.text_input("🔑 Nhập Google Gemini API Key:", type="password")
    topic = st.text_input("📝 Chủ đề video:", placeholder="Ví dụ: 3 sự thật thú vị về vũ trụ")
    voice_choice = st.selectbox("🎙️ Chọn giọng đọc AI:", [
        "vi-VN-HoaiMyNeural (Nữ miền Bắc truyền cảm)",
        "vi-VN-NamMinhNeural (Nam miền Bắc ấm áp)"
    ])
    voice_code = voice_choice.split(" ")[0]

    if st.button("🚀 TẠO TOÀN BỘ KỊCH BẢN & GIỌNG ĐỌC", type="primary", use_container_width=True):
        if not api_key or not topic:
            st.warning("⚠️ Vui lòng nhập API Key và chủ đề video!")
        else:
            with st.spinner("🤖 Gemini đang viết kịch bản và AI đang thu âm..."):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    prompt = f"Viết một kịch bản video TikTok 30 giây hấp dẫn về chủ đề: {topic}. Viết dạng lời đọc liên tục không ngắt quãng."
                    response = model.generate_content(prompt)
                    script_text = response.text
                    
                    st.text_area("📜 Kịch bản được tạo:", value=script_text, height=150)
                    
                    # Sinh file âm thanh qua edge-tts
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_audio:
                        audio_path = tmp_audio.name
                        
                    def run_tts():
                        async def generate():
                            communicate = edge_tts.Communicate(script_text, voice_code)
                            await communicate.save(audio_path)
                        asyncio.run(generate())

                    t = threading.Thread(target=run_tts)
                    t.start()
                    t.join()

                    st.success("🎉 Đã thu âm giọng đọc AI thành công!")
                    with open(audio_path, "rb") as f:
                        st.audio(f.read(), format="audio/mp3")
                except Exception as e:
                    st.error(f"Lỗi: {str(e)}")

# -----------------------------------------------------------------------------
# PHÂN HỆ 5: SÁNG TÁC NHẠC & GHÉP MV
# -----------------------------------------------------------------------------
elif menu == "5. 🎵 Sáng Tác Nhạc & Ghép MV":
    st.subheader("🎵 Sáng Tác Lời Bài Hát & Xuất MV")
    
    music_api = st.text_input("🔑 Nhập Gemini API Key:", type="password", key="music_api")
    genre = st.selectbox("Chọn thể loại bài hát:", ["Pop Ballad sâu lắng", "Rap sôi động", "Nhạc Lo-fi Chill buồn", "Nhạc Tết Vui Tươi"])
    song_topic = st.text_input("Ý tưởng bài hát:", placeholder="Ví dụ: Tình yêu tuổi học trò")

    if st.button("✍️ SÁNG TÁC LỜI BÀI HÁT", type="primary", use_container_width=True):
        if not music_api or not song_topic:
            st.warning("⚠️ Vui lòng nhập đầy đủ thông tin!")
        else:
            with st.spinner("🎼 Đang sáng tác lời bài hát..."):
                try:
                    genai.configure(api_key=music_api)
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    prompt = f"Hãy sáng tác toàn bộ lời bài hát hoàn chỉnh gồm [Intro], [Verse 1], [Chorus], [Verse 2], [Outro] theo thể loại {genre} về đề tài {song_topic}."
                    res = model.generate_content(prompt)
                    st.session_state['song_lyrics'] = res.text
                    st.success("✅ Đã hoàn thành lời bài hát!")
                except Exception as e:
                    st.error(f"Lỗi: {str(e)}")

    if 'song_lyrics' in st.session_state:
        st.text_area("📜 Lời bài hát:", value=st.session_state['song_lyrics'], height=250)

    st.markdown("---")
    st.markdown("#### 🎬 Ghép Ảnh Bìa & Nhạc Thành File Video MV (.mp4)")
    cover_img = st.file_uploader("Tải ảnh nền MV:", type=["jpg", "png", "jpeg"], key="mv_cover")
    beat_mp3 = st.file_uploader("Tải file nhạc Beat/Vocal (.mp3):", type=["mp3", "wav"], key="mv_audio")

    if st.button("🎞️ XUẤT FILE MV (.MP4)", use_container_width=True):
        if not cover_img or not beat_mp3:
            st.warning("⚠️ Vui lòng tải đủ ảnh nền và file âm thanh!")
        else:
            with st.spinner("⏳ Đang ghép ảnh và nhạc thành MV..."):
                try:
                    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_img:
                        tmp_img.write(cover_img.getvalue())
                        img_p = tmp_img.name
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_aud:
                        tmp_aud.write(beat_mp3.getvalue())
                        aud_p = tmp_aud.name
                    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_mv:
                        out_mv_p = tmp_mv.name

                    audio_clip = AudioFileClip(aud_p)
                    # Giới hạn độ dài demo nếu cần hoặc lấy toàn bộ
                    image_clip = ImageClip(img_p).set_duration(audio_clip.duration)
                    image_clip = image_clip.set_audio(audio_clip)
                    image_clip.write_videofile(out_mv_p, fps=24, codec="libx264", audio_codec="aac", verbose=False, logger=None)

                    st.success("🎉 MV đã được kết xuất thành công!")
                    with open(out_mv_p, "rb") as f:
                        mv_bytes = f.read()
                    st.video(mv_bytes)
                    st.download_button("📥 TẢI MV (.MP4)", data=mv_bytes, file_name="music_video.mp4", mime="video/mp4")
                except Exception as e:
                    st.error(f"Lỗi ghép MV: {str(e)}")
