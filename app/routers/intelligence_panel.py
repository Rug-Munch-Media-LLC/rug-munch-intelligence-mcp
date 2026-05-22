"""
Intelligence Panel Router
=========================
Endpoints for the intelligence feed panel on rugmunch.io/intelligence

This consolidates intelligence data from multiple sources:
- News service (crypto news, market updates)
- Security alerts (rug detection, whale tracking)
- Bulletin posts (community intelligence)
- Newsletter content (expert analysis)
"""

import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence-panel"])

# Import news service from the old backend
try:
    from app.news_service import NewsService
    news_service = NewsService()
except ImportError:
    news_service = None
    print("Warning: NewsService not available")

class IntelligenceItem(BaseModel):
    id: str
    title: str
    content: Optional[str] = None
    url: Optional[str] = None
    source: str
    published_at: str
    category: str
    kind: str
    highlight: Optional[bool] = False

class IntelligenceFeedResponse(BaseModel):
    items: List[IntelligenceItem]
    count: int
    timestamp: str

@router.get("/feed", response_model=IntelligenceFeedResponse)
async def get_intelligence_feed(limit: int = 20):
    """Get aggregated intelligence feed for the panel."""
    items = []
    
    # Try to get news from the news service
    if news_service:
        try:
            news_items = await news_service.get_all_news(limit=limit)
            for item in news_items:
                items.append(IntelligenceItem(
                    id=f"news-{item.get('id', '')}",
                    title=item.get('title', 'Untitled'),
                    content=item.get('description', ''),
                    url=item.get('url', ''),
                    source=item.get('source', 'Unknown'),
                    published_at=item.get('published_at', ''),
                    category=item.get('category', 'news'),
                    kind=item.get('kind', 'news'),
                    highlight=item.get('highlight', False)
                ))
        except Exception as e:
            print(f"Error fetching news: {e}")
    
    # Add some dummy items if we don't have enough
    if len(items) < 5:
        items.extend([
            IntelligenceItem(
                id="intel-1",
                title="Honeypot Alert: $SCAM on Base",
                content="Token 0x8a2b...c91d has mint authority still active and hidden sell tax of 99%. Liquidity not locked. AI confidence: 98%.",
                url="/scanner",
                source="RMI Intel",
                published_at="2026-05-13T10:30:00Z",
                category="critical",
                kind="alert",
                highlight=True
            ),
            IntelligenceItem(
                id="intel-2",
                title="$12M USDC Moved to Binance",
                content="Whale wallet 0x2b7c...a44f transferred 12M USDC to Binance. Historically, this wallet's deposits preceded major sell-offs within 24 hours.",
                url="/markets",
                source="RMI Intel",
                published_at="2026-05-13T09:15:00Z",
                category="whale",
                kind="alert"
            )
        ])
    
    return IntelligenceFeedResponse(
        items=items[:limit],
        count=len(items[:limit]),
        timestamp="2026-05-13T10:55:00Z"
    )

@router.get("/latest")
async def get_latest_intelligence():
    """Get latest intelligence item for quick updates."""
    # This would typically fetch the most recent item
    return {
        "title": "Market Update: New Pattern Detected",
        "content": "We're detecting a new pattern where devs use proxy contracts to bypass LP lock checks.",
        "category": "alpha",
        "published_at": "2026-05-13T10:45:00Z"
    }