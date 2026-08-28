import streamlit as st
import os
import io
import time
import asyncio
import tempfile
import urllib.parse
import requests
import numpy as np
import nest_asyncio
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

# Kích hoạt nest_asyncio để chống xung đột event loop trong Streamlit
nest_asyncio.apply()

st.set_page_config(page_title="AI Studio Ultimate Pro", page_icon="🎬", layout="centered")

# ==========================================================
# ⚙️ CẤU HÌNH GẮN CỐ ĐỊNH LINK SERVER GPU COLAB
# ==========================================================
COLAB_SERVER_URL = "https://stoppable-unrivaled-driver.ngrok-free.dev"

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

def run_async(coro):
    """Hàm chạy coroutine an toàn, không bị lỗi lồng event loop"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

async def _create_voice_async(text, voice_choice, output_path):
    voice_id = "vi-VN-HoaiMyNeural" if "Hoài My" in voice_choice else "vi-VN-NamMinhNeural"
    communicate = edge_tts.Communicate(text, voice_id)
    await communicate.save(output_path)

def create_voice(text, voice_choice, output_path):
    return run_async(_create_voice_async(text, voice_choice, output_path))

BANNER_URLS = {
    "HERO": "https://image.pollinations.ai/prompt/Futuristic%20creative%20AI%20video%20and%20music%20production%20studio,%20glowing%20neon%20holograms,%20Super%20Saiyan%20energy%20and%20dancing%20characters,%20ultra%20vibrant%203D%20cinematic%20digital%20art,%208k%20masterpiece?width=1200&height=400&model=flux&seed=777&nologo=true",
    "COLAB": "https://image.pollinations.ai/prompt/Futuristic%20supercomputer%20GPU%20cluster%20server,%20glowing%20cyan%20and%20purple%20neon%20data%20streams,%20motion%20capture%20AI%20facial%20animation%20grid,%20ultra%20high-tech%203D?width=1080&height=350&model=flux&seed=222&nologo=true",
    "SQUISH": "https://image.pollinations.ai/prompt/Cute%20chubby%20baby%20cheeks%20being%20gently%20squished%20by%20a%20hand,%20hilarious%20pouting%20grumpy%20expression,%20hyper-realistic%203D%20render,%20cinematic%20lighting?width=1080&height=350&model=flux&seed=444&nologo=true",
    "TRANSFORM": "https://image.pollinations.ai/prompt/Epic%20character%20transformation,%20split%20view%20between%20Super%20Saiyan%20golden%20hair%20and%20giant%20muscular%20hero,%20energetic%20lighting%20sparks,%20cinematic%203D%20render,%208k?width=1080&height=350&model=flux&seed=888&nologo=true",
    "VIDEO": "https://image.pollinations.ai/prompt/Social%20media%20short%20video%20creator%20concept,%209:16%20smartphone%20screen%20floating%20with%20cinematic%20scenes,%20subtitles,%20vibrant%20colors,%203D%20render?width=1080&height=350&model=flux&seed=999&nologo=true",
    "MUSIC": "https://image.pollinations.ai/prompt/Neon%20glowing%20music%20studio,%20floating%20musical%20notes,%20soundwaves,%20headphones,%20cyberpunk%20aesthetic,%20ultra%20detailed%203D?width=1080&height=350&model=flux&seed=333&nologo=true"
}

st.image(BANNER_URLS["HERO"], use_container_width=True)
st.title("🎬 AI Studio Ultimate Pro")
st.caption("Studio Đa Năng: Ghép Cử Động GPU Colab • Biến Hình 3D • Video Ngắn • Bóp Má • Nhạc AI")

# Tự động lấy API Key Gemini nếu có trong secrets
saved_api_key = st.secrets.get("GEMINI_API_KEY", "")
if saved_api_key:
    api_key = saved_api_key
    st.success("✅ Đã tự động kết nối Gemini API Key!")
else:
    api_key = st.text_input("🔑 Gemini API Key (*):", type="password", placeholder="Nhập Gemini API Key của bạn...")

st.markdown("### 🎯 Chọn Chức Năng Cần Sử Dụng:")
feature_choice = st.radio(
    "Danh sách tính năng:",
    [
        "🚀 Ghép Cử Động Thật 100% (GPU Colab Tự Động)",
        "✨ Vũ Trụ Biến Hình AI (Phình To, Saiyan, Anime...)",
        "🎬 Tạo Video Ngắn (TikTok/Reels Tự Động)",
        "🤏 Video Bóp Má & Phồng Mặt 3D (Mivora Style)",
        "🎵 Sáng Tác Nhạc & Lời"
    ],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown("---")

# ==========================================================
# 1. GHÉP CỬ ĐỘNG THẬT 100% (GPU COLAB TỰ ĐỘNG)
# ==========================================================
if feature_choice == "🚀 Ghép Cử Động Thật 100% (GPU Colab Tự Động)":
    st.image(BANNER_URLS["COLAB"], caption="⚡ GPU Cloud Server: Tự Động Render Cử Động Cơ Mặt, Mắt, Miệng Thật 100%", use_container_width=True)
    st.subheader("🚀 Trình Tạo Video Cử Động Ngũ Quan 3D (Tự Động Kết Nối)")
    st.caption("Chỉ cần tải ảnh và video mẫu lên, hệ thống sẽ tự động kết nối máy chủ GPU để xuất video.")

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        src_file = st.file_uploader("📸 1. Tải ảnh nhân vật tĩnh:", type=["jpg", "jpeg", "png", "webp"], key="colab_src_img")
    with col_c2:
        drv_file = st.file_uploader("🎞️ 2. Tải video cử động mẫu:", type=["mp4", "mov", "avi"], key="colab_drv_vid")

    if st.button("🎬 XUẤT VIDEO CỬ ĐỘNG THẬT 100%", use_container_width=True, key="btn_run_colab_render"):
        if not src_file or not drv_file:
            st.error("⚠️ Vui lòng tải lên đầy đủ cả Ảnh chân dung và Video cử động mẫu!")
        else:
            status = st.status("⏳ Đang gửi dữ liệu sang GPU Server để render...", expanded=True)
            try:
                target_api = f"{COLAB_SERVER_URL.rstrip('/')}/animate"
                
                status.write("📤 Đang chuyển ảnh và video sang máy chủ...")
                files = {
                    "source_image": (src_file.name, src_file.getvalue(), src_file.type if src_file.type else "image/jpeg"),
                    "driving_video": (drv_file.name, drv_file.getvalue(), drv_file.type if drv_file.type else "video/mp4")
                }

                status.write("🧠 GPU đang phân tích và render từng khung hình cơ mặt...")
                response = requests.post(target_api, files=files, timeout=240)

                if response.status_code == 200:
                    st.session_state['colab_rendered_video'] = response.content
                    status.update(label="✅ Render video thành công 100%!", state="complete", expanded=False)
                    st.success("🎉 Video cử động khuôn mặt chân thực của bạn đã hoàn thành!")
                else:
                    status.update(label="❌ Lỗi từ máy chủ GPU!", state="error")
                    st.error(f"Máy chủ phản hồi: {response.text}")

            except requests.exceptions.Timeout:
                status.update(label="❌ Hết thời gian chờ!", state="error")
                st.error("Quá thời gian xử lý (Timeout). Vui lòng thử lại với video mẫu ngắn hơn (dưới 8 giây).")
            except Exception as e:
                status.update(label="❌ Lỗi kết nối máy chủ!", state="error")
                st.error(f"Không thể kết nối đến GPU Server. Hãy kiểm tra xem notebook trên Colab có đang chạy không: {str(e)}")

    if 'colab_rendered_video' in st.session_state:
        st.video(st.session_state['colab_rendered_video'])
        st.download_button(
            "📥 Tải Video Cử Động Hoàn Chỉnh (.mp4)",
            data=st.session_state['colab_rendered_video'],
            file_name="AI_Face_Motion_Rendered.mp4",
            mime="video/mp4",
            use_container_width=True
        )

# ==========================================================
# 2. VŨ TRỤ BIẾN HÌNH AI
# ==========================================================
elif feature_choice == "✨ Vũ Trụ Biến Hình AI (Phình To, Saiyan, Anime...)":
    st.image(BANNER_URLS["TRANSFORM"], caption="⚡ Vũ Trụ Biến Hình AI: Giữ Nguyên Gương Mặt Thật", use_container_width=True)
    st.subheader("✨ Vũ Trụ Biến Hình AI (Khóa Nét Mặt + Video 6s)")
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
# 3. TẠO VIDEO NGẮN TIKTOK / REELS TỰ ĐỘNG
# ==========================================================
elif feature_choice == "🎬 Tạo Video Ngắn (TikTok/Reels Tự Động)":
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
                lines = [l.strip() for l in res_text.strip().split("\n") if l.strip()]

                with tempfile.TemporaryDirectory() as td:
                    scene_clips = []
                    target_size = (720, 1280)

                    for idx, f in enumerate(uploaded_files):
                        status.write(f"🔄 Đang xử lý phân cảnh {idx+1}/{len(uploaded_files)}...")
                        txt = lines[idx] if idx < len(lines) else f"Nội dung minh họa số {idx+1}."
                        
                        a_path = os.path.join(td, f"v_{idx}.mp3")
                        create_voice(txt, voice_option, a_path)

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
# 4. TẠO VIDEO BÓP MÁ & PHỒNG MẶT 3D (MIVORA STYLE)
# ==========================================================
elif feature_choice == "🤏 Video Bóp Má & Phồng Mặt 3D (Mivora Style)":
    st.image(BANNER_URLS["SQUISH"], caption="🤏 Tạo Video Bóp Má Phồng Mặt & Biểu Cảm Hờn Dỗi (Miễn Phí 100%)", use_container_width=True)
    st.subheader("🤏 Tạo Video Bóp Má & Hờn Dỗi 3D Chuẩn Mivora")
    st.caption("Tải 1 ảnh chân dung/em bé, hệ thống sẽ chuẩn hóa ảnh và hỗ trợ tạo video tương tác vật lý hoàn toàn miễn phí!")

    squish_file = st.file_uploader(
        "📸 Tải ảnh chân dung rõ mặt:", 
        type=["jpg", "jpeg", "png", "heic", "webp"], 
        key="uploader_squish"
    )

    squish_type = st.selectbox(
        "🎭 Chọn phong cách tương tác:",
        [
            "Bàn tay bóp má phồng lên $\rightarrow$ Thả ra nhăn mặt dỗi (Mivora Standard)",
            "Véo má 2 bên dễ thương $\rightarrow$ Thả ra cười tít mắt",
            "Bàn tay chọc vào má $\rightarrow$ Phồng mang trợn mắt hài hước"
        ]
    )

    if st.button("🚀 CHUẨN BỊ XUẤT VIDEO 3D MIỄN PHÍ", use_container_width=True, key="btn_prep_squish"):
        if not squish_file:
            st.error("⚠️ Vui lòng tải lên 1 bức ảnh chân dung!")
        else:
            with st.spinner("Đang tối ưu ảnh và tạo kịch bản vật lý..."):
                img_raw = Image.open(squish_file).convert("RGB")
                target_size = (720, 1280)
                img_opt = img_raw.resize(target_size, Image.Resampling.LANCZOS)
                
                buf_opt = io.BytesIO()
                img_opt.save(buf_opt, format="JPEG", quality=95)
                st.session_state['squish_img_bytes'] = buf_opt.getvalue()

                if "nhăn mặt dỗi" in squish_type:
                    p_text = "A realistic human hand reaches from the side and gently squishes the character's chubby cheek, causing the face to puff up realistically. The hand releases, and the character makes a cute angry, pouting facial expression with furrowed eyebrows, 3D hyper-realistic physics interaction, smooth 4k."
                elif "cười tít mắt" in squish_type:
                    p_text = "Two human hands gently pinch and pull both cheeks adorably. The hands release, and the character bursts into a cute joyful laughing smile, sparkling eyes, ultra-realistic smooth 3D motion."
                else:
                    p_text = "A finger pokes into the character's cheek, causing the entire face to inflate and puff up like a balloon, funny hilarious cartoonish physics, 3D render."

                st.session_state['squish_prompt'] = p_text
                st.success("✅ Đã chuẩn hóa ảnh và tạo lệnh chuyển động vật lý!")

    if 'squish_img_bytes' in st.session_state:
        st.markdown("---")
        st.markdown("### 🎬 Lựa Chọn Phương Thức Xuất Video Miễn Phí:")

        tab_m1, tab_m2 = st.tabs(["✨ Cách 1: Xuất Bằng Kling AI (Nhanh - Miễn Phí)", "⚡ Cách 2: Chạy Google Colab GPU (Tự Động)"])

        with tab_m1:
            st.info("""
            **3 Bước đơn giản để nhận video bóp má chuẩn 100%:**
            1. Bấm nút **'Tải Ảnh Đã Tối Ưu'** bên dưới về máy.
            2. Sao chép câu lệnh Prompt có sẵn.
            3. Bấm nút **'Mở Kling AI'** $\rightarrow$ Dán ảnh và Prompt vào để nhận video hoàn chỉnh!
            """)

            col_sq1, col_sq2 = st.columns(2)
            with col_sq1:
                st.download_button(
                    "📥 1. Tải Ảnh Đã Tối Ưu Về Máy", 
                    data=st.session_state['squish_img_bytes'], 
                    file_name="Squish_Target.jpg", 
                    mime="image/jpeg", 
                    use_container_width=True
                )
            with col_sq2:
                st.link_button("🌐 3. Mở Kling AI Miễn Phí", "https://klingai.com", use_container_width=True)

            st.text_area("📋 2. Câu lệnh Prompt (Đã tối ưu sẵn - Chỉ cần Copy):", st.session_state.get('squish_prompt', ''), height=90)

        with tab_m2:
            st.markdown("""
            **Chạy mô hình LivePortrait / SVD miễn phí trên GPU của Google:**
            * Google cấp miễn phí card đồ họa GPU T4 trên nền tảng đám mây.
            * Bạn có thể mở trực tiếp Notebook bên dưới để xử lý video mà không mất phí.
            """)
            st.link_button("🚀 Mở Google Colab Chạy GPU Miễn Phí", "https://colab.research.google.com/github/KwaiVGI/LivePortrait/blob/main/LivePortrait.ipynb", use_container_width=True)

# ==========================================================
# 5. SÁNG TÁC NHẠC & LỜI
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
                    res_lyrics = generate_content_with_fallback(client, prompt, primary_model="gemini-3.6-flash")
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
