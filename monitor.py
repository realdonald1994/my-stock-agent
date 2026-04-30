from google import genai
import requests
import os
import time
from datetime import datetime, timedelta

# 1. Tiered Stock Lists
PRIORITY_STOCKS = ["CLS", "HPS-A.TO"]
STANDARD_STOCKS = ["AAPL", "TSLA", "MSFT", "GOOG", "META", "INTC", "AMD"]

ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")
GEMINI_KEY = os.getenv("GEMINI_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_KEY)

def get_today_news(symbol):
    yesterday = datetime.utcnow() - timedelta(hours=24)
    time_from = yesterday.strftime("%Y%m%dT%H%M")
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&time_from={time_from}&apikey={ALPHA_VANTAGE_KEY}"
    
    try:
        r = requests.get(url)
        data = r.json()
        if "Note" in data: return []
        return data.get('feed', [])[:5]
    except:
        return []

def generate_analysis(stock, news_data):
    raw_text = "\n".join([f"- {n['title']}: {n['summary']}" for n in news_data])
    prompt = f"""
    Act as a Senior Financial Analyst. Analyze the last 24h news for {stock}:
    {raw_text}
    IMPORTANT: Provide the response in [CHINESE].
    Focus: 1. Corporate News (Earnings/Guidance) 2. Tech Updates 3. Technical Breakout Levels 4. Sentiment (1-10).
    Keep it concise (under 400 Chinese characters).
    """
    try:
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
        return response.text
    except:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        return response.text

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    res = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
    if res.status_code != 200:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})

def analyze_and_post():
    # Convert UTC to EST/EDT (Approx UTC-4)
    est_now = datetime.utcnow() - timedelta(hours=4)
    est_hour = est_now.hour
    est_minute = est_now.minute
    
    print(f"🕒 Current EST Time: {est_hour}:{est_minute}")

    # Logic adjusted for EST Market Hours:
    # Full List at Market Open (9:30 AM) and Market Close (4:30 PM)
    if (est_hour == 9) or (est_hour == 16):
        stocks_to_check = PRIORITY_STOCKS + STANDARD_STOCKS
        print(f"🚀 Running FULL LIST for EST Market Activity")
    else:
        stocks_to_check = PRIORITY_STOCKS
        print(f"🚀 Running PRIORITY ONLY for frequent monitoring")

    for stock in stocks_to_check:
        news = get_today_news(stock)
        if not news:
            continue
            
        analysis = generate_analysis(stock, news)
        if analysis:
            report = f"📦 **{stock} 今日动态深度解析 (EST)**\n\n{analysis}"
            send_to_telegram(report)
            time.sleep(2)

if __name__ == "__main__":
    analyze_and_post()
