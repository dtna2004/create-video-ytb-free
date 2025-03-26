import os
import pymongo
from dotenv import load_dotenv
import datetime
import json
from utils.config import MONGODB_URI, DB_NAME, MONGODB_ENABLED, TELEGRAM_ENABLED
from utils.telegram_utils import telegram_manager

# Tải các biến môi trường từ file .env
load_dotenv(verbose=True)

class DatabaseManager:
    def __init__(self):
        """Khởi tạo kết nối với MongoDB"""
        self.client = None
        self.db = None
        
        # Kiểm tra xem có sử dụng MongoDB không
        if MONGODB_ENABLED:
            self.connect()
        else:
            print("MongoDB đã bị tắt trong thiết lập, sẽ sử dụng Telegram hoặc lưu trữ tạm thời")
            
        # Kiểm tra Telegram
        if TELEGRAM_ENABLED and telegram_manager.is_configured():
            print("Đã kích hoạt lưu trữ video qua Telegram")
        else:
            print("Cảnh báo: Cả MongoDB và Telegram đều không được cấu hình đúng. Sẽ sử dụng lưu trữ tạm thời.")
    
    def connect(self):
        """Kết nối đến MongoDB"""
        try:
            self.client = pymongo.MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            self.client.server_info()  # Kiểm tra kết nối
            self.db = self.client[DB_NAME]
            print(f"Đã kết nối thành công đến MongoDB: {DB_NAME}")
        except Exception as e:
            print(f"Không thể kết nối đến MongoDB: {e}")
            print("Sẽ sử dụng Telegram hoặc lưu trữ tạm thời thay thế")
            self.client = None
            self.db = None
    
    def is_connected(self):
        """Kiểm tra xem đã kết nối đến MongoDB chưa"""
        return self.db is not None
    
    def save_video_data(self, video_data, story_title, series_name=None):
        """Lưu thông tin video vào MongoDB hoặc Telegram
        
        Args:
            video_data: Dữ liệu video (full_video, chapter_videos)
            story_title: Tiêu đề truyện
            series_name: Tên bộ truyện (nếu có)
        
        Returns:
            id: ID của bản ghi đã lưu hoặc None nếu thất bại
        """
        # Thử lưu vào MongoDB nếu đã kết nối
        if MONGODB_ENABLED and self.is_connected():
            try:
                # Chuẩn bị dữ liệu video
                video_document = {
                    "story_title": story_title,
                    "series_name": series_name,
                    "created_at": datetime.datetime.now(),
                    "full_video_path": video_data.get("full_video"),
                    "downloaded": False,
                    "chapters": []
                }
                
                # Thêm thông tin về các video chương
                for chapter_video in video_data.get("chapter_videos", []):
                    chapter_info = {
                        "chapter_num": chapter_video.get("chapter_num"),
                        "title": chapter_video.get("title"),
                        "video_path": chapter_video.get("video_path"),
                        "downloaded": False
                    }
                    video_document["chapters"].append(chapter_info)
                
                # Lưu vào collection videos
                result = self.db.videos.insert_one(video_document)
                print(f"Đã lưu thông tin video vào MongoDB với ID: {result.inserted_id}")
                return result.inserted_id
            
            except Exception as e:
                print(f"Lỗi khi lưu thông tin video vào MongoDB: {e}")
                print("Sẽ thử lưu qua Telegram...")
        
        # Nếu không thể lưu vào MongoDB, thử lưu qua Telegram
        if TELEGRAM_ENABLED and telegram_manager.is_configured():
            message_id = telegram_manager.save_video_data(video_data, story_title, series_name)
            if message_id:
                print(f"Đã lưu thông tin video lên Telegram với ID tin nhắn: {message_id}")
                return message_id
        
        # Nếu không thể lưu vào cả MongoDB và Telegram, trả về ID tạm thời
        temp_id = f"temp_id_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        print(f"Không thể lưu vào cả MongoDB và Telegram. Đang trả về ID tạm thời: {temp_id}")
        return temp_id
    
    def get_all_videos(self):
        """Lấy tất cả thông tin video từ MongoDB"""
        if MONGODB_ENABLED and self.is_connected():
            try:
                videos = list(self.db.videos.find())
                return videos
            except Exception as e:
                print(f"Lỗi khi lấy thông tin video từ MongoDB: {e}")
        
        # Trả về danh sách trống nếu không có MongoDB
        print("MongoDB không khả dụng. Không thể hiển thị danh sách video.")
        return []
    
    def get_videos_by_series(self, series_name):
        """Lấy tất cả video thuộc một bộ truyện"""
        if MONGODB_ENABLED and self.is_connected():
            try:
                videos = list(self.db.videos.find({"series_name": series_name}))
                return videos
            except Exception as e:
                print(f"Lỗi khi lấy thông tin video theo bộ truyện từ MongoDB: {e}")
        
        # Trả về danh sách trống nếu không có MongoDB
        print("MongoDB không khả dụng. Không thể hiển thị danh sách video theo bộ truyện.")
        return []
    
    def update_download_status(self, video_id, chapter_num=None, downloaded=True):
        """Cập nhật trạng thái tải xuống của video
        
        Args:
            video_id: ID của video (MongoDB ID hoặc Telegram message ID)
            chapter_num: Số chương (nếu None thì cập nhật video đầy đủ)
            downloaded: Trạng thái tải xuống (True/False)
        
        Returns:
            bool: True nếu cập nhật thành công, False nếu thất bại
        """
        # Thử cập nhật trong MongoDB nếu đã kết nối
        if MONGODB_ENABLED and self.is_connected():
            try:
                if str(video_id).startswith("tg_") or not self._is_mongodb_id(video_id):
                    # Đây là ID Telegram, không cần cập nhật trong MongoDB
                    return True
                
                if chapter_num is None:
                    # Cập nhật trạng thái tải xuống của video đầy đủ
                    result = self.db.videos.update_one(
                        {"_id": video_id},
                        {"$set": {"downloaded": downloaded}}
                    )
                else:
                    # Cập nhật trạng thái tải xuống của chương cụ thể
                    result = self.db.videos.update_one(
                        {"_id": video_id, "chapters.chapter_num": chapter_num},
                        {"$set": {"chapters.$.downloaded": downloaded}}
                    )
                
                return result.modified_count > 0
            
            except Exception as e:
                print(f"Lỗi khi cập nhật trạng thái tải xuống trong MongoDB: {e}")
        
        # Thử cập nhật trạng thái qua Telegram
        if TELEGRAM_ENABLED and telegram_manager.is_configured():
            if str(video_id).startswith("tg_") or self._is_telegram_id(video_id):
                return telegram_manager.update_download_status(video_id, downloaded)
        
        # Trả về True nếu không có MongoDB và Telegram
        return True
    
    def _is_mongodb_id(self, id_str):
        """Kiểm tra xem ID có phải là MongoDB ID hay không"""
        try:
            # Nếu có thể chuyển thành ObjectId, đó là MongoDB ID
            from bson.objectid import ObjectId
            ObjectId(str(id_str))
            return True
        except:
            return False
    
    def _is_telegram_id(self, id_str):
        """Kiểm tra xem ID có phải là Telegram message ID hay không"""
        # Telegram message ID thường là số nguyên
        try:
            id_int = int(id_str)
            return True
        except:
            return False
    
    def save_series(self, series_name, description=""):
        """Tạo hoặc cập nhật thông tin bộ truyện
        
        Args:
            series_name: Tên bộ truyện
            description: Mô tả về bộ truyện
        
        Returns:
            id: ID của bản ghi đã lưu hoặc None nếu thất bại
        """
        if MONGODB_ENABLED and self.is_connected():
            try:
                # Kiểm tra xem bộ truyện đã tồn tại chưa
                existing_series = self.db.series.find_one({"name": series_name})
                if existing_series:
                    # Nếu đã tồn tại, cập nhật mô tả
                    result = self.db.series.update_one(
                        {"name": series_name},
                        {"$set": {"description": description}}
                    )
                    return existing_series["_id"]
                else:
                    # Nếu chưa tồn tại, tạo mới
                    series_document = {
                        "name": series_name,
                        "description": description,
                        "created_at": datetime.datetime.now()
                    }
                    result = self.db.series.insert_one(series_document)
                    return result.inserted_id
            
            except Exception as e:
                print(f"Lỗi khi lưu thông tin bộ truyện vào MongoDB: {e}")
        
        # Nếu không có MongoDB, trả về ID tạm thời
        temp_id = f"temp_series_{series_name.replace(' ', '_')}"
        if TELEGRAM_ENABLED and telegram_manager.is_configured():
            # Gửi thông tin bộ truyện lên Telegram
            message = f"<b>Bộ truyện mới:</b> {series_name}\n<b>Mô tả:</b> {description}"
            message_id = telegram_manager.send_message(message)
            if message_id:
                return f"tg_series_{message_id}"
            
        return temp_id
    
    def get_all_series(self):
        """Lấy tất cả bộ truyện từ MongoDB"""
        if MONGODB_ENABLED and self.is_connected():
            try:
                series_list = list(self.db.series.find())
                return series_list
            except Exception as e:
                print(f"Lỗi khi lấy thông tin bộ truyện từ MongoDB: {e}")
        
        # Trả về danh sách tạm thời nếu không có MongoDB
        current_time = datetime.datetime.now()
        temp_series = [
            {
                "_id": "temp_id", 
                "name": "Sử dụng lưu trữ tạm thời", 
                "description": "MongoDB không khả dụng. Các video được lưu qua Telegram.",
                "created_at": current_time
            }
        ]
        return temp_series

# Tạo singleton instance
db_manager = DatabaseManager() 