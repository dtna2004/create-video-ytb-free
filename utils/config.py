import os
from dotenv import load_dotenv

# Kiểm tra file .env
print(f"CONFIG - Thư mục hiện tại: {os.getcwd()}")
print(f"CONFIG - File .env tồn tại: {os.path.exists('.env')}")

# Tải các biến môi trường từ file .env
load_dotenv(verbose=True)

# API keys
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
STABILITY_API_KEY = os.getenv('STABILITY_API_KEY')
ZHIPUAI_API_KEY = os.getenv('ZHIPUAI_API_KEY')

print(f"CONFIG - GOOGLE_API_KEY: {'Có giá trị' if GOOGLE_API_KEY else 'Không có giá trị'}")

# Kiểm tra các API key cần thiết
def validate_api_keys():
    missing_keys = []
    
    if not GOOGLE_API_KEY:
        missing_keys.append("GOOGLE_API_KEY")
    
    if missing_keys:
        raise ValueError(f"Thiếu các API keys sau: {', '.join(missing_keys)}. Vui lòng thêm vào file .env")

# Cấu hình mặc định
DEFAULT_CONFIG = {
    'num_chapters': 1,
    'tokens_per_chapter': 2000,
    'image_model': 'gemini',  # 'gemini', 'stable_diffusion', or 'cogview4'
    'tts_provider': 'google',  # 'google' or 'openai'
    'output_dir': 'output',
    'temp_dir': 'temp'
}

# Tạo thư mục nếu chưa tồn tại
def create_directories():
    os.makedirs(DEFAULT_CONFIG['output_dir'], exist_ok=True)
    os.makedirs(DEFAULT_CONFIG['temp_dir'], exist_ok=True) 