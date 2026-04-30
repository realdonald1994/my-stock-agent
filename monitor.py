from google import genai
import requests
import os
import time  # New: for waiting between retries

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
        print(f"❌ News fetch failed for {stock}: {e}")
        return []

def generate_with_retry(prompt, model_name="gemini-3-flash-preview", retries=3):
    """Tries to generate content, waiting if the server is busy."""
    for i in range(retries):
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            return response.text
        except Exception as e:
            if "503" in str(e) or "high demand" in str(e).lower():
                print(f"🔄 AI busy (Attempt {i+1}/{retries}). Waiting 15s...")
                time.sleep(15)  # Wait 15 seconds before trying again
            else:
                print(f"❌ AI Error: {e}")
                break
    return None

def analyze_and_post():
    header = "🚀 **Daily AI Market Watch**\n\n"
    final_report = header
    
    for stock in STOCKS:
        print(f"🔍 Processing {stock}...")
        news_data = get_stock_news(stock)
        
        if not news_data:
            continue
            
        raw_text = "\n".join([f"- {n['title']}: {n['summary']}" for n in news_data])
        prompt = f"Analyze news for {stock}: {raw_text}. Keep it brief, focus on technical breakouts and earnings."
        
        # Use the retry helper
        analysis = generate_with_retry(prompt)
        
        if analysis:
            final_report += f"**{stock} Analysis:**\n{analysis}\n\n---\n\n"
            print(f"✅ {stock} complete.")
        else:
            print(f"⏭️ Skipping {stock} due to AI unavailability.")

    # 3. Send to Telegram
    if final_report != header:
        print("📤 Sending to Telegram...")
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(telegram_url, data={
            "chat_id": TELEGRAM_CHAT_ID, 
            "text": final_report, 
            "parse_mode": "Markdown"
        })
    else:
        print("🚫 Nothing to send.")

if __name__ == "__main__":
    analyze_and_post()
