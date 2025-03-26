import os
from dotenv import load_dotenv
import streamlit as st

# Kiểm tra file .env
print(f"CONFIG - Thư mục hiện tại: {os.getcwd()}")
print(f"CONFIG - File .env tồn tại: {os.path.exists('.env')}")

# Tải các biến môi trường từ file .env
load_dotenv(verbose=True)

# Hàm để lấy giá trị biến môi trường hoặc từ Streamlit secrets
def get_env_var(key, default=None):
    # Thử lấy từ Streamlit secrets
    try:
        return st.secrets.get(key, os.getenv(key, default))
    except:
        # Nếu không chạy trong môi trường Streamlit, lấy từ os.environ
        return os.getenv(key, default)

# API keys
GOOGLE_API_KEY = get_env_var('GOOGLE_API_KEY')
OPENAI_API_KEY = get_env_var('OPENAI_API_KEY')
STABILITY_API_KEY = get_env_var('STABILITY_API_KEY')
ZHIPUAI_API_KEY = get_env_var('ZHIPUAI_API_KEY')

# Cấu hình MongoDB
MONGODB_URI = get_env_var('MONGODB_URI', 'mongodb://localhost:27017/')
DB_NAME = get_env_var('MONGODB_DB_NAME', 'auto_ytb_content')
MONGODB_ENABLED = get_env_var('MONGODB_ENABLED', 'true').lower() == 'true'

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