"""Video Composer - FFmpeg/MoviePy 기반 비디오 합성

여러 비디오 클립을 하나의 영상으로 합성합니다.
트랜지션, 오디오 믹싱, 텍스트 오버레이 지원.
"""

import os
import base64
import tempfile
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime

from pydantic import BaseModel, Field


class VideoClipInput(BaseModel):
    """비디오 클립 입력"""
    video_data: str = Field(..., description="비디오 데이터 (base64)")
    duration: Optional[float] = Field(default=None, description="클립 길이 (초)")
    start_time: Optional[float] = Field(default=0.0, description="시작 시간")
    end_time: Optional[float] = Field(default=None, description="종료 시간")

    # 트랜지션
    transition_in: Optional[str] = Field(
        default=None,
        description="입장 트랜지션 (fade, slide, zoom)"
    )
    transition_out: Optional[str] = Field(
        default=None,
        description="퇴장 트랜지션 (fade, slide, zoom)"
    )
    transition_duration: float = Field(
        default=0.5,
        description="트랜지션 길이 (초)"
    )

    # 텍스트 오버레이
    text_overlay: Optional[str] = Field(default=None, description="텍스트 오버레이")
    text_position: str = Field(default="bottom", description="텍스트 위치")
    text_style: Dict[str, Any] = Field(
        default_factory=lambda: {
            "fontsize": 40,
            "color": "white",
            "stroke_color": "black",
            "stroke_width": 2
        }
    )


class AudioInput(BaseModel):
    """오디오 입력"""
    audio_data: Optional[str] = Field(default=None, description="오디오 데이터 (base64)")
    audio_path: Optional[str] = Field(default=None, description="오디오 파일 경로")
    volume: float = Field(default=1.0, description="볼륨 (0.0 ~ 2.0)")
    fade_in: float = Field(default=0.5, description="페이드 인 길이")
    fade_out: float = Field(default=1.0, description="페이드 아웃 길이")
    loop: bool = Field(default=True, description="루프 여부")


class CompositionConfig(BaseModel):
    """합성 설정"""
    resolution: str = Field(default="1080p", description="출력 해상도")
    fps: int = Field(default=30, description="프레임레이트")
    codec: str = Field(default="libx264", description="비디오 코덱")
    audio_codec: str = Field(default="aac", description="오디오 코덱")
    bitrate: str = Field(default="8M", description="비트레이트")
    preset: str = Field(default="medium", description="인코딩 프리셋")

    # 크롭/리사이즈
    aspect_ratio: str = Field(default="9:16", description="화면 비율")
    background_color: str = Field(default="black", description="배경색")


class CompositionResult(BaseModel):
    """합성 결과"""
    success: bool
    video_data: Optional[str] = None  # base64
    output_path: Optional[str] = None
    duration: Optional[float] = None
    file_size_mb: Optional[float] = None
    error: Optional[str] = None
    processing_time_ms: Optional[int] = None


class VideoComposer:
    """
    비디오 합성기

    FFmpeg/MoviePy를 사용하여 여러 비디오 클립을 하나로 합성합니다.

    Features:
        - 비디오 클립 연결 (concat)
        - 트랜지션 효과 (fade, crossfade)
        - 텍스트 오버레이
        - 배경음악 믹싱
        - 해상도/FPS 통일

    Usage:
        composer = VideoComposer()

        result = await composer.compose(
            clips=[
                VideoClipInput(video_data="...", transition_out="fade"),
                VideoClipInput(video_data="...", text_overlay="Scene 2"),
            ],
            audio=AudioInput(audio_path="bgm.mp3"),
            config=CompositionConfig(resolution="1080p")
        )
    """

    RESOLUTION_MAP = {
        "720p": (720, 1280),   # 9:16 세로
        "1080p": (1080, 1920), # 9:16 세로
        "4k": (2160, 3840),    # 9:16 세로
        "720p_h": (1280, 720),   # 16:9 가로
        "1080p_h": (1920, 1080), # 16:9 가로
        "4k_h": (3840, 2160),    # 16:9 가로
    }

    def __init__(self, output_dir: Optional[str] = None):
        """
        VideoComposer 초기화

        Args:
            output_dir: 출력 디렉토리 (기본: data/output/videos)
        """
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent.parent.parent.parent.parent.parent.parent / "data/output/videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._check_dependencies()

    def _check_dependencies(self):
        """의존성 확인"""
        try:
            import moviepy.editor as mpe
            self._moviepy_available = True
        except ImportError:
            self._moviepy_available = False

        # FFmpeg 확인
        import subprocess
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            self._ffmpeg_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self._ffmpeg_available = False

    def _decode_video_to_file(self, video_data: str, suffix: str = ".mp4") -> str:
        """
        base64 비디오를 임시 파일로 저장

        Args:
            video_data: base64 비디오 데이터
            suffix: 파일 확장자

        Returns:
            임시 파일 경로
        """
        # data: prefix 제거
        if video_data.startswith("data:"):
            video_data = video_data.split(",", 1)[1]

        video_bytes = base64.b64decode(video_data)

        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, 'wb') as f:
            f.write(video_bytes)

        return path

    def _file_to_base64(self, file_path: str) -> str:
        """
        파일을 base64로 인코딩

        Args:
            file_path: 파일 경로

        Returns:
            base64 문자열
        """
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    async def compose(
        self,
        clips: List[VideoClipInput],
        audio: Optional[AudioInput] = None,
        config: Optional[CompositionConfig] = None
    ) -> CompositionResult:
        """
        비디오 클립들을 하나로 합성

        Args:
            clips: 비디오 클립 목록
            audio: 배경 오디오 (선택)
            config: 합성 설정

        Returns:
            CompositionResult
        """
        if not clips:
            return CompositionResult(
                success=False,
                error="No video clips provided"
            )

        config = config or CompositionConfig()
        start_time = datetime.now()

        try:
            if self._moviepy_available:
                result = await self._compose_with_moviepy(clips, audio, config)
            elif self._ffmpeg_available:
                result = await self._compose_with_ffmpeg(clips, audio, config)
            else:
                return CompositionResult(
                    success=False,
                    error="Neither MoviePy nor FFmpeg is available"
                )

            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            result.processing_time_ms = processing_time

            return result

        except Exception as e:
            return CompositionResult(
                success=False,
                error=str(e)
            )

    async def _compose_with_moviepy(
        self,
        clips: List[VideoClipInput],
        audio: Optional[AudioInput],
        config: CompositionConfig
    ) -> CompositionResult:
        """MoviePy를 사용한 합성"""
        import moviepy.editor as mpe

        temp_files = []
        video_clips = []

        try:
            # 해상도 파싱
            width, height = self.RESOLUTION_MAP.get(
                config.resolution,
                (1080, 1920)
            )

            # 각 클립 로드 및 처리
            for i, clip_input in enumerate(clips):
                # base64 → 임시 파일
                temp_path = self._decode_video_to_file(clip_input.video_data)
                temp_files.append(temp_path)

                # 클립 로드
                clip = mpe.VideoFileClip(temp_path)

                # 시간 범위 적용
                if clip_input.start_time or clip_input.end_time:
                    end = clip_input.end_time or clip.duration
                    clip = clip.subclip(clip_input.start_time, end)

                # 리사이즈
                clip = clip.resize(newsize=(width, height))

                # 트랜지션 적용
                if clip_input.transition_in == "fade":
                    clip = clip.fadein(clip_input.transition_duration)

                if clip_input.transition_out == "fade":
                    clip = clip.fadeout(clip_input.transition_duration)

                # 텍스트 오버레이
                if clip_input.text_overlay:
                    txt_clip = mpe.TextClip(
                        clip_input.text_overlay,
                        fontsize=clip_input.text_style.get("fontsize", 40),
                        color=clip_input.text_style.get("color", "white"),
                        stroke_color=clip_input.text_style.get("stroke_color", "black"),
                        stroke_width=clip_input.text_style.get("stroke_width", 2)
                    )
                    txt_clip = txt_clip.set_position(clip_input.text_position)
                    txt_clip = txt_clip.set_duration(clip.duration)
                    clip = mpe.CompositeVideoClip([clip, txt_clip])

                video_clips.append(clip)

            # 클립 연결
            final_clip = mpe.concatenate_videoclips(video_clips, method="compose")

            # 오디오 추가
            if audio:
                if audio.audio_data:
                    audio_path = self._decode_video_to_file(audio.audio_data, suffix=".mp3")
                    temp_files.append(audio_path)
                elif audio.audio_path:
                    audio_path = audio.audio_path
                else:
                    audio_path = None

                if audio_path:
                    audio_clip = mpe.AudioFileClip(audio_path)

                    # 볼륨 조절
                    if audio.volume != 1.0:
                        audio_clip = audio_clip.volumex(audio.volume)

                    # 길이 맞추기
                    if audio.loop and audio_clip.duration < final_clip.duration:
                        audio_clip = mpe.afx.audio_loop(audio_clip, duration=final_clip.duration)
                    else:
                        audio_clip = audio_clip.subclip(0, min(audio_clip.duration, final_clip.duration))

                    # 페이드 적용
                    if audio.fade_in:
                        audio_clip = audio_clip.audio_fadein(audio.fade_in)
                    if audio.fade_out:
                        audio_clip = audio_clip.audio_fadeout(audio.fade_out)

                    final_clip = final_clip.set_audio(audio_clip)

            # 출력 파일 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"composed_{timestamp}.mp4"

            # 비동기 인코딩 (스레드풀에서 실행)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: final_clip.write_videofile(
                    str(output_path),
                    fps=config.fps,
                    codec=config.codec,
                    audio_codec=config.audio_codec,
                    bitrate=config.bitrate,
                    preset=config.preset,
                    verbose=False,
                    logger=None
                )
            )

            # 결과 반환
            file_size_mb = output_path.stat().st_size / (1024 * 1024)

            return CompositionResult(
                success=True,
                video_data=self._file_to_base64(str(output_path)),
                output_path=str(output_path),
                duration=final_clip.duration,
                file_size_mb=round(file_size_mb, 2)
            )

        finally:
            # 클립 정리
            for clip in video_clips:
                clip.close()

            # 임시 파일 정리
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass

    async def _compose_with_ffmpeg(
        self,
        clips: List[VideoClipInput],
        audio: Optional[AudioInput],
        config: CompositionConfig
    ) -> CompositionResult:
        """FFmpeg를 사용한 합성 (MoviePy 미설치 시 대안)"""
        import subprocess

        temp_files = []

        try:
            # 해상도 파싱
            width, height = self.RESOLUTION_MAP.get(
                config.resolution,
                (1080, 1920)
            )

            # 각 클립을 임시 파일로 저장
            clip_paths = []
            for i, clip_input in enumerate(clips):
                temp_path = self._decode_video_to_file(clip_input.video_data)
                temp_files.append(temp_path)
                clip_paths.append(temp_path)

            # concat 리스트 파일 생성
            concat_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            temp_files.append(concat_file.name)

            for path in clip_paths:
                concat_file.write(f"file '{path}'\n")
            concat_file.close()

            # 출력 파일
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"composed_{timestamp}.mp4"

            # FFmpeg 명령 구성
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file.name,
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", config.codec,
                "-preset", config.preset,
                "-b:v", config.bitrate,
                "-r", str(config.fps),
            ]

            # 오디오 추가
            if audio and (audio.audio_data or audio.audio_path):
                if audio.audio_data:
                    audio_path = self._decode_video_to_file(audio.audio_data, suffix=".mp3")
                    temp_files.append(audio_path)
                else:
                    audio_path = audio.audio_path

                cmd.extend([
                    "-i", audio_path,
                    "-c:a", config.audio_codec,
                    "-shortest"
                ])
            else:
                cmd.extend(["-an"])  # 오디오 없음

            cmd.append(str(output_path))

            # FFmpeg 실행
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return CompositionResult(
                    success=False,
                    error=f"FFmpeg error: {stderr.decode()}"
                )

            # 결과 반환
            file_size_mb = output_path.stat().st_size / (1024 * 1024)

            # 비디오 길이 확인
            duration_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(output_path)
            ]

            duration_process = await asyncio.create_subprocess_exec(
                *duration_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            duration_stdout, _ = await duration_process.communicate()
            duration = float(duration_stdout.decode().strip()) if duration_stdout else None

            return CompositionResult(
                success=True,
                video_data=self._file_to_base64(str(output_path)),
                output_path=str(output_path),
                duration=duration,
                file_size_mb=round(file_size_mb, 2)
            )

        finally:
            # 임시 파일 정리
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass

    async def add_watermark(
        self,
        video_data: str,
        watermark_text: str = "",
        watermark_image: Optional[str] = None,
        position: str = "bottom_right",
        opacity: float = 0.7
    ) -> CompositionResult:
        """
        워터마크 추가

        Args:
            video_data: 비디오 데이터 (base64)
            watermark_text: 텍스트 워터마크
            watermark_image: 이미지 워터마크 (base64)
            position: 위치 (top_left, top_right, bottom_left, bottom_right, center)
            opacity: 투명도

        Returns:
            CompositionResult
        """
        if not self._moviepy_available:
            return CompositionResult(
                success=False,
                error="MoviePy is required for watermark feature"
            )

        import moviepy.editor as mpe

        temp_files = []

        try:
            # 비디오 로드
            video_path = self._decode_video_to_file(video_data)
            temp_files.append(video_path)

            clip = mpe.VideoFileClip(video_path)

            # 워터마크 생성
            if watermark_text:
                watermark = mpe.TextClip(
                    watermark_text,
                    fontsize=24,
                    color='white'
                ).set_opacity(opacity)
            elif watermark_image:
                img_path = self._decode_video_to_file(watermark_image, suffix=".png")
                temp_files.append(img_path)
                watermark = mpe.ImageClip(img_path).set_opacity(opacity)
            else:
                return CompositionResult(
                    success=False,
                    error="Either watermark_text or watermark_image is required"
                )

            watermark = watermark.set_duration(clip.duration)
            watermark = watermark.set_position(position.replace("_", " "))

            # 합성
            final_clip = mpe.CompositeVideoClip([clip, watermark])

            # 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"watermarked_{timestamp}.mp4"

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: final_clip.write_videofile(
                    str(output_path),
                    fps=clip.fps,
                    codec="libx264",
                    verbose=False,
                    logger=None
                )
            )

            file_size_mb = output_path.stat().st_size / (1024 * 1024)

            return CompositionResult(
                success=True,
                video_data=self._file_to_base64(str(output_path)),
                output_path=str(output_path),
                duration=final_clip.duration,
                file_size_mb=round(file_size_mb, 2)
            )

        finally:
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
