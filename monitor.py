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
    # Check for news within the last 24 hours
    yesterday = datetime.utcnow() - timedelta(hours=24)
    time_from = yesterday.strftime("%Y%m%dT%H%M")
    
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&time_from={time_from}&apikey={ALPHA_VANTAGE_KEY}"
    
    try:
        r = requests.get(url)
        data = r.json()
        if "Note" in data:
            print(f"⚠️ API Limit reached for {symbol}")
            return []
        
        feed = data.get('feed', [])
        return feed[:5] if feed else []
    except Exception as e:
        print(f"❌ News fetch failed for {symbol}: {e}")
        return []

def generate_analysis(stock, news_data):
    raw_text = "\n".join([f"- {n['title']}: {n['summary']}" for n in news_data])
    
    prompt = f"""
    Act as a Senior Financial Analyst. Analyze the last 24h news for {stock}:
    {raw_text}

    IMPORTANT: Provide the response in [CHINESE].
    Focus strictly on:
    1. 📢 **Corporate News**: Financial reports (Quarter/Month end), earnings, or guidance.
    2. 💻 **Technology & R&D**: AI infrastructure, new product releases, or tech breakthroughs.
    3. ⚡ **Technical Signals**: Breakout/breakdown risks with specific price levels.
    4. 🎯 **Sentiment Score**: 1-10.

    Keep it concise (under 400 Chinese characters).
    """
    
    try:
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
        return response.text
    except:
        # Fallback to stable model
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        return response.text

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    res = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
    if res.status_code != 200:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})

def analyze_and_post():
    # Determine current hour in UTC to decide which list to run
    current_hour = datetime.utcnow().hour
    
    # Logic: 
    # At 09:00 and 17:00 UTC -> Priority Only
    # At 13:00 and 22:00 UTC -> Full List
    if current_hour in [13, 22]:
        stocks_to_check = PRIORITY_STOCKS + STANDARD_STOCKS
        print(f"🚀 Running FULL LIST monitor ({len(stocks_to_check)} stocks)")
    else:
        stocks_to_check = PRIORITY_STOCKS
        print(f"🚀 Running PRIORITY ONLY monitor ({len(stocks_to_check)} stocks)")

    for stock in stocks_to_check:
        news = get_today_news(stock)
        if not news:
            print(f"ℹ️ No fresh news for {stock}. Skipping...")
            continue
            
        analysis = generate_analysis(stock, news)
        if analysis:
            report = f"📦 **{stock} 今日动态深度解析**\n\n{analysis}"
            send_to_telegram(report)
            time.sleep(2)

if __name__ == "__main__":
    analyze_and_post()
