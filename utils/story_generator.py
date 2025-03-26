import google.generativeai as genai
from tqdm import tqdm
import os
import json
from utils.config import GOOGLE_API_KEY

# Cấu hình API Gemini
genai.configure(api_key=GOOGLE_API_KEY)

class StoryGenerator:
    def __init__(self, model_name="gemini-2.0-flash"):
        self.model = genai.GenerativeModel(model_name)
    
    def generate_chapter(self, story_concept, chapter_num, total_chapters, max_tokens=800):
        """Tạo một chương truyện từ ý tưởng ban đầu"""
        prompt = f"""
        Dựa trên ý tưởng truyện sau: {story_concept}
        
        Hãy viết chương {chapter_num}/{total_chapters} của câu chuyện này.
        Chương này phải liên quan và phát triển từ ý tưởng chính.
        Mỗi chương nên có mở đầu, phần thân, và kết thúc rõ ràng.
        Nếu là chương đầu tiên, hãy giới thiệu nhân vật và bối cảnh.
        Nếu là chương cuối cùng, hãy kết thúc câu chuyện một cách hoàn chỉnh.
        
        Đảm bảo tạo ra nội dung hấp dẫn, giàu chi tiết và phù hợp để chuyển thành hình ảnh.
        """
        
        response = self.model.generate_content(prompt, generation_config={"max_output_tokens": max_tokens})
        return response.text
    
    def generate_full_story(self, story_concept, num_chapters=3, tokens_per_chapter=800, output_dir="output"):
        """Tạo toàn bộ câu chuyện với nhiều chương"""
        story_data = {
            "concept": story_concept,
            "num_chapters": num_chapters,
            "chapters": []
        }
        
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Đang tạo câu chuyện với {num_chapters} chương...")
        for i in tqdm(range(1, num_chapters + 1)):
            chapter_content = self.generate_chapter(
                story_concept, 
                i, 
                num_chapters,
                max_tokens=tokens_per_chapter
            )
            
            chapter_data = {
                "chapter_num": i,
                "title": f"Chương {i}",
                "content": chapter_content
            }
            
            story_data["chapters"].append(chapter_data)
            
            # Lưu chương vào file riêng
            chapter_filename = os.path.join(output_dir, f"chapter_{i}.txt")
            with open(chapter_filename, "w", encoding="utf-8") as f:
                f.write(chapter_content)
        
        # Lưu toàn bộ dữ liệu truyện vào file JSON
        story_filename = os.path.join(output_dir, "story_data.json")
        with open(story_filename, "w", encoding="utf-8") as f:
            json.dump(story_data, f, ensure_ascii=False, indent=2)
            
        print(f"Đã tạo xong câu chuyện với {num_chapters} chương.")
        print(f"Dữ liệu đã được lưu vào: {story_filename}")
        
        return story_data 