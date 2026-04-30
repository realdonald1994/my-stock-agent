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
        # Detect API Limit
        if "Note" in data: 
            return "API_LIMIT"
        return data.get('feed', [])[:5]
    except Exception as e:
        print(f"❌ Network Error for {symbol}: {e}")
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
    return res.status_code == 200

def analyze_and_post():
    # Convert UTC to EST/EDT (Approx UTC-4)
    est_now = datetime.utcnow() - timedelta(hours=4)
    est_hour = est_now.hour
    
    print(f"🕒 Current EST Time: {est_hour}:{est_now.minute}")

    if (est_hour == 9) or (est_hour == 16):
        stocks_to_check = PRIORITY_STOCKS + STANDARD_STOCKS
        print(f"🚀 Running FULL LIST for EST Market Activity")
    else:
        stocks_to_check = PRIORITY_STOCKS
        print(f"🚀 Running PRIORITY ONLY")

    for stock in stocks_to_check:
        print(f"🔍 Checking {stock}...") # This will now show in your logs
        news = get_today_news(stock)
        
        if news == "API_LIMIT":
            warning = "⚠️ **Alpha Vantage API Limit Reached**\n\nDaily 25-request limit exhausted. Monitoring paused until tomorrow's reset."
            send_to_telegram(warning)
            print("🛑 STOPPING: API Limit Reached.")
            return # Exit the entire script

        if not news:
            print(f"   No fresh news for {stock}.")
            continue
            
        analysis = generate_analysis(stock, news)
        if analysis:
            report = f"📦 **{stock} 今日动态深度解析 (EST)**\n\n{analysis}"
            send_to_telegram(report)
            print(f"   ✅ Report sent for {stock}.")
            time.sleep(2)

if __name__ == "__main__":
    analyze_and_post()
