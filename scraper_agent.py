"""
Scraper Agent - Web Scraping Twitter/X trực tiếp (NO API NEEDED)
Dùng BeautifulSoup + Requests - 100% FREE
Không cần API key, không có quota limit
"""
import asyncio
import aiohttp
import logging
import random
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from models import Post, PostSource

logger = logging.getLogger("ScraperAgent")

# Danh sách các User-Agent hiện đại để luân phiên
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0'
]

class WebScraperAgent:
    """Agent cào dữ liệu từ Twitter/X bằng web scraping"""

    def __init__(self, target_accounts: List[str]):
        self.target_accounts = [acc.lstrip("@") for acc in target_accounts]
        self.client = None
        self.last_scraped = {}

        # Danh sách mirror Nitter (ưu tiên các mirror thường hoạt động)
        self.nitter_mirrors = [
            "https://nitter.privacydev.net",
            "https://nitter.lunar.icu",
            "https://nitter.poast.org",
            "https://nitter.net"
        ]

    async def _get_session(self):
        if self.client is None:
            self.client = aiohttp.ClientSession()
        return self.client

    async def scrape_user_tweets(self, username: str, max_results: int = 5) -> List[Post]:
        """
        Cào tweets từ một user, thử qua từng mirror Nitter.
        """
        session = await self._get_session()
        # Chọn User-Agent ngẫu nhiên cho request
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        # Thử từng mirror
        for mirror in self.nitter_mirrors:
            nitter_url = f"{mirror}/{username}"
            logger.info(f"Scraping @{username} via {mirror}...")

            # Random delay nhẹ để tránh bị chặn
            await asyncio.sleep(random.uniform(1, 3))

            try:
                async with session.get(nitter_url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        posts = []

                        # Tìm các tweet (class .tweet)
                        tweets = soup.find_all('div', {'class': 'tweet'})
                        if not tweets:
                            logger.warning(f"No tweets found for @{username} via {mirror}")
                            continue

                        for tweet in tweets[:max_results]:
                            try:
                                text_elem = tweet.find('p', {'class': 'tweet-text'})
                                if not text_elem:
                                    continue
                                content = text_elem.get_text(strip=True)

                                # Trích xuất engagement
                                stats = tweet.find('div', {'class': 'tweet-stats'})
                                likes = retweets = replies = 0
                                if stats:
                                    stat_items = stats.find_all('span', {'class': 'stat'})
                                    if len(stat_items) >= 3:
                                        try:
                                            replies = int(stat_items[0].get_text().split()[0])
                                            retweets = int(stat_items[1].get_text().split()[0])
                                            likes = int(stat_items[2].get_text().split()[0])
                                        except:
                                            pass

                                if content and len(content) > 5:
                                    post = Post(
                                        id=tweet.get('id', f'tweet_{len(posts)}'),
                                        content=content,
                                        author=username,
                                        source=PostSource.X_TWITTER,
                                        created_at=datetime.now(),
                                        url=f"https://twitter.com/{username}",
                                        engagement={
                                            "likes": likes,
                                            "retweets": retweets,
                                            "replies": replies
                                        }
                                    )
                                    posts.append(post)
                            except Exception as e:
                                logger.debug(f"Error parsing tweet: {e}")
                                continue

                        if posts:
                            logger.info(f"✅ Scraped {len(posts)} tweets from @{username} via {mirror}")
                            self.last_scraped[username] = datetime.now()
                            return posts
                        else:
                            # Có response 200 nhưng không có tweet -> thử mirror khác
                            continue

                    elif response.status == 403:
                        logger.warning(f"Access forbidden (403) for @{username} via {mirror}")
                        # 403 thường do User-Agent hoặc IP bị chặn, thử mirror khác
                        continue
                    else:
                        logger.warning(f"Failed to fetch {nitter_url}: {response.status}")
                        continue

            except asyncio.TimeoutError:
                logger.warning(f"Timeout for @{username} via {mirror}")
                continue
            except Exception as e:
                logger.debug(f"Error with mirror {mirror}: {e}")
                continue

        # Nếu tất cả mirror Nitter đều thất bại, thử fallback Twstalker
        logger.info(f"All Nitter mirrors failed for @{username}, trying Twstalker...")
        return await self._scrape_from_twstalker(username, max_results)

    async def _scrape_from_twstalker(self, username: str, max_results: int) -> List[Post]:
        """Fallback: dùng twstalker.com"""
        try:
            session = await self._get_session()
            twstalker_url = f"https://twstalker.com/profile/{username}"
            headers = {'User-Agent': random.choice(USER_AGENTS)}
            async with session.get(twstalker_url, headers=headers, timeout=30) as response:
                if response.status != 200:
                    logger.warning(f"Twstalker failed for @{username}: {response.status}")
                    return []
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                posts = []
                # Twstalker có cấu trúc khác, tìm các container tweet
                tweets = soup.find_all('div', {'class': ['tweet', 'status', 'tweet-item']})
                for tweet in tweets[:max_results]:
                    text_elem = tweet.find(['p', 'span'], {'class': ['text', 'tweet-text', 'content']})
                    if text_elem:
                        content = text_elem.get_text(strip=True)
                        if content and len(content) > 5:
                            posts.append(Post(
                                id=f'tweet_{len(posts)}',
                                content=content,
                                author=username,
                                source=PostSource.X_TWITTER,
                                created_at=datetime.now(),
                                url=f"https://twitter.com/{username}",
                                engagement={"likes": 0, "retweets": 0, "replies": 0}
                            ))
                logger.info(f"✅ Scraped {len(posts)} tweets from @{username} (Twstalker)")
                return posts
        except Exception as e:
            logger.error(f"Twstalker fallback failed: {e}")
            return []

    async def scrape_all_accounts(self) -> List[Post]:
        all_posts = []
        for account in self.target_accounts:
            posts = await self.scrape_user_tweets(account, max_results=5)
            all_posts.extend(posts)
            # Delay giữa các tài khoản để tránh bị chặn
            await asyncio.sleep(random.uniform(3, 6))
        return all_posts

    async def close(self):
        if self.client:
            await self.client.aclose()

    def get_status(self) -> str:
        status = "📊 Scraper Status:\n"
        status += f"  Accounts: {', '.join(self.target_accounts)}\n"
        status += f"  Method: Web Scraping (NO API KEY)\n"
        status += f"  Mirrors: {', '.join(self.nitter_mirrors)}\n"
        for acc, last in self.last_scraped.items():
            minutes = (datetime.now() - last).total_seconds() / 60
            status += f"  Last scraped @{acc}: {minutes:.0f} min ago\n"
        return status
