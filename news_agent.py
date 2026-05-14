import feedparser
import google.generativeai as genai
import requests
import os

# Cấu hình
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 1. Danh sách nguồn RSS
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
        # Lấy 5 tin mới nhất mỗi nguồn để tránh quá tải token
        for entry in feed.entries[:5]:
            news_data += f"Tiêu đề: {entry.title}\n tóm tắt: {entry.summary}\n\n"
    return news_data

def summarize_news(raw_content):
    prompt = f"""
    Bạn là một trợ lý tin tức thông minh. Hãy tóm tắt các tin tức dưới đây thành một bản tin sáng súc tích.
    - Phân loại theo chủ đề (Kinh tế, Công nghệ, Thế giới...).
    - Mỗi tin gồm 1 dòng tiêu đề đậm và 1 dòng tóm tắt ý chính.
    - Dịch các tin tiếng Anh sang tiếng Việt.
    - Định dạng bằng Markdown để gửi Telegram.
    
    Nội dung thô:
    {raw_content}
    """
    response = model.generate_content(prompt)
    return response.text

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

if __name__ == "__main__":
    raw_news = fetch_news()
    summary = summarize_news(raw_news)
    send_telegram(summary)