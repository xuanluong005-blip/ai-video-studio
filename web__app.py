import streamlit as st
import tempfile
import os
from PIL import Image

st.title("🎭 Ghép Nhân Vật Tĩnh Vào Video Động (Giữ Ngũ Quan)")

col1, col2 = st.columns(2)
with col1:
    source_img = st.file_uploader("1. Tải ảnh nhân vật tĩnh (Source Image):", type=["jpg", "jpeg", "png"])
with col2:
    driving_vid = st.file_uploader("2. Tải video chuyển động mẫu (Driving Video):", type=["mp4", "mov", "avi"])

if st.button("🚀 BẮT ĐẦU GHÉP CHUYỂN ĐỘNG", use_container_width=True):
    if not source_img or not driving_vid:
        st.error("⚠️ Vui lòng tải lên cả ảnh nhân vật và video chuyển động mẫu!")
    else:
        with st.spinner("AI đang khóa ngũ quan và truyền chuyển động sang ảnh tĩnh..."):
            try:
                from gradio_client import Client, handle_file
                
                with tempfile.TemporaryDirectory() as td:
                    img_path = os.path.join(td, "source.jpg")
                    vid_path = os.path.join(td, "driving.mp4")
                    
                    # Lưu file tạm
                    Image.open(source_img).convert("RGB").save(img_path)
                    with open(vid_path, "wb") as f:
                        f.write(driving_vid.read())
                    
                    # Kết nối máy chủ LivePortrait AI
                    client = Client("KwaiVGI/LivePortrait")
                    result = client.predict(
                        source_image=handle_file(img_path),
                        driving_video=handle_file(vid_path),
                        api_name="/gpu"
                    )
                    
                    out_path = result[0] if isinstance(result, (tuple, list)) else result
                    
                    with open(out_path, "rb") as vf:
                        video_bytes = vf.read()
                    
                    st.success("🎉 Ghép chuyển động thành công!")
                    st.video(video_bytes)
                    st.download_button("📥 Tải Video Kết Quả", video_bytes, "swapped_motion.mp4", "video/mp4", use_container_width=True)
            except Exception as e:
                st.error(f"❌ Có lỗi xử lý: {str(e)}")
