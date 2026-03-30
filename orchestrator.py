"""
Orchestrator Agent - Điều phối tất cả agents
Giao tiếp với user qua Discord
Quản lý lịch trình và workflow
"""
import asyncio
import logging
import os
from datetime import datetime
import pytz
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from typing import List

from models import Post, ScheduleConfig
from scraper_agent import WebScraperAgent as ScraperAgent
from analyzer_agent_gemini import AnalyzerAgent
from content_creator_agent_gemini import ContentCreatorAgent

# Load environment variables
load_dotenv()

logger = logging.getLogger("OrchestratorAgent")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class OrchestratorAgent:
    """Agent điều phối toàn bộ hệ thống"""

    def __init__(self):
        """Khởi tạo Orchestrator"""
        self.discord_token = os.getenv("DISCORD_TOKEN")
        self.channel_id = int(os.getenv("DISCORD_CHANNEL_ID"))
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        # Parse target accounts
        import json
        x_accounts_str = os.getenv("X_ACCOUNTS", "[]")
        self.x_accounts = json.loads(x_accounts_str)
        
        # Parse schedule times
        schedule_times_str = os.getenv("ANALYSIS_TIMES", '["09:00", "13:00", "17:00", "21:00"]')
        self.analysis_times = json.loads(schedule_times_str)
        
        self.read_interval = int(os.getenv("READ_INTERVAL", 15))
        self.timezone = pytz.timezone(os.getenv("TIMEZONE", "Asia/Ho_Chi_Minh"))
        
        # Initialize agents
        self.scraper = ScraperAgent(self.x_accounts)
        self.analyzer = AnalyzerAgent(self.gemini_api_key)
        self.content_creator = ContentCreatorAgent(self.gemini_api_key)
        
        # Lưu trữ posts
        self.collected_posts: List[Post] = []
        
        # Discord bot setup
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        self.discord_channel = None
        
        # Setup events
        self._setup_bot_events()

    def _setup_bot_events(self):
        """Setup Discord bot events"""
        
        @self.bot.event
        async def on_ready():
            logger.info(f"Bot logged in as {self.bot.user}")
            self.discord_channel = self.bot.get_channel(self.channel_id)
            
            if self.discord_channel:
                await self.discord_channel.send(
                    "🤖 **Multi-Agent System Khởi động**\n"
                    f"⏱️ Đọc bài mỗi {self.read_interval} phút\n"
                    f"📊 Phân tích lúc: {', '.join(self.analysis_times)}\n"
                    f"🌍 Timezone: {self.timezone}\n"
                    f"👀 Theo dõi: {', '.join(self.x_accounts)}\n"
                    f"🌐 Dùng: Web Scraping (FREE, NO API KEY) ✨"
                )
            
            # Start background tasks
            self.scraper_loop.start()

        @self.bot.command(name="status")
        async def status_cmd(ctx):
            """Kiểm tra trạng thái hệ thống"""
            status_msg = f"""
**📈 TRẠNG THÁI HỆ THỐNG**
- Posts đã thu thập: {len(self.collected_posts)}
- Agents hoạt động: Scraper, Analyzer, Content Creator
- Khoảng cập nhật: {self.read_interval} phút
- Giờ phân tích: {', '.join(self.analysis_times)}
- Thời gian hiện tại: {datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S')}
            """
            await ctx.send(status_msg)

        @self.bot.command(name="analyze_now")
        async def analyze_now_cmd(ctx):
            """Phân tích ngay (không cần đợi giờ lên lịch)"""
            await ctx.send("⏳ Đang phân tích...")
            await self._analyze_and_create_content()

        @self.bot.command(name="posts")
        async def posts_cmd(ctx):
            """Xem posts đã thu thập"""
            if not self.collected_posts:
                await ctx.send("Chưa có posts được thu thập.")
                return
            
            msg = f"📝 **{len(self.collected_posts)} POSTS ĐÃ THU THẬP**\n\n"
            for i, post in enumerate(self.collected_posts[-10:], 1):
                msg += f"{i}. [{post.author}] {post.content[:50]}...\n"
            
            await ctx.send(msg)

        @self.bot.command(name="clear_posts")
        async def clear_posts_cmd(ctx):
            """Xóa posts đã lưu"""
            self.collected_posts.clear()
            await ctx.send("✅ Đã xóa tất cả posts.")

    @tasks.loop(minutes=15)
    async def scraper_loop(self):
        """Loop scraping mỗi 15 phút"""
        try:
            logger.info(f"Starting scrape at {datetime.now(self.timezone)}")
            posts = await self.scraper.scrape_all_accounts()
            
            if posts:
                self.collected_posts.extend(posts)
                logger.info(f"Collected {len(posts)} new posts. Total: {len(self.collected_posts)}")
                
                if self.discord_channel:
                    await self.discord_channel.send(
                        f"✅ Đã cào được {len(posts)} posts mới "
                        f"(Tổng: {len(self.collected_posts)})"
                    )
            else:
                logger.info("No new posts found")

        except Exception as e:
            logger.error(f"Error in scraper loop: {str(e)}")
            if self.discord_channel:
                await self.discord_channel.send(f"❌ Lỗi scraping: {str(e)}")

    @scraper_loop.before_loop
    async def before_scraper_loop(self):
        """Chờ bot ready trước khi start loop"""
        await self.bot.wait_until_ready()

    async def _check_and_analyze(self):
        """Check xem có phải giờ phân tích không"""
        now = datetime.now(self.timezone)
        current_time = now.strftime("%H:%M")
        
        if current_time in self.analysis_times:
            await self._analyze_and_create_content()

    async def _analyze_and_create_content(self):
        """Phân tích posts và tạo content"""
        if not self.collected_posts:
            logger.warning("No posts to analyze")
            if self.discord_channel:
                await self.discord_channel.send("⚠️ Không có posts để phân tích. Vui lòng chờ...")
            return

        try:
            # Phân tích
            logger.info("Starting analysis...")
            analysis = await self.analyzer.analyze_posts(self.collected_posts)
            
            if self.discord_channel:
                await self.discord_channel.send(
                    self.analyzer.format_analysis_for_discord(analysis)
                )

            # Tạo content
            logger.info("Creating content...")
            content = await self.content_creator.create_content(analysis)
            
            if self.discord_channel:
                await self.discord_channel.send(
                    self.content_creator.format_content_for_preview(content)
                )

            # Clear posts sau phân tích
            self.collected_posts.clear()
            logger.info("Analysis and content creation completed")

        except Exception as e:
            logger.error(f"Error in analysis: {str(e)}")
            if self.discord_channel:
                await self.discord_channel.send(f"❌ Lỗi phân tích: {str(e)}")

    async def start(self):
        """Khởi động Orchestrator"""
        logger.info("Starting Orchestrator Agent")
        
        # Run bot và scheduler concurrently
        await self.bot.start(self.discord_token)

    async def close(self):
        """Đóng kết nối"""
        await self.scraper.close()
        await self.bot.close()


async def main():
    """Main function"""
    orchestrator = OrchestratorAgent()
    
    try:
        await orchestrator.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await orchestrator.close()


if __name__ == "__main__":
    asyncio.run(main())
