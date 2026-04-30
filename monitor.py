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
    """Generates analysis with strict length constraints."""
    raw_text = "\n".join([f"- {n['title']}: {n['summary']}" for n in news_data])
    
    # Strict prompt to prevent the "message too long" error
    prompt = f"""
    Analyze news for {stock}: {raw_text}.
    Format:
    1. 📢 **Top News**: 1-sentence summary.
    2. ⚡ **Technical Signal**: Breakout/Breakdown risks & levels.
    3. 🎯 **Sentiment**: 1-10.
    
    Keep the total response under 1000 characters.
    """
    
    try:
        # Using the standard flash model for reliability
        response = client.models.generate_content(
            model="gemini-3-flash", 
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"❌ AI Error for {stock}: {e}")
        return None

def send_to_telegram(text):
    """Sends message. Retries as plain text if Markdown fails."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # Try Markdown first
    res = requests.post(url, data={
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": text, 
        "parse_mode": "Markdown"
    })
    
    # If Markdown fails (status 400), retry as Plain Text
    if res.status_code != 200:
        print(f"📡 Markdown failed for a message, retrying as Plain Text...")
        requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID, 
            "text": text
        })

def analyze_and_post():
    print("🚀 Starting Stock Agent...")
    
    for stock in STOCKS:
        print(f"🔍 Processing {stock}...")
        news = get_stock_news(stock)
        
        if not news:
            continue
            
        analysis = generate_analysis(stock, news)
        
        if analysis:
            report = f"📦 **{stock} AI Analysis**\n\n{analysis}"
            send_to_telegram(report)
            print(f"✅ {stock} sent to Telegram.")
            # Small pause to avoid Telegram rate limits
            time.sleep(1) 

if __name__ == "__main__":
    analyze_and_post()
