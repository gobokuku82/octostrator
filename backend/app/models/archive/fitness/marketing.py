"""Marketing Agent models - SocialMediaPost, Event"""
from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from datetime import datetime
from .base import Base


class SocialMediaPost(Base):
    """SNS 게시물 테이블 (Marketing Agent)"""
    __tablename__ = "social_media_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(50))  # instagram, facebook, blog, youtube
    content = Column(Text, nullable=False)
    media_urls = Column(Text)  # JSON: ["url1", "url2"]
    hashtags = Column(String(500))
    scheduled_time = Column(DateTime)
    posted_time = Column(DateTime)
    status = Column(String(20), default="draft")  # draft, scheduled, posted, failed
    engagement_metrics = Column(Text)  # JSON: {"likes": 120, "comments": 15, "shares": 8}
    created_at = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    """이벤트 테이블 (Marketing Agent)"""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    event_type = Column(String(50))  # promotion, challenge, workshop, open_house
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    target_audience = Column(String(100))  # new_members, existing, prospects
    participants = Column(Text)  # JSON: [user_ids]
    budget = Column(Float)
    revenue = Column(Float)
    status = Column(String(20), default="planned")  # planned, active, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
