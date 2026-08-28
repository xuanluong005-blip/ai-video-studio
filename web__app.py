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
from PIL import Image, ImageDraw, ImageFont
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

# 1. Cấu hình giao diện
st.set_page_config(
    page_title="AI Creative Studio Super Pro Max",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 800; color: #1976D2; margin-bottom: 0.2rem; }
    .sub-header { font-size: 1.05rem; color: #4B5563; margin-bottom: 1.5rem; }
    .scene-box { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 15px; margin-bottom: 15px; }
    .stButton>button { border-radius: 8px; font-weight: 600; height: 3em; }
</style>
""", unsafe_allow_html=True)

# 2. Sidebar điều khiển
with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/video-editing.png", width=110)
    st.title("⚙️ TRUNG TÂM ĐIỀU KHIỂN")
    
    server_url = st.text_input(
        "GPU Server URL (Cloudflare / Ngrok):",
        value="",
        placeholder="https://xxxx.ngrok-free.app",
        help="Dán URL tunnel được cung cấp từ Kaggle Notebook vào đây."
    )
    
    col_p1, col_p2 = st.columns([1, 1])
    with col_p1:
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

    with col_p2:
        if st.button("🧹 Reset App", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.markdown("---")
    gemini_key = st.text_input("Gemini API Key:", type="password", value="", help="Nhập API Key để mở khóa trợ lý viết kịch bản.")
    
    st.markdown("---")
    menu_choice = st.radio(
        "📌 CHỌN TÍNH NĂNG HOẠT ĐỘNG:",
        [
            "1. 🎞️ Xưởng Sản Xuất Video Phân Cảnh (Toàn Diện)",
            "2. 🗣️ Thử Nghiệm Nhanh Khẩu Hình 1 Cảnh (Lip-Sync)",
            "3. 🎭 Diễn Hoạt Biểu Cảm (LivePortrait GPU)",
            "4. 🎙️ Phòng Thu Giọng Nói AI (Edge-TTS)",
            "5. ✨ Trợ Lý Viết Kịch Bản Phân Cảnh (Gemini)"
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

    priority_order = [
        "models/gemini-3.6-flash", "models/gemini-3.6-pro",
        "models/gemini-2.5-flash", "models/gemini-1.5-flash", "gemini-1.5-flash"
    ]
    target_model = next((p for p in priority_order if p in available_models), "models/gemini-3.6-flash")
    model = genai.GenerativeModel(target_model)
    response = model.generate_content(prompt_text)
    if response and response.text:
        return response.text, target_model
    raise Exception("Mô hình không trả về nội dung.")

# ==============================================================================
# PHÂN HỆ CHÍNH: XƯỞNG SẢN XUẤT VIDEO PHÂN CẢNH
# ==============================================================================
if menu_choice == "1. 🎞️ Xưởng Sản Xuất Video Phân Cảnh (Toàn Diện)":
    st.markdown('<div class="main-header">🎞️ Xưởng Sản Xuất Video Phân Cảnh Toàn Diện</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Mỗi phân cảnh tự do lựa chọn: <b>🗣️ Ảnh nói chuyện (Lip-Sync Khớp Giọng)</b>, <b>🌟 Chuyển động TOÀN THÂN AI (SVD)</b>, <b>🐾 Động vật nói</b>, <b>👤 Người diễn hoạt</b> hoặc <b>🖼️ Ảnh tĩnh / Video Clip</b>.</div>', unsafe_allow_html=True)

    st.markdown("### ⚙️ 1. Cấu Hình Chung Toàn Video")
    col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
    with col_cfg1:
        prod_voice = st.selectbox(
            "Giọng đọc thuyết minh:",
            ["vi-VN-NamMinhNeural (Nam - Miền Bắc)", "vi-VN-HoaiMyNeural (Nữ - Miền Bắc)", "en-US-JennyNeural (Nữ - Mỹ)", "en-US-GuyNeural (Nam - Mỹ)"]
        ).split(" ")[0]
        
    with col_cfg2:
        ratio_choice = st.selectbox(
            "Tỷ lệ khung hình video:",
            ["16:9 Ngang (YouTube, Facebook, Web)", "9:16 Dọc (TikTok, Shorts, Reels)", "1:1 Vuông (Instagram Post)"]
        )
        
    with col_cfg3:
        motion_effect = st.selectbox(
            "Hiệu ứng chuyển cảnh cho cảnh TĨNH (Ken Burns):",
            ["Không sử dụng hiệu ứng", "Zoom In Nhẹ (Phóng to dần)", "Zoom Out Nhẹ (Thu nhỏ dần)"]
        )

    col_sub1, col_sub2 = st.columns(2)
    with col_sub1:
        sub_toggle = st.checkbox("Chèn phụ đề tiếng Việt tự động cho từng cảnh", value=True)
    with col_sub2:
        if sub_toggle:
            sub_font_size = st.slider("Cỡ chữ phụ đề:", min_value=20, max_value=50, value=30, step=2)
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
            sc_text = st.text_area(f"Lời thuyết minh cảnh {i + 1}:", value=def_text, key=f"sc_text_{i}", height=110)
        with c_sc2:
            sc_media = st.file_uploader(
                f"Tải Ảnh hoặc Video cảnh {i + 1}:",
                type=["jpg", "jpeg", "png", "mp4", "mov", "avi"],
                key=f"sc_media_{i}"
            )
            if sc_media:
                if sc_media.type.startswith("image"):
                    st.image(sc_media, width=140, caption="Hình ảnh cảnh")
                else:
                    st.video(sc_media)
        with c_sc3:
            anim_mode = st.selectbox(
                f"Chế độ hoạt họa cảnh {i + 1}:",
                [
                    "🗣️ Ảnh nói chuyện (Lip-Sync Khớp giọng thoại)",
                    "🌟 Chuyển động TOÀN THÂN AI (SVD Cinematic)",
                    "🐾 Cử động ĐỘNG VẬT (LivePortrait Animal)",
                    "👤 Cử động NGƯỜI (LivePortrait Human)",
                    "🖼️ Tĩnh (Không cử động / Video thường)"
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
                if "16:9" in ratio_choice:
                    target_w, target_h = 1280, 720
                elif "9:16" in ratio_choice:
                    target_w, target_h = 720, 1280
                else:
                    target_w, target_h = 720, 720

                scene_video_clips = []
                total_scenes = len(scenes_data)

                for idx, scene in enumerate(scenes_data):
                    pct = int(10 + (idx / total_scenes) * 70)
                    progress_bar.progress(pct, text=f"⏳ Đang xử lý Phân Cảnh {idx + 1}/{total_scenes}...")

                    # 1. Tạo file audio giọng đọc cho riêng phân cảnh này
                    comm = edge_tts.Communicate(scene["text"], prod_voice)
                    t_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                    asyncio.run(comm.save(t_audio.name))
                    sc_audio_clip = AudioFileClip(t_audio.name)
                    sc_duration = sc_audio_clip.duration

                    uploaded_file = scene["media"]
                    anim_choice = scene["mode"]
                    is_video = uploaded_file.type.startswith("video") or uploaded_file.name.lower().endswith((".mp4", ".mov", ".avi"))

                    # NẾU CẦN GPU XỬ LÝ (Lip-Sync, SVD, Animal, Human)
                    if ("🗣️" in anim_choice or "🌟" in anim_choice or "🐾" in anim_choice or "👤" in anim_choice) and not is_video:
                        if not server_url.strip():
                            st.error(f"❌ Cảnh {idx + 1} yêu cầu AI chuyển động nhưng chưa có GPU Server URL!")
                            st.stop()
                            
                        target_endpoint = f"{server_url.strip().rstrip('/')}/animate_scene"
                        headers = {"User-Agent": "Mozilla/5.0", "ngrok-skip-browser-warning": "true"}
                        
                        if "🗣️" in anim_choice:
                            progress_bar.progress(pct + 2, text=f"⏳ GPU đang khớp khẩu hình miệng theo lời nói cho Cảnh {idx + 1}...")
                            with open(t_audio.name, "rb") as af:
                                files = {
                                    "image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "image/jpeg"),
                                    "audio": ("voice.wav", af.read(), "audio/wav")
                                }
                                data = {"mode": "lipsync"}
                                resp = requests.post(target_endpoint, files=files, data=data, headers=headers, timeout=600)
                        
                        elif "🌟" in anim_choice:
                            progress_bar.progress(pct + 2, text=f"⏳ GPU đang sinh chuyển động toàn thân SVD cho Cảnh {idx + 1}...")
                            files = {"image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "image/jpeg")}
                            data = {"mode": "svd"}
                            resp = requests.post(target_endpoint, files=files, data=data, headers=headers, timeout=600)
                            
                        elif "🐾" in anim_choice:
                            progress_bar.progress(pct + 2, text=f"⏳ GPU đang tạo cử động Động vật cho Cảnh {idx + 1}...")
                            files = {"image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "image/jpeg")}
                            data = {"mode": "animal"}
                            resp = requests.post(target_endpoint, files=files, data=data, headers=headers, timeout=600)
                            
                        else:
                            progress_bar.progress(pct + 2, text=f"⏳ GPU đang tạo cử động Người cho Cảnh {idx + 1}...")
                            files = {"image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "image/jpeg")}
                            data = {"mode": "human"}
                            resp = requests.post(target_endpoint, files=files, data=data, headers=headers, timeout=600)

                        if resp.status_code == 200:
                            t_anim_vid = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                            t_anim_vid.write(resp.content)
                            t_anim_vid.close()
                            
                            raw_vid = VideoFileClip(t_anim_vid.name)
                            if raw_vid.duration < sc_duration:
                                loop_count = math.ceil(sc_duration / raw_vid.duration)
                                raw_vid = concatenate_videoclips([raw_vid] * loop_count)
                            raw_vid = raw_vid.subclip(0, sc_duration).resize(newsize=(target_w, target_h))
                            sc_composed = raw_vid.set_audio(sc_audio_clip)
                        else:
                            st.error(f"❌ Cảnh {idx + 1}: Máy chủ GPU không thể xử lý (Lỗi {resp.status_code}). Chi tiết: {resp.text}")
                            st.stop()
                    
                    elif is_video:
                        t_vid = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                        t_vid.write(uploaded_file.getvalue())
                        t_vid.close()

                        raw_vid = VideoFileClip(t_vid.name)
                        if raw_vid.duration < sc_duration:
                            loop_count = math.ceil(sc_duration / raw_vid.duration)
                            raw_vid = concatenate_videoclips([raw_vid] * loop_count)
                        
                        raw_vid = raw_vid.subclip(0, sc_duration).resize(newsize=(target_w, target_h))
                        sc_composed = raw_vid.set_audio(sc_audio_clip)
                    
                    else:
                        pil_img = Image.open(uploaded_file).convert("RGB")
                        pil_img = pil_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                        t_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                        pil_img.save(t_img.name, "JPEG", quality=90)
                        t_img.close()

                        sc_img_clip = ImageClip(t_img.name).set_duration(sc_duration)

                        if motion_effect == "Zoom In Nhẹ (Phóng to dần)":
                            sc_img_clip = sc_img_clip.fx(vfx.resize, lambda t: 1.0 + 0.04 * (t / sc_duration))
                        elif motion_effect == "Zoom Out Nhẹ (Thu nhỏ dần)":
                            sc_img_clip = sc_img_clip.fx(vfx.resize, lambda t: 1.04 - 0.04 * (t / sc_duration))

                        sc_composed = sc_img_clip.set_audio(sc_audio_clip)

                    # Phụ đề
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

                            max_chars = max(10, int(target_w / (sub_font_size * 0.65)))
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
                            pos_y = target_h - text_h - 50

                            for ox in range(-2, 3):
                                for oy in range(-2, 3):
                                    draw.multiline_text((pos_x + ox, pos_y + oy), rendered_txt, font=font, fill="black", align="center")

                            draw.multiline_text((pos_x, pos_y), rendered_txt, font=font, fill=sub_color, align="center")
                            return np.array(img)

                        sc_final_clip = sc_composed.fl_image(make_sub_frame)
                    else:
                        sc_final_clip = sc_composed

                    scene_video_clips.append(sc_final_clip)

                progress_bar.progress(85, text="⏳ Đang ghép nối các phân cảnh thành video hoàn chỉnh...")
                final_full_video = concatenate_videoclips(scene_video_clips, method="compose")

                out_vid_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                final_full_video.write_videofile(
                    out_vid_path,
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    preset="ultrafast",
                    threads=2,
                    logger=None
                )

                progress_bar.progress(100, text="✅ Render thành công tất cả các phân cảnh!")

                with open(out_vid_path, "rb") as vf:
                    final_bytes = vf.read()

                st.success("🎉 Video hoàn chỉnh từ các phân cảnh xuất bản thành công!")
                st.video(final_bytes)

                st.download_button(
                    label="⬇️ TẢI VIDEO HOÀN CHỈNH (MP4)",
                    data=final_bytes,
                    file_name="multi_scene_animated_video.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )
            except Exception as e:
                progress_bar.empty()
                st.error(f"❌ Xảy ra lỗi trong quá trình sản xuất video phân cảnh: {e}")

# ==============================================================================
# PHÂN HỆ 2: THỬ NGHIỆM NHANH KHẨU HÌNH (LIP-SYNC)
# ==============================================================================
elif menu_choice == "2. 🗣️ Thử Nghiệm Nhanh Khẩu Hình 1 Cảnh (Lip-Sync)":
    st.markdown('<div class="main-header">🗣️ Thử Nghiệm Nhanh Khẩu Hình 1 Cảnh (Lip-Sync)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Kiểm tra nhanh chuyển động mấp máy môi của một nhân vật duy nhất trước khi đưa vào dự án lớn.</div>', unsafe_allow_html=True)

    col_l1, col_l2 = st.columns([1, 1])
    with col_l1:
        lip_img = st.file_uploader("Tải lên ảnh chân dung rõ khuôn mặt người:", type=["jpg", "jpeg", "png"], key="single_lipsync_img")
        if lip_img:
            st.image(lip_img, width=220)

    with col_l2:
        lip_text = st.text_area("Lời thoại:", value="Xin chào các bạn, tôi là trợ lý ảo AI.", height=100)
        lip_v = st.selectbox("Giọng đọc:", ["vi-VN-NamMinhNeural (Nam Bắc)", "vi-VN-HoaiMyNeural (Nữ Bắc)"]).split(" ")[0]

    if st.button("🚀 Render Thử Khẩu Hình", type="primary", use_container_width=True):
        if not lip_img or not lip_text.strip() or not server_url.strip():
            st.warning("⚠️ Vui lòng cung cấp đầy đủ Ảnh, Lời thoại và GPU URL.")
        else:
            with st.spinner("Đang tạo video thử nghiệm..."):
                comm = edge_tts.Communicate(lip_text, lip_v)
                t_aud = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                asyncio.run(comm.save(t_aud.name))
                with open(t_aud.name, "rb") as af:
                    files = {"image": (lip_img.name, lip_img.getvalue(), "image/jpeg"), "audio": ("v.wav", af.read(), "audio/wav")}
                    res = requests.post(f"{server_url.strip().rstrip('/')}/lipsync", files=files, headers={"ngrok-skip-browser-warning": "true"}, timeout=600)
                if res.status_code == 200:
                    st.success("Tạo thành công!")
                    st.video(res.content)
                else:
                    st.error(f"Lỗi: {res.text}")

# ==============================================================================
# PHÂN HỆ 3: LIVEPORTRAIT GỐC (VIDEO DRIVING)
# ==============================================================================
elif menu_choice == "3. 🎭 Diễn Hoạt Biểu Cảm (LivePortrait GPU)":
    st.markdown('<div class="main-header">🎭 Diễn Hoạt Cử Động Biểu Cảm Khuôn Mặt (LivePortrait)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        img_f = st.file_uploader("Ảnh chân dung:", type=["jpg", "jpeg", "png"])
        if img_f: st.image(img_f, width=220)
    with c2:
        vid_f = st.file_uploader("Video mẫu biểu cảm driving:", type=["mp4", "mov", "avi"])
        if vid_f: st.video(vid_f)

    if st.button("🎬 Render LivePortrait", type="primary", use_container_width=True):
        if not img_f or not vid_f or not server_url.strip():
            st.warning("⚠️ Vui lòng tải đủ Ảnh, Video và GPU URL.")
        else:
            with st.spinner("GPU đang render..."):
                files = {"image": (img_f.name, img_f.getvalue(), "image/jpeg"), "video": (vid_f.name, vid_f.getvalue(), "video/mp4")}
                res = requests.post(f"{server_url.strip().rstrip('/')}/process", files=files, headers={"ngrok-skip-browser-warning": "true"}, timeout=600)
                if res.status_code == 200:
                    st.success("Thành công!")
                    st.video(res.content)
                else:
                    st.error(f"Lỗi: {res.text}")

# ==============================================================================
# PHÂN HỆ 4: EDGE-TTS
# ==============================================================================
elif menu_choice == "4. 🎙️ Phòng Thu Giọng Nói AI (Edge-TTS)":
    st.markdown('<div class="main-header">🎙️ Phòng Thu Giọng Nói Chuẩn AI (Edge-TTS)</div>', unsafe_allow_html=True)
    tts_txt = st.text_area("Văn bản cần đọc:", height=150, value="Chào mừng bạn đến với hệ thống AI Creative Studio.")
    v_dict = {
        "🇻🇳 vi-VN-NamMinhNeural (Nam Bắc)": "vi-VN-NamMinhNeural",
        "🇻🇳 vi-VN-HoaiMyNeural (Nữ Bắc)": "vi-VN-HoaiMyNeural",
        "🇺🇸 en-US-GuyNeural (Nam Mỹ)": "en-US-GuyNeural",
        "🇺🇸 en-US-JennyNeural (Nữ Mỹ)": "en-US-JennyNeural"
    }
    sel_v = v_dict[st.selectbox("Chọn giọng đọc:", list(v_dict.keys()))]
    if st.button("🔊 Tạo File Âm Thanh", type="primary", use_container_width=True):
        if tts_txt.strip():
            async def gen_aud():
                comm = edge_tts.Communicate(tts_txt, sel_v)
                t_f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                await comm.save(t_f.name)
                return t_f.name
            p = asyncio.run(gen_aud())
            st.success("Tạo âm thanh thành công!")
            st.audio(p)

# ==============================================================================
# PHÂN HỆ 5: GEMINI SCRIPT
# ==============================================================================
elif menu_choice == "5. ✨ Trợ Lý Viết Kịch Bản Phân Cảnh (Gemini)":
    st.markdown('<div class="main-header">✨ Trợ Lý Sáng Tạo Kịch Bản Phân Cảnh (Gemini)</div>', unsafe_allow_html=True)
    top = st.text_input("Chủ đề video:", value="3 thói quen buổi sáng để tràn đầy năng lượng")
    n_sc = st.slider("Số lượng cảnh:", 2, 8, 3)
    if st.button("✨ Viết Kịch Bản Bằng Gemini", type="primary", use_container_width=True):
        if not gemini_key.strip():
            st.error("Chưa nhập Gemini API Key!")
        else:
            with st.spinner("Gemini đang tạo kịch bản..."):
                try:
                    p = f"Hãy viết kịch bản video ngắn chủ đề: '{top}', chia đúng {n_sc} cảnh dạng [Cảnh 1]..., [Cảnh 2]..."
                    txt, m = call_gemini_smart_generator(gemini_key, p)
                    st.session_state["saved_scenes_script"] = txt
                    st.success(f"Tạo thành công bằng mô hình: {m}")
                except Exception as e:
                    st.error(f"Lỗi: {e}")
    st.text_area("Kịch bản:", value=st.session_state.get("saved_scenes_script", ""), height=220)
