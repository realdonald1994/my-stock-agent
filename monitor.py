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

def generate_with_retry(prompt, model_name="gemini-3-flash-preview", retries=3):
    for i in range(retries):
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            return response.text
        except Exception as e:
            if "503" in str(e):
                print(f"🔄 AI busy (Attempt {i+1}). Waiting 15s...")
                time.sleep(15)
            else:
                print(f"❌ AI Error: {e}")
                break
    return None

def send_telegram_message(message, use_markdown=True):
    """Helper to send message and print result."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    if use_markdown:
        payload["parse_mode"] = "Markdown"
    
    res = requests.post(url, data=payload)
    print(f"📡 Telegram Status: {res.status_code}")
    if res.status_code != 200:
        print(f"❌ Telegram Error Details: {res.text}")
    return res.status_code == 200

def analyze_and_post():
    # --- SANITY TEST ---
    print("🧪 Sending Test Message...")
    send_telegram_message("🤖 Stock Agent is online and checking the markets!")

    header = "🚀 **Daily AI Market Watch**\n\n"
    final_report = header
    
    for stock in STOCKS:
        print(f"🔍 Processing {stock}...")
        news_data = get_stock_news(stock)
        if not news_data: continue
            
        raw_text = "\n".join([f"- {n['title']}: {n['summary']}" for n in news_data])
        prompt = f"Analyze news for {stock}: {raw_text}. Focus on breakouts and earnings. Keep it brief."
        
        analysis = generate_with_retry(prompt)
        if analysis:
            final_report += f"**{stock} Analysis:**\n{analysis}\n\n---\n\n"
    
    # --- SEND ACTUAL REPORT ---
    if final_report != header:
        print("📤 Sending Full Report...")
        # If Markdown fails, we try sending as plain text
        if not send_telegram_message(final_report, use_markdown=True):
            print("🔄 Markdown failed. Retrying as Plain Text...")
            send_telegram_message(final_report, use_markdown=False)

if __name__ == "__main__":
    analyze_and_post()
