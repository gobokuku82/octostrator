"""ExecutionCache - 실행 결과 캐시 관리

동일한 입력에 대한 실행 결과를 캐싱하여
중복 실행을 방지하고 성능을 향상시킵니다.
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from threading import Lock
from hashlib import md5
import json
import logging

logger = logging.getLogger(__name__)


class CacheEntry:
    """캐시 엔트리

    Attributes:
        key: 캐시 키
        value: 캐시된 값
        created_at: 생성 시간
        expires_at: 만료 시간
        hit_count: 조회 횟수
    """

    def __init__(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600,
    ):
        self.key = key
        self.value = value
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=ttl_seconds)
        self.hit_count = 0

    def is_expired(self) -> bool:
        """만료 여부 확인"""
        return datetime.now() > self.expires_at

    def hit(self) -> Any:
        """캐시 히트 (조회 횟수 증가)"""
        self.hit_count += 1
        return self.value

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "key": self.key,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "hit_count": self.hit_count,
            "is_expired": self.is_expired(),
        }


class ExecutionCache:
    """실행 결과 캐시 (싱글톤)

    Example:
        ```python
        cache = get_execution_cache()

        # 캐시 키 생성
        key = cache.make_key("collector", {"keyword": "라네즈", "limit": 10})

        # 캐시 조회
        result = cache.get(key)
        if result is None:
            # 실행 및 캐싱
            result = collector.execute(...)
            cache.set(key, result, ttl_seconds=3600)
        ```
    """

    _instance: Optional["ExecutionCache"] = None
    _lock: Lock = Lock()

    # 기본 설정
    DEFAULT_TTL = 3600  # 1시간
    MAX_ENTRIES = 1000  # 최대 캐시 엔트리 수

    def __new__(cls) -> "ExecutionCache":
        """싱글톤 인스턴스 생성"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """캐시 초기화"""
        if self._initialized:
            return

        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }
        self._initialized = True
        logger.info("ExecutionCache initialized")

    def make_key(self, tool_name: str, params: Dict[str, Any]) -> str:
        """캐시 키 생성

        Args:
            tool_name: 도구 이름
            params: 실행 파라미터

        Returns:
            캐시 키 (MD5 해시)
        """
        # 파라미터를 정렬된 JSON으로 직렬화
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        key_input = f"{tool_name}:{sorted_params}"

        # MD5 해시 생성
        return md5(key_input.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """캐시 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 또는 None (만료/미존재 시)
        """
        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None

            entry = self._cache[key]

            if entry.is_expired():
                # 만료된 엔트리 제거
                del self._cache[key]
                self._stats["misses"] += 1
                logger.debug(f"Cache expired: {key[:8]}...")
                return None

            self._stats["hits"] += 1
            return entry.hit()

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = None,
    ) -> None:
        """캐시 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl_seconds: TTL (기본: DEFAULT_TTL)
        """
        if ttl_seconds is None:
            ttl_seconds = self.DEFAULT_TTL

        with self._lock:
            # 최대 엔트리 수 초과 시 정리
            if len(self._cache) >= self.MAX_ENTRIES:
                self._evict_expired()

                # 여전히 초과하면 가장 오래된 엔트리 제거
                if len(self._cache) >= self.MAX_ENTRIES:
                    self._evict_oldest()

            entry = CacheEntry(key, value, ttl_seconds)
            self._cache[key] = entry
            logger.debug(f"Cache set: {key[:8]}... (TTL: {ttl_seconds}s)")

    def get_or_execute(
        self,
        key: str,
        executor_func,
        ttl_seconds: int = None,
    ) -> Tuple[Any, bool]:
        """캐시 조회 또는 실행

        Args:
            key: 캐시 키
            executor_func: 실행 함수 (캐시 미스 시 호출)
            ttl_seconds: TTL

        Returns:
            (결과 값, 캐시 히트 여부) 튜플
        """
        result = self.get(key)
        if result is not None:
            return result, True

        # 캐시 미스: 실행 및 캐싱
        result = executor_func()
        self.set(key, result, ttl_seconds)
        return result, False

    async def async_get_or_execute(
        self,
        key: str,
        executor_func,
        ttl_seconds: int = None,
    ) -> Tuple[Any, bool]:
        """캐시 조회 또는 비동기 실행

        Args:
            key: 캐시 키
            executor_func: 비동기 실행 함수
            ttl_seconds: TTL

        Returns:
            (결과 값, 캐시 히트 여부) 튜플
        """
        result = self.get(key)
        if result is not None:
            return result, True

        # 캐시 미스: 비동기 실행 및 캐싱
        result = await executor_func()
        self.set(key, result, ttl_seconds)
        return result, False

    def invalidate(self, key: str) -> bool:
        """캐시 무효화

        Args:
            key: 캐시 키

        Returns:
            무효화 성공 여부
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache invalidated: {key[:8]}...")
                return True
            return False

    def invalidate_by_tool(self, tool_name: str) -> int:
        """도구별 캐시 무효화

        Args:
            tool_name: 도구 이름

        Returns:
            무효화된 엔트리 수
        """
        # 주의: 키가 해시이므로 도구 이름으로 직접 필터링 불가
        # 별도 인덱스가 필요하면 추후 구현
        logger.warning(f"invalidate_by_tool not implemented for hashed keys")
        return 0

    def _evict_expired(self) -> int:
        """만료된 엔트리 제거

        Returns:
            제거된 엔트리 수
        """
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]

        for key in expired_keys:
            del self._cache[key]

        self._stats["evictions"] += len(expired_keys)
        if expired_keys:
            logger.debug(f"Evicted {len(expired_keys)} expired entries")

        return len(expired_keys)

    def _evict_oldest(self, count: int = 100) -> int:
        """가장 오래된 엔트리 제거

        Args:
            count: 제거할 개수

        Returns:
            제거된 엔트리 수
        """
        # 생성 시간 기준 정렬
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].created_at
        )

        removed = 0
        for key, _ in sorted_entries[:count]:
            del self._cache[key]
            removed += 1

        self._stats["evictions"] += removed
        logger.debug(f"Evicted {removed} oldest entries")

        return removed

    def clear(self) -> None:
        """전체 캐시 초기화"""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환

        Returns:
            통계 딕셔너리
        """
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                self._stats["hits"] / total_requests
                if total_requests > 0
                else 0.0
            )

            return {
                "entries": len(self._cache),
                "max_entries": self.MAX_ENTRIES,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": hit_rate,
                "evictions": self._stats["evictions"],
            }

    def get_entries_info(self) -> list:
        """모든 캐시 엔트리 정보

        Returns:
            엔트리 정보 리스트
        """
        with self._lock:
            return [entry.to_dict() for entry in self._cache.values()]


# 싱글톤 인스턴스 접근 함수
_cache_instance: Optional[ExecutionCache] = None


def get_execution_cache() -> ExecutionCache:
    """ExecutionCache 싱글톤 인스턴스 반환

    Returns:
        ExecutionCache 인스턴스
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ExecutionCache()
    return _cache_instance
