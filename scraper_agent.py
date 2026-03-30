"""
Scraper Agent - Dùng Twexapi.io API (cheap, no limits)
https://twexapi.io/
"""
import asyncio
import aiohttp
import logging
import os
from datetime import datetime
from typing import List
from models import Post, PostSource

logger = logging.getLogger("ScraperAgent")

class ScraperAgent:
    def __init__(self, target_accounts: List[str]):
        self.target_accounts = [acc.lstrip("@") for acc in target_accounts]
        self.client = None
        self.api_key = os.getenv("TWEXAPI_KEY")  # Lấy từ environment
        if not self.api_key:
            raise ValueError("TWEXAPI_KEY not set in environment")
        self.last_scraped = {}

    async def _get_session(self):
        if self.client is None:
            self.client = aiohttp.ClientSession()
        return self.client

    async def scrape_user_tweets(self, username: str, max_results: int = 5) -> List[Post]:
        """
        Lấy tweets từ một user qua Twexapi.io
        Giả sử endpoint: /tweets?username={username}&limit={max_results}
        Cần kiểm tra tài liệu Twexapi.io để biết endpoint chính xác.
        """
        session = await self._get_session()
        # Giả sử endpoint là /tweets (có thể thay đổi)
        url = "https://twexapi.io/api/tweets"  # Cần xác nhận endpoint đúng
        params = {
            "username": username,
            "limit": max_results,
            "api_key": self.api_key
        }
        try:
            async with session.get(url, params=params, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"Twexapi.io error {response.status} for @{username}")
                    return []
                data = await response.json()
                # Giả sử data là danh sách tweet, mỗi tweet có id, text, created_at, like_count, retweet_count
                posts = []
                for tweet in data.get("tweets", []):  # Cấu trúc JSON cần kiểm tra
                    post = Post(
                        id=tweet.get("id", ""),
                        content=tweet.get("text", ""),
                        author=username,
                        source=PostSource.X_TWITTER,
                        created_at=datetime.fromisoformat(tweet.get("created_at", "").replace("Z", "+00:00")),
                        url=f"https://twitter.com/{username}/status/{tweet.get('id', '')}",
                        engagement={
                            "likes": tweet.get("like_count", 0),
                            "retweets": tweet.get("retweet_count", 0),
                            "replies": tweet.get("reply_count", 0)
                        }
                    )
                    posts.append(post)
                logger.info(f"✅ Scraped {len(posts)} tweets from @{username} via Twexapi.io")
                self.last_scraped[username] = datetime.now()
                return posts
        except Exception as e:
            logger.error(f"Error scraping @{username}: {e}")
            return []

    async def scrape_all_accounts(self) -> List[Post]:
        all_posts = []
        for account in self.target_accounts:
            posts = await self.scrape_user_tweets(account)
            all_posts.extend(posts)
            await asyncio.sleep(2)  # Tránh rate limit
        return all_posts

    async def close(self):
        if self.client:
            await self.client.aclose()
