import feedparser
from google import genai
import requests
import os

# Cấu hình
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Sử dụng SDK google-genai mới
client = genai.Client(api_key=GEMINI_API_KEY)

SOURCES = {
    "VnExpress": "https://vnexpress.net/rss/tin-moi-nhat.rss",
    "VnEconomy": "https://vneconomy.vn/rss/thoi-su.rss",
    "CNN": "http://rss.cnn.com/rss/edition.rss"
}

def fetch_news():
    news_data = ""
    for name, url in SOURCES.items():
        feed = feedparser.parse(url)
        news_data += f"\n--- Nguồn: {name} ---\n"
        for entry in feed.entries[:5]:
            # Xử lý lỗi AttributeError bằng cách dùng .get()
            title = entry.get('title', 'Không có tiêu đề')
            # Thử lấy summary, nếu không có thì lấy description, nếu không có nữa thì để trống
            summary = entry.get('summary', entry.get('description', 'Xem chi tiết tại link'))
            news_data += f"Tiêu đề: {title}\n tóm tắt: {summary}\n\n"
    return news_data

def summarize_news(raw_content):
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
    
    # Sử dụng bản Lite để tránh lỗi 429 Resource Exhausted
    response = client.models.generate_content(
        model="gemini-flash-latest", 
        contents=prompt
    )
    return response.text

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # Thử gửi với Markdown trước
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    response = requests.post(url, json=payload)
    
    # Nếu lỗi (400 Bad Request), gửi lại dưới dạng văn bản thuần
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
        # 1. Liệt kê các model khả dụng để debug lỗi 404
        print("--- Đang kiểm tra danh sách Model ---")
        for m in client.models.list():
            print(f"Model ID: {m.name}")
        print("------------------------------------\n")
        # 2. main logic
        raw_news = fetch_news()
        summary = summarize_news(raw_news)
        send_telegram(summary)
        print("Đã gửi bản tin thành công!")
    except Exception as e:
        print(f"Lỗi vận hành: {e}")
