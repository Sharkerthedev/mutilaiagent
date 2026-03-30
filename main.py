"""
Main Application Entry Point
Multi-Agent AI System cho cào và phân tích X/Twitter
Chạy trên Hugging Face Spaces
"""
import asyncio
import logging
import os
from dotenv import load_dotenv
from orchestrator import OrchestratorAgent
from x_accounts_parser import get_x_accounts

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
        logger.error("Please update your .env file with these values")
        return False
    
    # Check X_ACCOUNTS using easy parser
    x_accounts = get_x_accounts()
    if not x_accounts:
        logger.error("No valid X accounts configured")
        logger.error("Set X_ACCOUNTS in .env using one of these formats:")
        logger.error('  X_ACCOUNTS="elonmusk sama karpathy"')
        logger.error('  X_ACCOUNTS="@elonmusk, @sama, @karpathy"')
        logger.error('  X_ACCOUNTS="elonmusk\\nsama\\nkarpathy"')
        return False
    
    return True


async def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Multi-Agent AI System Starting")
    logger.info("=" * 60)
    
    # Validate environment
    if not validate_environment():
        return
    
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
