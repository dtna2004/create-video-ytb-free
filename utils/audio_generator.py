import os
import json
import requests
import tempfile
import base64
from io import BytesIO
from tqdm import tqdm
from gtts import gTTS
from utils.config import GOOGLE_API_KEY, OPENAI_API_KEY

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
            except Exception as e:
                print(f"Lỗi khi ghép audio: {e}")
                return {
                    "chapter_num": chapter_num,
                    "segments": audio_paths,
                    "full_audio": None
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