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
            print(f"⚠️ API Limit reached: {symbol}")
            return []
        return data.get('feed', [])[:5]
    except Exception as e:
        print(f"❌ Fetch news failed for {symbol}: {e}")
        return []

def generate_analysis(stock, news_data):
    raw_text = "\n".join([f"- {n['title']}: {n['summary']}" for n in news_data])
    
    # 核心：Prompt 为英文，要求输出为中文
    prompt = f"""
    Act as a Senior Financial Analyst. Analyze the following news for {stock}:
    {raw_text}

    IMPORTANT: Please provide your response in [CHINESE] and follow this format:
    1. 📢 **核心新闻**: Summarize the most impactful news (Priority: Earnings reports and Guidance).
    2. ⚡ **技术信号**: Analyze for "Breakout" or "Breakdown" risks. Mention key support/resistance levels.
    3. 🎯 **情绪评分**: Rate from 1-10 (10 is extremely Bullish).
    
    Constraint: Keep the response under 400 Chinese characters.
    """
    
    # 2026 推荐模型及回退机制
    models_to_try = ["gemini-3-flash-preview", "gemini-1.5-flash"]
    
    for model_id in models_to_try:
        try:
            print(f"🤖 Generating Chinese analysis using {model_id}...")
            response = client.models.generate_content(model=model_id, contents=prompt)
            return response.text
        except Exception as e:
            print(f"⚠️ {model_id} failed: {e}")
            time.sleep(2)
            continue
    return None

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    res = requests.post(url, data={
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": text, 
        "parse_mode": "Markdown"
    })
    # Fallback to plain text if Markdown parsing fails
    if res.status_code != 200:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})

def analyze_and_post():
    print("🚀 Stock Agent Started (English Prompt / Chinese Output)...")
    for stock in STOCKS:
        print(f"🔍 Processing {stock}...")
        news = get_stock_news(stock)
        if not news: continue
            
        analysis = generate_analysis(stock, news)
        if analysis:
            report = f"📦 **{stock} AI 深度解析**\n\n{analysis}"
            send_to_telegram(report)
            print(f"✅ {stock} report sent in Chinese.")
            time.sleep(1) # Rate limiting

if __name__ == "__main__":
    analyze_and_post()
