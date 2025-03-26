# Auto Create YouTube Content

Chương trình tự động tạo nội dung truyện và video dựa trên ý tưởng của người dùng.

## Tính năng
- Tạo nội dung truyện từ API Gemini-2.0-flash
- Cho phép chọn số chương và số token mỗi chương
- Tự động tạo hình ảnh từ nội dung truyện sử dụng API của:
  - CogView4 (ZhipuAI)
  - Stable Diffusion
  - Gemini-2.0-flash-exp-image-generation
- Tạo video bằng cách kết hợp text-to-speech và hình ảnh
- Giao diện người dùng thân thiện với Streamlit

## Cài đặt
1. Clone repository này
2. Cài đặt các thư viện cần thiết:
```
pip install -r requirements.txt
```
3. Tạo file `.env` với các API key cần thiết:
```
GOOGLE_API_KEY=your_google_api_key
OPENAI_API_KEY=your_openai_api_key
STABILITY_API_KEY=your_stability_api_key
ZHIPUAI_API_KEY=your_zhipuai_api_key
```

## Sử dụng
### Giao diện đồ họa (Streamlit)
Chạy ứng dụng Streamlit:
```
streamlit run app.py
```
Sau đó truy cập vào địa chỉ được hiển thị trong terminal (thường là http://localhost:8501).

### Dòng lệnh (CLI)
Chạy chương trình chính:
```
python main.py
```

## Các mô hình hỗ trợ

### Tạo truyện
- Google Gemini-2.0-flash

### Tạo hình ảnh
- Google Gemini-2.0-flash-exp-image-generation
- Stable Diffusion (thông qua Stability AI API)
- CogView4 (thông qua ZhipuAI API)

### Text-to-Speech
- Google Text-to-Speech (gTTS)
- OpenAI TTS

## Yêu cầu
- Python 3.8+
- Các API key hợp lệ cho các dịch vụ sử dụng

## Quy trình hoạt động
1. Tạo nội dung truyện từ ý tưởng của người dùng
2. Tạo hình ảnh minh họa cho từng đoạn truyện
3. Chuyển đổi nội dung truyện thành âm thanh
4. Tạo video kết hợp hình ảnh và âm thanh
5. Xuất video hoàn chỉnh để đăng lên YouTube 