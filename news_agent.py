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
    # Lấy mốc thời gian 24h trước
    yesterday = datetime.now() - timedelta(days=1)
    
    for name, url in SOURCES.items():
        feed = feedparser.parse(url)
        news_data += f"\n--- SOURCE: {name} ---\n"
        
        count = 0
        for entry in feed.entries:
            # Lấy thời gian xuất bản của bài báo
            published_time = entry.get('published_parsed')
            if published_time:
                dt_published = datetime.fromtimestamp(time.mktime(published_time))
                
                # CHỈ LẤY TIN TRONG 24H QUA
                if dt_published > yesterday:
                    title = entry.get('title', '')
                    desc = entry.get('description', entry.get('summary', ''))[:300]
                    news_data += f"TITLE: {title}\nCONTENT: {desc}\n\n"
                    count += 1
            
            if count >= 10: # Giới hạn 10 tin mới nhất mỗi nguồn
                break
    
    if not news_data.strip():
        return "No new articles found in the last 24 hours."
    return news_data

def summarize_news(raw_content):
    prompt = f"""
    # Lấy ngày hiện tại để ép AI tập trung
    today = datetime.now().strftime("%d/%m/%Y")
    
    prompt = f"""
    Hôm nay là ngày {today}. 
    Dưới đây là dữ liệu thô từ các trang báo. 
    NHIỆM VỤ:
    - Tóm tắt dựa TRÊN DUY NHẤT dữ liệu được cung cấp dưới đây. 
    - Tuyệt đối không sử dụng kiến thức cũ hoặc tự bịa ra tin tức không có trong văn bản.
    - Nếu dữ liệu thô trống hoặc không có tin mới, hãy báo: "Không có tin tức mới trong 24h qua".
    
    QUY TẮC NGÔN NGỮ:
    - CNN: KEEP ORIGINAL ENGLISH (Tittle & Content).
    - VNExpress/VnEconomy: Tiếng Việt.
    
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
