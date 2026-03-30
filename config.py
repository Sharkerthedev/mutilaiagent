"""
Configuration file cho Multi-Agent System
Các setting nâng cao có thể tuỳ chỉnh
"""
from dataclasses import dataclass
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ScraperConfig:
    """Cấu hình cho Scraper Agent"""
    # Số posts tối đa lấy từ một user
    max_posts_per_user: int = 10
    
    # Delay giữa các API call (tính bằng giây)
    rate_limit_delay: float = 1.0
    
    # Số lần retry khi API fail
    max_retries: int = 3
    
    # Timeout cho HTTP requests (giây)
    timeout: int = 30
    
    # Filter posts (optional)
    exclude_retweets: bool = True
    min_engagement_threshold: int = 0  # Minimum likes để include


@dataclass
class AnalyzerConfig:
    """Cấu hình cho Analyzer Agent"""
    # Max tokens cho Claude response
    max_tokens: int = 1500
    
    # Temperature (creativity level: 0-1)
    temperature: float = 0.7
    
    # Số topics tối đa để extract
    max_topics: int = 10
    
    # Ngôn ngữ phân tích
    language: str = "Vietnamese"
    
    # Loại sentiment được phân tích
    sentiment_types: List[str] = None
    
    def __post_init__(self):
        if self.sentiment_types is None:
            self.sentiment_types = ["positive", "negative", "neutral", "mixed"]


@dataclass
class ContentCreatorConfig:
    """Cấu hình cho Content Creator Agent"""
    # Max ký tự cho X post (280 là giới hạn)
    max_characters: int = 280
    
    # Temperature
    temperature: float = 0.8
    
    # Số biến thể content
    num_variations: int = 2
    
    # Include emoji hay không
    include_emoji: bool = True
    
    # Include hashtags hay không
    include_hashtags: bool = True
    
    # Số hashtags tối đa
    max_hashtags: int = 5
    
    # Tone of voice
    tone: str = "professional"  # professional, casual, funny, inspirational
    
    # Call-to-action
    include_cta: bool = True


@dataclass
class ScheduleConfig:
    """Cấu hình lịch trình"""
    # Giờ phân tích mỗi ngày (format 24h)
    analysis_times: List[str] = None
    
    # Interval scraping (phút)
    scrape_interval_minutes: int = 15
    
    # Timezone
    timezone: str = "Asia/Ho_Chi_Minh"
    
    # Ngày trong tuần để phân tích (0=Mon, 6=Sun)
    analysis_days: List[int] = None  # None = mỗi ngày
    
    def __post_init__(self):
        if self.analysis_times is None:
            self.analysis_times = ["09:00", "13:00", "17:00", "21:00"]
        if self.analysis_days is None:
            self.analysis_days = list(range(7))  # Mỗi ngày


@dataclass
class DiscordConfig:
    """Cấu hình Discord"""
    # Command prefix
    command_prefix: str = "!"
    
    # Gửi embed messages (fancy format)
    use_embeds: bool = True
    
    # Color cho embeds (hex)
    embed_color: int = 0x00FF00  # Green
    
    # Send separate messages cho mỗi component
    separate_messages: bool = False
    
    # Mention user khi có new content
    mention_on_update: bool = False


@dataclass
class APIConfig:
    """Cấu hình API"""
    # Model Claude sử dụng
    claude_model: str = "claude-3-5-sonnet-20241022"
    
    # Retry policy
    max_api_retries: int = 3
    retry_delay_seconds: int = 5
    
    # Timeout
    api_timeout: int = 60


class Config:
    """Main configuration class"""
    
    def __init__(self):
        self.scraper = ScraperConfig()
        self.analyzer = AnalyzerConfig()
        self.content_creator = ContentCreatorConfig()
        self.schedule = ScheduleConfig()
        self.discord = DiscordConfig()
        self.api = APIConfig()
        
        # Load từ environment nếu có
        self._load_from_env()
    
    def _load_from_env(self):
        """Load cấu hình từ environment variables"""
        import json
        
        # Analyzer
        if os.getenv("ANALYZER_MAX_TOKENS"):
            self.analyzer.max_tokens = int(os.getenv("ANALYZER_MAX_TOKENS"))
        
        # Content Creator
        if os.getenv("CONTENT_MAX_CHARS"):
            self.content_creator.max_characters = int(os.getenv("CONTENT_MAX_CHARS"))
        
        if os.getenv("CONTENT_TONE"):
            self.content_creator.tone = os.getenv("CONTENT_TONE")
        
        # Schedule
        if os.getenv("ANALYSIS_TIMES"):
            times_str = os.getenv("ANALYSIS_TIMES")
            try:
                self.schedule.analysis_times = json.loads(times_str)
            except:
                pass
        
        if os.getenv("READ_INTERVAL"):
            self.schedule.scrape_interval_minutes = int(os.getenv("READ_INTERVAL"))
        
        if os.getenv("TIMEZONE"):
            self.schedule.timezone = os.getenv("TIMEZONE")


# Global config instance
config = Config()

# Export config cho các modules
__all__ = [
    'config',
    'ScraperConfig',
    'AnalyzerConfig',
    'ContentCreatorConfig',
    'ScheduleConfig',
    'DiscordConfig',
    'APIConfig'
]


# Example usage:
if __name__ == "__main__":
    print("📋 Current Configuration:\n")
    print("🔍 Scraper:")
    print(f"  - Max posts per user: {config.scraper.max_posts_per_user}")
    print(f"  - Rate limit delay: {config.scraper.rate_limit_delay}s")
    print(f"  - Max retries: {config.scraper.max_retries}")
    
    print("\n📊 Analyzer:")
    print(f"  - Max tokens: {config.analyzer.max_tokens}")
    print(f"  - Temperature: {config.analyzer.temperature}")
    print(f"  - Language: {config.analyzer.language}")
    
    print("\n✍️  Content Creator:")
    print(f"  - Max characters: {config.content_creator.max_characters}")
    print(f"  - Tone: {config.content_creator.tone}")
    print(f"  - Max hashtags: {config.content_creator.max_hashtags}")
    
    print("\n⏰ Schedule:")
    print(f"  - Analysis times: {config.schedule.analysis_times}")
    print(f"  - Scrape interval: {config.schedule.scrape_interval_minutes} min")
    print(f"  - Timezone: {config.schedule.timezone}")
    
    print("\n💬 Discord:")
    print(f"  - Command prefix: {config.discord.command_prefix}")
    print(f"  - Use embeds: {config.discord.use_embeds}")
    
    print("\n🔗 API:")
    print(f"  - Claude model: {config.api.claude_model}")
    print(f"  - Max retries: {config.api.max_api_retries}")
