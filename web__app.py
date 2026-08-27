import streamlit as st
import os
import asyncio
import tempfile
from google import genai
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
import edge_tts
from PIL import Image

# Cấu hình giao diện tối ưu cho Điện Thoại & Máy Tính
st.set_page_config(
    page_title="AI Video Studio (9:16)",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 AI Video Creator (9:16)")
st.caption("Ứng dụng web tự động tạo video ngắn cho TikTok/Reels/Shorts")

# 1. Nhập API Key
api_key = st.text_input("🔑 Gemini API Key (*):", type="password", placeholder="Nhập Gemini API Key của bạn...")

# 2. Upload ảnh
uploaded_files = st.file_uploader(
    "📸 Chọn các bức ảnh minh họa (từ thư viện ảnh):", 
    type=["jpg", "jpeg", "png"], 
    accept_multiple_files=True
)

# 3. Tùy chọn giọng đọc
voice_option = st.selectbox("🎙️ Chọn giọng đọc AI:", ["Nữ (Hoài My)", "Nam (Nam Minh)"])

# 4. Nhập chủ đề video
topic = st.text_input("💡 Chủ đề Video:", placeholder="VD: 3 thói quen giúp bảo vệ cột sống lưng...")

# Hàm tạo giọng đọc
async def create_voice(text, voice_choice, output_path):
    voice_id = "vi-VN-HoaiMyNeural" if "Hoài My" in voice_choice else "vi-VN-NamMinhNeural"
    communicate = edge_tts.Communicate(text, voice_id)
    await communicate.save(output_path)

# Nút thực thi
if st.button("🚀 BẮT ĐẦU TẠO VIDEO", use_container_width=True):
    if not api_key:
        st.error("⚠️ Vui lòng nhập Gemini API Key trước khi bấm tạo video!")
    elif not uploaded_files:
        st.error("⚠️ Vui lòng tải lên ít nhất một bức ảnh!")
    elif not topic:
        st.error("⚠️ Vui lòng nhập chủ đề video!")
    else:
        status = st.status("Đang tiến hành tạo video...", expanded=True)
        try:
            # 1. Gọi AI viết kịch bản
            status.write("🤖 Đang phân tích kịch bản theo số lượng ảnh...")
            client = genai.Client(api_key=api_key)
            prompt = f"""Hãy viết kịch bản video ngắn tiếng Việt cho nền tảng TikTok/Reels về chủ đề: '{topic}'.
Kịch bản gồm đúng {len(uploaded_files)} câu ngắn gọn, súc tích tương ứng với {len(uploaded_files)} bức ảnh.
Mỗi dòng là 1 câu duy nhất. Không đánh số thứ tự, không chèn chú thích."""

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
            )
            lines = [l.strip() for l in response.text.strip().split("\n") if l.strip()]

            # 2. Dựng từng phân cảnh trong thư mục tạm
            with tempfile.TemporaryDirectory() as temp_dir:
                scene_clips = []
                target_size = (1080, 1920) # Chuẩn tỷ lệ dọc 9:16 cho điện thoại

                for i, file in enumerate(uploaded_files):
                    status.write(f"🔄 Đang xử lý phân cảnh {i+1}/{len(uploaded_files)}...")
                    
                    # Lời đọc phân cảnh
                    text = lines[i] if i < len(lines) else f"Nội dung minh họa cho cảnh số {i+1}."
                    
                    # Tạo audio
                    audio_path = os.path.join(temp_dir, f"voice_{i}.mp3")
                    asyncio.run(create_voice(text, voice_option, audio_path))

                    # Resize ảnh chuẩn 9:16
                    img = Image.open(file).convert("RGB")
                    img_resized = img.resize(target_size, Image.Resampling.LANCZOS)
                    img_path = os.path.join(temp_dir, f"img_{i}.jpg")
                    img_resized.save(img_path)

                    # Khớp thời lượng ảnh với giọng đọc
                    audio_clip = AudioFileClip(audio_path)
                    img_clip = ImageClip(img_path).with_duration(audio_clip.duration)
                    img_clip = img_clip.with_audio(audio_clip)
                    scene_clips.append(img_clip)

                # 3. Ghép nối video
                status.write("🎬 Đang xuất file MP4 hoàn chỉnh...")
                final_video = concatenate_videoclips(scene_clips, method="compose")
                output_video_path = os.path.join(temp_dir, "output_mobile_video.mp4")
                
                final_video.write_videofile(
                    output_video_path,
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    logger=None
                )

                # Đọc video vào bộ nhớ để hiển thị và tải
                with open(output_video_path, "rb") as f:
                    video_bytes = f.read()

                final_video.close()
                for clip in scene_clips:
                    clip.close()

                status.update(label="✅ Tạo video thành công!", state="complete", expanded=False)

                # 4. Hiển thị video và nút tải về
                st.success("🎉 Video của bạn đã sẵn sàng!")
                st.video(video_bytes)

                st.download_button(
                    label="📥 Tải Video Về Thiết Bị (.mp4)",
                    data=video_bytes,
                    file_name="video_tiktok_9_16.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )

        except Exception as e:
            status.update(label="❌ Có lỗi xảy ra!", state="error")
            st.error(f"Chi tiết lỗi: {str(e)}")