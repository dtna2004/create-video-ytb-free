import os
import json
import random
import tempfile
from tqdm import tqdm
from moviepy.editor import *
from pydub import AudioSegment
from PIL import Image

class VideoGenerator:
    def __init__(self, width=1280, height=720, fps=30):
        """
        Khởi tạo video generator
        width, height: kích thước video
        fps: frames per second
        """
        self.width = width
        self.height = height
        self.fps = fps
    
    def resize_image(self, image_path, output_path=None):
        """Resize hình ảnh để phù hợp với kích thước video"""
        try:
            img = Image.open(image_path)
            
            # Tính toán tỷ lệ khung hình
            img_ratio = img.width / img.height
            target_ratio = self.width / self.height
            
            if img_ratio > target_ratio:
                # Ảnh rộng hơn so với tỷ lệ target
                new_width = int(img.height * target_ratio)
                left = (img.width - new_width) // 2
                img = img.crop((left, 0, left + new_width, img.height))
            else:
                # Ảnh cao hơn so với tỷ lệ target
                new_height = int(img.width / target_ratio)
                top = (img.height - new_height) // 2
                img = img.crop((0, top, img.width, top + new_height))
            
            # Resize ảnh theo kích thước video
            img = img.resize((self.width, self.height), Image.LANCZOS)
            
            # Lưu ảnh đã resize
            if output_path:
                img.save(output_path)
                return output_path
            else:
                # Lưu vào file tạm
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    output_path = tmp.name
                    img.save(output_path)
                return output_path
                
        except Exception as e:
            print(f"Lỗi khi resize hình ảnh: {e}")
            return image_path
    
    def get_audio_duration(self, audio_path):
        """Lấy độ dài (giây) của file audio"""
        try:
            audio = AudioSegment.from_file(audio_path)
            return len(audio) / 1000.0  # Chuyển từ milliseconds sang giây
        except Exception as e:
            print(f"Lỗi khi lấy độ dài audio: {e}")
            return 0
    
    def create_segment_clip(self, segment_data, chapter_dir):
        """Tạo clip cho một đoạn văn bản với audio và hình ảnh"""
        audio_path = segment_data.get("audio_path")
        image_path = segment_data.get("image_path")
        
        if not audio_path or not os.path.exists(audio_path):
            print(f"Không tìm thấy file audio: {audio_path}")
            return None
            
        if not image_path or not os.path.exists(image_path):
            print(f"Không tìm thấy file hình ảnh: {image_path}")
            return None
        
        try:
            # Resize hình ảnh
            resized_image = self.resize_image(image_path)
            
            # Tạo image clip
            image_clip = ImageClip(resized_image, duration=None)
            
            # Tạo audio clip
            audio_clip = AudioFileClip(audio_path)
            
            # Cập nhật duration cho image clip
            image_clip = image_clip.set_duration(audio_clip.duration)
            
            # Thêm audio vào image clip
            video_clip = image_clip.set_audio(audio_clip)
            
            return video_clip
            
        except Exception as e:
            print(f"Lỗi khi tạo segment clip: {e}")
            return None
    
    def create_chapter_video(self, chapter_data, story_images, story_audio, output_dir):
        """Tạo video cho một chương"""
        chapter_num = chapter_data["chapter_num"]
        
        # Tìm dữ liệu audio cho chương này
        chapter_audio = None
        for audio_data in story_audio:
            if audio_data["chapter_num"] == chapter_num:
                chapter_audio = audio_data
                break
        
        if not chapter_audio:
            print(f"Không tìm thấy dữ liệu audio cho chương {chapter_num}")
            return None
        
        # Tìm dữ liệu hình ảnh cho chương này
        chapter_images = None
        for image_data in story_images:
            if image_data["chapter_num"] == chapter_num:
                chapter_images = image_data
                break
        
        if not chapter_images:
            print(f"Không tìm thấy dữ liệu hình ảnh cho chương {chapter_num}")
            return None
        
        # Nếu có file audio đầy đủ cho cả chương
        if chapter_audio.get("full_audio") and os.path.exists(chapter_audio["full_audio"]):
            output_path = os.path.join(output_dir, f"chapter_{chapter_num}.mp4")
            
            try:
                full_audio_clip = AudioFileClip(chapter_audio["full_audio"])
                audio_duration = full_audio_clip.duration
                
                # Tạo clip cho từng segment của chương
                segment_clips = []
                
                # Lấy danh sách hình ảnh
                available_images = []
                for img in chapter_images["images"]:
                    if img.get("image_path") and os.path.exists(img["image_path"]):
                        available_images.append(img["image_path"])
                
                if not available_images:
                    print(f"Không có hình ảnh khả dụng cho chương {chapter_num}")
                    return None
                
                # Phân bổ hình ảnh cho các segment
                segment_durations = []
                for segment in chapter_audio["segments"]:
                    if segment.get("audio_path") and os.path.exists(segment["audio_path"]):
                        duration = self.get_audio_duration(segment["audio_path"])
                        segment_durations.append((segment, duration))
                
                total_duration = sum(duration for _, duration in segment_durations)
                num_segments = len(segment_durations)
                num_images = len(available_images)
                
                # Tạo danh sách clips
                clips = []
                current_time = 0
                
                print(f"Phân bổ {num_images} ảnh cho {num_segments} đoạn audio")
                
                # Cách phân bổ hình ảnh mới, dựa trên tỷ lệ thời gian
                if num_segments <= num_images:
                    # Trường hợp nhiều ảnh hơn đoạn audio
                    # Phân bổ nhiều ảnh cho mỗi đoạn audio dựa trên thời lượng
                    for i, (segment, duration) in enumerate(segment_durations):
                        # Tính số ảnh sẽ sử dụng cho đoạn audio này dựa trên tỷ lệ thời lượng
                        segment_ratio = duration / total_duration
                        num_images_for_segment = max(1, round(segment_ratio * num_images))
                        
                        # Tính khoảng thời gian hiển thị cho mỗi ảnh
                        image_duration = duration / num_images_for_segment
                        
                        # Xác định các ảnh sẽ sử dụng cho đoạn này
                        start_idx = int((i / num_segments) * num_images)
                        
                        for j in range(num_images_for_segment):
                            img_idx = min(start_idx + j, num_images - 1)
                            image_path = available_images[img_idx]
                            
                            # Resize hình ảnh
                            resized_image = self.resize_image(image_path)
                            
                            # Tạo image clip
                            image_clip = ImageClip(resized_image)
                            image_clip = image_clip.set_duration(image_duration)
                            
                            # Set start time
                            seg_start_time = current_time + j * image_duration
                            image_clip = image_clip.set_start(seg_start_time)
                            
                            clips.append(image_clip)
                        
                        current_time += duration
                else:
                    # Trường hợp nhiều đoạn audio hơn ảnh
                    for i, (segment, duration) in enumerate(segment_durations):
                        # Chọn hình ảnh phù hợp dựa trên vị trí tương đối
                        img_index = min(int((i / num_segments) * num_images), num_images - 1)
                        image_path = available_images[img_index]
                        
                        # Resize hình ảnh
                        resized_image = self.resize_image(image_path)
                        
                        # Tạo image clip
                        image_clip = ImageClip(resized_image)
                        image_clip = image_clip.set_duration(duration)
                        
                        # Set start time
                        image_clip = image_clip.set_start(current_time)
                        
                        clips.append(image_clip)
                        current_time += duration
                
                # Ghép các clip lại với nhau
                final_clip = CompositeVideoClip(clips, size=(self.width, self.height))
                
                # Thêm audio vào video
                final_clip = final_clip.set_audio(full_audio_clip)
                
                # Xuất video
                final_clip.write_videofile(
                    output_path,
                    fps=self.fps,
                    codec="libx264",
                    audio_codec="aac",
                    temp_audiofile="temp-audio.m4a",
                    remove_temp=True
                )
                
                return output_path
                
            except Exception as e:
                print(f"Lỗi khi tạo video cho chương {chapter_num}: {e}")
                return None
        else:
            # Xử lý trường hợp không có full audio
            print(f"Không tìm thấy file audio đầy đủ cho chương {chapter_num}, sẽ ghép từ các segment")
            
            # TODO: Xử lý trường hợp này nếu cần
            return None
    
    def create_full_video(self, story_data, story_images, story_audio, output_dir="output"):
        """Tạo video đầy đủ cho toàn bộ câu chuyện"""
        videos_dir = os.path.join(output_dir, "videos")
        os.makedirs(videos_dir, exist_ok=True)
        
        # Tạo video cho từng chương
        chapter_videos = []
        
        print(f"Đang tạo video cho {len(story_data['chapters'])} chương...")
        for chapter in tqdm(story_data["chapters"]):
            video_path = self.create_chapter_video(chapter, story_images, story_audio, videos_dir)
            if video_path:
                chapter_videos.append({
                    "chapter_num": chapter["chapter_num"],
                    "title": chapter.get("title", f"Chương {chapter['chapter_num']}"),
                    "video_path": video_path
                })
        
        # Ghép tất cả các video chương thành một video hoàn chỉnh
        if chapter_videos:
            try:
                full_video_path = os.path.join(output_dir, "full_story.mp4")
                
                # Tạo clip cho từng chương
                clips = []
                for chapter_video in chapter_videos:
                    video_path = chapter_video["video_path"]
                    if os.path.exists(video_path):
                        clip = VideoFileClip(video_path)
                        clips.append(clip)
                
                # Nối các clip lại với nhau
                final_clip = concatenate_videoclips(clips)
                
                # Xuất video
                final_clip.write_videofile(
                    full_video_path,
                    fps=self.fps,
                    codec="libx264",
                    audio_codec="aac",
                    temp_audiofile="temp-audio.m4a",
                    remove_temp=True
                )
                
                print(f"Đã tạo video đầy đủ: {full_video_path}")
                
                # Lưu thông tin video vào file
                video_data = {
                    "full_video": full_video_path,
                    "chapter_videos": chapter_videos
                }
                
                video_data_path = os.path.join(output_dir, "video_data.json")
                with open(video_data_path, "w", encoding="utf-8") as f:
                    json.dump(video_data, f, ensure_ascii=False, indent=2)
                
                return video_data
                
            except Exception as e:
                print(f"Lỗi khi tạo video đầy đủ: {e}")
                return {
                    "full_video": None,
                    "chapter_videos": chapter_videos
                }
        
        return {
            "full_video": None,
            "chapter_videos": chapter_videos
        } 