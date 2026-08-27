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
from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except:
    pass

st.set_page_config(page_title="AI Studio Ultimate", page_icon="✨", layout="centered")

# ==========================================================
# ẢNH ĐẠI DIỆN VÀ BANNER CHỨC NĂNG SỐNG ĐỘNG (HD)
# ==========================================================
BANNER_URLS = {
    "HERO": "https://image.pollinations.ai/prompt/Futuristic%20creative%20AI%20video%20and%20music%20production%20studio,%20glowing%20neon%20holograms,%20Super%20Saiyan%20energy%20and%20dancing%20characters,%20ultra%20vibrant%203D%20cinematic%20digital%20art,%208k%20masterpiece?width=1200&height=400&model=flux&seed=777&nologo=true",
    "TRANSFORM": "https://image.pollinations.ai/prompt/Epic%20character%20transformation,%20split%20view%20between%20Super%20Saiyan%20golden%20hair%20and%20giant%20muscular%20hero,%20energetic%20lighting%20sparks,%20cinematic%203D%20render,%208k?width=1080&height=350&model=flux&seed=888&nologo=true",
    "VIDEO": "https://image.pollinations.ai/prompt/Social%20media%20short%20video%20creator%20concept,%209:16%20smartphone%20screen%20floating%20with%20cinematic%20scenes,%20subtitles,%20vibrant%20colors,%203D%20render?width=1080&height=350&model=flux&seed=999&nologo=true",
    "MEME": "https://image.pollinations.ai/prompt/Funny%20chubby%20cute%20baby%20wearing%20sunglasses%20dancing%20hip-hop%20on%20stage%20with%20colorful%20lights,%20joyful%203D%20animation%20style,%20high%20detail?width=1080&height=350&model=flux&seed=555&nologo=true",
    "MUSIC": "https://image.pollinations.ai/prompt/Neon%20glowing%20music%20studio,%20floating%20musical%20notes,%20soundwaves,%20headphones,%20cyberpunk%20aesthetic,%20ultra%20detailed%203D?width=1080&height=350&model=flux&seed=333&nologo=true"
}

# 1. Hiển thị Banner mở đầu
st.image(BANNER_URLS["HERO"], use_container_width=True)
st.title("✨ AI Studio Ultimate")
st.caption("Nền tảng sáng tạo đa phương tiện: Video TikTok • Biến Hình AI • Nhảy Meme • Sáng Tác Nhạc")

# 2. Tự động kết nối Key
saved_api_key = st.secrets.get("GEMINI_API_KEY", "")
if saved_api_key:
    api_key = saved_api_key
    st.success("✅ Đã tự động kết nối Gemini API Key!")
else:
    api_key = st.text_input("🔑 Gemini API Key (*):", type="password", placeholder="Nhập Gemini API Key của bạn...")

# 3. Menu chọn chức năng
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
# 1. VŨ TRỤ BIẾN HÌNH AI ĐA DẠNG
# ==========================================================
if feature_choice == "🎭 Vũ Trụ Biến Hình AI (Phình to, Goku, Anime...)":
    st.image(BANNER_URLS["TRANSFORM"], caption="⚡ Vũ Trụ Biến Hình AI: Phình To, Saiyan, Anime, Em Bé...", use_container_width=True)
    st.subheader("🎭 Vũ Trụ Biến Hình AI")
    st.caption("Tải 1 ảnh chân dung và chọn phong cách biến hình yêu thích!")

    trans_img_file = st.file_uploader(
        "📸 Tải lên ảnh chân dung hoặc toàn thân của bạn:", 
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

    if st.button("✨ BIẾN HÌNH NGAY", use_container_width=True, key="btn_execute_trans"):
        if not api_key:
            st.error("⚠️ Vui lòng đảm bảo đã kết nối Gemini API Key!")
        elif not trans_img_file:
            st.error("⚠️ Vui lòng tải lên 1 bức ảnh chân dung!")
        else:
            status = st.status("🔮 Đang kích hoạt hiệu ứng biến hình...", expanded=True)
            try:
                client = genai.Client(api_key=api_key)
                status.write("👁️ Gemini đang phân tích khuôn mặt và đặc điểm ảnh gốc...")
                user_image = Image.open(trans_img_file).convert("RGB")
                
                img_byte_arr = io.BytesIO()
                user_image.save(img_byte_arr, format='JPEG', quality=85)
                img_bytes = img_byte_arr.getvalue()

                analysis_prompt = "Describe this person concisely in 25 words: gender, facial features, hair, eye shape, posture."
                
                from google.genai import types
                analysis_res = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[
                        types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                        analysis_prompt
                    ]
                )
                person_desc = analysis_res.text.strip().replace("\n", " ")

                status.write("🎨 Đang vẽ ảnh theo hiệu ứng bạn chọn...")

                effect_prompt_map = {
                    "💪 Phình To Cơ Bắp (Lực Sĩ Thể Hình Khổng Lồ)": "extremely muscular bodybuilder transformation, massive bulging biceps and shoulders, hyper defined veins, heroic power pose, flexing muscles",
                    "🎈 Phình To Tròn Bụng (Mập Mạp Meme Đáng Yêu)": "funny chubby transformation, round puffy chubby cheeks, oversized cute belly, hilarious exaggerated round proportions",
                    "⚡ Siêu Saiyan Son Goku (Tóc Vàng Rực Lửa)": "Super Saiyan Goku from Dragon Ball with glowing spiky yellow hair, intense golden aura, teal eyes, iconic orange and navy gi",
                    "🌌 Son Goku Bản Năng Vô Cực (Tóc Bạc)": "Mastered Ultra Instinct Goku, glowing silver-white spiky hair, silver eyes, celestial cosmic galaxy aura, torn martial arts uniform",
                    "🧒 Biến Về Em Bé 5 Tuổi (Baby Face)": "turned into an adorable 5-year-old toddler, cute big sparkling eyes, chubby soft baby cheeks, youthful innocence",
                    "👴 Du Hành Tương Lai 80 Tuổi (Lão Hóa Tóc Bạc)": "aged to 80 years old, realistic facial wrinkles, wise elderly expression, distinguished silver gray hair and beard",
                    "🥷 Ninja Hokage (Làng Lá Naruto)": "Konoha ninja Hokage warrior from Naruto, wearing iconic Hokage cloak and headband, dramatic ninja battle stance",
                    "🦾 Người Máy Chiến Binh (Cyberpunk Cyborg)": "futuristic cyberpunk cyborg, half metallic chrome cybernetic face, glowing neon blue robotic optic eye, carbon fiber mechanical armor",
                    "👑 Tổng Tài Quyền Lực (Vest Tuxedo Doanh Nhân)": "ultra-wealthy billionaire CEO, wearing luxury black tailored Italian tuxedo, lavish penthouse luxury background"
                }

                style_prompt_map = {
                    "Điện Ảnh Thực Tế (Photorealistic / 3D Live-Action)": "cinematic 8k movie still, photorealistic, intricate textures, realistic lighting, unreal engine 5",
                    "Anime Nhật Bản Sắc Nét (Anime Art Style)": "vibrant Japanese anime masterpiece, sharp cel shading, dynamic anime line art, studio trigger aesthetic",
                    "Tranh Sơn Dầu Nghệ Thuật (Classic Oil Painting)": "classic museum oil painting, visible canvas texture, dramatic chiaroscuro lighting, rich palette",
                    "Manga Đen Trắng Đậm Chất (Comic Book Style)": "high-contrast Japanese manga drawing, dynamic speed lines, screentone shading, sharp ink lineart"
                }

                chosen_effect = effect_prompt_map[transform_mode]
                chosen_style = style_prompt_map[art_style]

                prompt_draw = f"Full transformation portrait of {person_desc}. Applied change: {chosen_effect}. Visual style: {chosen_style}. Masterpiece, highly detailed, centered composition"
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
                    st.success("🎉 Tác phẩm biến hình của bạn đã sẵn sàng!")
                else:
                    raise Exception("Không thể tải ảnh từ máy chủ AI.")

            except Exception as e:
                status.update(label="❌ Có lỗi xảy ra!", state="error")
                st.error(f"Chi tiết lỗi: {str(e)}")

    if 'trans_result_bytes' in st.session_state and 'trans_orig_bytes' in st.session_state:
        orig_pil = Image.open(io.BytesIO(st.session_state['trans_orig_bytes']))
        result_pil = Image.open(io.BytesIO(st.session_state['trans_result_bytes']))

        col_show1, col_show2 = st.columns(2)
        with col_show1:
            st.image(orig_pil, caption="Ảnh Gốc", use_container_width=True)
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
                res = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
                lines = [l.strip() for l in res.text.strip().split("\n") if l.strip()]

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
