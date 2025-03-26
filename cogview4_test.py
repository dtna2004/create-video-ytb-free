import os
import json
from dotenv import load_dotenv
import zhipuai

# Tải các biến môi trường từ file .env
load_dotenv(verbose=True)

# Lấy API key từ biến môi trường
ZHIPUAI_API_KEY = os.getenv('ZHIPUAI_API_KEY')

def test_cogview4_api():
    """Kiểm tra API CogView4"""
    print(f"API Key: {ZHIPUAI_API_KEY[:5]}...")
    
    try:
        # Kiểm tra phiên bản thư viện
        print(f"Phiên bản ZhipuAI: {zhipuai.__version__}")
        
        # Khởi tạo client
        client = zhipuai.ZhipuAI(api_key=ZHIPUAI_API_KEY)
        
        # Tạo một prompt đơn giản
        prompt = "A beautiful landscape with mountains and a lake"
        
        print(f"Đang gọi API CogView4 với prompt: {prompt}")
        
        # Gọi API tạo hình ảnh
        response = client.images.generations(
            model="cogview-4",
            prompt=prompt
        )
        
        # Hiển thị kết quả
        print("Kết quả:")
        print(json.dumps(response.model_dump(), indent=2))
        
        if hasattr(response, 'data') and len(response.data) > 0:
            print(f"URL hình ảnh: {response.data[0].url}")
            return True
        else:
            print("Không nhận được hình ảnh trong phản hồi")
            return False
            
    except Exception as e:
        print(f"Lỗi khi gọi API CogView4: {e}")
        return False

if __name__ == "__main__":
    test_cogview4_api() 