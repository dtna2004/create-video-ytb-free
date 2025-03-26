import os
from dotenv import load_dotenv

# Kiểm tra file .env
print(f"Thư mục hiện tại: {os.getcwd()}")
print(f"File .env tồn tại: {os.path.exists('.env')}")

# Tải các biến môi trường từ file .env
load_dotenv(verbose=True)

# Kiểm tra các API key
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
STABILITY_API_KEY = os.getenv('STABILITY_API_KEY')
ZHIPUAI_API_KEY = os.getenv('ZHIPUAI_API_KEY')

print(f"GOOGLE_API_KEY: {'Có giá trị' if GOOGLE_API_KEY else 'Không có giá trị'}")
print(f"OPENAI_API_KEY: {'Có giá trị' if OPENAI_API_KEY else 'Không có giá trị'}")
print(f"STABILITY_API_KEY: {'Có giá trị' if STABILITY_API_KEY else 'Không có giá trị'}")
print(f"ZHIPUAI_API_KEY: {'Có giá trị' if ZHIPUAI_API_KEY else 'Không có giá trị'}")

print("Các API key đầy đủ (chỉ hiển thị một phần để bảo mật):")
if GOOGLE_API_KEY:
    print(f"GOOGLE_API_KEY: {GOOGLE_API_KEY[:5]}...")
if OPENAI_API_KEY:
    print(f"OPENAI_API_KEY: {OPENAI_API_KEY[:5]}...")
if STABILITY_API_KEY:
    print(f"STABILITY_API_KEY: {STABILITY_API_KEY[:5]}...")
if ZHIPUAI_API_KEY:
    print(f"ZHIPUAI_API_KEY: {ZHIPUAI_API_KEY[:5]}...") 