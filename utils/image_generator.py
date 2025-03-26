import os
import json
import base64
import requests
import google.generativeai as genai
from io import BytesIO
from PIL import Image
from tqdm import tqdm
import re
from utils.config import GOOGLE_API_KEY, OPENAI_API_KEY, STABILITY_API_KEY, ZHIPUAI_API_KEY

class ImageGenerator:
    def __init__(self, model_type="gemini"):
        """
        Khởi tạo generator với model được chọn
        model_type: 'gemini', 'stable_diffusion', hoặc 'cogview4'
        """
        self.model_type = model_type
        self.characters_info = {}  # Lưu trữ thông tin nhân vật để đảm bảo tính nhất quán
        
        if model_type == "gemini":
            genai.configure(api_key=GOOGLE_API_KEY)
            self.model = genai.GenerativeModel("gemini-2.0-flash-exp-image-generation")
        elif model_type == "stable_diffusion":
            if not STABILITY_API_KEY:
                raise ValueError("Thiếu API key cho Stability AI")
            # Sử dụng API Stability AI
            self.api_host = 'https://api.stability.ai'
            self.api_key = STABILITY_API_KEY
        elif model_type == "cogview4":
            if not ZHIPUAI_API_KEY:
                raise ValueError("Thiếu API key cho ZhipuAI (CogView4)")
            # Sử dụng API ZhipuAI cho CogView4
            import zhipuai
            zhipuai.api_key = ZHIPUAI_API_KEY
            self.zhipuai = zhipuai
        else:
            raise ValueError(f"Model không được hỗ trợ: {model_type}")
        
        # Khởi tạo prompt model
        self.prompt_model = genai.GenerativeModel("gemini-2.0-flash")
    
    def _extract_character_info(self, story_data):
        """Phân tích nội dung truyện để trích xuất thông tin nhân vật và ngữ cảnh"""
        try:
            # Lấy nội dung từ chapter đầu tiên để phân tích nhân vật và ngữ cảnh
            first_chapter = story_data["chapters"][0]["content"]
            
            # Sử dụng Gemini để phân tích nhân vật và ngữ cảnh
            prompt = f"""
            Phân tích đoạn văn bản sau một cách toàn diện để trích xuất:

            1. THÔNG TIN VỀ CÁC NHÂN VẬT CHÍNH (tối đa 5 nhân vật):
               - Tên
               - Giới tính
               - Tuổi (ước lượng nếu không có thông tin cụ thể)
               - Đặc điểm ngoại hình chi tiết: Màu tóc, kiểu tóc, màu mắt, màu da, chiều cao, dáng người, trang phục đặc trưng
               - Tính cách: 3-5 đặc điểm tính cách rõ nét
               - Vai trò trong câu chuyện
               - Quan hệ với các nhân vật khác

            2. BỐI CẢNH VÀ KHÔNG GIAN:
               - Thời đại (cổ đại, trung đại, hiện đại, tương lai, giả tưởng...)
               - Bối cảnh địa lý và văn hóa (châu Á, châu Âu, châu Phi, giả tưởng...)
               - Đặc điểm văn hóa nổi bật (trang phục, kiến trúc, phong tục...)
               - Môi trường chính (đô thị, nông thôn, núi rừng, biển...)
               - Không khí tổng thể (u ám, vui tươi, bí ẩn, huyền bí...)

            3. CHỦ ĐỀ VÀ PHONG CÁCH:
               - Thể loại chính (giả tưởng, lịch sử, lãng mạn, kinh dị, hiện thực...)
               - Tông màu chủ đạo phù hợp với câu chuyện
               - Phong cách nghệ thuật phù hợp nhất để minh họa

            Văn bản: {first_chapter[:4000]}...

            Kết quả trả về phải theo định dạng JSON với cấu trúc sau:
            {{
                "characters": [
                    {{
                        "name": "Tên nhân vật",
                        "gender": "Nam/Nữ",
                        "age": "Tuổi (có thể ước lượng)",
                        "appearance": "Mô tả ngoại hình chi tiết",
                        "personality": "Mô tả tính cách",
                        "role": "Vai trò trong câu chuyện"
                    }},
                    ...
                ],
                "setting": {{
                    "era": "Thời đại",
                    "location": "Bối cảnh địa lý",
                    "culture": "Đặc điểm văn hóa",
                    "environment": "Môi trường chính",
                    "atmosphere": "Không khí tổng thể"
                }},
                "style": {{
                    "genre": "Thể loại chính",
                    "color_tone": "Tông màu chủ đạo",
                    "art_style": "Phong cách nghệ thuật phù hợp"
                }}
            }}
            
            Chỉ trả về JSON, không thêm giải thích.
            """
            
            try:
                response = self.prompt_model.generate_content(prompt)
                response_text = response.text
                
                # Trích xuất phần JSON
                json_match = re.search(r'```json\s*({.*?})\s*```', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
                
                # Làm sạch văn bản JSON
                response_text = response_text.strip()
                if response_text.startswith("```") and response_text.endswith("```"):
                    response_text = response_text[3:-3].strip()
                
                story_info = json.loads(response_text)
                print("Đã phân tích thông tin nhân vật và bối cảnh truyện thành công")
                return story_info
            except Exception as e:
                print(f"Lỗi khi trích xuất thông tin nhân vật và bối cảnh: {e}")
                # Nếu không phân tích được, trả về dữ liệu mặc định
                return {"characters": [], "setting": {}, "style": {}}
        except Exception as e:
            print(f"Lỗi khi phân tích nội dung truyện: {e}")
            return {"characters": [], "setting": {}, "style": {}}
    
    def analyze_chapter_for_image_count(self, chapter_text, chapter_num):
        """Phân tích chương truyện để xác định số lượng hình ảnh phù hợp"""
        try:
            prompt = f"""
            Phân tích đoạn văn bản sau đây và xác định số lượng hình ảnh phù hợp để minh họa.
            Hãy xem xét các yếu tố sau:
            1. Số lượng cảnh khác nhau trong đoạn văn
            2. Số lượng sự kiện quan trọng
            3. Sự thay đổi không gian, thời gian
            4. Sự xuất hiện của nhân vật mới
            
            Văn bản: {chapter_text[:3000]}...
            
            Hãy trả về kết quả phân tích dưới dạng JSON với cấu trúc sau:
            {{
                "image_count": số_lượng_hình_ảnh_đề_xuất,
                "scenes": [
                    {{
                        "description": "Mô tả ngắn gọn về cảnh",
                        "importance": "Mức độ quan trọng (1-5, với 5 là quan trọng nhất)"
                    }},
                    ...
                ]
            }}
            
            Lưu ý: Số lượng hình ảnh nên từ 15-100 tùy theo độ phức tạp của chương, và scenes nên sắp xếp theo thứ tự ưu tiên.
            Số lượng ảnh nên tỉ lệ với lượng token của chương(khoảng 50-100 token/1 ảnh).
            """
            
            try:
                response = self.prompt_model.generate_content(prompt)
                response_text = response.text
                
                # Trích xuất phần JSON
                json_match = re.search(r'```json\s*({.*?})\s*```', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
                
                # Làm sạch văn bản JSON
                response_text = response_text.strip()
                if response_text.startswith("```") and response_text.endswith("```"):
                    response_text = response_text[3:-3].strip()
                
                analysis_data = json.loads(response_text)
                
                # Đảm bảo số lượng hình ảnh hợp lý
                image_count = min(max(analysis_data.get("image_count", 15), 10), 100)
                
                print(f"Đề xuất {image_count} hình ảnh cho chương {chapter_num}")
                return {
                    "image_count": image_count,
                    "scenes": analysis_data.get("scenes", [])
                }
            except Exception as e:
                print(f"Lỗi khi phân tích số lượng hình ảnh: {e}")
                return {"image_count": 5, "scenes": []}
        except Exception as e:
            print(f"Lỗi khi phân tích chương: {e}")
            return {"image_count": 5, "scenes": []}
    
    def split_text_to_segments(self, text, segment_length=300, overlap=50):
        """Chia văn bản thành các đoạn nhỏ để tạo nhiều hình ảnh"""
        # Kiểm tra đầu vào để tránh MemoryError
        if not isinstance(text, str):
            print(f"Lỗi: Văn bản không phải kiểu string, mà là {type(text)}")
            return []
            
        if len(text) <= segment_length:
            return [text]
        
        # Nếu văn bản quá dài, cắt bớt để tránh MemoryError
        max_text_length = 10000  # Giới hạn độ dài tối đa
        if len(text) > max_text_length:
            text = text[:max_text_length]
            print(f"Cảnh báo: Văn bản quá dài, đã cắt bớt xuống {max_text_length} ký tự")
        
        segments = []
        start = 0
        
        try:
            while start < len(text):
                end = min(start + segment_length, len(text))
                
                # Tìm vị trí kết thúc câu gần nhất (dấu chấm, dấu chấm hỏi, dấu chấm than)
                if end < len(text):
                    for punct in ['. ', '? ', '! ']:
                        punct_pos = text.rfind(punct, start, end)
                        if punct_pos != -1:
                            end = punct_pos + 2  # +2 để bao gồm dấu câu và khoảng trắng
                            break
                
                if start >= end:  # Tránh vòng lặp vô hạn
                    end = min(start + segment_length, len(text))
                
                segment = text[start:end].strip()
                segments.append(segment)
                
                # Di chuyển điểm bắt đầu, đảm bảo tiến ít nhất 1 ký tự
                start = min(end, start + segment_length - overlap)
                if start == end and end < len(text):
                    start += 1
            
            return segments
        except Exception as e:
            print(f"Lỗi khi chia văn bản: {e}")
            # Trả về một đoạn ngắn nếu có lỗi
            return [text[:min(300, len(text))]]
    
    def generate_structured_prompt(self, segment, chapter_num=1):
        """Tạo prompt có cấu trúc với style, composition, background và nhân vật nhất quán"""
        try:
            # Trích xuất thông tin cảnh từ đoạn văn bản
            prompt_request = f"""
            Đọc đoạn văn bản sau và tạo một prompt có cấu trúc để tạo hình ảnh minh họa.
            Prompt phải được chia thành các phần sau:
            
            1. Subject: Mô tả chủ thể chính của hình ảnh (nhân vật, cảnh vật chính)
            2. Action: Mô tả hành động hoặc tình huống đang diễn ra
            3. Background: Mô tả bối cảnh, phong cảnh, môi trường xung quanh
            4. Lighting: Mô tả ánh sáng, thời gian trong ngày
            5. Style: Chọn một phong cách nghệ thuật phù hợp (ví dụ: tranh vẽ truyện tranh, phong cách anime, tranh sơn dầu, ảnh chân dung, v.v.)
            6. Atmosphere: Không khí, tâm trạng, cảm xúc của cảnh
            
            Văn bản: {segment}
            
            Trả về prompt đơn giản, chỉ chứa thông tin tối thiểu cần thiết, không quá 200 từ.
            """
            
            response = self.prompt_model.generate_content(prompt_request)
            base_prompt = response.text.strip()
            
            # Thêm thông tin nhân vật nhất quán
            character_info = ""
            if self.characters_info and "characters" in self.characters_info:
                for character in self.characters_info["characters"]:
                    if character["name"].lower() in segment.lower():
                        character_info += f"Character {character['name']}: {character['gender']}, {character['appearance']}. "
            
            # Thêm thông tin về bối cảnh và phong cách
            setting_info = ""
            style_info = ""
            
            if "setting" in self.characters_info:
                setting = self.characters_info["setting"]
                setting_details = []
                
                if setting.get("era"):
                    setting_details.append(f"Time period: {setting['era']}")
                if setting.get("location"):
                    setting_details.append(f"Location: {setting['location']}")
                if setting.get("culture"):
                    setting_details.append(f"Cultural elements: {setting['culture']}")
                if setting.get("environment"):
                    setting_details.append(f"Environment: {setting['environment']}")
                if setting.get("atmosphere"):
                    setting_details.append(f"Atmosphere: {setting['atmosphere']}")
                
                if setting_details:
                    setting_info = "Setting: " + ". ".join(setting_details) + ". "
            
            if "style" in self.characters_info:
                style = self.characters_info["style"]
                style_details = []
                
                if style.get("genre"):
                    style_details.append(f"Genre: {style['genre']}")
                if style.get("color_tone"):
                    style_details.append(f"Color tone: {style['color_tone']}")
                if style.get("art_style"):
                    style_details.append(f"Art style: {style['art_style']}")
                
                if style_details:
                    style_info = "Style: " + ". ".join(style_details) + ". "
            
            # Kết hợp thông tin
            final_prompt = f"{base_prompt}\n\n{character_info}\n\n{setting_info}\n\n{style_info}"
            
            # Tối ưu hóa prompt cho từng model
            if self.model_type == "cogview4":
                final_prompt = f"High quality, detailed illustration. {final_prompt}"
            elif self.model_type == "stable_diffusion":
                final_prompt = f"Detailed and realistic illustration. {final_prompt}"
            elif self.model_type == "gemini":
                final_prompt = f"Create a detailed illustration for this scene: {final_prompt}"
            
            return final_prompt
            
        except Exception as e:
            print(f"Lỗi khi tạo prompt có cấu trúc: {e}")
            return f"Illustration of: {segment[:200]}"
    
    def generate_image_gemini(self, prompt, output_path):
        """Tạo hình ảnh sử dụng Gemini image generation"""
        try:
            response = self.model.generate_content(prompt)
            
            if not response.parts:
                print(f"Không thể tạo hình ảnh từ prompt: {prompt}")
                return None
                
            for part in response.parts:
                if part.inline_data and part.inline_data.mime_type.startswith('image/'):
                    # Lưu hình ảnh
                    image_data = base64.b64decode(part.inline_data.data)
                    image = Image.open(BytesIO(image_data))
                    image.save(output_path)
                    return output_path
            
            print("Không nhận được hình ảnh trong phản hồi")
            return None
        except Exception as e:
            print(f"Lỗi khi tạo hình ảnh với Gemini: {e}")
            return None
    
    def generate_image_stable_diffusion(self, prompt, output_path):
        """Tạo hình ảnh sử dụng Stable Diffusion API"""
        try:
            url = f"{self.api_host}/v1/generation/stable-diffusion-v1-5/text-to-image"
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "text_prompts": [{"text": prompt}],
                "cfg_scale": 7,
                "height": 512,
                "width": 512,
                "samples": 1,
                "steps": 30,
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                print(f"Lỗi khi tạo hình ảnh với Stable Diffusion: {response.text}")
                return None
                
            data = response.json()
            
            if "artifacts" in data and len(data["artifacts"]) > 0:
                image_data = base64.b64decode(data["artifacts"][0]["base64"])
                image = Image.open(BytesIO(image_data))
                image.save(output_path)
                return output_path
            
            return None
            
        except Exception as e:
            print(f"Lỗi khi tạo hình ảnh với Stable Diffusion: {e}")
            return None
    
    def generate_image_cogview4(self, prompt, output_path):
        """Tạo hình ảnh sử dụng CogView4 API"""
        try:
            # Sửa lại cách gọi API ZhipuAI cho phù hợp với phiên bản mới
            import zhipuai
            
            # Sử dụng ZhipuAI API theo cách mới
            client = zhipuai.ZhipuAI(api_key=ZHIPUAI_API_KEY)
            response = client.images.generations(
                model="cogview-4",
                prompt=prompt
            )
            
            if hasattr(response, 'data') and len(response.data) > 0:
                image_url = response.data[0].url
                
                # Tải hình ảnh từ URL
                img_response = requests.get(image_url)
                if img_response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(img_response.content)
                    return output_path
            
            print("Không nhận được hình ảnh trong phản hồi CogView4")
            return None
            
        except Exception as e:
            print(f"Lỗi khi tạo hình ảnh với CogView4: {e}")
            # Fallback sang Gemini nếu CogView4 có lỗi
            print("Chuyển sang sử dụng Gemini để tạo hình ảnh...")
            return self.generate_image_gemini(prompt, output_path)
    
    def generate_image(self, prompt, output_path):
        """Tạo hình ảnh từ prompt sử dụng model đã chọn"""
        if self.model_type == "gemini":
            return self.generate_image_gemini(prompt, output_path)
        elif self.model_type == "stable_diffusion":
            return self.generate_image_stable_diffusion(prompt, output_path)
        elif self.model_type == "cogview4":
            return self.generate_image_cogview4(prompt, output_path)
    
    def process_chapter(self, chapter_text, chapter_num, output_dir="output/images"):
        """Xử lý một chương và tạo nhiều hình ảnh"""
        os.makedirs(output_dir, exist_ok=True)
        
        if not isinstance(chapter_text, str):
            print(f"Lỗi: Nội dung chapter không phải là string, mà là {type(chapter_text)}")
            chapter_text = str(chapter_text)
        
        # Phân tích chương để xác định số lượng hình ảnh phù hợp
        analysis = self.analyze_chapter_for_image_count(chapter_text, chapter_num)
        image_count = analysis["image_count"]
        scenes = analysis["scenes"]
        
        # Chia chương thành nhiều đoạn
        segments = self.split_text_to_segments(chapter_text)
        
        # Nếu có cảnh được phân tích, sử dụng chúng
        if scenes:
            print(f"Sử dụng {len(scenes)} cảnh đã phân tích cho chương {chapter_num}")
            # Lọc và sắp xếp cảnh theo mức độ quan trọng
            sorted_scenes = sorted(scenes, key=lambda x: int(x.get("importance", 1)), reverse=True)
            # Giới hạn số lượng cảnh theo image_count
            selected_scenes = sorted_scenes[:image_count]
            
            # Tạo mô tả cho từng cảnh
            image_paths = []
            print(f"Đang tạo {len(selected_scenes)} hình ảnh cho chương {chapter_num}...")
            
            for i, scene in enumerate(tqdm(selected_scenes)):
                scene_description = scene.get("description", "")
                # Tìm đoạn văn bản tương ứng với mô tả cảnh
                best_segment = ""
                for segment in segments:
                    if scene_description.lower() in segment.lower():
                        best_segment = segment
                        break
                
                # Nếu không tìm thấy đoạn phù hợp, sử dụng mô tả cảnh
                if not best_segment:
                    best_segment = scene_description
                
                prompt = self.generate_structured_prompt(best_segment, chapter_num)
                output_path = os.path.join(output_dir, f"chapter_{chapter_num}_image_{i+1}.png")
                
                result_path = self.generate_image(prompt, output_path)
                if result_path:
                    image_data = {
                        "segment_index": i,
                        "segment_text": best_segment,
                        "scene_description": scene_description,
                        "prompt": prompt,
                        "image_path": result_path
                    }
                    image_paths.append(image_data)
            
            return image_paths
        else:
            # Sử dụng phương pháp chia đoạn nếu không có cảnh được phân tích
            # Giới hạn số đoạn theo image_count
            segments = segments[:image_count]
            
            image_paths = []
            print(f"Đang tạo {len(segments)} hình ảnh cho chương {chapter_num}...")
            
            for i, segment in enumerate(tqdm(segments)):
                prompt = self.generate_structured_prompt(segment, chapter_num)
                output_path = os.path.join(output_dir, f"chapter_{chapter_num}_image_{i+1}.png")
                
                result_path = self.generate_image(prompt, output_path)
                if result_path:
                    image_data = {
                        "segment_index": i,
                        "segment_text": segment,
                        "prompt": prompt,
                        "image_path": result_path
                    }
                    image_paths.append(image_data)
            
            return image_paths
    
    def process_story(self, story_data, output_dir="output"):
        """Xử lý toàn bộ câu chuyện và tạo hình ảnh cho mỗi chương"""
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        # Phân tích truyện để trích xuất thông tin nhân vật
        print("Đang phân tích thông tin nhân vật để tạo hình ảnh nhất quán...")
        self.characters_info = self._extract_character_info(story_data)
        
        # Lưu thông tin nhân vật để sử dụng sau này
        characters_file = os.path.join(output_dir, "characters_info.json")
        with open(characters_file, "w", encoding="utf-8") as f:
            json.dump(self.characters_info, f, ensure_ascii=False, indent=2)
        
        story_images = []
        
        for chapter in story_data["chapters"]:
            chapter_num = chapter["chapter_num"]
            chapter_content = chapter["content"]
            
            # Đảm bảo chapter_content là string
            if not isinstance(chapter_content, str):
                print(f"Cảnh báo: Nội dung chapter {chapter_num} không phải string")
                chapter_content = str(chapter_content)
            
            chapter_images = self.process_chapter(chapter_content, chapter_num, images_dir)
            
            # Thêm thông tin về hình ảnh vào dữ liệu chương
            story_images.append({
                "chapter_num": chapter_num,
                "images": chapter_images
            })
        
        # Lưu thông tin hình ảnh vào file
        images_data_path = os.path.join(output_dir, "images_data.json")
        with open(images_data_path, "w", encoding="utf-8") as f:
            json.dump(story_images, f, ensure_ascii=False, indent=2)
        
        print(f"Đã tạo xong hình ảnh cho {len(story_data['chapters'])} chương.")
        print(f"Dữ liệu hình ảnh đã được lưu vào: {images_data_path}")
        
        return story_images 