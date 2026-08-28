import os
import re
import sys
import time
import math
import shutil
import tempfile
import asyncio
import threading
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import PIL.Image

if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS

import streamlit as st
import google.generativeai as genai
import edge_tts
from moviepy.editor import (
    ImageClip,
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
    vfx
)

# ==============================================================================
# 1. CẤU HÌNH GIAO DIỆN HỆ THỐNG
# ==============================================================================
st.set_page_config(
    page_title="AI Creative Studio Super Pro Max",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header { font-size: 2.1rem; font-weight: 800; color: #1976D2; margin-bottom: 0.2rem; }
    .sub-header { font-size: 1rem; color: #4B5563; margin-bottom: 1.2rem; }
    .scene-box { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 12px; margin-bottom: 12px; }
    .stButton>button { border-radius: 8px; font-weight: 600; height: 2.8em; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# HÀM TẠO CHUYỂN ĐỘNG LIÊN TỤC KHÔNG BỊ GIẬT HÌNH (SEAMLESS SMOOTH LOOP)
# ==============================================================================
def make_seamless_smooth_video(clip, target_duration):
    """
    Tạo vòng lặp mượt mà không bị giật/nhảy hình:
    Ghép clip xuôi + clip ngược (time_mirror) liên tục để chuyển động trôi êm ả tự nhiên.
    """
    if clip.duration >= target_duration:
        return clip.subclip(0, target_duration)
    
    # Tạo clip đảo chiều mượt mà
    rev_clip = clip.fx(vfx.time_mirror)
    pair_unit = concatenate_videoclips([clip, rev_clip])
    
    repeat_count = math.ceil(target_duration / pair_unit.duration) + 1
    long_chain = concatenate_videoclips([pair_unit] * repeat_count)
    return long_chain.subclip(0, target_duration)

# ==============================================================================
# HÀM BẢO TOÀN 100% HÌNH ẢNH (KHÔNG MẤT ĐẦU/MẶT + NỀN MỜ NGHỆ THUẬT)
# ==============================================================================
def fit_image_to_canvas(pil_img, target_w, target_h):
    """Giữ nguyên 100% con vật ở giữa không mất đầu, lót nền mờ phía sau."""
    orig_w, orig_h = pil_img.size
    
    # 1. Tạo nền mờ phía sau
    scale_bg = max(target_w / orig_w, target_h / orig_h)
    bg_w, bg_h = int(orig_w * scale_bg), int(orig_h * scale_bg)
    bg_img = pil_img.resize((bg_w, bg_h), Image.Resampling.LANCZOS)
    left = (bg_w - target_w) // 2
    top = (bg_h - target_h) // 2
    bg_crop = bg_img.crop((left, top, left + target_w, top + target_h))
    bg_blur = bg_crop.filter(ImageFilter.GaussianBlur(radius=20))

    # 2. Thu phóng vừa vặn toàn bộ ảnh chính
    scale_fg = min(target_w / orig_w, target_h / orig_h)
    fg_w, fg_h = int(orig_w * scale_fg), int(orig_h * scale_fg)
    fg_img = pil_img.resize((fg_w, fg_h), Image.Resampling.LANCZOS)
    
    pos_x = (target_w - fg_w) // 2
    pos_y = (target_h - fg_h) // 2
    bg_blur.paste(fg_img, (pos_x, pos_y))
    return bg_blur

def compose_fitted_video(clip, target_w, target_h):
    """Ghép video thành phẩm với nền mờ, không bao giờ cắt xén mặt/đầu nhân vật."""
    scale_fg = min(target_w / clip.w, target_h / clip.h)
    fg = clip.resize(scale_fg).set_position("center")
    
    scale_bg = max(target_w / clip.w, target_h / clip.h)
    bg = clip.resize(scale_bg).crop(x_center=clip.w*scale_bg/2, y_center=clip.h*scale_bg/2, width=target_w, height=target_h)
    
    def blur_frame(frame):
        im = Image.fromarray(frame).filter(ImageFilter.GaussianBlur(radius=15))
        return np.array(im)
        
    bg = bg.fl_image(blur_frame)
    return CompositeVideoClip([bg, fg], size=(target_w, target_h)).set_duration(clip.duration)

# ==============================================================================
# 2. THANH CÔNG CỤ SIDEBAR
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/video-editing.png", width=90)
    st.title("⚙️ ĐIỀU KHIỂN")
    
    server_url = st.text_input(
        "GPU Server URL (Ngrok):",
        value="",
        placeholder="https://xxxx.ngrok-free.app",
        help="Dán link GPU từ Kaggle vào đây."
    )
    
    col_ping1, col_ping2 = st.columns([1, 1])
    with col_ping1:
        if st.button("🔍 Kiểm Tra GPU", use_container_width=True):
            if not server_url.strip():
                st.warning("Chưa nhập link GPU!")
            else:
                with st.spinner("Đang ping..."):
                    try:
                        headers = {"User-Agent": "Mozilla/5.0", "ngrok-skip-browser-warning": "true"}
                        test_res = requests.get(server_url.strip().rstrip('/'), headers=headers, timeout=10)
                        if test_res.status_code == 200:
                            st.success("🟢 GPU Online!")
                        else:
                            st.warning(f"🟡 Phản hồi: {test_res.status_code}")
                    except Exception as err:
                        st.error(f"🔴 Mất kết nối: {err}")

    with col_ping2:
        if st.button("🧹 Reset App", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.markdown("---")
    gemini_key = st.text_input("Gemini API Key:", type="password", value="")
    
    st.markdown("---")
    menu_choice = st.radio(
        "📌 CHỌN PHÂN HỆ:",
        [
            "1. 🎞️ Xưởng Sản Xuất Video Phân Cảnh (Toàn Diện)",
            "2. ✨ Trợ Lý Viết Kịch Bản Phân Cảnh (Gemini)"
        ]
    )

def call_gemini_smart_generator(api_key, prompt_text):
    genai.configure(api_key=api_key)
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
    except Exception:
        pass

    priority_order = ["models/gemini-2.5-flash", "models/gemini-1.5-flash", "gemini-1.5-flash"]
    target_model = next((p for p in priority_order if p in available_models), "gemini-1.5-flash")
    model = genai.GenerativeModel(target_model)
    response = model.generate_content(prompt_text)
    if response and response.text:
        return response.text, target_model
    raise Exception("Mô hình không trả về nội dung.")

# ==============================================================================
# PHÂN HỆ 1: XƯỞNG SẢN XUẤT VIDEO PHÂN CẢNH
# ==============================================================================
if menu_choice == "1. 🎞️ Xưởng Sản Xuất Video Phân Cảnh (Toàn Diện)":
    st.markdown('<div class="main-header">🎞️ Xưởng Sản Xuất Video Phân Cảnh Toàn Diện</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Chuyển động liên tục êm ái, chống giật nhảy hình (Seamless Motion), bảo toàn 100% chủ thể không mất đầu/mặt.</div>', unsafe_allow_html=True)

    st.markdown("### ⚙️ 1. Cấu Hình Chung Toàn Video")
    col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
    with col_cfg1:
        prod_voice_dict = {
            "🇻🇳 vi-VN-NamMinhNeural (Nam - Miền Bắc)": "vi-VN-NamMinhNeural",
            "🇻🇳 vi-VN-HoaiMyNeural (Nữ - Miền Bắc)": "vi-VN-HoaiMyNeural",
            "🇺🇸 en-US-GuyNeural (Nam - Mỹ)": "en-US-GuyNeural",
            "🇺🇸 en-US-JennyNeural (Nữ - Mỹ)": "en-US-JennyNeural",
            "🇬🇧 en-GB-RyanNeural (Nam - Anh)": "en-GB-RyanNeural",
            "🇨🇳 zh-CN-YunxiNeural (Nam - Trung Quốc)": "zh-CN-YunxiNeural",
            "🇯🇵 ja-JP-KeitaNeural (Nam - Nhật Bản)": "ja-JP-KeitaNeural"
        }
        prod_voice_label = st.selectbox("Giọng đọc thuyết minh:", list(prod_voice_dict.keys()))
        selected_prod_voice = prod_voice_dict[prod_voice_label]
        
    with col_cfg2:
        ratio_choice = st.selectbox(
            "Tỷ lệ khung hình video:",
            [
                "9:16 Dọc (TikTok, Shorts, Reels) - Chuẩn điện thoại",
                "16:9 Ngang (YouTube, Facebook, Web) - Chuẩn máy tính",
                "1:1 Vuông (Instagram Post)"
            ]
        )
        
    with col_cfg3:
        motion_effect = st.selectbox(
            "Hiệu ứng chuyển động trôi êm cho cảnh TĨNH:",
            ["Trôi chậm êm ái (Cinematic Drift)", "Zoom In Mềm (Phóng to nhẹ)", "Zoom Out Mềm (Thu nhỏ nhẹ)"]
        )

    col_sub1, col_sub2 = st.columns(2)
    with col_sub1:
        sub_toggle = st.checkbox("Chèn phụ đề tiếng Việt tự động cho từng cảnh", value=True)
    with col_sub2:
        if sub_toggle:
            sub_font_size = st.slider("Cỡ chữ phụ đề:", min_value=18, max_value=40, value=26, step=2)
            sub_color = st.color_picker("Màu sắc chữ phụ đề:", "#FFE600")

    st.markdown("---")
    st.markdown("### 🎬 2. Thiết Lập Từng Phân Cảnh")

    if "num_scenes_count" not in st.session_state:
        st.session_state["num_scenes_count"] = 3

    col_btn_sc1, col_btn_sc2 = st.columns([1, 4])
    with col_btn_sc1:
        if st.button("➕ Thêm Phân Cảnh"):
            st.session_state["num_scenes_count"] += 1
            st.rerun()
    with col_btn_sc2:
        if st.session_state["num_scenes_count"] > 1:
            if st.button("➖ Giảm Phân Cảnh"):
                st.session_state["num_scenes_count"] -= 1
                st.rerun()

    scenes_data = []
    default_texts = [
        "Thức dậy sớm và uống một ly nước ấm để đánh thức mọi giác quan trong cơ thể.",
        "Dành ra mười lăm phút vận động nhẹ nhàng giúp tinh thần sảng khoái và tràn đầy năng lượng.",
        "Lập danh sách ba việc quan trọng nhất cần hoàn thành trong ngày để làm việc hiệu quả.",
        "Bắt đầu ngày mới với nụ cười và tinh thần quyết tâm chinh phục mọi thử thách."
    ]

    for i in range(st.session_state["num_scenes_count"]):
        st.markdown(f'<div class="scene-box">', unsafe_allow_html=True)
        st.markdown(f"#### 📍 Phân Cảnh {i + 1}")
        
        c_sc1, c_sc2, c_sc3 = st.columns([3, 2, 2])
        with c_sc1:
            def_text = default_texts[i % len(default_texts)]
            sc_text = st.text_area(f"Lời thuyết minh cảnh {i + 1}:", value=def_text, key=f"sc_text_{i}", height=100)
        with c_sc2:
            sc_media = st.file_uploader(
                f"Tải Ảnh hoặc Video cảnh {i + 1}:",
                type=["jpg", "jpeg", "png", "mp4", "mov", "avi"],
                key=f"sc_media_{i}"
            )
            if sc_media:
                if sc_media.type.startswith("image"):
                    st.image(sc_media, width=90, caption="Ảnh gốc")
                else:
                    st.video(sc_media)
        with c_sc3:
            anim_mode = st.selectbox(
                f"Chế độ hoạt họa cảnh {i + 1}:",
                [
                    "🖼️ 1. Ghép phụ đề và hình tĩnh (hoặc Video thường)",
                    "🌟 2. Nhân vật/Động vật chuyển động liên tục êm ái"
                ],
                key=f"sc_anim_mode_{i}"
            )
        
        scenes_data.append({"text": sc_text, "media": sc_media, "mode": anim_mode})
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🚀 BẮT ĐẦU SẢN XUẤT VIDEO THEO TỪNG CÔNG ĐOẠN", type="primary", use_container_width=True):
        missing_media = [idx + 1 for idx, sc in enumerate(scenes_data) if sc["media"] is None]
        empty_texts = [idx + 1 for idx, sc in enumerate(scenes_data) if not sc["text"].strip()]
        
        if missing_media:
            st.warning(f"⚠️ Vui lòng tải Ảnh hoặc Video cho các phân cảnh: {missing_media}")
        elif empty_texts:
            st.warning(f"⚠️ Vui lòng nhập lời thuyết minh cho các phân cảnh: {empty_texts}")
        else:
            progress_bar = st.progress(0, text="⏳ Đang chuẩn bị các công đoạn...")
            try:
                if "9:16" in ratio_choice:
                    target_w, target_h = 720, 1280
                elif "16:9" in ratio_choice:
                    target_w, target_h = 1280, 720
                else:
                    target_w, target_h = 720, 720

                scene_video_clips = []
                total_scenes = len(scenes_data)

                for idx, scene in enumerate(scenes_data):
                    pct = int(10 + (idx / total_scenes) * 70)
                    progress_bar.progress(pct, text=f"⏳ Đang xử lý Phân Cảnh {idx + 1}/{total_scenes}...")

                    # 1. Âm thanh giọng đọc
                    comm = edge_tts.Communicate(scene["text"], selected_prod_voice)
                    t_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                    asyncio.run(comm.save(t_audio.name))
                    sc_audio_clip = AudioFileClip(t_audio.name)
                    sc_duration = sc_audio_clip.duration

                    uploaded_file = scene["media"]
                    anim_choice = scene["mode"]
                    is_video = uploaded_file.type.startswith("video") or uploaded_file.name.lower().endswith((".mp4", ".mov", ".avi"))

                    # CHẾ ĐỘ 2: CHUYỂN ĐỘNG LIÊN TỤC KHÔNG GIẬT HÌNH
                    if "🌟" in anim_choice and not is_video:
                        if not server_url.strip():
                            st.error(f"❌ Cảnh {idx + 1} yêu cầu AI chuyển động nhưng chưa có GPU Server URL!")
                            st.stop()
                            
                        target_endpoint = f"{server_url.strip().rstrip('/')}/animate_scene"
                        headers = {"User-Agent": "Mozilla/5.0", "ngrok-skip-browser-warning": "true"}
                        
                        progress_bar.progress(pct + 2, text=f"⏳ GPU đang tạo chuyển động tự nhiên cho Cảnh {idx + 1}...")
                        files = {"image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "image/jpeg")}
                        resp = requests.post(target_endpoint, files=files, headers=headers, timeout=600)

                        if resp.status_code == 200:
                            t_anim_vid = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                            t_anim_vid.write(resp.content)
                            t_anim_vid.close()
                            
                            raw_vid = VideoFileClip(t_anim_vid.name)
                            # ÁP DỤNG SEAMLESS SMOOTH LOOP ĐẢO CHIỀU MỀM
                            smooth_vid = make_seamless_smooth_video(raw_vid, sc_duration)
                            composed_video = compose_fitted_video(smooth_vid, target_w, target_h)
                            sc_composed = composed_video.set_audio(sc_audio_clip)
                        else:
                            st.error(f"❌ Cảnh {idx + 1}: Máy chủ GPU báo lỗi: {resp.text}")
                            st.stop()
                    
                    # NẾU LÀ VIDEO GỐC
                    elif is_video:
                        t_vid = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                        t_vid.write(uploaded_file.getvalue())
                        t_vid.close()

                        raw_vid = VideoFileClip(t_vid.name)
                        smooth_vid = make_seamless_smooth_video(raw_vid, sc_duration)
                        composed_video = compose_fitted_video(smooth_vid, target_w, target_h)
                        sc_composed = composed_video.set_audio(sc_audio_clip)
                    
                    # CHẾ ĐỘ 1: ẢNH TĨNH VỚI CHUYỂN ĐỘNG TRÔI TỰ NHIÊN MỘT CHIỀU
                    else:
                        pil_img = Image.open(uploaded_file).convert("RGB")
                        fitted_img = fit_image_to_canvas(pil_img, target_w, target_h)
                        t_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                        fitted_img.save(t_img.name, "JPEG", quality=95)
                        t_img.close()

                        sc_img_clip = ImageClip(t_img.name).set_duration(sc_duration)

                        if motion_effect == "Trôi chậm êm ái (Cinematic Drift)":
                            sc_img_clip = sc_img_clip.fx(vfx.resize, lambda t: 1.0 + 0.03 * (t / sc_duration))
                        elif motion_effect == "Zoom In Mềm (Phóng to nhẹ)":
                            sc_img_clip = sc_img_clip.fx(vfx.resize, lambda t: 1.0 + 0.04 * (t / sc_duration))
                        elif motion_effect == "Zoom Out Mềm (Thu nhỏ nhẹ)":
                            sc_img_clip = sc_img_clip.fx(vfx.resize, lambda t: 1.04 - 0.04 * (t / sc_duration))

                        sc_composed = sc_img_clip.set_audio(sc_audio_clip)

                    # 3. Phụ đề tự động
                    if sub_toggle:
                        current_sub_text = scene["text"].replace("\n", " ")

                        def make_sub_frame(frame, txt=current_sub_text):
                            img = Image.fromarray(frame)
                            draw = ImageDraw.Draw(img)
                            try:
                                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", sub_font_size)
                            except Exception:
                                try:
                                    font = ImageFont.truetype("arial.ttf", sub_font_size)
                                except Exception:
                                    font = ImageFont.load_default()

                            max_chars = max(12, int(target_w / (sub_font_size * 0.65)))
                            words = txt.split()
                            lines = []
                            cur = []
                            for w in words:
                                cur.append(w)
                                if len(" ".join(cur)) > max_chars:
                                    lines.append(" ".join(cur[:-1]))
                                    cur = [w]
                            if cur:
                                lines.append(" ".join(cur))

                            rendered_txt = "\n".join(lines)
                            bbox = draw.multiline_textbbox((0, 0), rendered_txt, font=font, align="center")
                            text_w = bbox[2] - bbox[0]
                            text_h = bbox[3] - bbox[1]
                            pos_x = (target_w - text_w) // 2
                            bottom_margin = 140 if target_h > target_w else 60
                            pos_y = target_h - text_h - bottom_margin

                            for ox in range(-2, 3):
                                for oy in range(-2, 3):
                                    draw.multiline_text((pos_x + ox, pos_y + oy), rendered_txt, font=font, fill="black", align="center")

                            draw.multiline_text((pos_x, pos_y), rendered_txt, font=font, fill=sub_color, align="center")
                            return np.array(img)

                        sc_final_clip = sc_composed.fl_image(make_sub_frame)
                    else:
                        sc_final_clip = sc_composed

                    scene_video_clips.append(sc_final_clip)

                # 4. Nối video hoàn chỉnh
                progress_bar.progress(85, text="⏳ Đang ghép nối các phân cảnh thành video hoàn chỉnh...")
                final_full_video = concatenate_videoclips(scene_video_clips, method="compose")

                out_vid_path = os.path.join(tempfile.gettempdir(), f"final_output_{int(time.time())}.mp4")
                final_full_video.write_videofile(
                    out_vid_path,
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    ffmpeg_params=["-pix_fmt", "yuv420p"],
                    preset="ultrafast",
                    threads=2,
                    logger=None
                )

                progress_bar.progress(100, text="✅ Render thành công tất cả các phân cảnh!")

                with open(out_vid_path, "rb") as vf:
                    st.session_state["rendered_final_video"] = vf.read()

                final_full_video.close()
                for c in scene_video_clips:
                    c.close()

            except Exception as e:
                progress_bar.empty()
                st.error(f"❌ Xảy ra lỗi trong quá trình sản xuất video phân cảnh: {e}")

    # Hiển thị video thành phẩm
    if "rendered_final_video" in st.session_state and st.session_state["rendered_final_video"]:
        st.success("🎉 Video hoàn chỉnh đã xuất bản thành công!")
        
        col_v1, col_v2, col_v3 = st.columns([1, 1.4, 1])
        with col_v2:
            st.video(st.session_state["rendered_final_video"])
            st.download_button(
                label="⬇️ TẢI VIDEO HOÀN CHỈNH (MP4)",
                data=st.session_state["rendered_final_video"],
                file_name="social_video_output.mp4",
                mime="video/mp4",
                use_container_width=True
            )

# ==============================================================================
# PHÂN HỆ 2: TRỢ LÝ VIẾT KỊCH BẢN GEMINI
# ==============================================================================
elif menu_choice == "2. ✨ Trợ Lý Viết Kịch Bản Phân Cảnh (Gemini)":
    st.markdown('<div class="main-header">✨ Trợ Lý Sáng Tạo Kịch Bản Phân Cảnh (Gemini Studio)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Tự động biên soạn kịch bản chia rõ từng công đoạn/phân cảnh (Scene 1, Scene 2, Scene 3...) để dễ dàng ghép ảnh hoặc video tương ứng.</div>', unsafe_allow_html=True)

    col_g1, col_g2 = st.columns([2, 1])
    with col_g1:
        topic_input = st.text_input("Chủ đề video của bạn:", value="Quy trình 3 bước tái tạo năng lượng mỗi buổi sáng")
    with col_g2:
        num_scenes = st.slider("Số lượng phân cảnh (Scenes):", min_value=2, max_value=8, value=3)

    col_g3, col_g4 = st.columns(2)
    with col_g3:
        genre_option = st.selectbox(
            "Thể loại kịch bản:",
            ["Truyền cảm hứng & Động lực", "Hài hước & Viral", "Tin tức & Phân tích", "Review & Hướng dẫn", "Kể chuyện ngắn"]
        )
    with col_g4:
        target_audience = st.selectbox("Đối tượng khán giả:", ["Mọi lứa tuổi", "Gen Z & Học sinh - Sinh viên", "Dân công sở / Kinh doanh", "Gia đình"])

    if st.button("✨ TẠO KỊCH BẢN CHIA PHÂN CẢNH BẰNG GEMINI", type="primary", use_container_width=True):
        if not gemini_key.strip():
            st.error("❌ Vui lòng nhập Gemini API Key ở cột điều khiển bên trái.")
        else:
            with st.spinner("Gemini đang thiết kế kịch bản từng phân cảnh..."):
                try:
                    prompt = f"""
                    Bạn là một đạo diễn kiêm biên kịch video chuyên nghiệp.
                    Hãy viết kịch bản video ngắn về chủ đề: "{topic_input}".
                    - Thể loại: {genre_option}
                    - Khán giả: {target_audience}
                    - Hãy chia chính xác thành đúng {num_scenes} phân cảnh theo định dạng chuẩn sau để ứng dụng đọc được:
                    
                    [Cảnh 1] Lời thoại thuyết minh của phân cảnh 1
                    [Cảnh 2] Lời thoại thuyết minh của phân cảnh 2
                    ...
                    [Cảnh {num_scenes}] Lời thoại thuyết minh của phân cảnh {num_scenes}
                    
                    Quy tắc: Mỗi cảnh viết từ 20-35 từ, lời thoại trực tiếp, truyền cảm, không kèm theo mô tả góc quay phức tạp.
                    """
                    script_result, used_model = call_gemini_smart_generator(gemini_key, prompt)
                    st.success(f"🎉 Đã tạo kịch bản {num_scenes} phân cảnh thành công bởi mô hình: {used_model}")
                    st.session_state["saved_scenes_script"] = script_result
                except Exception as e:
                    st.error(f"❌ Lỗi khi tạo kịch bản: {e}")

    generated_script = st.text_area(
        "Nội dung kịch bản phân cảnh đã tạo:",
        value=st.session_state.get("saved_scenes_script", "[Cảnh 1] Thức dậy sớm và uống ngay một ly nước ấm để đánh thức mọi cơ quan trong cơ thể.\n[Cảnh 2] Dành ra mười lăm phút vận động nhẹ nhàng giúp tinh thần sảng khoái và tràn đầy năng lượng.\n[Cảnh 3] Lập danh sách ba việc quan trọng nhất cần hoàn thành trong ngày để làm việc hiệu quả."),
        height=220
    )
