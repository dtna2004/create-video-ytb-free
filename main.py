import os
import argparse
import json
from utils.config import validate_api_keys, create_directories, DEFAULT_CONFIG
from utils.story_generator import StoryGenerator
from utils.image_generator import ImageGenerator
from utils.audio_generator import AudioGenerator
from utils.video_generator import VideoGenerator

def parse_arguments():
    """Xử lý tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description="Tạo tự động truyện và video từ ý tưởng")
    
    parser.add_argument("--story_concept", type=str, help="Ý tưởng truyện cần tạo")
    parser.add_argument("--num_chapters", type=int, default=DEFAULT_CONFIG['num_chapters'],
                        help="Số chương truyện")
    parser.add_argument("--tokens_per_chapter", type=int, default=DEFAULT_CONFIG['tokens_per_chapter'],
                        help="Số token mỗi chương")
    parser.add_argument("--image_model", type=str, choices=["gemini", "stable_diffusion", "cogview4"],
                        default=DEFAULT_CONFIG['image_model'], help="Model tạo hình ảnh")
    parser.add_argument("--tts_provider", type=str, choices=["google", "openai"],
                        default=DEFAULT_CONFIG['tts_provider'], help="Provider text-to-speech")
    parser.add_argument("--output_dir", type=str, default=DEFAULT_CONFIG['output_dir'],
                        help="Thư mục lưu kết quả")
    parser.add_argument("--skip_story", action="store_true", help="Bỏ qua bước tạo truyện")
    parser.add_argument("--skip_images", action="store_true", help="Bỏ qua bước tạo hình ảnh")
    parser.add_argument("--skip_audio", action="store_true", help="Bỏ qua bước tạo audio")
    parser.add_argument("--skip_video", action="store_true", help="Bỏ qua bước tạo video")
    
    return parser.parse_args()

def read_story_data(output_dir):
    """Đọc dữ liệu truyện từ file JSON"""
    story_data_path = os.path.join(output_dir, "story_data.json")
    if os.path.exists(story_data_path):
        with open(story_data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def read_images_data(output_dir):
    """Đọc dữ liệu hình ảnh từ file JSON"""
    images_data_path = os.path.join(output_dir, "images_data.json")
    if os.path.exists(images_data_path):
        with open(images_data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def read_audio_data(output_dir):
    """Đọc dữ liệu audio từ file JSON"""
    audio_data_path = os.path.join(output_dir, "audio_data.json")
    if os.path.exists(audio_data_path):
        with open(audio_data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def interactive_mode():
    """Chế độ tương tác với người dùng để nhập tham số"""
    print("=== Chương trình tạo tự động truyện và video ===")
    
    story_concept = input("Nhập ý tưởng truyện của bạn: ")
    
    num_chapters = input(f"Số chương truyện (mặc định: {DEFAULT_CONFIG['num_chapters']}): ")
    num_chapters = int(num_chapters) if num_chapters.strip() else DEFAULT_CONFIG['num_chapters']
    
    tokens_per_chapter = input(f"Số token mỗi chương (mặc định: {DEFAULT_CONFIG['tokens_per_chapter']}): ")
    tokens_per_chapter = int(tokens_per_chapter) if tokens_per_chapter.strip() else DEFAULT_CONFIG['tokens_per_chapter']
    
    print("\nChọn model tạo hình ảnh:")
    print("1. Gemini-2.0-flash-exp-image-generation (mặc định)")
    print("2. Stable Diffusion")
    print("3. CogView4")
    image_model_choice = input("Lựa chọn của bạn (1-3): ")
    
    image_model = DEFAULT_CONFIG['image_model']
    if image_model_choice == "2":
        image_model = "stable_diffusion"
    elif image_model_choice == "3":
        image_model = "cogview4"
    
    print("\nChọn provider text-to-speech:")
    print("1. Google (mặc định)")
    print("2. OpenAI")
    tts_choice = input("Lựa chọn của bạn (1-2): ")
    
    tts_provider = DEFAULT_CONFIG['tts_provider']
    if tts_choice == "2":
        tts_provider = "openai"
    
    output_dir = input(f"Thư mục lưu kết quả (mặc định: {DEFAULT_CONFIG['output_dir']}): ")
    output_dir = output_dir.strip() if output_dir.strip() else DEFAULT_CONFIG['output_dir']
    
    return {
        "story_concept": story_concept,
        "num_chapters": num_chapters,
        "tokens_per_chapter": tokens_per_chapter,
        "image_model": image_model,
        "tts_provider": tts_provider,
        "output_dir": output_dir,
        "skip_story": False,
        "skip_images": False,
        "skip_audio": False,
        "skip_video": False
    }

def main():
    """Hàm chính của chương trình"""
    # Kiểm tra API keys
    try:
        validate_api_keys()
    except ValueError as e:
        print(f"Lỗi: {e}")
        print("Vui lòng cập nhật file .env với các API key cần thiết.")
        return
    
    # Xử lý tham số
    args = parse_arguments()
    
    # Nếu không có story_concept, chuyển sang chế độ tương tác
    if not args.story_concept:
        args_dict = interactive_mode()
        args = argparse.Namespace(**args_dict)
    
    # Tạo thư mục output
    os.makedirs(args.output_dir, exist_ok=True)
    create_directories()
    
    # Các biến lưu dữ liệu giữa các bước
    story_data = None
    story_images = None
    story_audio = None
    
    # Bước 1: Tạo truyện
    if not args.skip_story:
        print("\n=== Bước 1: Tạo nội dung truyện ===")
        story_generator = StoryGenerator()
        story_data = story_generator.generate_full_story(
            args.story_concept,
            num_chapters=args.num_chapters,
            tokens_per_chapter=args.tokens_per_chapter,
            output_dir=args.output_dir
        )
    else:
        print("\n=== Bỏ qua bước tạo truyện ===")
        story_data = read_story_data(args.output_dir)
        if not story_data:
            print("Không tìm thấy dữ liệu truyện. Vui lòng chạy lại mà không bỏ qua bước tạo truyện.")
            return
    
    # Bước 2: Tạo hình ảnh
    if not args.skip_images:
        print("\n=== Bước 2: Tạo hình ảnh minh họa ===")
        image_generator = ImageGenerator(model_type=args.image_model)
        story_images = image_generator.process_story(story_data, output_dir=args.output_dir)
    else:
        print("\n=== Bỏ qua bước tạo hình ảnh ===")
        story_images = read_images_data(args.output_dir)
        if not story_images and not args.skip_video:
            print("Không tìm thấy dữ liệu hình ảnh. Không thể tạo video mà không có hình ảnh.")
            return
    
    # Bước 3: Tạo audio
    if not args.skip_audio:
        print("\n=== Bước 3: Tạo audio từ text ===")
        audio_generator = AudioGenerator(provider=args.tts_provider)
        story_audio = audio_generator.process_story(story_data, output_dir=args.output_dir)
    else:
        print("\n=== Bỏ qua bước tạo audio ===")
        story_audio = read_audio_data(args.output_dir)
        if not story_audio and not args.skip_video:
            print("Không tìm thấy dữ liệu audio. Không thể tạo video mà không có audio.")
            return
    
    # Bước 4: Tạo video
    if not args.skip_video:
        print("\n=== Bước 4: Tạo video từ audio và hình ảnh ===")
        if story_images and story_audio:
            video_generator = VideoGenerator()
            video_data = video_generator.create_full_video(
                story_data, story_images, story_audio, output_dir=args.output_dir
            )
            
            if video_data and video_data.get("full_video"):
                print(f"\nĐã tạo xong video đầy đủ: {video_data['full_video']}")
            else:
                print("\nKhông thể tạo video đầy đủ, nhưng có thể đã tạo được video cho một số chương.")
        else:
            print("Không có đủ dữ liệu hình ảnh và audio để tạo video.")
    else:
        print("\n=== Bỏ qua bước tạo video ===")
    
    print("\n=== Hoàn thành! ===")
    print(f"Tất cả dữ liệu đã được lưu vào thư mục: {os.path.abspath(args.output_dir)}")

if __name__ == "__main__":
    main() 