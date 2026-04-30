from google import genai
import requests
import os
import time

# 1. Setup
STOCKS = ["NVDA", "AAPL", "TSLA"]
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")
GEMINI_KEY = os.getenv("GEMINI_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_KEY)

def get_stock_news(symbol):
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&apikey={ALPHA_VANTAGE_KEY}"
    try:
        r = requests.get(url)
        data = r.json()
        if "Note" in data:
            print(f"⚠️ Alpha Vantage API Limit reached for {symbol}")
            return []
        return data.get('feed', [])[:5]
    except Exception as e:
        print(f"❌ News fetch failed for {symbol}: {e}")
        return []

def generate_analysis(stock, news_data):
    raw_text = "\n".join([f"- {n['title']}: {n['summary']}" for n in news_data])
    prompt = f"Analyze news for {stock}: {raw_text}. Focus on breakouts and earnings. Keep it under 1000 chars."
    
    # List of models to try in order of preference
    # 'gemini-3-flash-preview' is the newest for 2026.
    # 'gemini-1.5-flash' is the hyper-stable legacy fallback.
    models_to_try = ["gemini-3-flash-preview", "gemini-1.5-flash"]
    
    for model_id in models_to_try:
        try:
            print(f"🤖 Attempting analysis with {model_id}...")
            response = client.models.generate_content(model=model_id, contents=prompt)
            return response.text
        except Exception as e:
            print(f"⚠️ {model_id} failed: {e}")
            time.sleep(2) # Short pause before fallback
            continue
    return None

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    res = requests.post(url, data={
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": text, 
        "parse_mode": "Markdown"
    })
    # If Markdown fails (status 400), retry as Plain Text
    if res.status_code != 200:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})

def analyze_and_post():
    print("🚀 Starting Stock Agent...")
    for stock in STOCKS:
        print(f"🔍 Processing {stock}...")
        news = get_stock_news(stock)
        if not news: continue
            
        analysis = generate_analysis(stock, news)
        if analysis:
            report = f"📦 **{stock} AI Analysis**\n\n{analysis}"
            send_to_telegram(report)
            print(f"✅ {stock} sent to Telegram.")
            time.sleep(1) 

if __name__ == "__main__":
    analyze_and_post()
