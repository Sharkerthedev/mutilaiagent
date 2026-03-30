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

class WebScraperAgent:
    """Agent cào dữ liệu từ Twitter/X qua Twexapi.io"""

    def __init__(self, target_accounts: List[str]):
        self.target_accounts = [acc.lstrip("@") for acc in target_accounts]
        self.client = None
        self.api_key = os.getenv("TWEXAPI_KEY")
        if not self.api_key:
            raise ValueError("TWEXAPI_KEY not set in environment")
        self.last_scraped = {}

    async def _get_session(self):
        if self.client is None:
            self.client = aiohttp.ClientSession()
        return self.client

    async def scrape_user_tweets(self, username: str, max_results: int = 5) -> List[Post]:
        """
        Lấy tweets từ một user qua Twexapi.io.
        Cần điều chỉnh endpoint và params theo tài liệu chính thức.
        """
        session = await self._get_session()
        # === ĐÂY LÀ GIẢ ĐỊNH, CẦN KIỂM TRA TÀI LIỆU TWEXAPI.IO ===
        url = "https://twexapi.io/api/tweets"  # Có thể thay đổi
        params = {
            "username": username,
            "limit": max_results,
            "api_key": self.api_key
        }
        # Nếu API yêu cầu key trong header, sửa lại như sau:
        # headers = {"Authorization": f"Bearer {self.api_key}"}
        # async with session.get(url, headers=headers, params=params, timeout=30) as response:

        try:
            async with session.get(url, params=params, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"Twexapi.io error {response.status} for @{username}")
                    return []
                data = await response.json()
                # Giả định JSON có cấu trúc: {"tweets": [{"id":..., "text":..., ...}]}
                tweets = data.get("tweets", [])
                posts = []
                for tweet in tweets:
                    # Chuyển đổi created_at
                    created_at_str = tweet.get("created_at", "")
                    if created_at_str:
                        try:
                            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        except:
                            created_at = datetime.now()
                    else:
                        created_at = datetime.now()

                    post = Post(
                        id=tweet.get("id", ""),
                        content=tweet.get("text", ""),
                        author=username,
                        source=PostSource.X_TWITTER,
                        created_at=created_at,
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

        except asyncio.TimeoutError:
            logger.warning(f"Timeout scraping @{username} via Twexapi.io")
            return []
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
