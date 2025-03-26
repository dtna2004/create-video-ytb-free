import os
import json
import requests
import tempfile
import base64
from io import BytesIO
from tqdm import tqdm
from gtts import gTTS
from utils.config import GOOGLE_API_KEY, OPENAI_API_KEY
import ffmpeg
import subprocess

class AudioGenerator:
    def __init__(self, provider="google"):
        """
        Khởi tạo generator với provider được chọn
        provider: 'google' hoặc 'openai'
        """
        self.provider = provider
    
    def generate_audio_google(self, text, output_path, language_code="vi", slow=False):
        """Tạo audio từ text sử dụng Google Text-to-Speech (gTTS)"""
        try:
            # Sử dụng gTTS thay vì Google Cloud TTS
            tts = gTTS(text=text, lang=language_code, slow=slow)
            tts.save(output_path)
            return output_path
            
        except Exception as e:
            print(f"Lỗi khi tạo audio với Google TTS: {e}")
            return None
    
    def generate_audio_openai(self, text, output_path, voice="alloy"):
        """Tạo audio từ text sử dụng OpenAI TTS API"""
        try:
            if not OPENAI_API_KEY:
                raise ValueError("Thiếu API key cho OpenAI")
                
            import openai
            openai.api_key = OPENAI_API_KEY
            
            response = openai.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            
            # Lưu file audio
            response.stream_to_file(output_path)
            
            return output_path
            
        except Exception as e:
            print(f"Lỗi khi tạo audio với OpenAI TTS: {e}")
            return None
    
    def split_text_for_tts(self, text, max_length=500):
        """Chia văn bản thành các đoạn phù hợp cho TTS"""
        if len(text) <= max_length:
            return [text]
        
        # Tìm vị trí kết thúc câu gần với max_length nhất
        segments = []
        start = 0
        
        while start < len(text):
            if start + max_length >= len(text):
                segments.append(text[start:])
                break
                
            end = start + max_length
            
            # Tìm vị trí kết thúc câu gần nhất
            for punct in ['.', '?', '!']:
                punct_pos = text.rfind(punct, start, end)
                if punct_pos != -1:
                    end = punct_pos + 1
                    break
                    
            # Nếu không tìm thấy dấu câu, cắt tại khoảng trắng gần nhất
            if end == start + max_length:
                space_pos = text.rfind(' ', start, end)
                if space_pos != -1:
                    end = space_pos + 1
            
            segments.append(text[start:end])
            start = end
        
        return segments
    
    def generate_audio(self, text, output_path):
        """Tạo audio từ text sử dụng provider đã chọn"""
        if self.provider == "google":
            return self.generate_audio_google(text, output_path)
        elif self.provider == "openai":
            return self.generate_audio_openai(text, output_path)
        else:
            raise ValueError(f"Provider không được hỗ trợ: {self.provider}")
    
    def process_chapter(self, chapter_text, chapter_num, output_dir="output/audio"):
        """Xử lý một chương và tạo audio"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Chia chương thành nhiều đoạn
        segments = self.split_text_for_tts(chapter_text)
        
        audio_paths = []
        print(f"Đang tạo {len(segments)} audio cho chương {chapter_num}...")
        
        for i, segment in enumerate(tqdm(segments)):
            output_path = os.path.join(output_dir, f"chapter_{chapter_num}_segment_{i+1}.mp3")
            
            result_path = self.generate_audio(segment, output_path)
            if result_path:
                audio_data = {
                    "segment_index": i,
                    "segment_text": segment,
                    "audio_path": result_path
                }
                audio_paths.append(audio_data)
        
        # Ghép các đoạn audio thành một file cho toàn bộ chương
        if audio_paths:
            try:
                from pydub import AudioSegment
                
                # Kiểm tra xem ffprobe đã được cài đặt chưa
                try:
                    combined = AudioSegment.empty()
                    for audio_data in audio_paths:
                        segment = AudioSegment.from_mp3(audio_data["audio_path"])
                        combined += segment
                    
                    chapter_audio_path = os.path.join(output_dir, f"chapter_{chapter_num}_full.mp3")
                    combined.export(chapter_audio_path, format="mp3")
                    
                    return {
                        "chapter_num": chapter_num,
                        "segments": audio_paths,
                        "full_audio": chapter_audio_path
                    }
                except FileNotFoundError as e:
                    if "ffprobe" in str(e):
                        print("Lỗi: ffprobe không được tìm thấy. Bạn cần cài đặt ffmpeg/ffprobe để ghép audio.")
                        print("Bạn có thể tải ffmpeg từ https://ffmpeg.org/download.html")
                        print("Hoặc sử dụng cài đặt nhanh:")
                        print("- Windows: choco install ffmpeg")
                        print("- Mac: brew install ffmpeg")
                        print("- Linux: apt install ffmpeg")
                        
                        # Trả về kết quả không có full audio
                        return {
                            "chapter_num": chapter_num,
                            "segments": audio_paths,
                            "full_audio": None,
                            "error": "ffprobe_not_found"
                        }
                    else:
                        raise e
            except Exception as e:
                print(f"Lỗi khi ghép audio: {e}")
                return {
                    "chapter_num": chapter_num,
                    "segments": audio_paths,
                    "full_audio": None,
                    "error": str(e)
                }
        
        return {
            "chapter_num": chapter_num,
            "segments": audio_paths,
            "full_audio": None
        }
    
    def process_story(self, story_data, output_dir="output"):
        """Xử lý toàn bộ câu chuyện và tạo audio cho mỗi chương"""
        audio_dir = os.path.join(output_dir, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        
        story_audio = []
        
        for chapter in story_data["chapters"]:
            chapter_num = chapter["chapter_num"]
            chapter_content = chapter["content"]
            
            chapter_audio = self.process_chapter(chapter_content, chapter_num, audio_dir)
            story_audio.append(chapter_audio)
        
        # Lưu thông tin audio vào file
        audio_data_path = os.path.join(output_dir, "audio_data.json")
        with open(audio_data_path, "w", encoding="utf-8") as f:
            json.dump(story_audio, f, ensure_ascii=False, indent=2)
        
        print(f"Đã tạo xong audio cho {len(story_data['chapters'])} chương.")
        print(f"Dữ liệu audio đã được lưu vào: {audio_data_path}")
        
        return story_audio
    
    def get_audio_duration(self, audio_path):
        """Lấy độ dài của file audio"""
        try:
            probe = ffmpeg.probe(audio_path)
            duration = float(probe['format']['duration'])
            return duration
        except Exception as e:
            print(f"Lỗi khi lấy thời lượng audio: {e}")
            # Trả về thời lượng mặc định nếu không thể xác định
            return 5.0  # Ước tính thời lượng trung bình cho mỗi đoạn
            
    def merge_audios(self, audio_files, output_path):
        """Ghép các file audio"""
        if not audio_files:
            return None
            
        try:
            # Kiểm tra ffprobe có tồn tại không
            try:
                subprocess.run(['ffprobe', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                print("CẢNH BÁO: Không tìm thấy ffprobe, cần cài đặt ffmpeg để ghép audio")
                print("Bạn có thể tải ffmpeg từ: https://ffmpeg.org/download.html")
                print("Hoặc sử dụng lệnh: ")
                print("  - Windows (với Chocolatey): choco install ffmpeg")
                print("  - macOS (với Homebrew): brew install ffmpeg")
                print("  - Ubuntu/Debian: sudo apt-get install ffmpeg")
                
                # Đánh dấu lỗi để sử dụng các audio segments riêng lẻ sau này
                return None
            
            # Tiếp tục nếu ffprobe tồn tại
            temp_list_file = "temp_audio_list.txt"
            
            with open(temp_list_file, "w", encoding="utf-8") as f:
                for audio_file in audio_files:
                    f.write(f"file '{audio_file}'\n")
            
            subprocess.run([
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                '-i', temp_list_file, '-c', 'copy', output_path
            ], check=True)
            
            # Xóa file tạm
            if os.path.exists(temp_list_file):
                os.remove(temp_list_file)
                
            return output_path
        except Exception as e:
            print(f"Lỗi khi ghép audio: {e}")
            # Đánh dấu lỗi để sử dụng các audio segments riêng lẻ sau này
            return None
            
    def generate_audio_for_chapter(self, chapter_data, output_dir):
        """Tạo audio cho một chương"""
        chapter_num = chapter_data["chapter_num"]
        chapter_title = chapter_data["title"]
        chapter_content = chapter_data["content"]
        
        # Tạo thư mục cho chapter nếu chưa tồn tại
        chapter_output_dir = os.path.join(output_dir, f"chapter_{chapter_num}")
        os.makedirs(chapter_output_dir, exist_ok=True)
        
        # Chuẩn bị dữ liệu audio
        audio_data = {
            "chapter_num": chapter_num,
            "title": chapter_title,
            "segments": [],
            "full_audio": ""
        }
        
        # Tạo audio cho title
        title_audio_path = os.path.join(chapter_output_dir, "title.mp3")
        self.generate_tts(chapter_title, title_audio_path)
        
        if os.path.exists(title_audio_path):
            audio_data["segments"].append({
                "text": chapter_title,
                "audio_path": title_audio_path,
                "is_title": True
            })
        
        # Chia nội dung thành các đoạn nhỏ hơn
        segments = self.split_content_for_tts(chapter_content)
        
        # Tạo audio cho từng đoạn văn
        segment_audio_files = [title_audio_path]
        
        for i, segment in enumerate(segments):
            segment_audio_path = os.path.join(chapter_output_dir, f"segment_{i+1}.mp3")
            self.generate_tts(segment, segment_audio_path)
            
            if os.path.exists(segment_audio_path):
                audio_data["segments"].append({
                    "text": segment,
                    "audio_path": segment_audio_path,
                    "is_title": False
                })
                segment_audio_files.append(segment_audio_path)
        
        # Ghép các file audio lại thành 1
        full_audio_path = os.path.join(chapter_output_dir, "full_audio.mp3")
        result = self.merge_audios(segment_audio_files, full_audio_path)
        
        if result:
            audio_data["full_audio"] = full_audio_path
        else:
            audio_data["error"] = True
            print(f"Không thể ghép audio cho chương {chapter_num}, sẽ sử dụng audio segments riêng lẻ.")
        
        return audio_data 