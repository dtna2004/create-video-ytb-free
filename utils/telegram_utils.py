import os
import requests
import json
from datetime import datetime
from utils.config import get_env_var

# Lấy thông tin Telegram Bot từ biến môi trường
TELEGRAM_BOT_TOKEN = get_env_var('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = get_env_var('TELEGRAM_CHAT_ID')

class TelegramManager:
    def __init__(self):
        """Khởi tạo Telegram Manager"""
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        if not self.bot_token or not self.chat_id:
            print("Cảnh báo: Thiếu thông tin Telegram Bot Token hoặc Chat ID")
            print("Vui lòng thêm TELEGRAM_BOT_TOKEN và TELEGRAM_CHAT_ID vào file .env")
    
    def is_configured(self):
        """Kiểm tra xem Telegram Bot đã được cấu hình đúng chưa"""
        return bool(self.bot_token and self.chat_id)
    
    def send_message(self, message):
        """Gửi tin nhắn đến Telegram chat"""
        if not self.is_configured():
            print("Không thể gửi tin nhắn: Telegram Bot chưa được cấu hình")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, data=data)
            response_json = response.json()
            
            if response_json.get("ok"):
                print(f"Đã gửi tin nhắn đến Telegram")
                return response_json.get("result", {}).get("message_id")
            else:
                print(f"Lỗi khi gửi tin nhắn đến Telegram: {response_json.get('description')}")
                return False
        except Exception as e:
            print(f"Lỗi khi gửi tin nhắn đến Telegram: {e}")
            return False
    
    def send_video(self, video_path, caption="", thumb_path=None):
        """Gửi video đến Telegram chat
        
        Args:
            video_path: Đường dẫn đến file video
            caption: Chú thích cho video
            thumb_path: Đường dẫn đến file thumbnail (tùy chọn)
            
        Returns:
            message_id: ID của tin nhắn trên Telegram nếu thành công, False nếu thất bại
        """
        if not self.is_configured():
            print("Không thể gửi video: Telegram Bot chưa được cấu hình")
            return False
        
        if not os.path.exists(video_path):
            print(f"Không thể gửi video: File không tồn tại ({video_path})")
            return False
        
        try:
            url = f"{self.base_url}/sendVideo"
            
            # Chuẩn bị dữ liệu form
            data = {
                "chat_id": self.chat_id,
                "caption": caption,
                "parse_mode": "HTML"
            }
            
            files = {
                "video": open(video_path, "rb")
            }
            
            # Thêm thumbnail nếu có
            if thumb_path and os.path.exists(thumb_path):
                files["thumb"] = open(thumb_path, "rb")
            
            # Gửi yêu cầu
            print(f"Đang gửi video lên Telegram... (file size: {os.path.getsize(video_path) / (1024*1024):.2f} MB)")
            response = requests.post(url, data=data, files=files)
            
            # Đóng file
            for file in files.values():
                file.close()
            
            # Xử lý kết quả
            response_json = response.json()
            
            if response_json.get("ok"):
                message_id = response_json.get("result", {}).get("message_id")
                print(f"Đã gửi video thành công đến Telegram (Message ID: {message_id})")
                return message_id
            else:
                print(f"Lỗi khi gửi video đến Telegram: {response_json.get('description')}")
                return False
        except Exception as e:
            print(f"Lỗi khi gửi video đến Telegram: {e}")
            return False
    
    def save_video_data(self, video_data, story_title, series_name=None):
        """Lưu thông tin video lên Telegram và trả về ID tin nhắn
        
        Args:
            video_data: Dữ liệu video (full_video, chapter_videos)
            story_title: Tiêu đề truyện
            series_name: Tên bộ truyện (nếu có)
            
        Returns:
            message_id: ID của tin nhắn trên Telegram
        """
        if not self.is_configured():
            temp_id = f"tg_temp_id_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            print(f"Telegram Bot chưa được cấu hình. Đang trả về ID tạm thời: {temp_id}")
            return temp_id
        
        full_video_path = video_data.get("full_video")
        chapter_videos = video_data.get("chapter_videos", [])
        
        # Tạo tiêu đề tin nhắn
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if series_name:
            caption = f"<b>Bộ truyện:</b> {series_name}\n<b>Tiêu đề:</b> {story_title}\n<b>Thời gian:</b> {timestamp}"
        else:
            caption = f"<b>Tiêu đề:</b> {story_title}\n<b>Thời gian:</b> {timestamp}"
        
        # Thêm thông tin chương vào caption
        if chapter_videos:
            caption += f"\n\n<b>Số chương:</b> {len(chapter_videos)}"
        
        # Gửi video đầy đủ nếu có
        if full_video_path and os.path.exists(full_video_path):
            message_id = self.send_video(full_video_path, caption)
            
            # Gửi thông tin thành công
            if message_id:
                # Gửi thêm tin nhắn với thông tin chi tiết
                details = f"<b>Chi tiết video:</b>\n"
                details += f"- <b>Đường dẫn:</b> {full_video_path}\n"
                details += f"- <b>Kích thước:</b> {os.path.getsize(full_video_path) / (1024*1024):.2f} MB\n"
                details += f"- <b>ID tin nhắn Telegram:</b> {message_id}"
                
                self.send_message(details)
                
                return message_id
        
        # Trường hợp không có video đầy đủ hoặc gửi thất bại
        return f"tg_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def update_download_status(self, message_id, downloaded=True):
        """Cập nhật trạng thái tải xuống bằng cách gửi tin nhắn mới
        
        Args:
            message_id: ID của tin nhắn Telegram
            downloaded: Trạng thái tải xuống
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu thất bại
        """
        if not self.is_configured():
            return True
        
        status = "đã tải xuống" if downloaded else "chưa tải xuống"
        message = f"Cập nhật trạng thái cho video (ID: {message_id}): {status}"
        
        return bool(self.send_message(message))

# Tạo instance mặc định
telegram_manager = TelegramManager() 