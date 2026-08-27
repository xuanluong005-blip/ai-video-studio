import streamlit as st
import os
import io
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
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

st.set_page_config(
    page_title="AI Video Studio Ultimate",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 AI Video Studio Ultimate")
st.caption("Xưởng sản xuất video ngắn tự động toàn diện trên Điện thoại & Máy tính")

# 1. Cấu hình Gemini API Key
api_key = st.text_input("🔑 Gemini API Key (*):", type="password", placeholder="Nhập Gemini API Key của bạn...")

# 2. Chế độ cung cấp hình ảnh
st.subheader("1. Nguồn hình ảnh")
image_source_mode = st.radio(
    "Chọn cách tạo hình ảnh cho video:",
    ["Tự tải ảnh từ điện thoại", "AI Tự Động Vẽ Ảnh Theo Kịch Bản (Không cần ảnh có sẵn)"],
    horizontal=True
)

uploaded_files = []
num_scenes_ai = 4
if image_source_mode == "Tự tải ảnh từ điện thoại":
    uploaded_files = st.file_uploader(
        "📸 Chọn các bức ảnh minh họa:", 
        type=["jpg", "jpeg", "png"], 
        accept_multiple_files=True
    )
else:
    num_scenes_ai = st.slider("Số lượng phân cảnh (ảnh) AI cần vẽ:", min_value=2, max_value=8, value=4)

# 3. Kịch bản & Định dạng video
st.subheader("2. Kịch bản & Khung hình")
col_sc1, col_sc2 = st.columns(2)
with col_sc1:
    aspect_ratio_choice = st.selectbox(
        "📐 Tỷ lệ khung hình:",
        ["Dọc 9:16 (TikTok, Reels, Shorts)", "Ngang 16:9 (YouTube, Web)", "Vuông 1:1 (Facebook, Insta)"]
    )
with col_sc2:
    script_style = st.selectbox(
        "🎭 Phong cách kịch bản:",
        ["Chia sẻ kiến thức / Mẹo hay", "Kể chuyện kịch tính, cuốn hút", "Review / Bán hàng hấp dẫn", "Hài hước / Giải trí"]
    )

topic = st.text_input("💡 Chủ đề Video:", placeholder="VD: 5 bí quyết quản lý thời gian hiệu quả...")

# 4. Âm thanh, Giọng đọc & Nhạc nền
st.subheader("3. Giọng đọc & Âm nhạc")
col_v1, col_v2 = st.columns(2)
with col_v1:
    voice_option = st.selectbox(
        "🎙️ Giọng đọc AI:", 
        ["Nữ miền Bắc (Hoài My)", "Nam miền Bắc (Nam Minh)", "Nữ tiếng Anh (Jenny)", "Nam tiếng Anh (Guy)"]
    )
with col_v2:
    filter_choice = st.selectbox(
        "🎨 Bộ lọc màu ảnh:", 
        ["Chuẩn (Gốc)", "Điện ảnh (Cinematic)", "Rực rỡ (Vibrant)", "Đen trắng (Vintage B&W)"]
    )

music_source = st.radio("Chọn nguồn nhạc nền:", ["Kho nhạc có sẵn", "Tải file MP3 từ máy/điện thoại", "Không dùng"], horizontal=True)
music_option = "Không dùng"
user_custom_audio = None

MUSIC_URLS = {
    "Lofi Thư Giãn": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3?filename=lofi-study-112191.mp3",
    "Sôi Động / Năng Lượng": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3?filename=upbeat-energetic-pop-109038.mp3",
    "Kịch Tính / Cinematic": "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0a13f69d2.mp3?filename=action-cinematic-trailer-14249.mp3"
}

if music_source == "Kho nhạc có sẵn":
    music_option = st.selectbox("🎵 Danh sách bài hát:", list(MUSIC_URLS.keys()))
elif music_source == "Tải file MP3 từ máy/điện thoại":
    user_custom_audio = st.file_uploader("Tải file nhạc (.mp3):", type=["mp3"])

# 5. Phụ đề & Watermark
st.subheader("4. Phụ đề & Bản quyền kênh")
col_sub1, col_sub2, col_sub3 = st.columns(3)
with col_sub1:
    enable_subtitles = st.checkbox("📝 Bật phụ đề chữ", value=True)
with col_sub2:
    sub_color = st.selectbox("Màu chữ phụ đề:", ["Vàng (#FFEB3B)", "Trắng (#FFFFFF)", "Xanh Neon (#00FFCC)"])
with col_sub3:
    sub_position = st.selectbox("Vị trí phụ đề:", ["Phía dưới (Chuẩn)", "Ở giữa màn hình", "Phía trên"])

col_eff1, col_eff2 = st.columns(2)
with col_eff1:
    enable_zoom = st.checkbox("✨ Bật hiệu ứng Zoom chuyển động", value=True)
with col_eff2:
    watermark_text = st.text_input("🏷️ Tên kênh / Logo Watermark:", placeholder="VD: @kenh_cua_toi")

# Ánh xạ cấu hình tỷ lệ khung hình
DIMENSIONS = {
    "Dọc 9:16 (TikTok, Reels, Shorts)": (1080, 1920),
    "Ngang 16:9 (YouTube, Web)": (1920, 1080),
    "Vuông 1:1 (Facebook, Insta)": (1080, 1080)
}

COLOR_MAP = {
    "Vàng (#FFEB3B)": "#FFEB3B",
    "Trắng (#FFFFFF)": "#FFFFFF",
    "Xanh Neon (#00FFCC)": "#00FFCC"
}

VOICE_MAP = {
    "Nữ miền Bắc (Hoài My)": "vi-VN-HoaiMyNeural",
    "Nam miền Bắc (Nam Minh)": "vi-VN-NamMinhNeural",
    "Nữ tiếng Anh (Jenny)": "en-US-JennyNeural",
    "Nam tiếng Anh (Guy)": "en-US-GuyNeural"
}

async def generate_voice(text, voice_id, output_path):
    communicate = edge_tts.Communicate(text, voice_id)
    await communicate.save(output_path)

def apply_color_filter(pil_img, filter_name):
    if filter_name == "Điện ảnh (Cinematic)":
        enhancer = ImageEnhance.Contrast(pil_img)
        img = enhancer.enhance(1.2)
        enhancer_c = ImageEnhance.Color(img)
        return enhancer_c.enhance(0.85)
    elif filter_name == "Rực rỡ (Vibrant)":
        enhancer = ImageEnhance.Color(pil_img)
        img = enhancer.enhance(1.35)
        enhancer_b = ImageEnhance.Brightness(img)
        return enhancer_b.enhance(1.05)
    elif filter_name == "Đen trắng (Vintage B&W)":
        return pil_img.convert("L").convert("RGB")
    return pil_img

def draw_decorations(pil_img, text, with_sub, sub_hex, pos_name, watermark):
    img = pil_img.copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size

    # Vẽ Watermark / Tên kênh
    if watermark and watermark.strip():
        try:
            wm_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
        except:
            wm_font = ImageFont.load_default()
        draw.text((40, 50), watermark.strip(), font=wm_font, fill=(255, 255, 255, 180))

    # Vẽ Phụ đề
    if with_sub and text.strip():
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
        except:
            font = ImageFont.load_default()

        words = text.split()
        lines, curr = [], ""
        for word in words:
            if len(curr + " " + word) < 24:
                curr = (curr + " " + word).strip()
            else:
                lines.append(curr)
                curr = word
        if curr:
            lines.append(curr)

        line_h = 65
        total_h = len(lines) * line_h

        if pos_name == "Phía trên":
            y_start = 180
        elif pos_name == "Ở giữa màn hình":
            y_start = (h - total_h) // 2
        else:
            y_start = h - total_h - 220

        for idx, line in enumerate(lines):
            y = y_start + idx * line_h
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            x = (w - text_w) // 2

            pad_x, pad_y = 18, 8
            draw.rounded_rectangle(
                [x - pad_x, y - pad_y, x + text_w + pad_x, y + line_h - 15 + pad_y],
                radius=12,
                fill=(0, 0, 0, 195)
            )
            draw.text((x, y), line, font=font, fill=sub_hex)

    return img

def render_scene(img_path, audio_path, subtitle_text, target_size, with_zoom, with_sub, sub_hex, pos_name, wm_text, filter_name):
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration
    target_w, target_h = target_size

    with Image.open(img_path) as base:
        base_pil = base.convert("RGB").resize(target_size, Image.Resampling.LANCZOS)
        base_pil = apply_color_filter(base_pil, filter_name)
        base_pil = draw_decorations(base_pil, subtitle_text, with_sub, sub_hex, pos_name, wm_text)

    if with_zoom:
        def make_frame(t):
            scale = 1.0 + 0.10 * (t / max(duration, 0.1))
            new_w = int(target_w * scale)
            new_h = int(target_h * scale)
            im_resized = base_pil.resize((new_w, new_h), Image.Resampling.BILINEAR)
            x_crop = (new_w - target_w) // 2
            y_crop = (new_h - target_h) // 2
            return np.array(im_resized.crop((x_crop, y_crop, x_crop + target_w, y_crop + target_h)))
        clip = VideoClip(make_frame, duration=duration)
    else:
        clip = ImageClip(np.array(base_pil)).with_duration(duration)

    return clip.with_audio(audio_clip)

# Nút thực thi chính
if st.button("🚀 BẮT ĐẦU TẠO VIDEO PRO", use_container_width=True):
    if not api_key:
        st.error("⚠️ Vui lòng nhập Gemini API Key trước!")
    elif image_source_mode == "Tự tải ảnh từ điện thoại" and not uploaded_files:
        st.error("⚠️ Vui lòng tải lên ít nhất một bức ảnh minh họa!")
    elif not topic:
        st.error("⚠️ Vui lòng nhập chủ đề video!")
    else:
        status = st.status("Đang khởi tạo studio...", expanded=True)
        try:
            client = genai.Client(api_key=api_key)
            target_dim = DIMENSIONS[aspect_ratio_choice]
            total_scenes = len(uploaded_files) if image_source_mode == "Tự tải ảnh từ điện thoại" else num_scenes_ai

            # 1. Tạo kịch bản bằng Gemini AI
            status.write("🤖 Đang phân tích kịch bản theo phong cách đã chọn...")
            prompt = f"""Hãy viết kịch bản video ngắn tiếng Việt phong cách '{script_style}' về chủ đề: '{topic}'.
Yêu cầu:
- Gồm đúng {total_scenes} câu súc tích, giàu hình tượng, phù hợp làm video ngắn.
- Mỗi câu là 1 dòng riêng biệt. Không đánh số, không thêm ghi chú."""

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
            )
            script_lines = [l.strip() for l in response.text.strip().split("\n") if l.strip()]

            with tempfile.TemporaryDirectory() as temp_dir:
                scene_images = []

                # 2. Xử lý ảnh: Tự tải lên hoặc AI tự vẽ
                if image_source_mode == "Tự tải ảnh từ điện thoại":
                    for idx, uploaded in enumerate(uploaded_files):
                        p = os.path.join(temp_dir, f"input_{idx}.jpg")
                        with open(p, "wb") as f:
                            f.write(uploaded.read())
                        scene_images.append(p)
                else:
                    # AI tự vẽ ảnh bằng Imagen
                    for idx in range(total_scenes):
                        scene_txt = script_lines[idx] if idx < len(script_lines) else topic
                        status.write(f"🎨 AI đang vẽ bức ảnh minh họa cho cảnh {idx+1}/{total_scenes}...")
                        
                        img_prompt = f"Cinematic digital photography, high details, vibrant, 8k: {scene_txt}"
                        img_res = client.models.generate_images(
                            model="imagen-3.0-generate-002",
                            prompt=img_prompt,
                            config=dict(number_of_images=1, aspect_ratio="9:16" if "9:16" in aspect_ratio_choice else "16:9")
                        )
                        p = os.path.join(temp_dir, f"ai_img_{idx}.jpg")
                        for generated_image in img_res.generated_images:
                            image = Image.open(io.BytesIO(generated_image.image.image_bytes))
                            image.save(p)
                        scene_images.append(p)

                # 3. Dựng từng phân cảnh (Giọng nói + Phụ đề + Hiệu ứng)
                scene_clips = []
                voice_id = VOICE_MAP[voice_option]
                sub_hex = COLOR_MAP[sub_color]

                for i, img_path in enumerate(scene_images):
                    status.write(f"🎬 Đang lồng tiếng và hiệu ứng cho cảnh {i+1}/{len(scene_images)}...")
                    txt = script_lines[i] if i < len(script_lines) else f"Phân cảnh minh họa {i+1}."
                    
                    audio_p = os.path.join(temp_dir, f"voice_{i}.mp3")
                    asyncio.run(generate_voice(txt, voice_id, audio_p))

                    clip = render_scene(
                        img_path, audio_p, txt, target_dim,
                        with_zoom=enable_zoom, 
                        with_sub=enable_subtitles,
                        sub_hex=sub_hex,
                        pos_name=sub_position,
                        wm_text=watermark_text,
                        filter_name=filter_choice
                    )
                    scene_clips.append(clip)

                # 4. Nối toàn bộ phân cảnh
                status.write("🎞️ Đang ghép nối toàn bộ video...")
                main_video = concatenate_videoclips(scene_clips, method="compose")

                # 5. Lồng nhạc nền
                if music_source == "Kho nhạc có sẵn" and music_option in MUSIC_URLS:
                    status.write("🎵 Đang hòa âm nhạc nền có sẵn...")
                    bg_p = os.path.join(temp_dir, "bg_music.mp3")
                    res = requests.get(MUSIC_URLS[music_option], timeout=15)
                    with open(bg_p, "wb") as f:
                        f.write(res.content)
                    bg_audio = AudioFileClip(bg_p).with_duration(main_video.duration).multiply_volume(0.12)
                    main_video = main_video.with_audio(CompositeAudioClip([main_video.audio, bg_audio]))
                elif music_source == "Tải file MP3 từ máy/điện thoại" and user_custom_audio is not None:
                    status.write("🎵 Đang hòa âm file nhạc cá nhân...")
                    bg_p = os.path.join(temp_dir, "custom_bg.mp3")
                    with open(bg_p, "wb") as f:
                        f.write(user_custom_audio.read())
                    bg_audio = AudioFileClip(bg_p).with_duration(main_video.duration).multiply_volume(0.15)
                    main_video = main_video.with_audio(CompositeAudioClip([main_video.audio, bg_audio]))

                # 6. Xuất video MP4
                status.write("⚡ Đang kết xuất video chất lượng cao...")
                output_video_path = os.path.join(temp_dir, "video_ultimate_output.mp4")
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

                status.update(label="✅ Xuất video thành công!", state="complete", expanded=False)

                st.success("🎉 Video của bạn đã tạo hoàn tất!")
                st.video(video_bytes)

                st.download_button(
                    label="📥 Tải Video Về Điện Thoại (.mp4)",
                    data=video_bytes,
                    file_name="video_ai_studio_pro.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )

        except Exception as e:
            status.update(label="❌ Có lỗi xảy ra!", state="error")
            st.error(f"Chi tiết lỗi: {str(e)}")
