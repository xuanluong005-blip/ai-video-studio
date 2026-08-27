import streamlit as st
import os
import io
import time
import asyncio
import tempfile
import urllib.parse
import requests
import numpy as np
from google import genai
from google.genai import types
from moviepy import (
    ImageClip, 
    AudioFileClip, 
    CompositeAudioClip, 
    concatenate_videoclips,
    VideoClip
)
import edge_tts
from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass

st.set_page_config(page_title="AI Studio Ultimate", page_icon="✨", layout="centered")

# Hàm gọi Gemini với cơ chế tự động thử lại và đổi mô hình dự phòng
def generate_content_with_fallback(client, contents, primary_model="gemini-2.5-flash"):
    candidate_models = [
        primary_model,
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-2.5-pro"
    ]
    
    last_err = None
    for model_name in candidate_models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                last_err = e
                time.sleep(1.5)
    raise last_err

BANNER_URLS = {
    "HERO": "https://image.pollinations.ai/prompt/Futuristic%20creative%20AI%20video%20and%20music%20production%20studio,%20glowing%20neon%20holograms,%20Super%20Saiyan%20energy%20and%20dancing%20characters,%20ultra%20vibrant%203D%20cinematic%20digital%20art,%208k%20masterpiece?width=1200&height=400&model=flux&seed=777&nologo=true",
    "TRANSFORM": "https://image.pollinations.ai/prompt/Epic%20character%20transformation,%20split%20view%20between%20Super%20Saiyan%20golden%20hair%20and%20giant%20muscular%20hero,%20energetic%20lighting%20sparks,%20cinematic%203D%20render,%208k?width=1080&height=350&model=flux&seed=888&nologo=true",
    "VIDEO": "https://image.pollinations.ai/prompt/Social%20media%20short%20video%20creator%20concept,%209:16%20smartphone%20screen%20floating%20with%20cinematic%20scenes,%20subtitles,%20vibrant%20colors,%203D%20render?width=1080&height=350&model=flux&seed=999&nologo=true",
    "MEME": "https://image.pollinations.ai/prompt/Funny%20chubby%20cute%20baby%20wearing%20sunglasses%20dancing%20hip-hop%20on%20stage%20with%20colorful%20lights,%20joyful%203D%20animation%20style,%20high%20detail?width=1080&height=350&model=flux&seed=555&nologo=true",
    "MUSIC": "https://image.pollinations.ai/prompt/Neon%20glowing%20music%20studio,%20floating%20musical%20notes,%20soundwaves,%20headphones,%20cyberpunk%20aesthetic,%20ultra%20detailed%203D?width=1080&height=350&model=flux&seed=333&nologo=true"
}

st.image(BANNER_URLS["HERO"], use_container_width=True)
st.title("✨ AI Studio Ultimate")
st.caption("Nền tảng sáng tạo đa phương tiện: Video TikTok • Biến Hình AI • Nhảy Meme • Sáng Tác Nhạc")

saved_api_key = st.secrets.get("GEMINI_API_KEY", "")
if saved_api_key:
    api_key = saved_api_key
    st.success("✅ Đã tự động kết nối Gemini API Key!")
else:
    api_key = st.text_input("🔑 Gemini API Key (*):", type="password", placeholder="Nhập Gemini API Key của bạn...")

st.markdown("### 🎯 Chọn Chức Năng Bạn Muốn Dùng:")
feature_choice = st.radio(
    "Danh sách tính năng:",
    [
        "🎭 Vũ Trụ Biến Hình AI (Phình to, Goku, Anime...)",
        "🎬 Tạo Video Ngắn (TikTok/Reels)",
        "🕺 Video Nhảy & Biểu Cảm Meme",
        "🎵 Sáng Tác Nhạc & Lời"
    ],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown("---")

# ==========================================================
# 1. VŨ TRỤ BIẾN HÌNH AI
# ==========================================================
if feature_choice == "🎭 Vũ Trụ Biến Hình AI (Phình to, Goku, Anime...)":
    st.image(BANNER_URLS["TRANSFORM"], caption="⚡ Vũ Trụ Biến Hình AI: Giữ Nguyên Gương Mặt Thật", use_container_width=True)
    st.subheader("🎭 Vũ Trụ Biến Hình AI (Khóa Nét Mặt Gốc)")
    st.caption("Tải ảnh chân dung rõ mặt, AI sẽ phân tích và giữ nét mặt của bạn khi biến hình!")

    trans_img_file = st.file_uploader(
        "📸 Tải lên ảnh chân dung cận mặt của bạn:", 
        type=["jpg", "jpeg", "png", "heic", "webp"], 
        key="trans_uploader"
    )

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        transform_mode = st.selectbox(
            "🔮 Chọn kiểu biến hình:",
            [
                "💪 Phình To Cơ Bắp (Lực Sĩ Thể Hình Khổng Lồ)",
                "🎈 Phình To Tròn Bụng (Mập Mạp Meme Đáng Yêu)",
                "⚡ Siêu Saiyan Son Goku (Tóc Vàng Rực Lửa)",
                "🌌 Son Goku Bản Năng Vô Cực (Tóc Bạc)",
                "🧒 Biến Về Em Bé 5 Tuổi (Baby Face)",
                "👴 Du Hành Tương Lai 80 Tuổi (Lão Hóa Tóc Bạc)",
                "🥷 Ninja Hokage (Làng Lá Naruto)",
                "🦾 Người Máy Chiến Binh (Cyberpunk Cyborg)",
                "👑 Tổng Tài Quyền Lực (Vest Tuxedo Doanh Nhân)"
            ]
        )
    with col_t2:
        art_style = st.selectbox(
            "🎨 Phong cách hình ảnh:",
            [
                "Điện Ảnh Thực Tế (Photorealistic / 3D Live-Action)", 
                "Anime Nhật Bản Sắc Nét (Anime Art Style)", 
                "Tranh Sơn Dầu Nghệ Thuật (Classic Oil Painting)",
                "Manga Đen Trắng Đậm Chất (Comic Book Style)"
            ]
        )

    if st.button("✨ BIẾN HÌNH GIỮ GƯƠNG MẶT NGAY", use_container_width=True, key="btn_execute_trans"):
        if not api_key:
            st.error("⚠️ Vui lòng đảm bảo đã kết nối Gemini API Key!")
        elif not trans_img_file:
            st.error("⚠️ Vui lòng tải lên 1 bức ảnh chân dung rõ mặt!")
        else:
            status = st.status("🔮 Đang quét và khóa nét gương mặt thật...", expanded=True)
            try:
                client = genai.Client(api_key=api_key)
                user_image = Image.open(trans_img_file).convert("RGB")
                
                img_byte_arr = io.BytesIO()
                user_image.save(img_byte_arr, format='JPEG', quality=85)
                img_bytes = img_byte_arr.getvalue()

                status.write("👁️ Đang trích xuất tỉ lệ khuôn mặt, mắt, mũi, cằm...")
                analysis_prompt = (
                    "Look closely at the person in this image. Write a detailed description focusing ONLY on their "
                    "facial identity: exact ethnicity, face shape, jawline, eye shape, nose structure, lips, skin tone, "
                    "and current facial expression. Format as a concise description under 30 words."
                )
                
                contents_payload = [
                    types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                    analysis_prompt
                ]
                
                person_desc_text = generate_content_with_fallback(client, contents_payload)
                person_desc = person_desc_text.strip().replace("\n", " ")

                status.write("🎨 Đang kết hợp gương mặt gốc với hiệu ứng biến hình...")

                effect_prompt_map = {
                    "💪 Phình To Cơ Bắp (Lực Sĩ Thể Hình Khổng Lồ)": "transformed body with massive shredded bodybuilder muscles, giant vascular biceps and traps, keeping the exact same facial identity, heroic power pose",
                    "🎈 Phình To Tròn Bụng (Mập Mạp Meme Đáng Yêu)": "funny chubby exaggerated round body with cute puffy cheeks, keeping the identical face features, hilarious cartoonish proportions",
                    "⚡ Siêu Saiyan Son Goku (Tóc Vàng Rực Lửa)": "exact same face features and face shape of the person, transformed into Super Saiyan with glowing spiky yellow hair, intense golden aura, teal eyes, orange martial arts gi",
                    "🌌 Son Goku Bản Năng Vô Cực (Tóc Bạc)": "exact same face features of the person, with Mastered Ultra Instinct silver spiky hair, silver eyes, divine celestial galaxy aura, battle-torn gi",
                    "🧒 Biến Về Em Bé 5 Tuổi (Baby Face)": "young toddler version keeping the identical eyes and facial features of this person, cute baby cheeks, youthful innocence",
                    "👴 Du Hành Tương Lai 80 Tuổi (Lão Hóa Tóc Bạc)": "elderly aged version preserving the person's exact bone structure and eyes, realistic skin aging, silver white hair and beard",
                    "🥷 Ninja Hokage (Làng Lá Naruto)": "exact same person wearing Konoha Hokage cloak and forehead protector, dramatic ninja battle stance, maintaining original face identity",
                    "🦾 Người Máy Chiến Binh (Cyberpunk Cyborg)": "exact same face of the person with half metallic cybernetic implants, glowing neon blue optic eye, high-tech carbon fiber armor",
                    "👑 Tổng Tài Quyền Lực (Vest Tuxedo Doanh Nhân)": "exact same person dressed in luxury black bespoke Italian tuxedo, billionaire CEO aesthetic, lavish penthouse background"
                }

                style_prompt_map = {
                    "Điện Ảnh Thực Tế (Photorealistic / 3D Live-Action)": "photorealistic portrait, 8k movie still, maintaining original person's face identity, highly detailed skin texture, cinematic lighting",
                    "Anime Nhật Bản Sắc Nét (Anime Art Style)": "anime character illustration keeping the distinct facial features of the original person, vibrant studio art style, sharp cel shading",
                    "Tranh Sơn Dầu Nghệ Thuật (Classic Oil Painting)": "classic museum oil portrait preserving facial likeness, rich brushwork, chiaroscuro lighting",
                    "Manga Đen Trắng Đậm Chất (Comic Book Style)": "high-contrast manga drawing capturing the person's exact likeness, screentone shading, dynamic lineart"
                }

                chosen_effect = effect_prompt_map[transform_mode]
                chosen_style = style_prompt_map[art_style]

                prompt_draw = (
                    f"A portrait of a person with the EXACT facial features: ({person_desc}). "
                    f"Transformation applied: {chosen_effect}. "
                    f"Style: {chosen_style}. Masterpiece, face closely resembles the subject, sharp focus, centered."
                )
                encoded_prompt = urllib.parse.quote(prompt_draw)

                seed_num = np.random.randint(1000, 999999)
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=720&height=1280&model=flux&seed={seed_num}&nologo=true"

                res = requests.get(image_url, timeout=35)
                if res.status_code == 200:
                    buf_orig = io.BytesIO()
                    user_image.save(buf_orig, format="JPEG")
                    st.session_state['trans_orig_bytes'] = buf_orig.getvalue()
                    st.session_state['trans_result_bytes'] = res.content
                    status.update(label="✅ Biến hình hoàn tất!", state="complete", expanded=False)
                    st.success("🎉 Tác phẩm biến hình đã hoàn thành với khuôn mặt của bạn!")
                else:
                    raise Exception("Không thể tải ảnh từ máy chủ vẽ tranh.")

            except Exception as e:
                status.update(label="❌ Có lỗi xảy ra!", state="error")
                st.error(f"Chi tiết lỗi: {str(e)}")

    if 'trans_result_bytes' in st.session_state and 'trans_orig_bytes' in st.session_state:
        orig_pil = Image.open(io.BytesIO(st.session_state['trans_orig_bytes']))
        result_pil = Image.open(io.BytesIO(st.session_state['trans_result_bytes']))

        col_show1, col_show2 = st.columns(2)
        with col_show1:
            st.image(orig_pil, caption="Ảnh Gốc Của Bạn", use_container_width=True)
        with col_show2:
            st.image(result_pil, caption="Ảnh Sau Biến Hình", use_container_width=True)

        st.download_button(
            label="📥 Tải Ảnh Biến Hình Về Điện Thoại",
            data=st.session_state['trans_result_bytes'],
            file_name="AI_Transform_Result.jpg",
            mime="image/jpeg",
            use_container_width=True
        )

# ==========================================================
# 2. TẠO VIDEO NGẮN TIKTOK / REELS
# ==========================================================
elif feature_choice == "🎬 Tạo Video Ngắn (TikTok/Reels)":
    st.image(BANNER_URLS["VIDEO"], caption="🎬 Xưởng Tạo Video TikTok / Reels Tự Động", use_container_width=True)
    st.subheader("🎬 Xưởng Tạo Video Ngắn 9:16 Tự Động")
    uploaded_files = st.file_uploader(
        "📸 Chọn các bức ảnh minh họa:", 
        type=["jpg", "jpeg", "png", "heic", "webp"], 
        accept_multiple_files=True,
        key="uploader_vid"
    )

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
                
                res_text = generate_content_with_fallback(client, prompt)
                lines = [l.strip() for l in res_text.strip().split("\n") if l.strip()]

                with tempfile.TemporaryDirectory() as td:
                    scene_clips = []
                    target_size = (720, 1280)

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
                    for sc in scene_clips:
                        sc.close()

                    status.update(label="✅ Đã hoàn tất!", state="complete", expanded=False)
                    st.success("🎉 Video của bạn đã sẵn sàng!")
                    st.video(video_bytes)
                    st.download_button("📥 Tải Video Về Máy", video_bytes, "video_9_16.mp4", "video/mp4", use_container_width=True)

            except Exception as e:
                status.update(label="❌ Lỗi xử lý!", state="error")
                st.error(f"Chi tiết: {str(e)}")

# ==========================================================
# 3. VIDEO NHẢY & BIỂU CẢM MEME
# ==========================================================
elif feature_choice == "🕺 Video Nhảy & Biểu Cảm Meme":
    st.image(BANNER_URLS["MEME"], caption="🕺 Tạo Video Nhảy Meme Vui Nhộn & Biểu Cảm Khuôn Mặt", use_container_width=True)
    st.subheader("🕺 Biến Ảnh Thành Video Nhảy & Biểu Cảm Meme")
    st.caption("Tải ảnh em bé, thú cưng hoặc người thân để tạo video nhún nhảy theo nhạc vui nhộn!")

    meme_img_file = st.file_uploader(
        "📸 Tải ảnh chân dung hoặc toàn thân:", 
        type=["jpg", "jpeg", "png", "heic", "webp"], 
        key="meme_uploader"
    )

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        dance_style = st.selectbox(
            "💃 Chọn điệu nhảy / Động tác:",
            [
                "Nhún Nhảy Meme Đáng Yêu (Chubby Baby Dance)",
                "Lắc Đầu Theo Nhịp Nhạc (Head Bobbing Rhythm)",
                "Nhảy Hip-Hop Cực Ngầu (Street Dance Groove)",
                "Biểu Cảm Hài Hước Cười Mỉm (Funny Smirk & Wink)"
            ]
        )
    with col_m2:
        meme_music = st.selectbox(
            "🎵 Nhạc nền Meme vui nhộn:",
            ["Nhạc Vui Nhộn / Hài Hước", "Nhạc Pop Năng Động", "Không dùng nhạc"]
        )

    MEME_AUDIO_URLS = {
        "Nhạc Vui Nhộn / Hài Hước": "https://cdn.pixabay.com/download/audio/2022/10/14/audio_9939f792cb.mp3?filename=funny-kids-123497.mp3",
        "Nhạc Pop Năng Động": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3?filename=upbeat-energetic-pop-109038.mp3"
    }

    if st.button("🚀 TẠO VIDEO NHẢY MEME NGAY", use_container_width=True, key="btn_create_meme"):
        if not meme_img_file:
            st.error("⚠️ Vui lòng tải lên 1 bức ảnh chân dung hoặc em bé!")
        else:
            status = st.status("🕺 Đang phân tích và tạo chuyển động nhún nhảy...", expanded=True)
            try:
                user_meme_img = Image.open(meme_img_file).convert("RGB")
                status.write("🎬 Đang tổng hợp hiệu ứng nhún nhảy theo nhịp nhạc...")
                with tempfile.TemporaryDirectory() as td:
                    target_w, target_h = 540, 960
                    meme_resized = user_meme_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    duration_dance = 6.0

                    def make_dance_frame(t):
                        bounce_y = int(18 * np.sin(2 * np.pi * 2.0 * t))
                        tilt_x = int(12 * np.cos(2 * np.pi * 1.0 * t))
                        scale = 1.0 + 0.04 * np.sin(2 * np.pi * 2.0 * t)
                        nw, nh = int(target_w * scale), int(target_h * scale)
                        im_b = meme_resized.resize((nw, nh), Image.Resampling.BILINEAR)
                        xc, yc = (nw - target_w) // 2, (nh - target_h) // 2
                        cropped = im_b.crop((xc, yc, xc + target_w, yc + target_h))
                        frame_np = np.array(cropped)
                        return np.roll(frame_np, shift=(bounce_y, tilt_x), axis=(0, 1))

                    dance_clip = VideoClip(make_dance_frame, duration=duration_dance)

                    if meme_music != "Không dùng nhạc" and meme_music in MEME_AUDIO_URLS:
                        status.write("🎵 Đang ghép nhạc nền vui nhộn...")
                        bg_p = os.path.join(td, "meme_music.mp3")
                        r_audio = requests.get(MEME_AUDIO_URLS[meme_music], timeout=15)
                        with open(bg_p, "wb") as af:
                            af.write(r_audio.content)
                        audio_c = AudioFileClip(bg_p).with_duration(duration_dance)
                        dance_clip = dance_clip.with_audio(audio_c)

                    out_dance_path = os.path.join(td, "meme_dance.mp4")
                    dance_clip.write_videofile(out_dance_path, fps=24, codec="libx264", audio_codec="aac" if meme_music != "Không dùng nhạc" else None, logger=None)

                    with open(out_dance_path, "rb") as vf:
                        st.session_state['meme_video_bytes'] = vf.read()

                    dance_clip.close()

                status.update(label="✅ Đã tạo video nhảy Meme thành công!", state="complete", expanded=False)
                st.success("🎉 Video nhún nhảy vui nhộn của bạn đã hoàn tất!")

            except Exception as e:
                status.update(label="❌ Có lỗi xảy ra!", state="error")
                st.error(f"Chi tiết lỗi: {str(e)}")

    if 'meme_video_bytes' in st.session_state:
        st.video(st.session_state['meme_video_bytes'])
        st.download_button(
            "📥 Tải Video Nhảy Meme (.mp4)",
            data=st.session_state['meme_video_bytes'],
            file_name="AI_Meme_Dance.mp4",
            mime="video/mp4",
            use_container_width=True
        )

# ==========================================================
# 4. SÁNG TÁC NHẠC & LỜI
# ==========================================================
elif feature_choice == "🎵 Sáng Tác Nhạc & Lời":
    st.image(BANNER_URLS["MUSIC"], caption="🎵 AI Studio Sáng Tác Nhạc & Phổ Thơ", use_container_width=True)
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
                    res_lyrics = generate_content_with_fallback(client, prompt)
                    st.session_state['song_lyrics'] = res_lyrics
                except Exception as e:
                    st.error(f"Lỗi: {str(e)}")

    if 'song_lyrics' in st.session_state:
        st.text_area("📝 Lời bài hát đã tạo:", st.session_state['song_lyrics'], height=250)
        st.info("💡 Bạn copy lời bài hát trên dán vào **Suno.com** để tạo file MP3 có ca sĩ hát miễn phí!")

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

                    im = Image.open(mv_image).convert("RGB").resize((720, 1280), Image.Resampling.LANCZOS)
                    im.save(img_path)

                    with open(audio_path, "wb") as f:
                        f.write(mv_audio.read())

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
