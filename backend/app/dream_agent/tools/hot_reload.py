"""Tool Hot Reload - YAML 파일 변경 감지 및 자동 리로드

Phase 2: watchdog 기반 YAML 도구 정의 파일 변경 감지.
"""

import os
import time
import logging
from pathlib import Path
from threading import Thread, Event
from typing import Callable, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class YAMLWatcher:
    """YAML 파일 변경 감지기

    tools/definitions 디렉토리의 YAML 파일 변경을 감지하고
    콜백 함수를 호출합니다.

    Example:
        ```python
        def on_change(changed_files):
            print(f"Changed: {changed_files}")
            reload_tools()

        watcher = YAMLWatcher(definitions_dir, on_change)
        watcher.start()
        # ...
        watcher.stop()
        ```
    """

    def __init__(
        self,
        watch_dir: Path,
        on_change: Callable[[Set[str]], None],
        interval: float = 1.0,
        extensions: tuple = (".yaml", ".yml"),
    ):
        """YAMLWatcher 초기화

        Args:
            watch_dir: 감시할 디렉토리
            on_change: 변경 시 호출할 콜백
            interval: 감시 간격 (초)
            extensions: 감시할 파일 확장자
        """
        self.watch_dir = Path(watch_dir)
        self.on_change = on_change
        self.interval = interval
        self.extensions = extensions

        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self._file_mtimes: dict = {}

    def _get_files(self) -> dict:
        """감시 대상 파일과 수정 시간 조회"""
        files = {}
        if not self.watch_dir.exists():
            return files

        for ext in self.extensions:
            for file_path in self.watch_dir.glob(f"*{ext}"):
                try:
                    mtime = file_path.stat().st_mtime
                    files[str(file_path)] = mtime
                except OSError:
                    pass

        return files

    def _check_changes(self) -> Set[str]:
        """변경된 파일 확인"""
        changed = set()
        current_files = self._get_files()

        # 새로 추가되거나 수정된 파일
        for path, mtime in current_files.items():
            if path not in self._file_mtimes:
                changed.add(path)
                logger.info(f"[HotReload] New file: {path}")
            elif mtime > self._file_mtimes[path]:
                changed.add(path)
                logger.info(f"[HotReload] Modified: {path}")

        # 삭제된 파일
        for path in self._file_mtimes:
            if path not in current_files:
                changed.add(path)
                logger.info(f"[HotReload] Deleted: {path}")

        self._file_mtimes = current_files
        return changed

    def _watch_loop(self):
        """감시 루프"""
        logger.info(f"[HotReload] Started watching: {self.watch_dir}")

        # 초기 상태 기록
        self._file_mtimes = self._get_files()

        while not self._stop_event.is_set():
            try:
                changed = self._check_changes()
                if changed:
                    logger.info(f"[HotReload] Detected {len(changed)} change(s)")
                    try:
                        self.on_change(changed)
                    except Exception as e:
                        logger.error(f"[HotReload] Callback error: {e}")
            except Exception as e:
                logger.error(f"[HotReload] Watch error: {e}")

            self._stop_event.wait(self.interval)

        logger.info("[HotReload] Stopped watching")

    def start(self):
        """감시 시작"""
        if self._thread and self._thread.is_alive():
            logger.warning("[HotReload] Already running")
            return

        self._stop_event.clear()
        self._thread = Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """감시 중지"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    def is_running(self) -> bool:
        """실행 중 여부"""
        return self._thread is not None and self._thread.is_alive()


class ToolHotReloader:
    """도구 Hot Reload 관리자

    YAML 파일 변경 시 ToolDiscovery를 자동으로 리로드합니다.

    Example:
        ```python
        reloader = get_tool_hot_reloader()
        reloader.start()

        # YAML 파일 수정 시 자동 리로드됨
        # ...

        reloader.stop()
        ```
    """

    _instance: Optional["ToolHotReloader"] = None

    def __new__(cls) -> "ToolHotReloader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        from .discovery import get_tool_discovery
        from .loader import YAMLToolLoader

        # definitions 디렉토리 경로
        self._definitions_dir = Path(__file__).parent / "definitions"

        self._discovery = get_tool_discovery
        self._loader_class = YAMLToolLoader
        self._watcher: Optional[YAMLWatcher] = None
        self._reload_count = 0
        self._last_reload: Optional[datetime] = None

        self._initialized = True

    def _on_files_changed(self, changed_files: Set[str]):
        """파일 변경 시 콜백"""
        logger.info(f"[ToolHotReloader] Reloading due to {len(changed_files)} change(s)")

        try:
            # Discovery 리셋
            from .discovery import ToolDiscovery
            ToolDiscovery.reset()

            # YAML 리로드
            discovery = self._discovery()
            loader = self._loader_class(self._definitions_dir)
            tools = loader.load_all()

            for spec in tools:
                discovery.register(spec)

            self._reload_count += 1
            self._last_reload = datetime.now()

            logger.info(
                f"[ToolHotReloader] Reload complete: {len(tools)} tools, "
                f"count={self._reload_count}"
            )

        except Exception as e:
            logger.error(f"[ToolHotReloader] Reload failed: {e}")

    def start(self):
        """Hot Reload 시작"""
        if self._watcher and self._watcher.is_running():
            logger.warning("[ToolHotReloader] Already running")
            return

        self._watcher = YAMLWatcher(
            watch_dir=self._definitions_dir,
            on_change=self._on_files_changed,
            interval=1.0,
        )
        self._watcher.start()
        logger.info("[ToolHotReloader] Started")

    def stop(self):
        """Hot Reload 중지"""
        if self._watcher:
            self._watcher.stop()
            self._watcher = None
        logger.info("[ToolHotReloader] Stopped")

    def is_running(self) -> bool:
        """실행 중 여부"""
        return self._watcher is not None and self._watcher.is_running()

    def get_stats(self) -> dict:
        """통계 정보"""
        return {
            "running": self.is_running(),
            "reload_count": self._reload_count,
            "last_reload": self._last_reload.isoformat() if self._last_reload else None,
            "watch_dir": str(self._definitions_dir),
        }

    def force_reload(self):
        """강제 리로드"""
        self._on_files_changed({"manual_trigger"})


# 싱글톤 접근 함수
_hot_reloader_instance: Optional[ToolHotReloader] = None


def get_tool_hot_reloader() -> ToolHotReloader:
    """ToolHotReloader 싱글톤 인스턴스 반환"""
    global _hot_reloader_instance
    if _hot_reloader_instance is None:
        _hot_reloader_instance = ToolHotReloader()
    return _hot_reloader_instance


def start_hot_reload():
    """Hot Reload 시작 (헬퍼 함수)"""
    reloader = get_tool_hot_reloader()
    reloader.start()
    return reloader


def stop_hot_reload():
    """Hot Reload 중지 (헬퍼 함수)"""
    reloader = get_tool_hot_reloader()
    reloader.stop()
