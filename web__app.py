import streamlit as st
import os
import asyncio
import tempfile
import numpy as np
import requests
from google import genai
from moviepy import (
    ImageClip, 
    AudioFileClip, 
    CompositeAudioClip, 
    concatenate_videoclips,
    VideoClip
)
import edge_tts
from PIL import Image, ImageDraw, ImageFont

# Cấu hình giao diện Web
st.set_page_config(
    page_title="AI Video Studio Pro (9:16)",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 AI Video Creator Pro (9:16)")
st.caption("Studio tạo video ngắn chuẩn CapCut: Hiệu ứng Zoom + Phụ đề + Nhạc nền")

# 1. Cấu hình Gemini API Key
api_key = st.text_input("🔑 Gemini API Key (*):", type="password", placeholder="Nhập Gemini API Key của bạn...")

# 2. Upload ảnh
uploaded_files = st.file_uploader(
    "📸 Chọn ảnh minh họa (từ thư viện ảnh):", 
    type=["jpg", "jpeg", "png"], 
    accept_multiple_files=True
)

# 3. Cấu hình âm thanh
col1, col2 = st.columns(2)
with col1:
    voice_option = st.selectbox("🎙️ Giọng đọc AI:", ["Nữ (Hoài My)", "Nam (Nam Minh)"])
with col2:
    music_option = st.selectbox(
        "🎵 Nhạc nền:", 
        ["Không dùng", "Lofi Thư Giãn", "Sôi Động / Năng Lượng", "Kịch Tính / Cuốn Hút"]
    )

# 4. Tùy chọn hiệu ứng
col3, col4 = st.columns(2)
with col3:
    enable_zoom = st.checkbox("✨ Bật hiệu ứng Zoom chuyển động", value=True)
with col4:
    enable_subtitles = st.checkbox("📝 Bật tự động gắn phụ đề chữ", value=True)

# 5. Nhập chủ đề video
topic = st.text_input("💡 Chủ đề Video:", placeholder="VD: 3 sự thật thú vị về vũ trụ...")

# Kho link nhạc nền mẫu miễn phí (Royalty-free)
MUSIC_URLS = {
    "Lofi Thư Giãn": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3?filename=lofi-study-112191.mp3",
    "Sôi Động / Năng Lượng": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3?filename=upbeat-energetic-pop-109038.mp3",
    "Kịch Tính / Cuốn Hút": "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0a13f69d2.mp3?filename=action-cinematic-trailer-14249.mp3"
}

async def create_voice(text, voice_choice, output_path):
    voice_id = "vi-VN-HoaiMyNeural" if "Hoài My" in voice_choice else "vi-VN-NamMinhNeural"
    communicate = edge_tts.Communicate(text, voice_id)
    await communicate.save(output_path)

def draw_subtitle_on_frame(pil_img, text):
    """Vẽ phụ đề chữ lên ảnh bằng PIL (chống lỗi font trên Linux/Cloud)"""
    img = pil_img.copy()
    draw = ImageDraw.Draw(img)
    width, height = img.size

    # Cắt dòng chữ tự động nếu quá dài
    words = text.split()
    lines = []
    curr_line = ""
    for w in words:
        if len(curr_line + " " + w) < 22:
            curr_line = (curr_line + " " + w).strip()
        else:
            lines.append(curr_line)
            curr_line = w
    if curr_line:
        lines.append(curr_line)

    # Thử load font mặc định hoặc font hệ thống
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 52)
    except:
        font = ImageFont.load_default()

    line_height = 65
    total_text_height = len(lines) * line_height
    y_start = height - total_text_height - 280  # Vị trí phụ đề ở 1/3 dưới màn hình

    for idx, line in enumerate(lines):
        y = y_start + idx * line_height
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) // 2

        # Hộp nền đen mờ bo tròn nổi bật chữ
        pad_x, pad_y = 20, 10
        draw.rounded_rectangle(
            [x - pad_x, y - pad_y, x + text_w + pad_x, y + line_height - 15 + pad_y],
            radius=15,
            fill=(0, 0, 0, 190)
        )
        # Viết chữ vàng/trắng nổi bật
        draw.text((x, y), line, font=font, fill="#FFEB3B")

    return img

def create_scene_clip(img_path, audio_path, subtitle_text, with_zoom, with_sub):
    """Tạo phân cảnh video kết hợp Zoom, Subtitle và Audio"""
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration
    target_w, target_h = 1080, 1920

    base_pil = Image.open(img_path).convert("RGB").resize((target_w, target_h), Image.Resampling.LANCZOS)
    if with_sub:
        base_pil = draw_subtitle_on_frame(base_pil, subtitle_text)

    base_np = np.array(base_pil)

    if with_zoom:
        def make_frame(t):
            # Tính tỉ lệ phóng to nhẹ từ 1.0 đến 1.12 theo thời gian
            scale = 1.0 + 0.12 * (t / max(duration, 0.1))
            new_w = int(target_w * scale)
            new_h = int(target_h * scale)
            
            # Phóng to và crop giữa
            im_resized = base_pil.resize((new_w, new_h), Image.Resampling.BILINEAR)
            x_crop = (new_w - target_w) // 2
            y_crop = (new_h - target_h) // 2
            cropped = im_resized.crop((x_crop, y_crop, x_crop + target_w, y_crop + target_h))
            return np.array(cropped)

        clip = VideoClip(make_frame, duration=duration)
    else:
        clip = ImageClip(base_np).with_duration(duration)

    return clip.with_audio(audio_clip)

# Nút thực thi tạo video
if st.button("🚀 BẮT ĐẦU TẠO VIDEO PRO", use_container_width=True):
    if not api_key:
        st.error("⚠️ Vui lòng nhập Gemini API Key trước!")
    elif not uploaded_files:
        st.error("⚠️ Vui lòng tải lên ít nhất một bức ảnh!")
    elif not topic:
        st.error("⚠️ Vui lòng nhập chủ đề video!")
    else:
        status = st.status("Đang khởi tạo studio...", expanded=True)
        try:
            # 1. Kịch bản AI
            status.write("🤖 Đang phân tích kịch bản theo số lượng ảnh...")
            client = genai.Client(api_key=api_key)
            prompt = f"""Hãy viết kịch bản video ngắn tiếng Việt cho nền tảng TikTok/Reels về chủ đề: '{topic}'.
Kịch bản gồm đúng {len(uploaded_files)} câu ngắn gọn, cuốn hút tương ứng với {len(uploaded_files)} bức ảnh.
Mỗi dòng là 1 câu duy nhất. Không đánh số thứ tự, không chèn chú thích."""

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
            )
            lines = [l.strip() for l in response.text.strip().split("\n") if l.strip()]

            with tempfile.TemporaryDirectory() as temp_dir:
                scene_clips = []

                # 2. Xử lý từng phân cảnh
                for i, file in enumerate(uploaded_files):
                    status.write(f"🎬 Đang dựng cảnh {i+1}/{len(uploaded_files)} (Zoom + Phụ đề)...")
                    text = lines[i] if i < len(lines) else f"Phân cảnh minh họa {i+1}."
                    
                    audio_path = os.path.join(temp_dir, f"voice_{i}.mp3")
                    asyncio.run(create_voice(text, voice_option, audio_path))

                    img_path = os.path.join(temp_dir, f"raw_img_{i}.jpg")
                    with open(img_path, "wb") as f:
                        f.write(file.read())

                    scene_clip = create_scene_clip(
                        img_path, audio_path, text, 
                        with_zoom=enable_zoom, 
                        with_sub=enable_subtitles
                    )
                    scene_clips.append(scene_clip)

                status.write("🎞️ Đang nối các phân cảnh...")
                main_video = concatenate_videoclips(scene_clips, method="compose")

                # 3. Lồng nhạc nền nếu có chọn
                if music_option != "Không dùng" and music_option in MUSIC_URLS:
                    status.write("🎵 Đang tải và ghép nhạc nền hòa âm...")
                    bg_music_path = os.path.join(temp_dir, "bg_music.mp3")
                    res = requests.get(MUSIC_URLS[music_option], timeout=15)
                    with open(bg_music_path, "wb") as mf:
                        mf.write(res.content)
                    
                    bg_audio = AudioFileClip(bg_music_path).with_duration(main_video.duration)
                    bg_audio = bg_audio.multiply_volume(0.12)  # Âm lượng nhạc nền 12% để nghe rõ giọng đọc

                    final_audio = CompositeAudioClip([main_video.audio, bg_audio])
                    main_video = main_video.with_audio(final_audio)

                # 4. Xuất file MP4
                status.write("⚡ Đang kết xuất video 9:16 chất lượng cao...")
                output_video_path = os.path.join(temp_dir, "video_capcut_style.mp4")
                main_video.write_videofile(
                    output_video_path,
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    logger=None
                )

                with open(output_video_path, "rb") as f:
                    video_bytes = f.read()

                main_video.close()
                for c in scene_clips:
                    c.close()

                status.update(label="✅ Đã hoàn tất xuất video!", state="complete", expanded=False)

                # 5. Hiển thị & Tải về
                st.success("🎉 Video của bạn đã sẵn sàng!")
                st.video(video_bytes)

                st.download_button(
                    label="📥 Tải Video Chuẩn Pro (.mp4)",
                    data=video_bytes,
                    file_name="video_capcut_ai_pro.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )

        except Exception as e:
            status.update(label="❌ Có lỗi xảy ra!", state="error")
            st.error(f"Chi tiết lỗi: {str(e)}")
