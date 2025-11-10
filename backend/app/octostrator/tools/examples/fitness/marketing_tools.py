"""Marketing Agent Tools

SNS 게시물 관리, 마케팅 이벤트 관리 관련 도구들
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from backend.database.relation_db.models import SocialMediaPost, Event
from backend.database.relation_db.session import get_db
import logging
import json

logger = logging.getLogger(__name__)


# ==================== Social Media Post Tools ====================

async def create_social_post(
    platform: str,
    content: str,
    media_urls: Optional[List[str]] = None,
    hashtags: Optional[List[str]] = None,
    scheduled_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """SNS 게시물 생성

    Args:
        platform: 플랫폼 (instagram, facebook, blog, youtube)
        content: 게시물 내용
        media_urls: 미디어 URL 목록
        hashtags: 해시태그 목록
        scheduled_time: 예약 시간

    Returns:
        생성된 SNS 게시물 정보
    """
    try:
        # Convert lists to JSON strings
        media_urls_json = json.dumps(media_urls) if media_urls else None
        hashtags_str = ",".join(hashtags) if hashtags else ""

        # Determine status based on scheduled_time
        status = "scheduled" if scheduled_time else "draft"

        with get_db() as db:
            post = SocialMediaPost(
                platform=platform,
                content=content,
                media_urls=media_urls_json,
                hashtags=hashtags_str,
                scheduled_time=scheduled_time,
                status=status
            )
            db.add(post)
            db.commit()
            db.refresh(post)

            logger.info(f"[Marketing] Social media post created for {platform}: Post ID {post.id}")

            return {
                "success": True,
                "post_id": post.id,
                "platform": platform,
                "status": status,
                "content": content[:100] + "..." if len(content) > 100 else content,
                "scheduled_time": scheduled_time.isoformat() if scheduled_time else None,
                "created_at": post.created_at.isoformat()
            }
    except Exception as e:
        logger.error(f"[Marketing] Failed to create social media post: {e}")
        return {"success": False, "error": str(e)}


async def schedule_post(
    post_id: int,
    scheduled_time: datetime
) -> Dict[str, Any]:
    """SNS 게시물 예약

    Args:
        post_id: 게시물 ID
        scheduled_time: 예약 시간

    Returns:
        예약된 게시물 정보
    """
    try:
        with get_db() as db:
            post = db.query(SocialMediaPost).filter(
                SocialMediaPost.id == post_id
            ).first()

            if not post:
                return {"success": False, "error": f"Post with ID {post_id} not found"}

            post.scheduled_time = scheduled_time
            post.status = "scheduled"
            db.commit()
            db.refresh(post)

            logger.info(f"[Marketing] Post {post_id} scheduled for {scheduled_time}")

            return {
                "success": True,
                "post_id": post.id,
                "platform": post.platform,
                "status": post.status,
                "scheduled_time": scheduled_time.isoformat(),
                "content": post.content[:100] + "..." if len(post.content) > 100 else post.content
            }
    except Exception as e:
        logger.error(f"[Marketing] Failed to schedule post {post_id}: {e}")
        return {"success": False, "error": str(e)}


async def publish_post(post_id: int) -> Dict[str, Any]:
    """SNS 게시물 즉시 발행

    Args:
        post_id: 게시물 ID

    Returns:
        발행된 게시물 정보
    """
    try:
        with get_db() as db:
            post = db.query(SocialMediaPost).filter(
                SocialMediaPost.id == post_id
            ).first()

            if not post:
                return {"success": False, "error": f"Post with ID {post_id} not found"}

            post.status = "posted"
            post.posted_time = datetime.now()
            db.commit()
            db.refresh(post)

            logger.info(f"[Marketing] Post {post_id} published on {post.platform}")

            return {
                "success": True,
                "post_id": post.id,
                "platform": post.platform,
                "status": post.status,
                "posted_time": post.posted_time.isoformat(),
                "content": post.content[:100] + "..." if len(post.content) > 100 else post.content
            }
    except Exception as e:
        logger.error(f"[Marketing] Failed to publish post {post_id}: {e}")
        return {"success": False, "error": str(e)}


async def get_posts(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """SNS 게시물 조회

    Args:
        platform: 플랫폼 필터 (instagram, facebook, blog, youtube)
        status: 상태 필터 (draft, scheduled, posted, failed)
        limit: 조회 개수 제한

    Returns:
        SNS 게시물 목록
    """
    try:
        with get_db() as db:
            query = db.query(SocialMediaPost)

            if platform:
                query = query.filter(SocialMediaPost.platform == platform)
            if status:
                query = query.filter(SocialMediaPost.status == status)

            posts = query.order_by(SocialMediaPost.created_at.desc()).limit(limit).all()

            posts_list = []
            for post in posts:
                # Parse JSON fields
                media_urls = json.loads(post.media_urls) if post.media_urls else []
                engagement = json.loads(post.engagement_metrics) if post.engagement_metrics else {}

                posts_list.append({
                    "post_id": post.id,
                    "platform": post.platform,
                    "content": post.content[:100] + "..." if len(post.content) > 100 else post.content,
                    "status": post.status,
                    "media_urls": media_urls,
                    "hashtags": post.hashtags,
                    "scheduled_time": post.scheduled_time.isoformat() if post.scheduled_time else None,
                    "posted_time": post.posted_time.isoformat() if post.posted_time else None,
                    "engagement_metrics": engagement,
                    "created_at": post.created_at.isoformat()
                })

            logger.info(f"[Marketing] Retrieved {len(posts_list)} social media posts")

            return {
                "success": True,
                "count": len(posts_list),
                "posts": posts_list
            }
    except Exception as e:
        logger.error(f"[Marketing] Failed to retrieve posts: {e}")
        return {"success": False, "error": str(e)}


async def update_post_engagement(
    post_id: int,
    likes: int,
    comments: int,
    shares: int
) -> Dict[str, Any]:
    """SNS 게시물 참여도 업데이트

    Args:
        post_id: 게시물 ID
        likes: 좋아요 수
        comments: 댓글 수
        shares: 공유 수

    Returns:
        업데이트된 게시물 정보
    """
    try:
        with get_db() as db:
            post = db.query(SocialMediaPost).filter(
                SocialMediaPost.id == post_id
            ).first()

            if not post:
                return {"success": False, "error": f"Post with ID {post_id} not found"}

            # Create engagement metrics JSON
            engagement_metrics = {
                "likes": likes,
                "comments": comments,
                "shares": shares
            }

            post.engagement_metrics = json.dumps(engagement_metrics)
            db.commit()
            db.refresh(post)

            logger.info(f"[Marketing] Engagement metrics updated for post {post_id}: {engagement_metrics}")

            return {
                "success": True,
                "post_id": post.id,
                "platform": post.platform,
                "engagement_metrics": engagement_metrics,
                "content": post.content[:100] + "..." if len(post.content) > 100 else post.content
            }
    except Exception as e:
        logger.error(f"[Marketing] Failed to update engagement metrics for post {post_id}: {e}")
        return {"success": False, "error": str(e)}


# ==================== Event Management Tools ====================

async def create_event(
    title: str,
    description: str,
    event_type: str,
    start_date: datetime,
    end_date: datetime,
    target_audience: str,
    budget: float
) -> Dict[str, Any]:
    """마케팅 이벤트 생성

    Args:
        title: 이벤트 제목
        description: 이벤트 설명
        event_type: 이벤트 유형 (promotion, challenge, workshop, open_house)
        start_date: 시작 날짜
        end_date: 종료 날짜
        target_audience: 대상 고객 (new_members, existing, prospects)
        budget: 예산

    Returns:
        생성된 이벤트 정보
    """
    try:
        with get_db() as db:
            event = Event(
                title=title,
                description=description,
                event_type=event_type,
                start_date=start_date,
                end_date=end_date,
                target_audience=target_audience,
                budget=budget,
                participants=json.dumps([]),  # Initialize empty participants list
                status="planned"
            )
            db.add(event)
            db.commit()
            db.refresh(event)

            logger.info(f"[Marketing] Event created: {title} (ID: {event.id})")

            return {
                "success": True,
                "event_id": event.id,
                "title": title,
                "event_type": event_type,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "status": event.status,
                "budget": budget,
                "created_at": event.created_at.isoformat()
            }
    except Exception as e:
        logger.error(f"[Marketing] Failed to create event: {e}")
        return {"success": False, "error": str(e)}


async def get_events(
    status: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """마케팅 이벤트 조회

    Args:
        status: 상태 필터 (planned, active, completed, cancelled)
        limit: 조회 개수 제한

    Returns:
        마케팅 이벤트 목록
    """
    try:
        with get_db() as db:
            query = db.query(Event)

            if status:
                query = query.filter(Event.status == status)

            events = query.order_by(Event.start_date.desc()).limit(limit).all()

            events_list = []
            for event in events:
                # Parse participants JSON
                participants = json.loads(event.participants) if event.participants else []

                events_list.append({
                    "event_id": event.id,
                    "title": event.title,
                    "event_type": event.event_type,
                    "start_date": event.start_date.isoformat(),
                    "end_date": event.end_date.isoformat(),
                    "status": event.status,
                    "target_audience": event.target_audience,
                    "participants_count": len(participants),
                    "budget": event.budget,
                    "revenue": event.revenue,
                    "created_at": event.created_at.isoformat()
                })

            logger.info(f"[Marketing] Retrieved {len(events_list)} events")

            return {
                "success": True,
                "count": len(events_list),
                "events": events_list
            }
    except Exception as e:
        logger.error(f"[Marketing] Failed to retrieve events: {e}")
        return {"success": False, "error": str(e)}


async def update_event_status(
    event_id: int,
    status: str,
    revenue: Optional[float] = None
) -> Dict[str, Any]:
    """이벤트 상태 업데이트

    Args:
        event_id: 이벤트 ID
        status: 새로운 상태 (planned, active, completed, cancelled)
        revenue: 이벤트 수익 (선택사항)

    Returns:
        업데이트된 이벤트 정보
    """
    try:
        with get_db() as db:
            event = db.query(Event).filter(Event.id == event_id).first()

            if not event:
                return {"success": False, "error": f"Event with ID {event_id} not found"}

            event.status = status
            if revenue is not None:
                event.revenue = revenue

            db.commit()
            db.refresh(event)

            logger.info(f"[Marketing] Event {event_id} status updated to {status}")

            return {
                "success": True,
                "event_id": event.id,
                "title": event.title,
                "status": event.status,
                "budget": event.budget,
                "revenue": event.revenue,
                "start_date": event.start_date.isoformat(),
                "end_date": event.end_date.isoformat()
            }
    except Exception as e:
        logger.error(f"[Marketing] Failed to update event {event_id}: {e}")
        return {"success": False, "error": str(e)}


async def add_event_participant(
    event_id: int,
    user_id: int
) -> Dict[str, Any]:
    """이벤트에 참가자 추가

    Args:
        event_id: 이벤트 ID
        user_id: 사용자 ID

    Returns:
        업데이트된 이벤트 정보
    """
    try:
        with get_db() as db:
            event = db.query(Event).filter(Event.id == event_id).first()

            if not event:
                return {"success": False, "error": f"Event with ID {event_id} not found"}

            # Parse current participants
            participants = json.loads(event.participants) if event.participants else []

            # Add participant if not already in list
            if user_id not in participants:
                participants.append(user_id)
                event.participants = json.dumps(participants)
                db.commit()
                db.refresh(event)
                logger.info(f"[Marketing] User {user_id} added to event {event_id}")
            else:
                logger.info(f"[Marketing] User {user_id} is already a participant in event {event_id}")

            return {
                "success": True,
                "event_id": event.id,
                "title": event.title,
                "participants_count": len(participants),
                "user_id_added": user_id,
                "status": event.status
            }
    except Exception as e:
        logger.error(f"[Marketing] Failed to add participant to event {event_id}: {e}")
        return {"success": False, "error": str(e)}


__all__ = [
    "create_social_post",
    "schedule_post",
    "publish_post",
    "get_posts",
    "update_post_engagement",
    "create_event",
    "get_events",
    "update_event_status",
    "add_event_participant"
]
