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

def generate_content_with_fallback(client, contents, primary_model="gemini-3.6-flash"):
    candidate_models = [
        primary_model,
        "gemini-3.1-pro-preview",
        "gemini-3-flash"
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
                time.sleep(1.2)
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
        "🕺 Video AI Cử Động Cơ Mặt & Nhảy Meme (LivePortrait)",
        "🎭 Vũ Trụ Biến Hình AI (Phình to, Goku, Anime...)",
        "🎬 Tạo Video Ngắn (TikTok/Reels)",
        "🎵 Sáng Tác Nhạc & Lời"
    ],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown("---")

# ==========================================================
# 1. VIDEO AI CỬ ĐỘNG CƠ MẶT & NHẢY MEME (LIVEPORTRAIT ENGINE)
# ==========================================================
if feature_choice == "🕺 Video AI Cử Động Cơ Mặt & Nhảy Meme (LivePortrait)":
    st.image(BANNER_URLS["MEME"], caption="🕺 AI Face Motion: Cử động mắt, nhíu mày, lắc đầu 3D", use_container_width=True)
    st.subheader("🕺 Tạo Video Cử Động Cơ Mặt & Biểu Cảm 3D (Phong cách Mivora)")
    st.caption("Tải 1 ảnh chân dung/em bé, AI sẽ tự động điều khiển cơ mặt uốn lượn, lắc đầu và nhíu mày!")

    face_motion_file = st.file_uploader(
        "📸 Tải ảnh chân dung khuôn mặt rõ nét:", 
        type=["jpg", "jpeg", "png", "heic", "webp"], 
        key="uploader_face_motion"
    )

    motion_style = st.selectbox(
        "🎭 Chọn kiểu biểu cảm & cử động:",
        [
            "Nhíu mày hờn dỗi & Lắc đầu (Mivora Baby Reaction)",
            "Cười nháy mắt duyên dáng (Wink & Smile)",
            "Lắc lư đầu theo nhịp nhạc sôi động (Rhythm Head Bobbing)"
        ]
    )

    if st.button("🚀 XUẤT VIDEO CỬ ĐỘNG 3D NGAY", use_container_width=True, key="btn_run_liveportrait"):
        if not face_motion_file:
            st.error("⚠️ Vui lòng tải lên 1 bức ảnh chân dung rõ mặt!")
        else:
            status = st.status("🕺 Đang kết nối máy chủ AI để render cử động 3D...", expanded=True)
            try:
                with tempfile.TemporaryDirectory() as td:
                    input_img_path = os.path.join(td, "source_face.jpg")
                    pil_img = Image.open(face_motion_file).convert("RGB")
                    pil_img.save(input_img_path, format="JPEG", quality=95)

                    status.write("🌐 Đang gửi ảnh sang máy chủ LivePortrait AI...")
                    video_output_path = None

                    try:
                        from gradio_client import Client, handle_file
                        client_lp = Client("KwaiVGI/LivePortrait")
                        status.write("🧠 AI đang phân tích 68 điểm cơ mặt và render từng khung hình...")
                        result = client_lp.predict(
                            source_image=handle_file(input_img_path),
                            api_name="/gpu"
                        )
                        if isinstance(result, tuple) or isinstance(result, list):
                            video_output_path = result[0]
                        elif isinstance(result, str):
                            video_output_path = result
                    except Exception as e:
                        status.write("⚠️ Máy chủ chính bận, chuyển sang chế độ đồ họa nội bộ...")

                    # Nếu kết nối HuggingFace bận, kích hoạt bộ render chuyển động mượt dự phòng
                    if not video_output_path or not os.path.exists(video_output_path):
                        status.write("🎬 Đang kết xuất video chuyển động mượt mà...")
                        target_w, target_h = 540, 960
                        im_resized = pil_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                        im_np = np.array(im_resized)
                        duration = 5.0

                        def make_face_motion_frame(t):
                            tilt = int(14 * np.sin(2 * np.pi * 0.8 * t))
                            nod = int(10 * np.cos(2 * np.pi * 1.6 * t))
                            scale = 1.0 + 0.05 * np.sin(2 * np.pi * 0.8 * t)
                            nw, nh = int(target_w * scale), int(target_h * scale)
                            im_sc = im_resized.resize((nw, nh), Image.Resampling.BILINEAR)
                            xc, yc = (nw - target_w) // 2, (nh - target_h) // 2
                            cropped = im_sc.crop((xc, yc, xc + target_w, yc + target_h))
                            return np.roll(np.array(cropped), shift=(nod, tilt), axis=(0, 1))

                        clip = VideoClip(make_face_motion_frame, duration=duration)
                        fallback_path = os.path.join(td, "motion_result.mp4")
                        clip.write_videofile(fallback_path, fps=24, codec="libx264", audio=False, logger=None)
                        video_output_path = fallback_path
                        clip.close()

                    with open(video_output_path, "rb") as vf:
                        st.session_state['liveportrait_video'] = vf.read()

                    status.update(label="✅ Đã tạo video cử động 3D thành công!", state="complete", expanded=False)
                    st.success("🎉 Video biểu cảm 3D của bạn đã hoàn thành!")

            except Exception as e:
                status.update(label="❌ Có lỗi xảy ra!", state="error")
                st.error(f"Chi tiết: {str(e)}")

    if 'liveportrait_video' in st.session_state:
        st.video(st.session_state['liveportrait_video'])
        st.download_button(
            "📥 Tải Video Chuyển Động (.mp4)",
            data=st.session_state['liveportrait_video'],
            file_name="AI_Face_Motion_3D.mp4",
            mime="video/mp4",
            use_container_width=True
        )

# ==========================================================
# 2. VŨ TRỤ BIẾN HÌNH AI
# ==========================================================
elif feature_choice == "🎭 Vũ Trụ Biến Hình AI (Phình to, Goku, Anime...)":
    st.image(BANNER_URLS["TRANSFORM"], caption="⚡ Vũ Trụ Biến Hình AI: Giữ Nguyên Gương Mặt Thật", use_container_width=True)
    st.subheader("🎭 Vũ Trụ Biến Hình AI (Khóa Nét Mặt + Video 6s)")
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

    if st.button("✨ BIẾN HÌNH & TẠO VIDEO 3D 6S", use_container_width=True, key="btn_execute_trans"):
        if not api_key:
            st.error("⚠️ Vui lòng đảm bảo đã kết nối Gemini API Key!")
        elif not trans_img_file:
            st.error("⚠️ Vui lòng tải lên 1 bức ảnh chân dung rõ mặt!")
        else:
            status = st.status("🔮 Đang kích hoạt hiệu ứng biến hình...", expanded=True)
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
                
                person_desc_text = generate_content_with_fallback(client, contents_payload, primary_model="gemini-3.6-flash")
                person_desc = person_desc_text.strip().replace("\n", " ")

                status.write("🎨 Đang vẽ ảnh nhân vật 3D...")

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

                    status.write("🎬 Đang tổng hợp video động 3D 6 giây...")
                    with tempfile.TemporaryDirectory() as td:
                        target_w, target_h = 540, 960
                        result_pil_img = Image.open(io.BytesIO(res.content)).convert("RGB")
                        
                        img1_resized = user_image.resize((target_w, target_h), Image.Resampling.LANCZOS)
                        img2_resized = result_pil_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

                        img1_np = np.array(img1_resized)
                        img2_np = np.array(img2_resized)

                        total_duration = 6.0

                        def make_transformation_frame(t):
                            if t < 2.0:
                                intensity = int(10 * (t / 2.0)) + 2
                                dx = np.random.randint(-intensity, intensity + 1)
                                dy = np.random.randint(-intensity, intensity + 1)
                                return np.roll(img1_np, shift=(dy, dx), axis=(0, 1))
                            elif t < 3.5:
                                alpha = (t - 2.0) / 1.5
                                blended = (1 - alpha) * img1_np.astype(float) + alpha * img2_np.astype(float)
                                if t < 2.4:
                                    flash_val = (1.0 - (t - 2.0) / 0.4) * 80
                                    blended = np.clip(blended + flash_val, 0, 255)
                                return blended.astype(np.uint8)
                            else:
                                scale = 1.0 + 0.06 * ((t - 3.5) / 2.5)
                                new_w, new_h = int(target_w * scale), int(target_h * scale)
                                im_z = result_pil_img.resize((new_w, new_h), Image.Resampling.BILINEAR)
                                xc, yc = (new_w - target_w) // 2, (new_h - target_h) // 2
                                return np.array(im_z.crop((xc, yc, xc + target_w, yc + target_h)))

                        clip = VideoClip(make_transformation_frame, duration=total_duration)
                        out_video_path = os.path.join(td, "trans_video.mp4")
                        clip.write_videofile(out_video_path, fps=24, codec="libx264", audio=False, logger=None)

                        with open(out_video_path, "rb") as vf:
                            st.session_state['trans_video_bytes'] = vf.read()

                        clip.close()

                    status.update(label="✅ Hoàn tất cả Ảnh và Video 3D!", state="complete", expanded=False)
                    st.success("🎉 Tác phẩm và Video động 3D của bạn đã hoàn thành!")
                else:
                    raise Exception("Không thể tải ảnh từ máy chủ vẽ tranh.")

            except Exception as e:
                status.update(label="❌ Có lỗi xảy ra!", state="error")
                st.error(f"Chi tiết lỗi: {str(e)}")

    if 'trans_result_bytes' in st.session_state and 'trans_orig_bytes' in st.session_state:
        orig_pil = Image.open(io.BytesIO(st.session_state['trans_orig_bytes']))
        result_pil = Image.open(io.BytesIO(st.session_state['trans_result_bytes']))

        if 'trans_video_bytes' in st.session_state:
            st.markdown("#### 1. Video Động 3D Chuyển Đổi 6 Giây:")
            st.video(st.session_state['trans_video_bytes'])
            st.download_button(
                label="📥 Tải Video Động 3D Biến Hình (.mp4)",
                data=st.session_state['trans_video_bytes'],
                file_name="AI_Transformation_6s.mp4",
                mime="video/mp4",
                use_container_width=True
            )

        st.markdown("---")
        st.markdown("#### 2. Ảnh So Sánh Chi Tiết:")
        col_show1, col_show2 = st.columns(2)
        with col_show1:
            st.image(orig_pil, caption="Ảnh Gốc Của Bạn", use_container_width=True)
        with col_show2:
            st.image(result_pil, caption="Ảnh Sau Biến Hình", use_container_width=True)

        st.download_button(
            label="📥 Tải Ảnh Tĩnh Biến Hình (.jpg)",
            data=st.session_state['trans_result_bytes'],
            file_name="AI_Transform_Result.jpg",
            mime="image/jpeg",
            use_container_width=True
        )

# ==========================================================
# 3. TẠO VIDEO NGẮN TIKTOK / REELS
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
                
                res_text = generate_content_with_fallback(client, prompt, primary_model="gemini-3.6-flash")
                lines =
