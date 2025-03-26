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
- Lưu trữ video qua Telegram hoặc MongoDB (tùy chọn)

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

# Thiết lập Telegram (khuyến nghị)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
TELEGRAM_ENABLED=true

# Thiết lập MongoDB (tùy chọn)
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB_NAME=auto_ytb_content
MONGODB_ENABLED=false
```

## Thiết lập Telegram Bot
Để lưu trữ video qua Telegram, bạn cần tạo một Telegram Bot và lấy thông tin cần thiết:

1. Mở Telegram và tìm kiếm "@BotFather"
2. Gửi lệnh `/newbot` và làm theo hướng dẫn để tạo bot mới
3. Sau khi tạo xong, BotFather sẽ cung cấp cho bạn một token. Sao chép token này vào biến `TELEGRAM_BOT_TOKEN` trong file `.env`
4. Để lấy Chat ID, bạn có hai cách:
   - **Cách 1**: Gửi tin nhắn đến bot [@userinfobot](https://t.me/userinfobot), nó sẽ trả về ID của bạn
   - **Cách 2**: Tạo một kênh hoặc nhóm riêng, thêm bot của bạn vào kênh/nhóm đó, sau đó gửi tin nhắn và lấy ID của kênh/nhóm từ URL của tin nhắn
5. Thêm Chat ID vào biến `TELEGRAM_CHAT_ID` trong file `.env`
6. Đảm bảo đặt `TELEGRAM_ENABLED=true` trong file `.env`

Lưu ý: Khi sử dụng Telegram làm nơi lưu trữ, video của bạn sẽ được gửi đến bot và bạn có thể xem và tải xuống từ đó.

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

## Lưu trữ dữ liệu
- Telegram Bot (khuyến nghị khi triển khai trên cloud)
- MongoDB (tùy chọn, thích hợp cho môi trường local)

## Yêu cầu
- Python 3.8+
- Các API key hợp lệ cho các dịch vụ sử dụng

## Quy trình hoạt động
1. Tạo nội dung truyện từ ý tưởng của người dùng
2. Tạo hình ảnh minh họa cho từng đoạn truyện
3. Chuyển đổi nội dung truyện thành âm thanh
4. Tạo video kết hợp hình ảnh và âm thanh
5. Lưu trữ video qua Telegram hoặc MongoDB
6. Xuất video hoàn chỉnh để đăng lên YouTube 