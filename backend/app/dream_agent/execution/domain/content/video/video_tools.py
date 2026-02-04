"""Video Tools - 비디오 관련 기본 Tools"""

from typing import Dict, Any, List
from langchain_core.tools import tool


@tool
def validate_storyboard(storyboard: Dict[str, Any]) -> Dict[str, Any]:
    """
    스토리보드 유효성 검증

    Args:
        storyboard: 스토리보드 데이터

    Returns:
        {"valid": bool, "errors": List[str], "warnings": List[str]}
    """
    errors = []
    warnings = []

    # 필수 필드 확인
    if "scenes" not in storyboard:
        errors.append("Missing 'scenes' field")

    scenes = storyboard.get("scenes", [])
    if len(scenes) == 0:
        errors.append("No scenes found in storyboard")

    # Scene 유효성 검증
    for idx, scene in enumerate(scenes):
        if "description" not in scene:
            errors.append(f"Scene {idx+1}: Missing 'description'")
        if "duration" not in scene:
            warnings.append(f"Scene {idx+1}: Missing 'duration', using default 3s")

    # 총 길이 확인
    total_duration = sum(s.get("duration", 3) for s in scenes)
    if total_duration > 60:
        warnings.append(f"Total duration {total_duration}s exceeds recommended 60s")
    elif total_duration < 5:
        warnings.append(f"Total duration {total_duration}s is too short")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "scene_count": len(scenes),
        "total_duration": total_duration
    }


@tool
def save_video_metadata(
    comfyui_result: Dict[str, Any],
    storyboard: Dict[str, Any]
) -> str:
    """
    비디오 메타데이터 저장

    Args:
        comfyui_result: ComfyUI 실행 결과
        storyboard: 원본 스토리보드

    Returns:
        저장된 메타데이터 파일 경로
    """
    import json
    from pathlib import Path
    from datetime import datetime

    output_dir = Path("data/output/videos")
    output_dir.mkdir(parents=True, exist_ok=True)

    job_id = comfyui_result.get("job_id", "unknown")
    meta_path = output_dir / f"{job_id}_meta.json"

    metadata = {
        "job_id": job_id,
        "status": comfyui_result.get("status"),
        "storyboard_id": storyboard.get("id"),
        "video_url": comfyui_result.get("output", {}).get("video_url"),
        "thumbnail_url": comfyui_result.get("output", {}).get("thumbnail_url"),
        "frames": comfyui_result.get("output", {}).get("frames", []),
        "metadata": comfyui_result.get("metadata", {}),
        "cost": comfyui_result.get("cost", 0),
        "mock": comfyui_result.get("mock", False),
        "created_at": datetime.now().isoformat()
    }

    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return str(meta_path)
