import feedparser
from google import genai
import requests
import os

# Cấu hình
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

# Cập nhật lại link RSS chuẩn xác hơn
SOURCES = {
    "VnExpress": "https://vnexpress.net/rss/tin-moi-nhat.rss",
    "VnEconomy": "https://vneconomy.vn/rss/thoi-su.rss",
    "CNN": "https://rss.cnn.com/rss/edition.rss" # Chuyển sang https
}

def fetch_news():
    news_data = ""
    # Giả lập User-Agent của trình duyệt để tránh bị VnEconomy/CNN chặn (Lỗi 403)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for name, url in SOURCES.items():
        try:
            print(f"Đang lấy tin từ nguồn: {name}...")
            # Dùng requests để fetch XML về trước nhằm bypass cơ chế chặn bot
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Parse nội dung XML nhận được từ requests
                feed = feedparser.parse(response.content)
                
                if not feed.entries:
                    print(f"⚠️ Nguồn {name} không trả về tin nào (Bị trống).")
                    continue
                    
                news_data += f"\n--- Nguồn: {name} ---\n"
                for entry in feed.entries[:5]:
                    title = entry.get('title', 'Không có tiêu đề')
                    summary = entry.get('summary', entry.get('description', 'Xem chi tiết tại link'))
                    news_data += f"Tiêu đề: {title}\n tóm tắt: {summary}\n\n"
            else:
                print(f"❌ Lỗi {response.status_code} khi kết nối tới {name}")
                
        except Exception as e:
            print(f"❌ Lỗi khi xử lý nguồn {name}: {e}")
            
    return news_data

def summarize_news(raw_content):
    # Giữ nguyên Prompt của bạn
    prompt = f"""
    Bạn là biên tập viên tin tức thông minh phục vụ cho Khang (Software Engineer & Investor).
    Hãy tổng hợp tin tức từ dữ liệu thô dưới đây:

    YÊU CẦU NỘI DUNG:
    1. 📈 KINH TẾ & CHỨNG KHOÁN: Ưu tiên tối đa HPG, FPT, VCB và thị trường chung.
    2. 💻 CÔNG NGHỆ: Các cập nhật mới về AI, Full-stack, DevOps.
    3. 🌐 TIN NỔI BẬT KHÁC: Tổng hợp các sự kiện nóng hổi trong ngày tại Việt Nam.
    4. 🇺🇸 CNN HIGHLIGHTS: Lọc ra 3-5 tin quan trọng nhất, GIỮ NGUYÊN TIẾNG ANH.

    ĐỊNH DẠNG (BẮT BUỘC):
    - Dùng bullet points (*), tối đa 10 dòng/tin.
    - Phân chia section rõ ràng bằng Emoji.
    - KHÔNG sử dụng các ký tự đặc biệt gây lỗi Markdown ngoại trừ dấu * để in đậm.
    
    Dữ liệu:
    {raw_content}
    """
    
    response = client.models.generate_content(
        model="gemini-flash-latest", 
        contents=prompt
    )
    return response.text

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        print(f"Markdown lỗi, đang gửi lại dạng text thuần... Lỗi: {response.text}")
        payload.pop("parse_mode") 
        retry_response = requests.post(url, json=payload)
        if retry_response.status_code == 200:
            print("Đã gửi thành công dạng text thuần!")
        else:
            print(f"Thất bại hoàn toàn: {retry_response.text}")

if __name__ == "__main__":
    try:
        print("--- Đang kiểm tra danh sách Model ---")
        for m in client.models.list():
            print(f"Model ID: {m.name}")
        print("------------------------------------\n")
        
        raw_news = fetch_news()
        
        # Kiểm tra xem có dữ liệu thô không trước khi gọi AI
        if raw_news.strip():
            summary = summarize_news(raw_news)
            send_telegram(summary)
            print("Đã gửi bản tin thành công!")
        else:
            print("Không thu thập được bất kỳ tin tức nào từ tất cả các nguồn.")
            
    except Exception as e:
        print(f"Lỗi vận hành: {e}")
