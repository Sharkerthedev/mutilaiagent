"""
Models cho Multi-Agent AI System
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum


class PostSource(str, Enum):
    """Nguồn bài viết"""
    X_TWITTER = "x_twitter"
    DISCORD = "discord"


class Post(BaseModel):
    """Model cho một bài viết"""
    id: str
    content: str
    author: str
    source: PostSource
    created_at: datetime
    url: Optional[str] = None
    engagement: Optional[dict] = None  # likes, retweets, replies


class AnalysisResult(BaseModel):
    """Kết quả phân tích từ Analyzer Agent"""
    raw_posts: List[Post]
    summary: str
    key_topics: List[str]
    sentiment: str  # positive, negative, neutral
    recommendations: List[str]
    analyzed_at: datetime


class ContentData(BaseModel):
    """Dữ liệu content đã được tạo"""
    original_analysis: AnalysisResult
    raw_content: str  # Content sau phân tích
    seo_optimized: str  # Content sau SEO optimize
    hashtags: List[str]
    created_at: datetime


class AgentMessage(BaseModel):
    """Thông điệp giữa các agents"""
    sender: str
    receiver: str
    message_type: str  # "post_collection", "analysis", "content_creation"
    payload: dict
    timestamp: datetime


class ScheduleConfig(BaseModel):
    """Cấu hình lịch trình"""
    analysis_times: List[str]  # ["09:00", "13:00", "17:00", "21:00"]
    read_interval: int  # 15 phút
    timezone: str  # "Asia/Ho_Chi_Minh"
