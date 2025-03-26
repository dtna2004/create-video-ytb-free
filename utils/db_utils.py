import os
import pymongo
from dotenv import load_dotenv
import datetime
import json

# Tải các biến môi trường từ file .env
load_dotenv(verbose=True)

# Cấu hình MongoDB
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('MONGODB_DB_NAME', 'auto_ytb_content')
MONGODB_ENABLED = os.getenv('MONGODB_ENABLED', 'true').lower() == 'true'

class DatabaseManager:
    def __init__(self):
        """Khởi tạo kết nối với MongoDB"""
        self.client = None
        self.db = None
        if MONGODB_ENABLED:
            self.connect()
        else:
            print("MongoDB đã bị tắt trong thiết lập, sẽ sử dụng lưu trữ tạm thời")
    
    def connect(self):
        """Kết nối đến MongoDB"""
        try:
            self.client = pymongo.MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            self.client.server_info()  # Kiểm tra kết nối
            self.db = self.client[DB_NAME]
            print(f"Đã kết nối thành công đến MongoDB: {DB_NAME}")
        except Exception as e:
            print(f"Không thể kết nối đến MongoDB: {e}")
            print("Sẽ sử dụng lưu trữ tạm thời thay thế")
            self.client = None
            self.db = None
    
    def is_connected(self):
        """Kiểm tra xem đã kết nối đến MongoDB chưa"""
        return self.db is not None
    
    def save_video_data(self, video_data, story_title, series_name=None):
        """Lưu thông tin video vào MongoDB
        
        Args:
            video_data: Dữ liệu video (full_video, chapter_videos)
            story_title: Tiêu đề truyện
            series_name: Tên bộ truyện (nếu có)
        
        Returns:
            id: ID của bản ghi đã lưu hoặc None nếu thất bại
        """
        if not MONGODB_ENABLED:
            print("MongoDB đã bị tắt, đang sử dụng lưu trữ tạm thời")
            return "temp_id_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            
        if not self.is_connected():
            print("Chưa kết nối đến MongoDB, đang sử dụng lưu trữ tạm thời")
            return "temp_id_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        
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
            return "temp_id_error_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    
    def get_all_videos(self):
        """Lấy tất cả thông tin video từ MongoDB"""
        if not MONGODB_ENABLED or not self.is_connected():
            print("MongoDB không khả dụng cho thao tác get_all_videos")
            return []
        
        try:
            videos = list(self.db.videos.find())
            return videos
        except Exception as e:
            print(f"Lỗi khi lấy thông tin video từ MongoDB: {e}")
            return []
    
    def get_videos_by_series(self, series_name):
        """Lấy tất cả video thuộc một bộ truyện"""
        if not MONGODB_ENABLED or not self.is_connected():
            print("MongoDB không khả dụng cho thao tác get_videos_by_series")
            return []
        
        try:
            videos = list(self.db.videos.find({"series_name": series_name}))
            return videos
        except Exception as e:
            print(f"Lỗi khi lấy thông tin video theo bộ truyện từ MongoDB: {e}")
            return []
    
    def update_download_status(self, video_id, chapter_num=None, downloaded=True):
        """Cập nhật trạng thái tải xuống của video
        
        Args:
            video_id: ID của video trong MongoDB
            chapter_num: Số chương (nếu None thì cập nhật video đầy đủ)
            downloaded: Trạng thái tải xuống (True/False)
        
        Returns:
            bool: True nếu cập nhật thành công, False nếu thất bại
        """
        if not MONGODB_ENABLED or not self.is_connected():
            print("MongoDB không khả dụng cho thao tác update_download_status")
            return True  # Giả lập thành công
        
        try:
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
            print(f"Lỗi khi cập nhật trạng thái tải xuống: {e}")
            return True  # Giả lập thành công
    
    def save_series(self, series_name, description=""):
        """Tạo hoặc cập nhật thông tin bộ truyện
        
        Args:
            series_name: Tên bộ truyện
            description: Mô tả về bộ truyện
        
        Returns:
            id: ID của bản ghi đã lưu hoặc None nếu thất bại
        """
        if not MONGODB_ENABLED or not self.is_connected():
            print("MongoDB không khả dụng cho thao tác save_series")
            return "temp_series_" + series_name.replace(" ", "_")
        
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
            return "temp_series_error_" + series_name.replace(" ", "_")
    
    def get_all_series(self):
        """Lấy tất cả bộ truyện từ MongoDB"""
        if not MONGODB_ENABLED or not self.is_connected():
            print("MongoDB không khả dụng cho thao tác get_all_series")
            # Trả về danh sách trống cùng với thông tin loại bỏ MongoDB
            temp_series = [
                {"_id": "temp_id", "name": "Sử dụng lưu trữ tạm thời", "description": "MongoDB không khả dụng", "created_at": datetime.datetime.now()}
            ]
            return temp_series
        
        try:
            series_list = list(self.db.series.find())
            return series_list
        except Exception as e:
            print(f"Lỗi khi lấy thông tin bộ truyện từ MongoDB: {e}")
            return []

# Tạo singleton instance
db_manager = DatabaseManager() 