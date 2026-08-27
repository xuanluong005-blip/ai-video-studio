import streamlit as st
import os
import io
import asyncio
import tempfile
import urllib.parse
import requests
import numpy as np
from google import genai
from moviepy import (
    ImageClip, 
    AudioFileClip, 
    CompositeAudioClip, 
    concatenate_videoclips,
    VideoClip
)
import edge_tts
from PIL import Image, ImageEnhance

# Tự động hỗ trợ mọi định dạng ảnh điện thoại (HEIC, WEBP, JPG, PNG)
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except:
    pass

st.set_page_config(page_title="AI Studio Ultimate", page_icon="⚡", layout="centered")
st.title("⚡ AI Studio Ultimate")
st.caption("Studio Đa Năng: Video Ngắn (9:16) • Sáng Tác Nhạc • Hóa Thân & Video Gồng Songoku")

# Nhận diện Key tự động
saved_api_key = st.secrets.get("GEMINI_API_KEY", "")
if saved_api_key:
    api_key = saved_api_key
    st.success("✅ Đã tự động kết nối Gemini API Key của bạn!")
else:
    api_key = st.text_input("🔑 Gemini API Key (*):", type="password", placeholder="Nhập Gemini API Key của bạn...")

tab1, tab2, tab3 = st.tabs(["🎬 Sáng Tạo Video (9:16)", "🎵 Sáng Tác Nhạc & Lời", "⚡ Hóa Thân Songoku"])

# ==========================================
# TAB 1: TẠO VIDEO DỌC TIKTOK / REELS
# ==========================================
with tab1:
    st.subheader("1. Chọn hình ảnh minh họa")
    uploaded_files = st.file_uploader(
        "📸 Chọn ảnh từ máy / điện thoại:", 
        type=["jpg", "jpeg", "png", "heic", "webp"], 
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
            st.error("⚠️ Vui lòng nhập đầy đủ API Key, ảnh và chủ đề video!")
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
                        im = Image.open(f).convert("RGB").resize(target_size, Image.Resampling.LANCZOS)
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
            st.error("⚠️ Vui lòng nhập API Key và chủ đề bài hát!")
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
    mv_image = st.file_uploader("🖼️ Chọn ảnh bìa bài hát:", type=["jpg", "jpeg", "png", "heic", "webp"], key="mv_img_upload")
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

                    im = Image.open(mv_image).convert("RGB").resize((1080, 1920), Image.Resampling.LANCZOS)
                    im.save(img_path)

                    with open(audio_path, "wb") as f: f.write(mv_audio.read())

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
# TAB 3: HÓA THÂN & TẠO VIDEO GỒNG BIẾN HÌNH SONGOKU
# ==========================================
with tab3:
    st.subheader("⚡ Biến Ảnh Người Thật Thành Son Goku / Super Saiyan")
    goku_img_file = st.file_uploader("📸 Tải lên ảnh chân dung của bạn:", type=["jpg", "jpeg", "png", "heic", "webp"], key="goku_uploader")
    
    col_gk1, col_gk2 = st.columns(2)
    with col_gk1:
        saiyan_form = st.selectbox(
            "🔥 Chọn cấp độ biến hình (Form):",
            [
                "Super Saiyan Cấp 1 (Tóc vàng kim rực lửa)", 
                "Super Saiyan Blue (Tóc xanh dương thần thánh)", 
                "Bản Năng Vô Cực - Ultra Instinct (Tóc bạc)",
                "Son Goku Cơ Bản (Tóc đen nguyên bản)"
            ]
        )
    with col_gk2:
        art_style = st.selectbox(
            "🎨 Phong cách hình ảnh:",
            ["Điện Ảnh Thực Tế (3D Cinematic Live-Action)", "Anime Dragon Ball Cổ Điển (90s)", "Manga Siêu Nét"]
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
                
                status.write("👁️ Gemini đang quét khuôn mặt và tư thế...")
                user_image = Image.open(goku_img_file).convert("RGB")
                
                img_byte_arr = io.BytesIO()
                user_image.save(img_byte_arr, format='JPEG')
                img_bytes = img_byte_arr.getvalue()

                analysis_prompt = "Describe this person in English (gender, facial features, hair, eye angle, posture) concisely in 30 words."
                
                from google.genai import types
                analysis_res = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[
                        types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                        analysis_prompt
                    ]
                )
                person_desc = analysis_res.text.strip().replace("\n", " ")

                status.write("🔥 Đang vẽ ảnh Son Goku...")
                form_dict = {
                    "Super Saiyan Cấp 1 (Tóc vàng kim rực lửa)": "Super Saiyan with glowing spiky yellow hair, intense golden aura, teal eyes, wearing orange Turtle School gi",
                    "Super Saiyan Blue (Tóc xanh dương thần thánh)": "Super Saiyan Blue SSGSS, glowing bright cyan blue spiky hair, divine blue fire aura, orange gi",
                    "Bản Năng Vô Cực - Ultra Instinct (Tóc bạc)": "Mastered Ultra Instinct, glowing silver white spiky hair, divine celestial aura, torn orange gi",
                    "Son Goku Cơ Bản (Tóc đen nguyên bản)": "Base form Son Goku, iconic black spiky hair, classic orange and blue martial arts gi"
                }

                style_dict = {
                    "Điện Ảnh Thực Tế (3D Cinematic Live-Action)": "cinematic 8k movie still, photorealistic, intricate textures, realistic lighting, unreal engine 5",
                    "Anime Dragon Ball Cổ Điển (90s)": "classic 1990s Dragon Ball Z anime style, Akira Toriyama aesthetic, cel shaded, vintage colors",
                    "Manga Siêu Nét": "high detail dynamic Japanese manga drawing, screentone shading, sharp ink lineart"
                }

                chosen_f = form_dict[saiyan_form]
                chosen_s = style_dict[art_style]

                prompt_draw = f"Portrait transformation of {person_desc} into Son Goku character from Dragon Ball, {chosen_f}, {chosen_s}, masterpiece, highly detailed, centered"
                encoded_prompt = urllib.parse.quote(prompt_draw)

                seed_num = np.random.randint(1000, 999999)
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&model=flux&seed={seed_num}&nologo=true"

                res = requests.get(image_url, timeout=30)
                if res.status_code == 200:
                    result_img = Image.open(io.BytesIO(res.content)).convert("RGB")
                    
                    st.session_state['orig_img'] = user_image
                    st.session_state['goku_img'] = result_img
                    st.session_state['saiyan_prompt'] = (
                        f"Cinematic video transition, a person powers up violently screaming, "
                        f"golden energy aura explodes around their body, hair turns spiky golden glowing Super Saiyan, "
                        f"epic Dragon Ball live-action transformation, 8k cinematic masterpiece"
                    )

                    status.update(label="✅ Biến hình thành công!", state="complete", expanded=False)
                    st.success("🎉 Bạn đã hóa thân thành Son Goku!")

                else:
                    raise Exception("Không thể tải ảnh từ máy chủ AI.")

            except Exception as e:
                status.update(label="❌ Có lỗi xảy ra!", state="error")
                st.error(f"Chi tiết lỗi: {str(e)}")

    # Hiển thị kết quả và 2 phương án làm video
    if 'goku_img' in st.session_state and 'orig_img' in st.session_state:
        orig_pil = st.session_state['orig_img']
        goku_pil = st.session_state['goku_img']

        col_show1, col_show2 = st.columns(2)
        with col_show1:
            st.image(orig_pil, caption="Ảnh Gốc Của Bạn", use_container_width=True)
        with col_show2:
            st.image(goku_pil, caption="Ảnh Son Goku AI", use_container_width=True)

        st.markdown("---")
        st.subheader("🎬 Chọn Cách Xuất Video Biến Hình Super Saiyan:")

        tab_opt1, tab_opt2 = st.tabs(["🚀 Phương Án 1: Xuất Video Gồng Tức Thì Trên Web", "🌟 Phương Án 2: AI Video Siêu Thực (Kling/Luma)"])

        # ==========================================================
        # PHƯƠNG ÁN 1: XUẤT VIDEO GỒNG RUNG + FLASH + MORPHING
        # ==========================================================
        with tab_opt1:
            st.info("💡 Web sẽ tự động tạo video MP4 dài 6.5s: **Giai đoạn gồng rung lắc -> Lóe sáng -> Biến hình sang Goku -> Bùng nổ hào quang.**")
            
            if st.button("🎥 XUẤT VIDEO BIẾN HÌNH TỰ ĐỘNG (MP4)", use_container_width=True, key="btn_render_morph"):
                with st.spinner("Đang tổng hợp hiệu ứng chuyển động rung lắc và hào quang..."):
                    try:
                        with tempfile.TemporaryDirectory() as td:
                            target_w, target_h = 1080, 1920
                            img1_resized = orig_pil.resize((target_w, target_h), Image.Resampling.LANCZOS)
                            img2_resized = goku_pil.resize((target_w, target_h), Image.Resampling.LANCZOS)

                            img1_np = np.array(img1_resized)
                            img2_np = np.array(img2_resized)

                            total_duration = 6.5

                            def make_transformation_frame(t):
                                # 0s - 2.0s: Gồng rung lắc mạnh (Camera Shake)
                                if t < 2.0:
                                    intensity = int(12 * (t / 2.0)) + 3
                                    dx = np.random.randint(-intensity, intensity + 1)
                                    dy = np.random.randint(-intensity, intensity + 1)
                                    shifted = np.roll(img1_np, shift=(dy, dx), axis=(0, 1))
                                    return shifted
                                
                                # 2.0s - 3.5s: Lóe sáng và Morphing (Crossfade + Flash)
                                elif t < 3.5:
                                    alpha = (t - 2.0) / 1.5
                                    blended = (1 - alpha) * img1_np.astype(float) + alpha * img2_np.astype(float)
                                    
                                    # Hiệu ứng lóe chớp sáng ở khoảnh khắc nổ (2.0s - 2.4s)
                                    if t < 2.4:
                                        flash_val = (1.0 - (t - 2.0) / 0.4) * 80
                                        blended = np.clip(blended + flash_val, 0, 255)
                                    return blended.astype(np.uint8)

                                # 3.5s - 6.5s: Thể Goku hoàn chỉnh + Zoom bùng nổ
                                else:
                                    scale = 1.0 + 0.08 * ((t - 3.5) / 3.0)
                                    new_w, new_h = int(target_w * scale), int(target_h * scale)
                                    im_z = goku_pil.resize((new_w, new_h), Image.Resampling.BILINEAR)
                                    xc, yc = (new_w - target_w) // 2, (new_h - target_h) // 2
                                    cropped = im_z.crop((xc, yc, xc + target_w, yc + target_h))
                                    return np.array(cropped)

                            clip = VideoClip(make_transformation_frame, duration=total_duration)
                            out_video_path = os.path.join(td, "goku_transform.mp4")
                            clip.write_videofile(out_video_path, fps=24, codec="libx264", audio=False, logger=None)

                            with open(out_video_path, "rb") as vf:
                                video_bytes = vf.read()

                            clip.close()

                            st.success("🎉 Video biến hình đã sẵn sàng!")
                            st.video(video_bytes)
                            st.download_button(
                                "📥 Tải Video Biến Hình (.mp4)",
                                data=video_bytes,
                                file_name="Goku_Super_Saiyan_Transformation.mp4",
                                mime="video/mp4",
                                use_container_width=True
                            )

                    except Exception as e:
                        st.error(f"Lỗi xuất video: {str(e)}")

        # ==========================================================
        # PHƯƠNG ÁN 2: DÙNG KLING / LUMA DIFFUSION CHO PHIM SIÊU THỰC
        # ==========================================================
        with tab_opt2:
            st.info("""
            **Cách tạo video người thật gồng hét há miệng biến thành Saiyan 100% như phim Hollywood:**
            1. Tải 2 bức ảnh bên dưới về điện thoại.
            2. Mở web **[klingai.com](https://klingai.com)** hoặc **[lumalabs.ai/dream-machine](https://lumalabs.ai/dream-machine)** (Miễn phí).
            3. Chọn tính năng **Start Frame (Ảnh đầu)** = Ảnh gốc, và **End Frame (Ảnh cuối)** = Ảnh Goku.
            4. Dán đoạn Prompt chuẩn tiếng Anh bên dưới vào để AI kết xuất video!
            """)

            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                b1 = io.BytesIO()
                orig_pil.save(b1, format="JPEG")
                st.download_button("📥 1. Tải Start Frame (Ảnh Gốc)", b1.getvalue(), "Frame1_Original.jpg", "image/jpeg", use_container_width=True)
            with col_dl2:
                b2 = io.BytesIO()
                goku_pil.save(b2, format="JPEG")
                st.download_button("📥 2. Tải End Frame (Ảnh Goku)", b2.getvalue(), "Frame2_Goku.jpg", "image/jpeg", use_container_width=True)

            st.text_area("📋 Prompt AI Video (Copy dán vào Kling / Luma):", st.session_state['saiyan_prompt'], height=100)
