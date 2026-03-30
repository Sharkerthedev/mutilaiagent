"""
Main Application Entry Point
Multi-Agent AI System cho cào và phân tích X/Twitter
Chạy trên Render (hoặc Hugging Face Spaces)
"""
import asyncio
import logging
import os
from dotenv import load_dotenv
from orchestrator import OrchestratorAgent

# Thêm thư viện web server
from aiohttp import web

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('multi_agent.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("Main")


def parse_x_accounts(env_var):
    """Parse X_ACCOUNTS từ biến môi trường dễ dàng."""
    if not env_var:
        return []
    # Loại bỏ khoảng trắng, dấu ngoặc, @
    env_var = env_var.strip()
    # Nếu có dấu phẩy
    if ',' in env_var:
        accounts = [a.strip().lstrip('@') for a in env_var.split(',') if a.strip()]
    # Nếu có dấu cách (cách nhau bằng khoảng trắng)
    elif ' ' in env_var:
        accounts = [a.strip().lstrip('@') for a in env_var.split() if a.strip()]
    # Nếu có dấu xuống dòng
    elif '\n' in env_var:
        accounts = [a.strip().lstrip('@') for a in env_var.split('\n') if a.strip()]
    else:
        # Có thể là một tên duy nhất
        accounts = [env_var.lstrip('@')] if env_var else []
    # Lọc bỏ rỗng
    accounts = [a for a in accounts if a]
    return accounts


def validate_environment():
    """Validate các biến môi trường cần thiết"""
    required_vars = [
        "DISCORD_TOKEN",
        "DISCORD_CHANNEL_ID",
        "GEMINI_API_KEY",
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        logger.error(f"Missing required variables: {', '.join(missing)}")
        logger.error("Please update your environment variables with these values")
        return False
    
    # Check X_ACCOUNTS – không bắt buộc nhưng cảnh báo nếu trống
    x_accounts_raw = os.getenv("X_ACCOUNTS", "")
    if not x_accounts_raw:
        logger.warning("X_ACCOUNTS not set. No accounts will be scraped.")
    else:
        accounts = parse_x_accounts(x_accounts_raw)
        if not accounts:
            logger.warning("No valid X accounts found in X_ACCOUNTS.")
        else:
            logger.info(f"✓ Loaded {len(accounts)} accounts: {', '.join(accounts)}")
    
    return True


async def handle_health(request):
    """Health check endpoint cho Render."""
    return web.Response(text="Bot is running")


async def start_web_server():
    """Chạy web server nhỏ trên cổng do Render cung cấp."""
    port = int(os.environ.get('PORT', 10000))
    app = web.Application()
    app.router.add_get('/', handle_health)
    app.router.add_get('/health', handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"✅ Web server started on port {port}")


async def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Multi-Agent AI System Starting")
    logger.info("=" * 60)
    
    # Validate environment
    if not validate_environment():
        logger.error("Environment validation failed. Exiting.")
        return
    
    # Khởi động web server trong nền
    asyncio.create_task(start_web_server())
    
    # Initialize Orchestrator
    orchestrator = OrchestratorAgent()
    
    try:
        logger.info("Initializing agents...")
        logger.info("- Scraper Agent (Web Scraping - NO API KEY)")
        logger.info("- Analyzer Agent (Gemini AI)")
        logger.info("- Content Creator Agent (SEO Optimized)")
        logger.info("")
        logger.info("Starting Discord bot and background tasks...")
        
        await orchestrator.start()
        
    except KeyboardInterrupt:
        logger.info("\nShutdown signal received")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
    finally:
        logger.info("Closing connections...")
        await orchestrator.close()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║   Multi-Agent AI System - X/Twitter Automation      ║
    ║   - Web Scraping (NO API KEY)                         ║
    ║   - Analyzer Agent (Gemini AI)                        ║
    ║   - Content Creator (SEO Optimized)                   ║
    ║   - Discord Integration (Real-time notifications)     ║
    ║   100% FREE - Unlimited Scraping                      ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())
