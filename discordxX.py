import os
import discord
import aiohttp
import asyncio
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
X_USER_IDS = os.getenv("X_USER_IDS").split(',')

headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
client = discord.Client(intents=discord.Intents.default())

# 記錄每個帳號的最新推文 ID
last_tweet_ids = {user_id: None for user_id in X_USER_IDS}

# 記錄帳號名稱
usernames = {}

async def get_username(session, user_id):
    url = f"https://api.x.com/2/users/{user_id}"
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            return data["data"]["username"]  # 回傳 username
        else:
            print(f"Error fetching username {user_id}: {response.status}")
            return None

async def get_latest_tweet(session, user_id):
    url = f"https://api.x.com/2/users/{user_id}/tweets?max_results=5"
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            tweet = data["data"][0] if "data" in data else None
            return user_id, tweet
        else:
            print(f"Error fetching tweets {user_id}: {response.status}")
            return user_id, None

async def check_all_tweets(channel):
    async with aiohttp.ClientSession() as session:
        # 如果 usernames 還沒取得，就先抓一次
        for user_id in X_USER_IDS:
            if user_id not in usernames:
                usernames[user_id] = await get_username(session, user_id)

        tasks = [get_latest_tweet(session, user_id) for user_id in X_USER_IDS]
        results = await asyncio.gather(*tasks)

        for user_id, tweet in results:
            if tweet and tweet["id"] != last_tweet_ids[user_id]:
                username = usernames.get(user_id, user_id)
                tweet_url = f"https://x.com/i/web/status/{tweet['id']}"
                await channel.send(f"🔔 新推文來自 @{username}：\n{tweet_url}")
                last_tweet_ids[user_id] = tweet["id"]

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    channel = client.get_channel(DISCORD_CHANNEL_ID)

    # 初始化最新推文
    await check_all_tweets(channel)

    while True:
        await asyncio.sleep(60)  # 每分鐘檢查一次
        await check_all_tweets(channel)

client.run(DISCORD_TOKEN)
