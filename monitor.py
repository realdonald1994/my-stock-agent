from google import genai
import requests
import os

# 1. Setup
STOCKS = ["NVDA", "AAPL", "TSLA"]
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")
GEMINI_KEY = os.getenv("GEMINI_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialize the new 2026 Client
client = genai.Client(api_key=GEMINI_KEY)

def get_stock_news(symbol):
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&apikey={ALPHA_VANTAGE_KEY}"
    response = requests.get(url).json()
    return response.get('feed', [])[:5]

def analyze_and_post():
    final_report = "🚀 **Daily AI Market Watch**\n\n"
    
    for stock in STOCKS:
        news_data = get_stock_news(stock)
        raw_text = "\n".join([f"- {n['title']}: {n['summary']}" for n in news_data])
        
        prompt = f"""
        Act as a Professional Equity Analyst. Analyze the news for {stock}:
        {raw_text}

        Report in this format:
        1. 📢 **Top News**: Summary of the biggest headline (Earnings/Quarterly Reports take priority).
        2. ⚡ **Technical Signal**: Based on news, is there a 'Breakout' or 'Breakdown' risk? Identify key price levels mentioned.
        3. 🎯 **Sentiment**: Rate from 1-10 (10 is extremely Bullish).
        """
        
        # Calling the modern Gemini 3 Flash model
        response = client.models.generate_content(
            model="gemini-3-flash", 
            contents=prompt
        )
        
        final_report += f"**{stock} Analysis:**\n{response.text}\n\n---\n\n"

    # Send to Telegram
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(telegram_url, data={
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": final_report, 
        "parse_mode": "Markdown"
    })

if __name__ == "__main__":
    analyze_and_post()
