from google import genai  # Modern 2026 SDK
import requests
import os

# 1. Configuration
STOCKS = ["NVDA", "AAPL", "TSLA"]
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")
GEMINI_KEY = os.getenv("GEMINI_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 2. Initialize the Client
# The SDK automatically handles the v1beta routing for preview models
client = genai.Client(api_key=GEMINI_KEY)

def get_stock_news(symbol):
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&apikey={ALPHA_VANTAGE_KEY}"
    try:
        response = requests.get(url).json()
        return response.get('feed', [])[:5]
    except Exception as e:
        print(f"Error fetching news for {symbol}: {e}")
        return []

def analyze_and_post():
    final_report = "🚀 **Daily AI Market Watch**\n\n"
    
    for stock in STOCKS:
        news_data = get_stock_news(stock)
        if not news_data:
            continue
            
        raw_text = "\n".join([f"- {n['title']}: {n['summary']}" for n in news_data])
        
        # Refined Technical/Earnings Prompt
        prompt = f"""
        Act as a Professional Equity Analyst specializing in Technical Analysis and Earnings.
        Analyze the following news for {stock}:
        {raw_text}

        Report in this EXACT format:
        1. 📢 **Top News**: Summary of the biggest headline (Priority: Earnings/Quarterly Reports).
        2. ⚡ **Technical Signal**: Identify 'Breakout' or 'Breakdown' risks. Mention key price levels if found.
        3. 🎯 **Sentiment**: Rate 1-10 (10 is high-conviction Bullish).
        """
        
        # Use the correct preview model string for April 2026
        try:
            response = client.models.generate_content(
                model="gemini-3-flash-preview", 
                contents=prompt
            )
            final_report += f"**{stock} Analysis:**\n{response.text}\n\n---\n\n"
        except Exception as e:
            print(f"AI Generation failed for {stock}: {e}")

    # 3. Send to Telegram
    if final_report != "🚀 **Daily AI Market Watch**\n\n":
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(telegram_url, data={
            "chat_id": TELEGRAM_CHAT_ID, 
            "text": final_report, 
            "parse_mode": "Markdown"
        })

if __name__ == "__main__":
    analyze_and_post()
