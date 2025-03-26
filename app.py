import os
import streamlit as st
import json
import tempfile
from PIL import Image
import time
import uuid
from utils.config import validate_api_keys, create_directories, DEFAULT_CONFIG
from utils.story_generator import StoryGenerator
from utils.image_generator import ImageGenerator
from utils.audio_generator import AudioGenerator
from utils.video_generator import VideoGenerator
from utils.db_utils import db_manager
from utils.telegram_utils import telegram_manager
import pandas as pd
import traceback

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="Tạo Truyện và Video Tự Động",
    page_icon="🎬",
    layout="wide"
)

# Hàm tạo thư mục output với ID phiên
def create_session_directory():
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(int(time.time()))
    
    session_dir = os.path.join(DEFAULT_CONFIG['output_dir'], st.session_state.session_id)
    os.makedirs(session_dir, exist_ok=True)
    return session_dir

# Hàm đọc dữ liệu từ file JSON
def read_json_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# Hàm hiển thị thông tin truyện
def display_story(story_data, output_dir):
    st.header("Nội dung truyện đã tạo")
    
    for chapter in story_data["chapters"]:
        with st.expander(f"Chương {chapter['chapter_num']}: {chapter.get('title', '')}"):
            st.write(chapter["content"])
            
            # Nút tải xuống chương
            chapter_file = os.path.join(output_dir, f"chapter_{chapter['chapter_num']}.txt")
            if os.path.exists(chapter_file):
                with open(chapter_file, "r", encoding="utf-8") as f:
                    chapter_text = f.read()
                st.download_button(
                    label=f"Tải xuống chương {chapter['chapter_num']}",
                    data=chapter_text,
                    file_name=f"chapter_{chapter['chapter_num']}.txt",
                    mime="text/plain"
                )

# Hàm hiển thị hình ảnh
def display_images(story_images):
    """Hiển thị hình ảnh minh họa cho từng chương"""
    st.subheader("Hình ảnh minh họa")
    
    # Kiểm tra dữ liệu hình ảnh
    if not story_images:
        st.warning("Không có dữ liệu hình ảnh nào.")
        return
    
    # Hiển thị theo tabs cho từng chương
    chapter_tabs = st.tabs([f"Chương {chapter_data['chapter_num']}" for chapter_data in story_images])
    
    for i, tab in enumerate(chapter_tabs):
        chapter_data = story_images[i]
        chapter_images = chapter_data.get("images", [])
        
        with tab:
            if not chapter_images:
                st.warning(f"Không có hình ảnh cho Chương {chapter_data['chapter_num']}.")
                continue
            
            st.write(f"Có {len(chapter_images)} hình ảnh minh họa cho chương này.")
            
            # Hiển thị hình ảnh theo grid
            cols = 2
            for j in range(0, len(chapter_images), cols):
                row_cols = st.columns(cols)
                
                for k in range(cols):
                    idx = j + k
                    if idx < len(chapter_images):
                        image_data = chapter_images[idx]
                        image_path = image_data.get("image_path")
                        
                        with row_cols[k]:
                            if os.path.exists(image_path):
                                st.image(image_path, use_column_width=True)
                                
                                # Hiển thị thông tin đoạn văn được sử dụng
                                with st.expander("Xem đoạn văn và prompt"):
                                    st.markdown("**Đoạn văn bản:**")
                                    st.text(image_data.get("segment_text", "")[:300] + "...")
                                    
                                    st.markdown("**Prompt đã sử dụng:**")
                                    prompt = image_data.get("prompt", "")
                                    prompt_parts = prompt.split("\n\n")
                                    
                                    # Hiển thị cấu trúc prompt theo từng phần
                                    if len(prompt_parts) > 1:
                                        st.text(prompt_parts[0])  # Hiển thị phần chính của prompt
                                        if len(prompt_parts) > 1:
                                            st.text("Thông tin nhân vật:" + prompt_parts[1])
                                    else:
                                        st.text(prompt)
                            else:
                                st.error(f"Không tìm thấy file: {image_path}")
    
    # Tùy chọn tải xuống tất cả hình ảnh
    with st.expander("Tải xuống hình ảnh"):
        all_images = []
        for chapter in story_images:
            for img in chapter.get("images", []):
                if img.get("image_path") and os.path.exists(img.get("image_path")):
                    all_images.append(img.get("image_path"))
        
        if all_images:
            st.write(f"Có tổng cộng {len(all_images)} hình ảnh.")
            st.markdown("Sử dụng thư mục output để tìm các hình ảnh đã tạo.")

# Hàm hiển thị audio
def display_audio(story_audio):
    st.header("Audio đã tạo")
    
    for chapter_audio in story_audio:
        chapter_num = chapter_audio["chapter_num"]
        full_audio = chapter_audio.get("full_audio")
        
        with st.expander(f"Audio cho Chương {chapter_num}"):
            if full_audio and os.path.exists(full_audio):
                st.audio(full_audio)
                st.download_button(
                    label=f"Tải xuống audio chương {chapter_num}",
                    data=open(full_audio, "rb").read(),
                    file_name=f"chapter_{chapter_num}_audio.mp3",
                    mime="audio/mpeg"
                )
            else:
                segments = chapter_audio.get("segments", [])
                if segments:
                    for i, segment in enumerate(segments):
                        audio_path = segment.get("audio_path")
                        if audio_path and os.path.exists(audio_path):
                            st.write(f"**Đoạn {i+1}:**")
                            st.audio(audio_path)
                else:
                    st.write("Không có audio nào được tạo cho chương này.")

# Hàm hiển thị video
def display_videos(video_data, video_id=None):
    st.header("Video đã tạo")
    
    full_video = video_data.get("full_video")
    if full_video and os.path.exists(full_video):
        st.subheader("Video truyện đầy đủ")
        st.video(full_video)
        
        # Tạo nút tải xuống với callback để cập nhật trạng thái
        video_bytes = open(full_video, "rb").read()
        col1, col2 = st.columns([3, 1])
        with col1:
            # Tạo key duy nhất bằng cách thêm UUID ngẫu nhiên
            random_uuid = str(uuid.uuid4())
            download_key = f"download_full_{video_id if video_id else 'default'}_{random_uuid}"
            st.download_button(
                label="Tải xuống video đầy đủ",
                data=video_bytes,
                file_name="full_story.mp4",
                mime="video/mp4",
                on_click=update_download_status if video_id else None,
                kwargs={"video_id": video_id} if video_id else None,
                key=download_key
            )
        with col2:
            if video_id:
                st.info("📥 Đã lưu vào cơ sở dữ liệu")
            
    
    chapter_videos = video_data.get("chapter_videos", [])
    if chapter_videos:
        st.subheader("Video từng chương")
        for chapter_video in chapter_videos:
            video_path = chapter_video.get("video_path")
            chapter_num = chapter_video.get("chapter_num")
            if video_path and os.path.exists(video_path):
                with st.expander(f"Video Chương {chapter_num}"):
                    st.video(video_path)
                    
                    # Tạo key duy nhất cho nút tải xuống video chương
                    chapter_random_uuid = str(uuid.uuid4())
                    chapter_download_key = f"download_chapter_{chapter_num}_{video_id if video_id else 'default'}_{chapter_random_uuid}"
                    
                    # Tải xuống với cập nhật trạng thái
                    st.download_button(
                        label=f"Tải xuống video chương {chapter_num}",
                        data=open(video_path, "rb").read(),
                        file_name=f"chapter_{chapter_num}_video.mp4",
                        mime="video/mp4",
                        on_click=update_download_status if video_id else None,
                        kwargs={"video_id": video_id, "chapter_num": chapter_num} if video_id else None,
                        key=chapter_download_key
                    )
    
    # Hiển thị các frame hình ảnh nếu có story_images trong session_state
    if "custom_story_images" in st.session_state:
        display_frames(video_data, st.session_state.custom_story_images, st.session_state.get("custom_story_output_dir", "output"))

# Hàm cập nhật trạng thái tải xuống trong MongoDB
def update_download_status(video_id, chapter_num=None):
    if not video_id:
        return
    
    result = db_manager.update_download_status(video_id, chapter_num, downloaded=True)
    if result:
        if chapter_num:
            st.session_state.download_status[f"chapter_{chapter_num}"] = True
        else:
            st.session_state.download_status["full_video"] = True

# Hàm hiển thị log
def create_log_container():
    """Tạo container để hiển thị log chi tiết"""
    log_container = st.expander("Xem log tiến trình", expanded=False)
    log_placeholder = log_container.empty()
    return log_placeholder

def update_log(log_placeholder, message):
    """Cập nhật log với thông báo mới"""
    if "log_messages" not in st.session_state:
        st.session_state.log_messages = []
    
    timestamp = time.strftime("%H:%M:%S", time.localtime())
    log_entry = f"[{timestamp}] {message}"
    st.session_state.log_messages.append(log_entry)
    
    # Hiển thị tất cả các log
    log_placeholder.code("\n".join(st.session_state.log_messages))

def main():
    st.title("🎬 Tạo Tự Động Truyện và Video từ Ý Tưởng")
    st.markdown("""
    Ứng dụng này giúp bạn tạo tự động nội dung truyện và video từ ý tưởng của bạn. 
    Sử dụng các mô hình AI tiên tiến nhất để tạo nội dung truyện, hình ảnh minh họa, âm thanh và video.
    """)
    
    # Kiểm tra API keys khi ứng dụng khởi động
    try:
        validate_api_keys()
    except ValueError as e:
        st.error(f"Lỗi: {e}")
        st.warning("Vui lòng cập nhật file .env với các API key cần thiết.")
        return
    
    # Tạo thư mục output cho phiên làm việc hiện tại
    output_dir = create_session_directory()
    create_directories()
    
    # Tạo tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Cài đặt", "Tạo Truyện", "Tạo Hình ảnh", "Tạo Audio", "Tạo Video", "Tạo Tất Cả", "Tạo Truyện Theo Chương Có Sẵn"])
    
    # Tab Cài đặt
    with tab1:
        st.header("Cài đặt truyện")
        
        # Form nhập thông tin
        with st.form("story_form"):
            story_concept = st.text_area("Ý tưởng truyện của bạn", 
                                        help="Nhập ý tưởng hoặc chủ đề cho câu chuyện bạn muốn tạo")
            
            col1, col2 = st.columns(2)
            with col1:
                num_chapters = st.number_input("Số chương truyện", 
                                               min_value=1, max_value=10, 
                                               value=DEFAULT_CONFIG['num_chapters'])
                
                tokens_per_chapter = st.number_input("Số token mỗi chương", 
                                                    min_value=100, max_value=2000, 
                                                    value=DEFAULT_CONFIG['tokens_per_chapter'],
                                                    step=100)
            
            with col2:
                image_model = st.selectbox("Model tạo hình ảnh", 
                                           options=["cogview4", "stable_diffusion", "gemini"],
                                           index=0,
                                           format_func=lambda x: {
                                               "cogview4": "CogView 4",
                                               "stable_diffusion": "Stable Diffusion",
                                               "gemini": "Gemini 2.0 Flash Image Gen"
                                           }.get(x, x))
                
                tts_provider = st.selectbox("Provider text-to-speech", 
                                           options=["google", "openai"],
                                           index=0,
                                           format_func=lambda x: {
                                               "google": "Google TTS (gTTS)",
                                               "openai": "OpenAI TTS"
                                           }.get(x, x))
            
            # Lưu cài đặt
            submitted = st.form_submit_button("Lưu cài đặt")
            if submitted:
                if not story_concept:
                    st.error("Vui lòng nhập ý tưởng truyện!")
                else:
                    # Lưu cài đặt vào session_state với key khác
                    st.session_state.story_config = {
                        "story_concept": story_concept,
                        "num_chapters": num_chapters,
                        "tokens_per_chapter": tokens_per_chapter,
                        "image_model": image_model,
                        "tts_provider": tts_provider,
                        "output_dir": output_dir
                    }
                    st.success("Đã lưu cài đặt thành công!")
        
        # Hiển thị cài đặt hiện tại
        if 'story_config' in st.session_state:
            st.subheader("Cài đặt hiện tại")
            settings = st.session_state.story_config
            st.json(json.dumps({
                "story_concept": settings["story_concept"][:50] + "..." if len(settings["story_concept"]) > 50 else settings["story_concept"],
                "num_chapters": settings["num_chapters"],
                "tokens_per_chapter": settings["tokens_per_chapter"],
                "image_model": settings["image_model"],
                "tts_provider": settings["tts_provider"]
            }, indent=2))
    
    # Tab Tạo Truyện
    with tab2:
        st.header("Tạo nội dung truyện")
        
        if 'story_config' not in st.session_state:
            st.warning("Vui lòng cài đặt thông tin truyện ở tab Cài đặt trước!")
        else:
            settings = st.session_state.story_config
            
            # Nút tạo truyện
            if st.button("Tạo nội dung truyện"):
                with st.spinner("Đang tạo nội dung truyện..."):
                    story_generator = StoryGenerator()
                    story_data = story_generator.generate_full_story(
                        settings["story_concept"],
                        num_chapters=settings["num_chapters"],
                        tokens_per_chapter=settings["tokens_per_chapter"],
                        output_dir=settings["output_dir"]
                    )
                    
                    # Lưu story_data vào session_state
                    st.session_state.story_data = story_data
                    st.success(f"Đã tạo xong câu chuyện với {settings['num_chapters']} chương!")
            
            # Hiển thị nội dung truyện nếu đã tạo
            if 'story_data' in st.session_state:
                display_story(st.session_state.story_data, settings["output_dir"])
            else:
                # Kiểm tra xem có file story_data.json không
                story_data_path = os.path.join(settings["output_dir"], "story_data.json")
                if os.path.exists(story_data_path):
                    story_data = read_json_data(story_data_path)
                    if story_data:
                        st.session_state.story_data = story_data
                        display_story(story_data, settings["output_dir"])
    
    # Tab Tạo Hình ảnh
    with tab3:
        st.header("Tạo hình ảnh minh họa")
        
        if 'story_config' not in st.session_state:
            st.warning("Vui lòng cài đặt thông tin truyện ở tab Cài đặt trước!")
        elif 'story_data' not in st.session_state:
            st.warning("Vui lòng tạo nội dung truyện ở tab Tạo Truyện trước!")
        else:
            settings = st.session_state.story_config
            
            # Tùy chọn cấu hình tạo hình ảnh
            with st.expander("Tùy chọn nâng cao", expanded=False):
                max_images_per_chapter = st.slider("Số hình ảnh tối đa cho mỗi chương", 
                                                   min_value=1, max_value=10, value=5)
                sample_chapters = st.checkbox("Chỉ tạo hình ảnh cho một số chương mẫu", value=False)
                
                if sample_chapters:
                    num_chapters = len(st.session_state.story_data["chapters"])
                    selected_chapters = st.multiselect(
                        "Chọn các chương cần tạo hình ảnh",
                        options=list(range(1, num_chapters + 1)),
                        default=[1]
                    )
            
            # Nút tạo hình ảnh
            if st.button("Tạo hình ảnh minh họa"):
                try:
                    with st.spinner(f"Đang tạo hình ảnh minh họa với model {settings['image_model']}..."):
                        # Khởi tạo ImageGenerator với tùy chọn nâng cao
                        image_generator = ImageGenerator(model_type=settings["image_model"])
                        
                        # Giới hạn số chương nếu cần
                        if sample_chapters and selected_chapters:
                            filtered_story_data = {
                                "concept": st.session_state.story_data["concept"],
                                "num_chapters": len(selected_chapters),
                                "chapters": [
                                    chapter for chapter in st.session_state.story_data["chapters"] 
                                    if chapter["chapter_num"] in selected_chapters
                                ]
                            }
                            story_data_to_process = filtered_story_data
                        else:
                            story_data_to_process = st.session_state.story_data
                        
                        # Xử lý tạo hình ảnh
                        story_images = image_generator.process_story(
                            story_data_to_process, 
                            output_dir=settings["output_dir"]
                        )
                        
                        # Lưu story_images vào session_state
                        st.session_state.story_images = story_images
                        st.success("Đã tạo xong hình ảnh minh họa!")
                except MemoryError:
                    st.error("Lỗi: Không đủ bộ nhớ để xử lý. Hãy thử giảm số chương hoặc chọn phương pháp 'Chỉ tạo hình ảnh cho một số chương mẫu'.")
                except Exception as e:
                    st.error(f"Lỗi khi tạo hình ảnh: {str(e)}")
                    st.info("Hãy thử lại với ít chương hơn hoặc giảm kích thước nội dung.")
            
            # Hiển thị hình ảnh nếu đã tạo
            if 'story_images' in st.session_state:
                display_images(st.session_state.story_images)
            else:
                # Kiểm tra xem có file images_data.json không
                images_data_path = os.path.join(settings["output_dir"], "images_data.json")
                if os.path.exists(images_data_path):
                    story_images = read_json_data(images_data_path)
                    if story_images:
                        st.session_state.story_images = story_images
                        display_images(story_images)
    
    # Tab Tạo Audio
    with tab4:
        st.header("Tạo Audio từ Text")
        
        if 'story_config' not in st.session_state:
            st.warning("Vui lòng cài đặt thông tin truyện ở tab Cài đặt trước!")
        elif 'story_data' not in st.session_state:
            st.warning("Vui lòng tạo nội dung truyện ở tab Tạo Truyện trước!")
        else:
            settings = st.session_state.story_config
            
            # Nút tạo audio
            if st.button("Tạo audio từ text"):
                with st.spinner(f"Đang tạo audio với provider {settings['tts_provider']}..."):
                    audio_generator = AudioGenerator(provider=settings["tts_provider"])
                    story_audio = audio_generator.process_story(
                        st.session_state.story_data, 
                        output_dir=settings["output_dir"]
                    )
                    
                    # Lưu story_audio vào session_state
                    st.session_state.story_audio = story_audio
                    st.success("Đã tạo xong audio!")
            
            # Hiển thị audio nếu đã tạo
            if 'story_audio' in st.session_state:
                display_audio(st.session_state.story_audio)
            else:
                # Kiểm tra xem có file audio_data.json không
                audio_data_path = os.path.join(settings["output_dir"], "audio_data.json")
                if os.path.exists(audio_data_path):
                    story_audio = read_json_data(audio_data_path)
                    if story_audio:
                        st.session_state.story_audio = story_audio
                        display_audio(story_audio)
    
    # Tab Tạo Video
    with tab5:
        st.header("Tạo Video từ Audio và Hình ảnh")
        
        if 'story_config' not in st.session_state:
            st.warning("Vui lòng cài đặt thông tin truyện ở tab Cài đặt trước!")
        elif 'story_data' not in st.session_state:
            st.warning("Vui lòng tạo nội dung truyện ở tab Tạo Truyện trước!")
        elif 'story_images' not in st.session_state:
            st.warning("Vui lòng tạo hình ảnh ở tab Tạo Hình ảnh trước!")
        elif 'story_audio' not in st.session_state:
            st.warning("Vui lòng tạo audio ở tab Tạo Audio trước!")
        else:
            settings = st.session_state.story_config
            
            # Tùy chọn cho video
            with st.expander("Tùy chọn video", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    width = st.number_input("Chiều rộng video (pixels)", min_value=320, max_value=1920, value=1280, step=16)
                with col2:
                    height = st.number_input("Chiều cao video (pixels)", min_value=240, max_value=1080, value=720, step=16)
                
                fps = st.slider("Frames per second (FPS)", min_value=15, max_value=60, value=30, step=1)
            
            # Nút tạo video
            if st.button("Tạo video"):
                with st.spinner("Đang tạo video... Quá trình này có thể mất nhiều thời gian..."):
                    video_generator = VideoGenerator(width=width, height=height, fps=fps)
                    video_data = video_generator.create_full_video(
                        st.session_state.story_data,
                        st.session_state.story_images,
                        st.session_state.story_audio,
                        output_dir=settings["output_dir"]
                    )
                    
                    # Lưu video_data vào session_state
                    st.session_state.video_data = video_data
                    
                    if video_data and video_data.get("full_video"):
                        st.success("Đã tạo xong video đầy đủ!")
                    else:
                        st.warning("Không thể tạo video đầy đủ, nhưng có thể đã tạo được video cho một số chương.")
            
            # Hiển thị video nếu đã tạo
            if 'video_data' in st.session_state:
                display_videos(st.session_state.video_data)

    # Tab Tạo Tất Cả
    with tab6:
        st.header("Tạo Tất Cả - Một Nhấp Hoàn Thành")
        
        # Form nhập thông tin
        with st.form("all_in_one_form"):
            st.markdown("### Cài đặt truyện")
            
            story_concept = st.text_area("Ý tưởng truyện của bạn", 
                help="Nhập ý tưởng hoặc chủ đề cho câu chuyện bạn muốn tạo")
            
            col1, col2 = st.columns(2)
            with col1:
                num_chapters = st.number_input("Số chương truyện", 
                    min_value=1, max_value=10, 
                    value=DEFAULT_CONFIG['num_chapters'])
                
                tokens_per_chapter = st.number_input("Số token mỗi chương", 
                    min_value=100, max_value=4000, 
                    value=DEFAULT_CONFIG['tokens_per_chapter'],
                    step=100)
            
            with col2:
                image_model = st.selectbox("Model tạo hình ảnh", 
                    options=["cogview4", "stable_diffusion", "gemini"],
                    index=0,
                    format_func=lambda x: {
                        "cogview4": "CogView 4",
                        "gemini": "Gemini 2.0 Flash Image Gen",
                        "stable_diffusion": "Stable Diffusion"
                        
                    }.get(x, x),
                    key="all_in_one_image_model")
                
                tts_provider = st.selectbox("Provider text-to-speech", 
                    options=["google", "openai"],
                    index=0,
                    format_func=lambda x: {
                        "google": "Google TTS (gTTS)",
                        "openai": "OpenAI TTS"
                    }.get(x, x),
                    key="all_in_one_tts")
            
            # Tùy chọn nâng cao (thu gọn mặc định)
            with st.expander("Tùy chọn nâng cao", expanded=False):
                st.markdown("#### Tùy chọn video")
                vcol1, vcol2 = st.columns(2)
                with vcol1:
                    width = st.number_input("Chiều rộng video (pixels)", 
                                          min_value=320, max_value=1920, value=1280, step=16)
                with vcol2:
                    height = st.number_input("Chiều cao video (pixels)", 
                                           min_value=240, max_value=1080, value=720, step=16)
                
                fps = st.slider("Frames per second (FPS)", 
                              min_value=15, max_value=60, value=30, step=1)
            
            # Nút thực hiện tất cả
            submitted = st.form_submit_button("🚀 Tạo Tất Cả")
            
        # Xử lý khi người dùng nhấn nút
        if submitted:
            if not story_concept:
                st.error("Vui lòng nhập ý tưởng truyện!")
            else:
                # Lưu cài đặt
                all_in_one_settings = {
                    "story_concept": story_concept,
                    "num_chapters": num_chapters,
                    "tokens_per_chapter": tokens_per_chapter,
                    "image_model": image_model,
                    "tts_provider": tts_provider,
                    "output_dir": output_dir,
                    "video_width": width if 'width' in locals() else 1280,
                    "video_height": height if 'height' in locals() else 720,
                    "video_fps": fps if 'fps' in locals() else 30
                }
                
                # Hiển thị khung tiến trình
                progress_container = st.empty()
                progress_bar = st.progress(0)
                status_container = st.empty()
                
                # Tạo container hiển thị log
                log_placeholder = create_log_container()
                update_log(log_placeholder, f"Bắt đầu quy trình tạo nội dung tự động với ý tưởng: {story_concept[:100]}...")
                
                try:
                    # Bước 1: Tạo truyện
                    with st.spinner("Bước 1/4: Đang tạo nội dung truyện..."):
                        status_container.info("Bước 1/4: Đang tạo nội dung truyện...")
                        update_log(log_placeholder, f"Bắt đầu tạo {num_chapters} chương truyện với {tokens_per_chapter} token mỗi chương")
                        
                        story_generator = StoryGenerator()
                        story_data = story_generator.generate_full_story(
                            all_in_one_settings["story_concept"],
                            num_chapters=all_in_one_settings["num_chapters"],
                            tokens_per_chapter=all_in_one_settings["tokens_per_chapter"],
                            output_dir=all_in_one_settings["output_dir"]
                        )
                        
                        # Lưu story_data vào session_state
                        st.session_state.story_data = story_data
                        progress_bar.progress(25)
                        status_container.success(f"✅ Đã tạo xong câu chuyện với {all_in_one_settings['num_chapters']} chương!")
                        update_log(log_placeholder, f"✅ Đã tạo xong câu chuyện với {all_in_one_settings['num_chapters']} chương")
                        update_log(log_placeholder, f"Đường dẫn file dữ liệu truyện: {all_in_one_settings['output_dir']}/story_data.json")
                    
                    # Bước 2: Tạo hình ảnh
                    with st.spinner("Bước 2/4: Đang tạo hình ảnh minh họa..."):
                        status_container.info("Bước 2/4: Đang tạo hình ảnh minh họa...")
                        update_log(log_placeholder, f"Bắt đầu tạo hình ảnh minh họa sử dụng model {all_in_one_settings['image_model']}")
                        
                        image_generator = ImageGenerator(model_type=all_in_one_settings["image_model"])
                        # Thêm các sự kiện vào log
                        def log_image_event(chapter_num, scene_num, total_scenes):
                            update_log(log_placeholder, f"Đang tạo hình ảnh {scene_num}/{total_scenes} cho chương {chapter_num}")
                        
                        # Trích xuất thông tin nhân vật
                        update_log(log_placeholder, "Đang phân tích thông tin nhân vật để tạo hình ảnh nhất quán...")
                        
                        story_images = image_generator.process_story(
                            story_data, 
                            output_dir=all_in_one_settings["output_dir"]
                        )
                        
                        # Lưu story_images vào session_state
                        st.session_state.story_images = story_images
                        progress_bar.progress(50)
                        status_container.success("✅ Đã tạo xong hình ảnh minh họa!")
                        update_log(log_placeholder, "✅ Đã tạo xong hình ảnh minh họa")
                        total_images = sum(len(chapter.get("images", [])) for chapter in story_images)
                        update_log(log_placeholder, f"Tổng cộng đã tạo {total_images} hình ảnh cho {len(story_images)} chương")
                        update_log(log_placeholder, f"Đường dẫn file dữ liệu hình ảnh: {all_in_one_settings['output_dir']}/images_data.json")
                    
                    # Bước 3: Tạo audio
                    with st.spinner("Bước 3/4: Đang tạo audio..."):
                        status_container.info("Bước 3/4: Đang tạo audio...")
                        update_log(log_placeholder, f"Bắt đầu tạo audio sử dụng provider {all_in_one_settings['tts_provider']}")
                        
                        audio_generator = AudioGenerator(provider=all_in_one_settings["tts_provider"])
                        story_audio = audio_generator.process_story(
                            story_data, 
                            output_dir=all_in_one_settings["output_dir"]
                        )
                        
                        # Lưu story_audio vào session_state
                        st.session_state.story_audio = story_audio
                        progress_bar.progress(75)
                        status_container.success("✅ Đã tạo xong audio!")
                        update_log(log_placeholder, "✅ Đã tạo xong audio")
                        update_log(log_placeholder, f"Đường dẫn file dữ liệu audio: {all_in_one_settings['output_dir']}/audio_data.json")
                    
                    # Bước 4: Tạo video
                    with st.spinner("Bước 4/4: Đang tạo video... Quá trình này có thể mất nhiều thời gian..."):
                        status_container.info("Bước 4/4: Đang tạo video... Quá trình này có thể mất nhiều thời gian...")
                        update_log(log_placeholder, f"Bắt đầu tạo video với kích thước {all_in_one_settings['video_width']}x{all_in_one_settings['video_height']}, {all_in_one_settings['video_fps']} FPS")
                        
                        video_generator = VideoGenerator(
                            width=all_in_one_settings["video_width"],
                            height=all_in_one_settings["video_height"],
                            fps=all_in_one_settings["video_fps"]
                        )
                        video_data = video_generator.create_full_video(
                            story_data,
                            story_images,
                            story_audio,
                            output_dir=all_in_one_settings["output_dir"]
                        )
                        
                        # Lưu video_data vào session_state
                        st.session_state.video_data = video_data
                        progress_bar.progress(100)
                        
                        if video_data and video_data.get("full_video"):
                            status_container.success("🎉 Hoàn thành! Đã tạo xong video đầy đủ!")
                            update_log(log_placeholder, "🎉 Hoàn thành! Đã tạo xong video đầy đủ")
                            update_log(log_placeholder, f"Đường dẫn video đầy đủ: {video_data.get('full_video')}")
                        else:
                            status_container.warning("⚠️ Không thể tạo video đầy đủ, nhưng có thể đã tạo được video cho một số chương.")
                            update_log(log_placeholder, "⚠️ Không thể tạo video đầy đủ, nhưng có thể đã tạo được video cho một số chương")
                            if video_data and video_data.get("chapter_videos"):
                                for chapter_video in video_data.get("chapter_videos"):
                                    if chapter_video.get("video_path"):
                                        update_log(log_placeholder, f"Video chương {chapter_video.get('chapter_num')}: {chapter_video.get('video_path')}")
                        
                        # Hiển thị kết quả cuối cùng
                        if "video_data" in st.session_state and st.session_state.video_data:
                            all_videos = []
                            full_video = st.session_state.video_data.get("full_video")
                            if full_video and os.path.exists(full_video):
                                st.subheader("Video đầy đủ")
                                st.video(full_video)
                                st.download_button(
                                    label="Tải xuống video đầy đủ",
                                    data=open(full_video, "rb").read(),
                                    file_name="full_story.mp4",
                                    mime="video/mp4"
                                )
                                
                                # Thông tin đường dẫn
                                st.info(f"Video đã được lưu tại: {os.path.abspath(full_video)}")
                                all_videos.append(full_video)
                        
                        # Đánh giá kết quả
                        update_log(log_placeholder, "===== KẾT QUẢ CUỐI CÙNG =====")
                        update_log(log_placeholder, f"- Số chương đã tạo: {len(story_data['chapters'])}")
                        update_log(log_placeholder, f"- Tổng số hình ảnh: {sum(len(chapter.get('images', [])) for chapter in story_images)}")
                        update_log(log_placeholder, f"- Tổng số video: {len(all_videos)}")
                        update_log(log_placeholder, f"- Thời gian hoàn thành: {time.strftime('%H:%M:%S', time.localtime())}")
                        
                except Exception as e:
                    progress_container.empty()
                    status_container.error(f"❌ Lỗi: {str(e)}")
                    update_log(log_placeholder, f"❌ Lỗi: {str(e)}")
                    st.exception(e)
                    st.info("Bạn có thể thử lại với số chương ít hơn hoặc điều chỉnh các thông số khác.")

    # Tab Tạo Truyện Theo Chương Có Sẵn
    with tab7:
        st.header("Tạo Truyện Theo Chương Có Sẵn")
        
        # Khởi tạo session state cho danh sách chương và bộ truyện
        if 'custom_chapters' not in st.session_state:
            st.session_state.custom_chapters = []
        if 'current_series' not in st.session_state:
            st.session_state.current_series = None
        if 'download_status' not in st.session_state:
            st.session_state.download_status = {}
        if 'video_id_in_db' not in st.session_state:
            st.session_state.video_id_in_db = None
        
        # Quản lý bộ truyện
        with st.expander("Quản lý bộ truyện", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Hiển thị danh sách bộ truyện
                series_list = db_manager.get_all_series()
                series_names = ["Không thuộc bộ nào"] + [series["name"] for series in series_list]
                selected_series = st.selectbox(
                    "Chọn bộ truyện", 
                    options=series_names, 
                    index=0
                )
                
                if selected_series != "Không thuộc bộ nào":
                    st.session_state.current_series = selected_series
                else:
                    st.session_state.current_series = None
                
            with col2:
                # Form thêm bộ truyện mới
                with st.form("add_series_form", clear_on_submit=True):
                    new_series_name = st.text_input("Tên bộ truyện mới")
                    series_desc = st.text_area("Mô tả", height=100)
                    
                    submitted = st.form_submit_button("Thêm bộ truyện")
                    if submitted and new_series_name:
                        db_manager.save_series(new_series_name, series_desc)
                        st.success(f"Đã thêm bộ truyện '{new_series_name}'")
                        st.rerun()
        
        # Tiêu đề truyện
        if 'story_title' not in st.session_state:
            st.session_state.story_title = "Truyện từ chương có sẵn"
            
        st.text_input("Tiêu đề truyện", value=st.session_state.story_title, 
                     key="story_title_input", 
                     on_change=lambda: setattr(st.session_state, 'story_title', st.session_state.story_title_input))
        
        # Hiển thị bảng quản lý chương
        if st.session_state.custom_chapters:
            st.subheader("Quản lý chương")
            
            # Chuẩn bị dữ liệu cho DataFrame
            chapter_data = []
            for chapter in st.session_state.custom_chapters:
                # Lấy 10 ký tự đầu tiên của nội dung
                preview = chapter["content"][:10] + "..." if len(chapter["content"]) > 10 else chapter["content"]
                
                # Trạng thái video
                has_video = "✅" if chapter.get("video_path") and os.path.exists(chapter.get("video_path")) else "❌"
                
                # Trạng thái tải xuống
                downloaded = "✅" if st.session_state.download_status.get(f"chapter_{chapter['chapter_num']}") else "❌"
                
                chapter_data.append({
                    "STT": chapter["chapter_num"],
                    "Tiêu đề": chapter.get("title", f"Chương {chapter['chapter_num']}"),
                    "Nội dung": preview,
                    "Có video": has_video,
                    "Đã tải xuống": downloaded
                })
            
            # Tạo và hiển thị DataFrame
            df = pd.DataFrame(chapter_data)
            st.dataframe(df, use_container_width=True)
            
            # Nút xóa tất cả chương
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("🗑️ Xóa tất cả chương"):
                    st.session_state.custom_chapters = []
                    st.success("Đã xóa tất cả chương!")
                    st.rerun()
            with col2:
                # Nút tạo video một nhấp
                if st.button("🚀 Tạo video (tất cả các bước)"):
                    if not st.session_state.custom_chapters:
                        st.error("Không có chương nào để tạo video!")
                    else:
                        create_all_in_one_for_custom_chapters()
        
        # Form thêm chương mới
        with st.form("add_chapter_form"):
            st.subheader("Thêm chương mới")
            
            chapter_num = st.number_input("Số thứ tự chương", min_value=1, value=len(st.session_state.custom_chapters) + 1)
            chapter_title = st.text_input("Tiêu đề chương", value=f"Chương {chapter_num}")
            chapter_content = st.text_area("Nội dung chương", height=200)
            
            # Nút thêm chương
            submitted = st.form_submit_button("Thêm chương")
            if submitted:
                if not chapter_content:
                    st.error("Nội dung chương không được để trống!")
                else:
                    # Kiểm tra xem số thứ tự đã tồn tại chưa
                    existing_nums = [ch["chapter_num"] for ch in st.session_state.custom_chapters]
                    if chapter_num in existing_nums:
                        st.warning(f"Chương {chapter_num} đã tồn tại! Vui lòng chọn số thứ tự khác.")
                    else:
                        new_chapter = {
                            "chapter_num": chapter_num,
                            "title": chapter_title,
                            "content": chapter_content
                        }
                        st.session_state.custom_chapters.append(new_chapter)
                        st.session_state.story_data = None  # Đánh dấu cần tái tạo dữ liệu truyện
                        st.success(f"Đã thêm chương {chapter_num}: {chapter_title}")
                        st.rerun()
        
        # Nút xóa chương được chọn
        with st.expander("Xóa chương"):
            if st.session_state.custom_chapters:
                chapter_to_delete = st.selectbox(
                    "Chọn chương cần xóa", 
                    options=[ch["chapter_num"] for ch in st.session_state.custom_chapters],
                    format_func=lambda x: f"Chương {x}"
                )
                
                if st.button("Xóa chương đã chọn"):
                    # Tìm và xóa chương khỏi danh sách
                    for i, chapter in enumerate(st.session_state.custom_chapters):
                        if chapter["chapter_num"] == chapter_to_delete:
                            del st.session_state.custom_chapters[i]
                            st.session_state.story_data = None  # Đánh dấu cần tái tạo dữ liệu truyện
                            st.success(f"Đã xóa chương {chapter_to_delete}")
                            st.rerun()
                            break
            else:
                st.info("Chưa có chương nào để xóa.")
        
        # Tạo story_data từ các chương đã nhập
        if st.session_state.custom_chapters:
            # Sắp xếp chương theo số thứ tự
            st.session_state.custom_chapters.sort(key=lambda x: x["chapter_num"])
            
            # Tạo cấu trúc story_data
            custom_story_data = {
                "concept": st.session_state.story_title,
                "num_chapters": len(st.session_state.custom_chapters),
                "chapters": st.session_state.custom_chapters
            }
            
            # Tạo video cho từng chương
            st.subheader("Tạo Hình ảnh, Audio và Video")
            
            # Cài đặt cho việc tạo media
            col1, col2 = st.columns(2)
            with col1:
                image_model = st.selectbox(
                    "Model tạo hình ảnh", 
                    options=["cogview4", "stable_diffusion", "cogview4"],
                    index=0,
                    format_func=lambda x: {
                        "cogview4": "CogView 4",
                        "gemini": "Gemini 2.0 Flash Image Gen",
                        "stable_diffusion": "Stable Diffusion"
                    }.get(x, x),
                    key="custom_image_model"
                )
            
            with col2:
                tts_provider = st.selectbox(
                    "Provider text-to-speech", 
                    options=["google", "openai"],
                    index=0,
                    format_func=lambda x: {
                        "google": "Google TTS (gTTS)",
                        "openai": "OpenAI TTS"
                    }.get(x, x),
                    key="custom_tts_provider"
                )
            
            # Tùy chọn video
            with st.expander("Tùy chọn video", expanded=False):
                vcol1, vcol2 = st.columns(2)
                with vcol1:
                    width = st.number_input("Chiều rộng video (pixels)", 
                                          min_value=320, max_value=1920, value=1280, step=16,
                                          key="custom_story_width")
                with vcol2:
                    height = st.number_input("Chiều cao video (pixels)", 
                                           min_value=240, max_value=1080, value=720, step=16,
                                           key="custom_story_height")
                
                fps = st.slider("Frames per second (FPS)", 
                              min_value=15, max_value=60, value=30, step=1,
                              key="custom_story_fps")
            
            # Buttons cho từng bước xử lý
            col1, col2, col3 = st.columns(3)
            
            # Tạo output directory nếu không có
            if 'custom_story_output_dir' not in st.session_state:
                output_dir = create_session_directory()
                st.session_state.custom_story_output_dir = output_dir
            else:
                output_dir = st.session_state.custom_story_output_dir
            
            # Nút tạo hình ảnh
            with col1:
                if st.button("1. Tạo hình ảnh", key="custom_story_create_images"):
                    with st.spinner(f"Đang tạo hình ảnh minh họa với model {image_model}..."):
                        try:
                            # Lưu story_data vào file để dùng sau này
                            story_data_path = os.path.join(output_dir, "story_data.json")
                            with open(story_data_path, "w", encoding="utf-8") as f:
                                json.dump(custom_story_data, f, ensure_ascii=False, indent=2)
                            
                            # Khởi tạo ImageGenerator
                            image_generator = ImageGenerator(model_type=image_model)
                            
                            # Xử lý tạo hình ảnh
                            story_images = image_generator.process_story(
                                custom_story_data, 
                                output_dir=output_dir
                            )
                            
                            # Lưu story_images vào session_state
                            st.session_state.custom_story_images = story_images
                            st.success("Đã tạo xong hình ảnh minh họa!")
                        except Exception as e:
                            st.error(f"Lỗi khi tạo hình ảnh: {str(e)}")
            
            # Nút tạo audio
            with col2:
                if st.button("2. Tạo audio", key="custom_story_create_audio"):
                    with st.spinner(f"Đang tạo audio với provider {tts_provider}..."):
                        try:
                            audio_generator = AudioGenerator(provider=tts_provider)
                            story_audio = audio_generator.process_story(
                                custom_story_data, 
                                output_dir=output_dir
                            )
                            
                            # Lưu story_audio vào session_state
                            st.session_state.custom_story_audio = story_audio
                            st.success("Đã tạo xong audio!")
                        except Exception as e:
                            st.error(f"Lỗi khi tạo audio: {str(e)}")
            
            # Nút tạo video
            with col3:
                if st.button("3. Tạo video", key="custom_story_create_video"):
                    if 'custom_story_images' not in st.session_state:
                        st.error("Vui lòng tạo hình ảnh trước!")
                    elif 'custom_story_audio' not in st.session_state:
                        st.error("Vui lòng tạo audio trước!")
                    else:
                        with st.spinner("Đang tạo video... Quá trình này có thể mất nhiều thời gian..."):
                            try:
                                video_generator = VideoGenerator(width=width, height=height, fps=fps)
                                video_data = video_generator.create_full_video(
                                    custom_story_data,
                                    st.session_state.custom_story_images,
                                    st.session_state.custom_story_audio,
                                    output_dir=output_dir
                                )
                                
                                # Lưu video_data vào session_state
                                st.session_state.custom_story_video = video_data
                                
                                # Lưu thông tin video vào MongoDB
                                story_title = st.session_state.get("story_title", "My Story")
                                series_name = st.session_state.get("current_series", None)
                                
                                video_id = db_manager.save_video_data(
                                    video_data,
                                    story_title,
                                    series_name
                                )
                                
                                # Cập nhật video_id vào session state
                                st.session_state.video_id_in_db = video_id
                                
                                if video_id:
                                    st.success(f"Đã tạo lại video thành công và lưu với ID: {video_id}")
                                else:
                                    st.warning("Đã tạo lại video nhưng không thể lưu vào cơ sở dữ liệu.")
                                
                                # Hiển thị video mới
                                display_videos(video_data, video_id)
                                
                                # Rerun để cập nhật UI
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi khi tạo lại video: {str(e)}")
            
            # Hiển thị kết quả nếu có
            if 'custom_story_video' in st.session_state:
                display_videos(st.session_state.custom_story_video, st.session_state.video_id_in_db)
        else:
            st.info("Vui lòng thêm ít nhất một chương để tạo truyện và video.")

    # Thông tin cuối trang
    st.markdown("---")
    st.markdown("### Thông tin")
    st.markdown("""
    **Auto Create YouTube Content** - Công cụ tạo nội dung tự động từ ý tưởng đến video.
    
    Sử dụng các API:
    - Tạo nội dung truyện: Gemini-2.0-flash
    - Tạo hình ảnh: Google Gemini, Stable Diffusion, CogView4
    - Tạo audio: Google TTS (gTTS), OpenAI TTS
    - Lưu trữ dữ liệu: MongoDB
    """)

def create_all_in_one_for_custom_chapters():
    """Tạo video từ các chương đã tải lên"""
    st.header("Tạo Truyện Theo Chương Có Sẵn", divider="rainbow")
    
    # Tạo container cho log
    log_placeholder = create_log_container()
    update_log(log_placeholder, "Bắt đầu quá trình tạo truyện và video...")
    
    # Form nhập thông tin
    with st.form("custom_chapters_form"):
        # Series info
        series_name = st.text_input("Tên bộ truyện (không bắt buộc)", help="Nhập tên bộ truyện nếu có")
        
        # Truyện info
        story_title = st.text_input("Tiêu đề truyện", help="Nhập tiêu đề cho truyện của bạn")
        
        st.write("### Nhập nội dung các chương")
        
        # Tạo tabs cho từng chương
        tabs = st.tabs([f"Chương {i+1}" for i in range(5)])
        
        chapters_data = []
        
        for i, tab in enumerate(tabs):
            with tab:
                chapter_title = st.text_input(f"Tiêu đề chương {i+1}", value=f"Chương {i+1}", key=f"ch_title_{i}")
                chapter_content = st.text_area(f"Nội dung chương {i+1}", height=200, key=f"ch_content_{i}")
                
                # Thêm dữ liệu chương vào danh sách
                chapters_data.append({
                    "index": i,
                    "title": chapter_title,
                    "content": chapter_content
                })
        
        # Cấu hình
        col1, col2 = st.columns(2)
        
        with col1:
            image_model = st.selectbox(
                "Model tạo hình ảnh", 
                options=["cogview4", "stable_diffusion", "gemini"],
                index=0,
                format_func=lambda x: {
                    "cogview4": "CogView 4",
                    "stable_diffusion": "Stable Diffusion",
                    "gemini": "Gemini 2.0 Flash Image Gen"
                }.get(x, x),
                key="custom_image_model"
            )
        
        with col2:
            tts_provider = st.selectbox(
                "Provider text-to-speech", 
                options=["google", "openai"],
                index=0,
                format_func=lambda x: {
                    "google": "Google TTS (gTTS)",
                    "openai": "OpenAI TTS"
                }.get(x, x),
                key="custom_tts_provider"
            )
        
        submit_button = st.form_submit_button("Tạo truyện và video")
    
    if submit_button:
        # Kiểm tra các chương có nội dung
        valid_chapters = [ch for ch in chapters_data if ch["content"].strip()]
        
        if not valid_chapters:
            st.error("Vui lòng nhập nội dung cho ít nhất một chương!")
            return
        
        if not story_title:
            st.error("Vui lòng nhập tiêu đề truyện!")
            return
        
        # Tạo thư mục đầu ra
        output_dir = create_session_directory()
        create_directories()
        
        # Lưu thông tin vào session_state
        if "custom_story_output_dir" not in st.session_state:
            st.session_state.custom_story_output_dir = output_dir
        
        # Chuẩn bị dữ liệu truyện
        story_data = {
            "concept": story_title,
            "num_chapters": len(valid_chapters),
            "chapters": []
        }
        
        for i, ch in enumerate(valid_chapters):
            chapter_data = {
                "chapter_num": i + 1,
                "title": ch["title"],
                "content": ch["content"]
            }
            story_data["chapters"].append(chapter_data)
        
        # Lưu dữ liệu truyện
        story_file = os.path.join(output_dir, "story_data.json")
        with open(story_file, "w", encoding="utf-8") as f:
            json.dump(story_data, f, ensure_ascii=False, indent=2)
        
        for i, chapter in enumerate(story_data["chapters"]):
            chapter_file = os.path.join(output_dir, f"chapter_{i+1}.txt")
            with open(chapter_file, "w", encoding="utf-8") as f:
                f.write(chapter["content"])
        
        update_log(log_placeholder, f"Đã lưu nội dung {len(valid_chapters)} chương.")
        
        # Xử lý tạo hình ảnh
        update_log(log_placeholder, "Đang tạo hình ảnh cho truyện...")
        image_generator = ImageGenerator(model_type=image_model)
        story_images = image_generator.process_story(story_data, output_dir=output_dir)
        
        # Lưu vào session_state
        st.session_state.custom_story_images = story_images
        
        # Xử lý tạo audio
        update_log(log_placeholder, "Đang tạo audio cho truyện...")
        try:
            audio_generator = AudioGenerator(provider=tts_provider)
            story_audio = audio_generator.process_story(story_data, output_dir=output_dir)
            
            # Xử lý tạo video
            update_log(log_placeholder, "Đang tạo video cho truyện...")
            video_generator = VideoGenerator()
            video_data = video_generator.create_full_video(
                story_data, 
                story_images, 
                story_audio, 
                output_dir=output_dir
            )
            
            # Lưu thông tin vào session_state
            st.session_state.custom_story_video = video_data
            
            # Lưu vào cơ sở dữ liệu
            from utils.db_utils import db_manager
            from utils.telegram_utils import telegram_manager
            
            # Khởi tạo video_id với giá trị mặc định
            video_id = None
            
            try:
                update_log(log_placeholder, "Đang lưu thông tin video vào cơ sở dữ liệu...")
                
                # Lưu vào MongoDB nếu đã kết nối
                if db_manager.is_connected():
                    video_id = db_manager.save_video_data(video_data, story_title, series_name)
                    update_log(log_placeholder, f"Đã lưu vào MongoDB với ID: {video_id}")
                
                # Nếu MongoDB không khả dụng và Telegram được cấu hình, thử gửi qua Telegram
                if (not video_id or not db_manager.is_connected()) and telegram_manager.is_configured():
                    update_log(log_placeholder, "Đang gửi video lên Telegram...")
                    
                    # Lấy đường dẫn video đầy đủ
                    full_video_path = video_data.get("full_video")
                    
                    if full_video_path and os.path.exists(full_video_path):
                        # Tạo caption
                        caption = f"<b>Tiêu đề:</b> {story_title}"
                        if series_name:
                            caption += f"\n<b>Bộ truyện:</b> {series_name}"
                        
                        # Gửi video lên Telegram
                        message_id = telegram_manager.send_video(full_video_path, caption)
                        
                        if message_id:
                            update_log(log_placeholder, f"Đã gửi video thành công lên Telegram với ID: {message_id}")
                            # Gán video_id nếu chưa có từ save_video_data
                            if not video_id:
                                video_id = f"tg_{message_id}"
                        else:
                            update_log(log_placeholder, "Không thể gửi video lên Telegram.")
                    else:
                        update_log(log_placeholder, f"Không tìm thấy file video đầy đủ tại: {full_video_path}")
                
                # Lưu ID vào session state
                if video_id:
                    st.session_state.video_id_in_db = video_id
                
            except Exception as e:
                update_log(log_placeholder, f"Lỗi khi lưu video: {str(e)}")
            
            # Hiển thị video mới
            display_videos(video_data, video_id if video_id else None)
            
            # Rerun để cập nhật UI
            st.rerun()
        except Exception as e:
            update_log(log_placeholder, f"Lỗi: {str(e)}")
            update_log(log_placeholder, f"Traceback: {traceback.format_exc()}")

def display_frames(video_data, story_images, output_dir):
    """Hiển thị các frame hình ảnh, prompt và nút tạo lại ảnh"""
    st.subheader("Các frame hình ảnh trong video")
    st.info("Xem và chỉnh sửa các frame hình ảnh được sử dụng trong video.")
    
    # Kiểm tra xem có story_images không
    if not story_images:
        st.warning("Không tìm thấy thông tin về hình ảnh đã tạo.")
        return
    
    # Tạo danh sách các tab cho từng chương
    chapter_titles = [f"Chương {ch['chapter_num']}" for ch in story_images]
    tabs = st.tabs(chapter_titles)
    
    # Hiển thị hình ảnh và prompt cho từng chương
    for i, chapter_images in enumerate(story_images):
        with tabs[i]:
            images = chapter_images.get("images", [])
            if not images:
                st.warning(f"Không có hình ảnh nào cho {chapter_titles[i]}")
                continue
            
            # Hiển thị lưới hình ảnh, 3 ảnh mỗi hàng
            for j in range(0, len(images), 3):
                cols = st.columns(3)
                for k in range(3):
                    idx = j + k
                    if idx < len(images):
                        img_data = images[idx]
                        image_path = img_data.get("image_path")
                        prompt = img_data.get("prompt", "Không có thông tin prompt")
                        
                        if image_path and os.path.exists(image_path):
                            with cols[k]:
                                st.image(image_path, caption=f"Frame {idx+1}")
                                
                                # Hiển thị prompt trong expander
                                with st.expander("Xem prompt"):
                                    st.text_area("Prompt", value=prompt, height=150, key=f"prompt_{chapter_images['chapter_num']}_{idx}")
                                
                                # Nút tạo lại ảnh
                                if st.button("Tạo lại ảnh này", key=f"recreate_{chapter_images['chapter_num']}_{idx}"):
                                    with st.spinner("Đang tạo lại hình ảnh..."):
                                        try:
                                            # Lấy model từ session state hoặc mặc định
                                            image_model = st.session_state.get("custom_image_model", "gemini")
                                            
                                            # Khởi tạo ImageGenerator
                                            image_generator = ImageGenerator(model_type=image_model)
                                            
                                            # Lấy prompt đã chỉnh sửa
                                            edited_prompt = st.session_state[f"prompt_{chapter_images['chapter_num']}_{idx}"]
                                            
                                            # Tạo lại hình ảnh
                                            new_image_path = image_generator.generate_image(edited_prompt, image_path)
                                            
                                            if new_image_path:
                                                st.success("Đã tạo lại hình ảnh thành công!")
                                                st.image(new_image_path, caption=f"Frame {idx+1} (Đã tạo lại)")
                                                
                                                # Cập nhật đường dẫn ảnh trong session state
                                                img_data["image_path"] = new_image_path
                                                img_data["prompt"] = edited_prompt
                                            else:
                                                st.error("Không thể tạo lại hình ảnh, vui lòng thử lại.")
                                        except Exception as e:
                                            st.error(f"Lỗi khi tạo lại hình ảnh: {str(e)}")
                        else:
                            with cols[k]:
                                st.warning(f"Không tìm thấy hình ảnh tại: {image_path}")
    
    # Thêm nút để tạo lại video sau khi đã chỉnh sửa hình ảnh
    if st.button("Tạo lại video với hình ảnh đã chỉnh sửa", key="recreate_video"):
        with st.spinner("Đang tạo lại video... Quá trình này có thể mất nhiều thời gian..."):
            try:
                # Khởi tạo VideoGenerator
                width = st.session_state.get("custom_story_width", 1280)
                height = st.session_state.get("custom_story_height", 720)
                fps = st.session_state.get("custom_story_fps", 30)
                video_generator = VideoGenerator(width=width, height=height, fps=fps)
                
                # Lấy dữ liệu story từ session state
                story_data = None
                story_audio = None
                
                if "custom_chapters" in st.session_state:
                    # Tạo cấu trúc story_data từ custom_chapters
                    story_data = {
                        "concept": st.session_state.get("story_title", "My Story"),
                        "num_chapters": len(st.session_state.custom_chapters),
                        "chapters": st.session_state.custom_chapters
                    }
                
                if "custom_story_audio" in st.session_state:
                    story_audio = st.session_state.custom_story_audio
                
                if story_data and story_audio and story_images:
                    # Tạo lại video
                    video_data = video_generator.create_full_video(
                        story_data, 
                        story_images, 
                        story_audio, 
                        output_dir=output_dir
                    )
                    
                    # Cập nhật session state với video mới
                    st.session_state.custom_story_video = video_data
                    
                    # Lưu thông tin video vào MongoDB
                    story_title = st.session_state.get("story_title", "My Story")
                    series_name = st.session_state.get("current_series", None)
                    
                    # Khởi tạo video_id
                    video_id = None
                    
                    try:
                        # Lưu vào MongoDB nếu đã kết nối
                        if db_manager.is_connected():
                            video_id = db_manager.save_video_data(video_data, story_title, series_name)
                            st.success(f"Đã lưu video vào MongoDB với ID: {video_id}")
                        
                        # Nếu MongoDB không khả dụng và Telegram được cấu hình, thử gửi qua Telegram
                        if (not video_id or not db_manager.is_connected()) and telegram_manager.is_configured():
                            st.info("Đang gửi video lên Telegram...")
                            
                            # Lấy đường dẫn video đầy đủ
                            full_video_path = video_data.get("full_video")
                            
                            if full_video_path and os.path.exists(full_video_path):
                                # Tạo caption
                                caption = f"<b>Tiêu đề:</b> {story_title}"
                                if series_name:
                                    caption += f"\n<b>Bộ truyện:</b> {series_name}"
                                
                                # Gửi video lên Telegram
                                message_id = telegram_manager.send_video(full_video_path, caption)
                                
                                if message_id:
                                    st.success(f"Đã gửi video thành công lên Telegram với ID: {message_id}")
                                    # Gán video_id nếu chưa có từ save_video_data
                                    if not video_id:
                                        video_id = f"tg_{message_id}"
                                else:
                                    st.warning("Không thể gửi video lên Telegram.")
                            else:
                                st.warning(f"Không tìm thấy file video đầy đủ tại: {full_video_path}")
                        
                        # Lưu ID vào session state
                        if video_id:
                            st.session_state.video_id_in_db = video_id
                        
                    except Exception as e:
                        st.error(f"Lỗi khi lưu video: {str(e)}")
                    
                    # Hiển thị video mới
                    display_videos(video_data, video_id if video_id else None)
                    
                    # Rerun để cập nhật UI
                    st.rerun()
                else:
                    st.error("Không có đủ dữ liệu để tạo lại video. Vui lòng tạo video trước.")
            except Exception as e:
                st.error(f"Lỗi khi tạo lại video: {str(e)}")

if __name__ == "__main__":
    main() 