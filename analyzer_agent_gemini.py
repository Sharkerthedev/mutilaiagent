"""
Analyzer Agent - Sử dụng Google Gemini API (FREE)
Phân tích và tổng hợp dữ liệu từ posts
Chạy theo lịch: 9h, 13h, 17h, 21h

Gemini Free Tier:
- 60 requests/minute
- 1500 requests/day
- No credit card required
Lấy key: https://aistudio.google.com/app/apikeys
"""
import logging
import json
import asyncio
import time
from datetime import datetime
from typing import List
import google.generativeai as genai
from models import Post, AnalysisResult

logger = logging.getLogger("AnalyzerAgent")


class RateLimiter:
    """Rate limiter cho Gemini API (60 req/min)"""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
    
    async def wait_if_needed(self):
        """Chờ nếu vượt quá rate limit"""
        now = time.time()
        # Remove old requests outside window
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.window_seconds]
        
        if len(self.requests) >= self.max_requests:
            sleep_time = self.window_seconds - (now - self.requests[0])
            if sleep_time > 0:
                logger.warning(f"⏳ Rate limit reached. Waiting {sleep_time:.1f}s...")
                await asyncio.sleep(sleep_time)
        
        self.requests.append(now)


class AnalyzerAgent:
    """Agent phân tích posts dùng Gemini API (FREE)"""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        """
        Args:
            api_key: Google Gemini API key (FREE)
            model: Model name (gemini-1.5-flash, gemini-1.5-pro)
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.rate_limiter = RateLimiter(max_requests=60, window_seconds=60)
        self.conversation_history = []

    def _prepare_posts_text(self, posts: List[Post]) -> str:
        """Chuẩn bị text từ posts để phân tích"""
        if not posts:
            return "Không có posts để phân tích."

        posts_text = f"Có {len(posts)} posts để phân tích:\n\n"
        
        for i, post in enumerate(posts, 1):
            posts_text += f"{i}. [{post.author}] ({post.created_at.strftime('%Y-%m-%d %H:%M')})\n"
            posts_text += f"   Content: {post.content}\n"
            if post.engagement:
                posts_text += f"   Engagement: {post.engagement['likes']} likes, {post.engagement['retweets']} retweets\n"
            posts_text += "\n"

        return posts_text

    async def analyze_posts(self, posts: List[Post]) -> AnalysisResult:
        """
        Phân tích một tập hợp posts dùng Gemini
        
        Args:
            posts: Danh sách Post objects
            
        Returns:
            AnalysisResult với summary, topics, sentiment, recommendations
        """
        posts_text = self._prepare_posts_text(posts)

        # Prompt cho Gemini để phân tích
        analysis_prompt = f"""Bạn là một chuyên gia phân tích xu hướng mạng xã hội và nội dung.

{posts_text}

Hãy phân tích những posts trên và cung cấp:
1. Tóm tắt chính (2-3 dòng): Các chủ đề chính được nhắc đến
2. Danh sách các chủ đề chính (5-10 topics)
3. Tổng thể cảm tính: positive, negative, hay neutral
4. 3-5 khuyến nghị để tạo content hấp dẫn dựa trên các trends này

**IMPORTANT**: Trả lời CHỈ dưới dạng JSON, không cần giải thích thêm:
{{
    "summary": "Tóm tắt chính",
    "key_topics": ["topic1", "topic2", ...],
    "sentiment": "positive/negative/neutral",
    "recommendations": ["rec1", "rec2", ...]
}}"""

        try:
            # Chờ nếu vượt rate limit
            await self.rate_limiter.wait_if_needed()
            
            logger.info(f"Gọi Gemini API để phân tích {len(posts)} posts...")
            
            # Call Gemini API
            response = self.model.generate_content(
                analysis_prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 1000,
                }
            )

            response_text = response.text
            
            logger.debug(f"Gemini response: {response_text[:200]}...")
            
            # Extract JSON từ response
            try:
                # Tìm JSON trong response
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    analysis_data = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in response")
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Could not parse JSON response: {str(e)}")
                logger.warning(f"Full response: {response_text}")
                analysis_data = {
                    "summary": response_text[:300],
                    "key_topics": ["general_trends", "engagement", "content"],
                    "sentiment": "neutral",
                    "recommendations": ["Create engaging content based on trends"]
                }

            result = AnalysisResult(
                raw_posts=posts,
                summary=analysis_data.get("summary", ""),
                key_topics=analysis_data.get("key_topics", []),
                sentiment=analysis_data.get("sentiment", "neutral"),
                recommendations=analysis_data.get("recommendations", []),
                analyzed_at=datetime.now()
            )

            logger.info(f"✅ Analysis completed: {len(posts)} posts analyzed")
            return result

        except Exception as e:
            logger.error(f"Error analyzing posts: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            
            # Return default result on error
            return AnalysisResult(
                raw_posts=posts,
                summary="Analysis failed - using fallback analysis",
                key_topics=["trending", "engagement", "content"],
                sentiment="neutral",
                recommendations=[
                    "Create content around trending topics",
                    "Engage with community",
                    "Post during peak hours"
                ],
                analyzed_at=datetime.now()
            )

    def format_analysis_for_discord(self, analysis: AnalysisResult) -> str:
        """Format kết quả phân tích để gửi lên Discord"""
        message = f"""
**📊 PHÂN TÍCH LÚC {analysis.analyzed_at.strftime('%H:%M:%S')}**

**Tóm tắt:**
{analysis.summary}

**Chủ đề chính:**
{', '.join(analysis.key_topics[:5])}

**Cảm tính chung:** {analysis.sentiment.upper()}

**💡 Khuyến nghị cho content:**
"""
        for i, rec in enumerate(analysis.recommendations, 1):
            message += f"{i}. {rec}\n"

        message += "\n✨ *Powered by Google Gemini (Free)*"
        return message


async def test_analyzer():
    """Test analyzer agent với Gemini"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set")
        return
    
    test_posts = [
        Post(
            id="1",
            content="AI is revolutionizing everything. Machine learning models are getting smarter each day.",
            author="@tech_news",
            source="x_twitter",
            created_at=datetime.now(),
            engagement={"likes": 100, "retweets": 50, "replies": 20}
        ),
        Post(
            id="2",
            content="Just launched our AI-powered analytics platform. 10x faster insights!",
            author="@startup_ceo",
            source="x_twitter",
            created_at=datetime.now(),
            engagement={"likes": 200, "retweets": 80, "replies": 40}
        )
    ]

    analyzer = AnalyzerAgent(api_key=api_key)
    analysis = await analyzer.analyze_posts(test_posts)
    print(analyzer.format_analysis_for_discord(analysis))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # asyncio.run(test_analyzer())
