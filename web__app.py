import streamlit as st
import os
import io
import asyncio
import tempfile
import numpy as np
from google import genai
from moviepy import (
    ImageClip, 
    AudioFileClip, 
    CompositeAudioClip, 
    concatenate_videoclips
)
import edge_tts
from PIL import Image

st.set_page_config(page_title="AI Studio Ultimate", page_icon="⚡", layout="centered")
st.title("⚡ AI Studio Ultimate")
st.caption("Studio Đa Năng: Video Ngắn (9:16) • Sáng Tác Nhạc • Hóa Thân Songoku AI")

# =======================================================
# TỰ ĐỘNG NHẬN DIỆN GEMINI API KEY ĐÃ LƯU TRÊN HỆ THỐNG
# =======================================================
saved_api_key = st.secrets.get("GEMINI_API_KEY", "")

if saved_api_key:
    api_key = saved_api_key
    st.success("✅ Đã tự động kết nối Gemini API Key của bạn!")
else:
    api_key = st.text_input("🔑 Gemini API Key (*):", type="password", placeholder="Nhập Gemini API Key của bạn...")

# TẠO 3 TAB CHỨC NĂNG
tab1, tab2, tab3 = st.tabs(["🎬 Sáng Tạo Video (9:16)", "🎵 Sáng Tác Nhạc & Lời", "⚡ Hóa Thân Songoku"])

# ==========================================
# TAB 1: TẠO VIDEO DỌC TIKTOK / REELS
# ==========================================
with tab1:
    st.subheader("1. Chọn hình ảnh minh họa")
    uploaded_files = st.file_uploader(
        "📸 Chọn ảnh từ máy / điện thoại:", 
        type=["jpg", "jpeg", "png"], 
        accept_multiple_files=True,
        key="uploader_vid"
    )

    st.subheader("2. Cấu hình nội dung & Giọng đọc")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        voice_option = st.selectbox("🎙️ Giọng đọc AI:", ["Nữ (Hoài My)", "Nam (Nam Minh)"])
    with col_v2:
        music_option = st.selectbox("🎵 Nhạc nền:", ["Không dùng", "Lofi Thư Giãn", "Sôi Động"])

    topic = st.text_input("💡 Chủ đề Video:", placeholder="VD: 3 thói quen giúp ngủ ngon hơn...", key="topic_vid")

    async def create_voice(text, voice_choice, output_path):
        voice_id = "vi-VN-HoaiMyNeural" if "Hoài My" in voice_choice else "vi-VN-NamMinhNeural"
        communicate = edge_tts.Communicate(text, voice_id)
        await communicate.save(output_path)

    if st.button("🚀 BẮT ĐẦU TẠO VIDEO", use_container_width=True, key="btn_create_vid"):
        if not api_key or not uploaded_files or not topic:
            st.error("⚠️ Vui lòng đảm bảo đã có API Key, ảnh minh họa và chủ đề video!")
        else:
            status = st.status("Đang dựng video...", expanded=True)
            try:
                status.write("🤖 Đang phân tích kịch bản...")
                client = genai.Client(api_key=api_key)
                prompt = f"Hãy viết kịch bản video ngắn TikTok về chủ đề '{topic}'. Gồm đúng {len(uploaded_files)} câu súc tích tương ứng {len(uploaded_files)} ảnh. Mỗi câu 1 dòng, không đánh số."
                res = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
                lines = [l.strip() for l in res.text.strip().split("\n") if l.strip()]

                with tempfile.TemporaryDirectory() as td:
                    scene_clips = []
                    target_size = (1080, 1920)

                    for idx, f in enumerate(uploaded_files):
                        status.write(f"🔄 Đang xử lý phân cảnh {idx+1}/{len(uploaded_files)}...")
                        txt = lines[idx] if idx < len(lines) else f"Nội dung minh họa số {idx+1}."
                        
                        a_path = os.path.join(td, f"v_{idx}.mp3")
                        asyncio.run(create_voice(txt, voice_option, a_path))

                        img_path = os.path.join(td, f"img_{idx}.jpg")
                        with open(img_path, "wb") as img_file:
                            img_file.write(f.read())

                        im = Image.open(img_path).convert("RGB").resize(target_size, Image.Resampling.LANCZOS)
                        im.save(img_path)

                        ac = AudioFileClip(a_path)
                        ic = ImageClip(img_path).with_duration(ac.duration).with_audio(ac)
                        scene_clips.append(ic)

                    status.write("🎬 Đang kết xuất video...")
                    final_video = concatenate_videoclips(scene_clips, method="compose")
                    out_video = os.path.join(td, "output.mp4")
                    final_video.write_videofile(out_video, fps=24, codec="libx264", audio_codec="aac", logger=None)

                    with open(out_video, "rb") as out_f:
                        video_bytes = out_f.read()

                    final_video.close()
                    for sc in scene_clips: sc.close()

                    status.update(label="✅ Đã hoàn tất!", state="complete", expanded=False)
                    st.success("🎉 Video của bạn đã sẵn sàng!")
                    st.video(video_bytes)
                    st.download_button("📥 Tải Video Về Máy", video_bytes, "video_9_16.mp4", "video/mp4", use_container_width=True)

            except Exception as e:
                status.update(label="❌ Lỗi xử lý!", state="error")
                st.error(f"Chi tiết: {str(e)}")

# ==========================================
# TAB 2: SÁNG TÁC NHẠC & LỜI BÀI HÁT
# ==========================================
with tab2:
    st.subheader("1. Sáng tác lời bài hát (Lyrics AI)")
    song_topic = st.text_input("💡 Chủ đề ca khúc:", placeholder="VD: Tình yêu tuổi học trò, Nhạc truyền động lực...")
    song_genre = st.selectbox("🎸 Thể loại âm nhạc:", ["Pop Ballad", "Rap / Hip-Hop", "Rock", "Lofi Chill", "Nhạc Quê Hương"])

    if st.button("✍️ SÁNG TÁC LỜI BÀI HÁT", use_container_width=True, key="btn_lyrics"):
        if not api_key or not song_topic:
            st.error("⚠️ Vui lòng đảm bảo đã có API Key và chủ đề bài hát!")
        else:
            with st.spinner("AI đang sáng tác lời và gieo vần..."):
                try:
                    client = genai.Client(api_key=api_key)
                    prompt = f"Sáng tác bài hát tiếng Việt phong cách {song_genre} về: '{song_topic}'. Bố cục chuẩn: [Verse 1], [Chorus], [Verse 2], [Chorus], [Bridge], [Outro]. Lời cảm xúc, vần điệu bắt tai."
                    res = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
                    st.session_state['song_lyrics'] = res.text
                except Exception as e:
                    st.error(f"Lỗi: {str(e)}")

    if 'song_lyrics' in st.session_state:
        st.text_area("📝 Lời bài hát đã tạo:", st.session_state['song_lyrics'], height=250)
        st.info("💡 **Gợi ý:** Bạn copy lời bài hát trên dán vào web **Suno.com** để tạo file MP3 có ca sĩ hát miễn phí!")

    st.subheader("2. Ghép Ảnh & Nhạc thành Music Video")
    mv_image = st.file_uploader("🖼️ Chọn ảnh bìa bài hát:", type=["jpg", "png"], key="mv_img_upload")
    mv_audio = st.file_uploader("🎵 Tải lên file nhạc MP3 (Bài hát):", type=["mp3"], key="mv_audio_upload")

    if st.button("🎬 XUẤT MUSIC VIDEO", use_container_width=True, key="btn_mv_render"):
        if not mv_image or not mv_audio:
            st.error("⚠️ Vui lòng tải đủ cả Ảnh bìa và File nhạc MP3!")
        else:
            with st.spinner("Đang ghép nhạc và ảnh thành video..."):
                with tempfile.TemporaryDirectory() as td:
                    img_path = os.path.join(td, "cover.jpg")
                    audio_path = os.path.join(td, "song.mp3")
                    out_mv = os.path.join(td, "mv.mp4")

                    with open(img_path, "wb") as f: f.write(mv_image.read())
                    with open(audio_path, "wb") as f: f.write(mv_audio.read())

                    im = Image.open(img_path).convert("RGB").resize((1080, 1920), Image.Resampling.LANCZOS)
                    im.save(img_path)

                    ac = AudioFileClip(audio_path)
                    ic = ImageClip(img_path).with_duration(ac.duration).with_audio(ac)
                    ic.write_videofile(out_mv, fps=24, codec="libx264", audio_codec="aac", logger=None)

                    with open(out_mv, "rb") as f:
                        mv_bytes = f.read()

                    ic.close()
                    ac.close()

                    st.success("🎉 Music Video đã hoàn tất!")
                    st.video(mv_bytes)
                    st.download_button("📥 Tải Music Video Về Máy", mv_bytes, "Music_Video.mp4", "video/mp4", use_container_width=True)

# ==========================================
# TAB 3: HÓA THÂN THÀNH SONGOKU (AI COSPLAY)
# ==========================================
with tab3:
    st.subheader("⚡ Biến Ảnh Người Thật Thành Son Goku / Super Saiyan")
    goku_img_file = st.file_uploader("📸 Tải lên ảnh chân dung hoặc toàn thân của bạn:", type=["jpg", "jpeg", "png"], key="goku_uploader")
    
    col_gk1, col_gk2 = st.columns(2)
    with col_gk1:
        saiyan_form = st.selectbox(
            "🔥 Chọn cấp độ biến hình (Form):",
            [
                "Super Saiyan Cấp 1 (Tóc vàng kim rực lửa)", 
                "Super Saiyan Blue (Tóc xanh dương thần thánh)", 
                "Bản Năng Vô Cực - Ultra Instinct (Tóc bạc, hào quang trắng)",
                "Son Goku Cơ Bản (Tóc đen nguyên bản, áo cam xanh)"
            ]
        )
    with col_gk2:
        art_style = st.selectbox(
            "🎨 Phong cách hình ảnh:",
            ["Điện Ảnh Thực Tế (Photorealistic / 3D Live-Action)", "Anime Dragon Ball Cổ Điển (Akira Toriyama 90s)", "Manga Đen Trắng Siêu Nét"]
        )

    if st.button("⚡ BIẾN HÌNH THÀNH SONGOKU NGAY", use_container_width=True, key="btn_goku"):
        if not api_key:
            st.error("⚠️ Vui lòng đảm bảo đã kết nối Gemini API Key!")
        elif not goku_img_file:
            st.error("⚠️ Vui lòng tải lên 1 bức ảnh chân dung!")
        else:
            status = st.status("⚡ Đang kích hoạt siêu Saiyan...", expanded=True)
            try:
                client = genai.Client(api_key=api_key)
                
                status.write("👁️ AI đang phân tích khuôn mặt và đặc điểm ảnh gốc...")
                user_image = Image.open(goku_img_file)
                
                analysis_prompt = (
                    "Hãy mô tả chi tiết người trong bức ảnh này (giới tính, góc mặt, biểu cảm khuôn mặt, "
                    "hướng nhìn, tư thế cơ thể) bằng tiếng Anh để làm prompt tái tạo nhân vật."
                )
                analysis_res = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[analysis_prompt, user_image]
                )
                person_desc = analysis_res.text.strip()

                status.write("🔥 Đang tích tụ Ki và triệu hồi hào quang Saiyan...")
                
                form_prompt_map = {
                    "Super Saiyan Cấp 1 (Tóc vàng kim rực lửa)": "Super Saiyan with glowing spiky golden yellow hair, vibrant golden energy aura, teal eyes, wearing iconic orange and dark blue martial arts gi with blue wristbands.",
                    "Super Saiyan Blue (Tóc xanh dương thần thánh)": "Super Saiyan God Super Saiyan (SSGSS Blue), glowing bright cyan blue spiky hair, divine blue fire energy aura, blue eyes, wearing orange martial arts gi.",
                    "Bản Năng Vô Cực - Ultra Instinct (Tóc bạc, hào quang trắng)": "Mastered Ultra Instinct form, glowing silver-white spiky hair, silver eyes, divine celestial galaxy aura, intense calm expression, shredded orange gi.",
                    "Son Goku Cơ Bản (Tóc đen nguyên bản, áo cam xanh)": "Base form Son Goku, iconic black spiky anime hair, confident smirk, wearing classic orange and navy blue Turtle School gi."
                }
                
                style_prompt_map = {
                    "Điện Ảnh Thực Tế (Photorealistic / 3D Live-Action)": "Cinematic live-action movie still, 8k resolution, photorealistic, intricate fabric texture, hyper-detailed lighting and sparks.",
                    "Anime Dragon Ball Cổ Điển (Akira Toriyama 90s)": "Iconic 1990s Dragon Ball Z anime art style, Akira Toriyama aesthetic, cel-shaded, sharp line art, vibrant vintage colors.",
                    "Manga Đen Trắng Siêu Nét": "High-contrast Japanese manga illustration, dynamic speed lines, screentone shading, ultra detailed ink drawing."
                }

                chosen_form = form_prompt_map[saiyan_form]
                chosen_style = style_prompt_map[art_style]

                final_image_prompt = (
                    f"A transformation of this person: {person_desc}. "
                    f"Transformed into Son Goku character from Dragon Ball: {chosen_form}. "
                    f"Art style: {chosen_style}. Masterpiece, dynamic fighting stance, epic composition."
                )

                status.write("🎨 Đang kết xuất bức ảnh Son Goku hoàn chỉnh...")
                gen_result = client.models.generate_images(
                    model="imagen-3.0-generate-002",
                    prompt=final_image_prompt,
                    config=dict(number_of_images=1, aspect_ratio="9:16")
                )

                for generated_image in gen_result.generated_images:
                    result_img = Image.open(io.BytesIO(generated_image.image.image_bytes))
                    
                    status.update(label="✅ Biến hình thành công!", state="complete", expanded=False)
                    st.success("🎉 Bức ảnh Son Goku của bạn đã được tạo thành công!")
                    
                    col_show1, col_show2 = st.columns(2)
                    with col_show1:
                        st.image(user_image, caption="Ảnh Gốc Của Bạn", use_container_width=True)
                    with col_show2:
                        st.image(result_img, caption="Phiên Bản Son Goku AI", use_container_width=True)

                    buf = io.BytesIO()
                    result_img.save(buf, format="JPEG", quality=95)
                    st.download_button(
                        label="📥 Tải Ảnh Son Goku Siêu Nét Về Máy",
                        data=buf.getvalue(),
                        file_name="Songoku_AI_Cosplay.jpg",
                        mime="image/jpeg",
                        use_container_width=True
                    )

            except Exception as e:
                status.update(label="❌ Có lỗi xảy ra!", state="error")
                st.error(f"Chi tiết lỗi: {str(e)}")
