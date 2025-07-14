import feedparser
from newspaper import Article
from pymongo import MongoClient
from datetime import datetime
import asyncio
from time import sleep
from telegram import Bot
import openai

# Mongo & Telegram setup
client = MongoClient("mongodb://localhost:27017")
db = client.news_db
collection = db.articles

TELEGRAM_TOKEN = "Token"
CHANNEL_ID = "channel_id"
bot = Bot(token=TELEGRAM_TOKEN)

rss_feeds = {
    "BBC": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "New York Daily News": "https://www.nydailynews.com/feed",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "New York Times": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "NHK": "https://www3.nhk.or.jp/rss/news/cat0.xml"
}

def extract_article_text(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        return f"❌ Could not extract article content: {e}"

def chatbot(message):
    prompt = f"""You are a Telegram news channel copywriter.
Your task is to:
- Translate the following news article into Russian
- Make it concise and engaging for Telegram readers
- Keep the total output under 4096 characters (Telegram limit)
- Preserve the main facts and tone of the article
Here is the article:
\"\"\"
{message}
\"\"\""""
    try:
        client = openai.OpenAI(api_key="Your_api_key")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

async def post_to_telegram(article):
    message = f"📰 <b>{article['title']}</b>\n" \
              f"🔗 <a href='{article['link']}'>Read more</a>\n" \
              f"🗞️ Source: {article['source']}\n" \
              f"Content:{article['content']}"
    post = chatbot(message)
    await bot.send_message(chat_id=CHANNEL_ID, text=post[:4096], parse_mode='HTML')
    await asyncio.sleep(2)

async def main():
    while True:
        print(f"\n🕒 Fetching news at {datetime.now()}\n")

        for source_name, rss_url in rss_feeds.items():
            print(f"\n=== 🌍 Fetching from {source_name} ===\n")

            feed = feedparser.parse(rss_url)

            for entry in feed.entries[:5]:
                full_text = extract_article_text(entry.link)

                article_data = {
                    "source": source_name,
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.get('published'),
                    "content": full_text
                }

                if not collection.find_one({"link": article_data["link"]}):
                    collection.insert_one(article_data)
                    print(f"✅ Inserted: {entry.title}")
                    await post_to_telegram(article_data)
                else:
                    print(f"⚠️ Already exists: {entry.title}")

                print("-" * 80)

        print("✅ Sleeping for 10 minutes...\n")
        await asyncio.sleep(300)  # Sleep for 600 seconds = 10 minutes


# 🔁 Run async function
if __name__ == "__main__":
    asyncio.run(main())
