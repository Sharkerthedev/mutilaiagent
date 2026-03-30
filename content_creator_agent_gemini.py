"""
Content Creator Agent - Tạo content tối ưu SEO dùng Gemini (FREE)
Gemini Free Tier: 60 requests/minute, 1500/day
"""
import logging
import json
import asyncio
import time
from datetime import datetime
from typing import Optional
import google.generativeai as genai
from models import AnalysisResult, ContentData

logger = logging.getLogger("ContentCreatorAgent")


class ContentCreatorAgent:
    """Agent tạo content tối ưu SEO dùng Gemini API (FREE)"""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        """
        Args:
            api_key: Google Gemini API key (FREE)
            model: Model name
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.request_times = []

    async def _rate_limit_check(self):
        """Check and enforce rate limiting (60/min)"""
        now = time.time()
        # Remove requests outside 60-second window
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        if len(self.request_times) >= 59:  # Leave buffer
            sleep_time = 60 - (now - self.request_times[0])
            if sleep_time > 0:
                logger.warning(f"⏳ Rate limit approaching. Waiting {sleep_time:.1f}s...")
                await asyncio.sleep(sleep_time)
        
        self.request_times.append(now)

    async def create_content(
        self,
        analysis: AnalysisResult,
        max_chars: int = 280,
        include_variations: bool = True
    ) -> ContentData:
        """
        Tạo content tối ưu từ kết quả phân tích
        
        Args:
            analysis: AnalysisResult từ Analyzer Agent
            max_chars: Độ dài tối đa (X limit là 280)
            include_variations: Tạo nhiều biến thể
            
        Returns:
            ContentData với raw content và optimized content
        """
        
        # Bước 1: Tạo raw content từ analysis
        creation_prompt = f"""Bạn là một content creator chuyên viết bài viral trên X/Twitter.

Dựa trên phân tích sau:
- Tóm tắt: {analysis.summary}
- Chủ đề: {', '.join(analysis.key_topics)}
- Cảm tính: {analysis.sentiment}
- Khuyến nghị: {analysis.recommendations[0] if analysis.recommendations else 'Create engaging content'}

Hãy tạo một bài post hấp dẫn, ngắn gọn, có khả năng viral cao.

Yêu cầu:
1. Viết bài post chính (max 280 ký tự, không dấu hashtag)
2. Viết 1 biến thể thay thế khác
3. Gợi ý 3 hashtags phù hợp
4. Thêm emoji để tăng engagement

**IMPORTANT**: Trả lời CHỈ dưới dạng JSON:
{{
    "main_post": "Bài post chính (max 280 chars)",
    "variation": "Biến thể 1",
    "hashtags": ["#tag1", "#tag2", "#tag3"],
    "emojis": "😀🚀💡"
}}"""

        try:
            await self._rate_limit_check()
            
            logger.info("Gọi Gemini để tạo content...")
            
            response = self.model.generate_content(
                creation_prompt,
                generation_config={
                    "temperature": 0.8,
                    "max_output_tokens": 800,
                }
            )

            response_text = response.text
            
            # Extract JSON
            try:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    content_data = json.loads(json_str)
                else:
                    raise ValueError("No JSON found")
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Could not parse JSON: {str(e)}")
                content_data = {
                    "main_post": response_text[:280],
                    "variation": response_text[280:560] if len(response_text) > 280 else "Check main post",
                    "hashtags": ["#trending", "#content", "#viral"],
                    "emojis": "✨🔥"
                }

            raw_content = content_data.get("main_post", "")[:280]

            # Bước 2: SEO optimization
            seo_content = await self._optimize_seo(
                raw_content,
                analysis.key_topics,
                content_data.get("hashtags", [])
            )

            result = ContentData(
                original_analysis=analysis,
                raw_content=raw_content,
                seo_optimized=seo_content,
                hashtags=content_data.get("hashtags", []),
                created_at=datetime.now()
            )

            logger.info("✅ Content created and optimized")
            return result

        except Exception as e:
            logger.error(f"Error creating content: {str(e)}")
            return ContentData(
                original_analysis=analysis,
                raw_content="Content creation failed - please try again",
                seo_optimized="Content creation failed",
                hashtags=["#content", "#viral"],
                created_at=datetime.now()
            )

    async def _optimize_seo(
        self,
        content: str,
        keywords: list,
        hashtags: list
    ) -> str:
        """
        Optimize content cho SEO & engagement
        
        Args:
            content: Nội dung gốc
            keywords: Các keyword chính
            hashtags: Các hashtag
            
        Returns:
            Content được optimize
        """
        
        seo_prompt = f"""Bạn là chuyên gia SEO cho mạng xã hội X.

Content gốc: "{content}"
Keywords để tích hợp: {', '.join(keywords[:5])}
Hashtags: {' '.join(hashtags[:3])}

Hãy optimize:
1. Tích hợp 1-2 keywords tự nhiên
2. Giữ dưới 280 ký tự
3. Thêm 1-2 emoji hợp lý
4. Thêm hashtags ở cuối
5. Tăng engagement potential

**Trả lời chỉ nội dung được optimize, không giải thích:**"""

        try:
            await self._rate_limit_check()
            
            response = self.model.generate_content(
                seo_prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 300,
                }
            )

            optimized = response.text.strip()
            # Ensure under 280 chars
            if len(optimized) > 280:
                optimized = optimized[:277] + "..."
            
            return optimized

        except Exception as e:
            logger.error(f"Error optimizing SEO: {str(e)}")
            # Return with hashtags at least
            return f"{content} {' '.join(hashtags[:2])}"

    def format_content_for_preview(self, content: ContentData) -> str:
        """Format content để preview trên Discord"""
        message = f"""
**✍️ CONTENT ĐƯỢC TẠO LÚC {content.created_at.strftime('%H:%M:%S')}**

**📝 Bài post gốc:**
{content.raw_content}

**🎯 Bài post tối ưu SEO:**
{content.seo_optimized}

**#️⃣ Hashtags gợi ý:**
{' '.join(content.hashtags)}

---
**Ghi chú:** Bạn có thể copy trực tiếp hoặc chỉnh sửa trước khi đăng X.
*Powered by Google Gemini (Free)*
"""
        return message


async def test_content_creator():
    """Test content creator agent"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set")
        return
    
    test_analysis = AnalysisResult(
        raw_posts=[],
        summary="The tech industry is trending towards AI adoption. Remote work and digital transformation dominate.",
        key_topics=["AI", "automation", "tech", "startup"],
        sentiment="positive",
        recommendations=["Create AI content", "Engage tech community"],
        analyzed_at=datetime.now()
    )
    
    creator = ContentCreatorAgent(api_key=api_key)
    content = await creator.create_content(test_analysis)
    print(creator.format_content_for_preview(content))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # asyncio.run(test_content_creator())
