"""
Scraper Agent - Web Scraping Twitter/X trực tiếp (NO API NEEDED)
Dùng BeautifulSoup + Requests - 100% FREE
Không cần API key, không có quota limit
"""
import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import List, Optional
from bs4 import BeautifulSoup
from models import Post, PostSource
import time
import random

logger = logging.getLogger("ScraperAgent")


class WebScraperAgent:
    """Agent cào dữ liệu từ Twitter/X bằng web scraping"""

    def __init__(self, target_accounts: List[str]):
        """
        Args:
            target_accounts: Danh sách user cần theo dõi (e.g., ["@elonmusk", "@username"])
        """
        self.target_accounts = [acc.lstrip("@") for acc in target_accounts]
        self.client = None
        self.last_scraped = {}
        
        # Headers giả lập browser để tránh bị block
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    async def _get_session(self):
        """Tạo HTTP session nếu chưa có"""
        if self.client is None:
            self.client = aiohttp.ClientSession()
        return self.client

    async def scrape_user_tweets(self, username: str, max_results: int = 5) -> List[Post]:
        """
        Cào tweets từ một user dùng web scraping
        
        Args:
            username: Tên user (không có @)
            max_results: Số lượng tweets tối đa
            
        Returns:
            Danh sách Post objects
        """
        try:
            session = await self._get_session()
            
            # Method 1: Dùng nitter.net (Twitter alternative frontend - free)
            # Nitter là mirror của Twitter, có thể scrape dễ dàng
            nitter_url = f"https://nitter.poast.org/{username}"
            
            logger.info(f"Scraping tweets from @{username} via Nitter...")
            
            # Add random delay để tránh rate limiting
            await asyncio.sleep(random.uniform(1, 3))
            
            async with session.get(nitter_url, headers=self.headers, timeout=30) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {nitter_url}: {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                posts = []
                
                # Tìm tweets trong HTML structure của Nitter
                # Nitter structure: div.tweet-body
                tweets = soup.find_all('div', {'class': 'tweet'})
                
                if not tweets:
                    logger.warning(f"No tweets found for @{username}")
                    # Try alternative method if Nitter fails
                    return await self._scrape_from_twstalker(username, max_results)
                
                for tweet in tweets[:max_results]:
                    try:
                        # Extract tweet text
                        text_elem = tweet.find('p', {'class': 'tweet-text'})
                        if not text_elem:
                            continue
                        
                        content = text_elem.get_text(strip=True)
                        
                        # Extract tweet metadata
                        time_elem = tweet.find('span', {'class': 'tweet-date'})
                        tweet_id = tweet.get('id', f'tweet_{len(posts)}')
                        
                        # Try to extract engagement metrics
                        stats = tweet.find('div', {'class': 'tweet-stats'})
                        likes = 0
                        retweets = 0
                        replies = 0
                        
                        if stats:
                            stat_items = stats.find_all('span', {'class': 'stat'})
                            # Nitter shows: replies, retweets, likes
                            if len(stat_items) >= 3:
                                try:
                                    replies = int(stat_items[0].get_text().split()[0])
                                    retweets = int(stat_items[1].get_text().split()[0])
                                    likes = int(stat_items[2].get_text().split()[0])
                                except:
                                    pass
                        
                        # Skip empty tweets
                        if not content or len(content) < 5:
                            continue
                        
                        post = Post(
                            id=tweet_id,
                            content=content,
                            author=username,
                            source=PostSource.X_TWITTER,
                            created_at=datetime.now(),
                            url=f"https://twitter.com/{username}",
                            engagement={
                                "likes": likes,
                                "retweets": retweets,
                                "replies": replies,
                            }
                        )
                        posts.append(post)
                        
                    except Exception as e:
                        logger.debug(f"Error parsing tweet: {str(e)}")
                        continue
                
                logger.info(f"✅ Scraped {len(posts)} tweets from @{username}")
                self.last_scraped[username] = datetime.now()
                return posts

        except asyncio.TimeoutError:
            logger.warning(f"Timeout scraping @{username}")
            return []
        except Exception as e:
            logger.error(f"Error scraping @{username}: {str(e)}")
            return []

    async def _scrape_from_twstalker(self, username: str, max_results: int) -> List[Post]:
        """
        Fallback method: Dùng twstalker.com (nếu Nitter fail)
        """
        try:
            session = await self._get_session()
            
            # Twstalker API (free)
            twstalker_url = f"https://twstalker.com/profile/{username}"
            
            logger.info(f"Trying fallback: Twstalker for @{username}...")
            
            async with session.get(twstalker_url, headers=self.headers, timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"Twstalker also failed for @{username}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                posts = []
                
                # Twstalker structure varies, try to find tweet containers
                tweets = soup.find_all('div', {'class': ['tweet', 'status', 'tweet-item']})
                
                for tweet in tweets[:max_results]:
                    try:
                        text_elem = tweet.find(['p', 'span'], {'class': ['text', 'tweet-text', 'content']})
                        if not text_elem:
                            continue
                        
                        content = text_elem.get_text(strip=True)
                        
                        if not content or len(content) < 5:
                            continue
                        
                        post = Post(
                            id=f'tweet_{len(posts)}',
                            content=content,
                            author=username,
                            source=PostSource.X_TWITTER,
                            created_at=datetime.now(),
                            url=f"https://twitter.com/{username}",
                            engagement={"likes": 0, "retweets": 0, "replies": 0}
                        )
                        posts.append(post)
                    except:
                        continue
                
                logger.info(f"✅ Scraped {len(posts)} tweets from @{username} (Twstalker)")
                return posts
                
        except Exception as e:
            logger.error(f"Twstalker fallback failed: {str(e)}")
            return []

    async def scrape_all_accounts(self) -> List[Post]:
        """Cào tweets từ tất cả accounts"""
        all_posts = []
        
        for account in self.target_accounts:
            posts = await self.scrape_user_tweets(account, max_results=5)
            all_posts.extend(posts)
            
            # Add random delay giữa các requests
            await asyncio.sleep(random.uniform(2, 5))

        return all_posts

    async def close(self):
        """Đóng session"""
        if self.client:
            await self.client.aclose()

    def get_status(self) -> str:
        """Get scraper status"""
        status = "📊 Scraper Status:\n"
        status += f"  Accounts: {', '.join(self.target_accounts)}\n"
        status += f"  Method: Web Scraping (NO API KEY)\n"
        status += f"  Source: Nitter.net (Twitter mirror)\n"
        status += f"  Cost: FREE ✅\n"
        
        for account, last_time in self.last_scraped.items():
            time_ago = datetime.now() - last_time
            status += f"  Last scraped @{account}: {time_ago.total_seconds()/60:.0f} minutes ago\n"
        
        return status


async def test_scraper():
    """Test web scraper"""
    import json
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    x_accounts_str = os.getenv("X_ACCOUNTS", '["@twitter"]')
    accounts = json.loads(x_accounts_str)
    
    if not accounts:
        print("❌ X_ACCOUNTS not set in .env")
        return
    
    try:
        scraper = WebScraperAgent(accounts)
        
        print(f"✓ Web Scraper initialized")
        print(f"✓ Target accounts: {accounts}")
        print(f"✓ Testing web scraping (NO API KEY NEEDED)...")
        
        posts = await scraper.scrape_all_accounts()
        
        print(f"✓ Fetched {len(posts)} posts total")
        
        if posts:
            print(f"\n📝 Sample posts:")
            for i, post in enumerate(posts[:3], 1):
                print(f"\n  {i}. [@{post.author}]")
                print(f"     Content: {post.content[:100]}...")
                print(f"     Engagement: {post.engagement}")
        else:
            print("⚠️  No posts returned (account may be restricted)")
        
        print(f"\n{scraper.get_status()}")
        
        await scraper.close()
        print("\n✅ Web Scraper Agent test completed")
        
    except Exception as e:
        print(f"❌ Scraper test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_scraper())
