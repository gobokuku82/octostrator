"""Mock Data Provider - Mock 데이터 제공

개발 및 테스트를 위한 Mock 데이터 제공
"""

from typing import Dict, Any, Optional
from pathlib import Path
import json
from langchain_core.tools import tool


class MockDataProvider:
    """Mock 데이터 제공 클래스"""

    def __init__(self, mock_data_dir: str = "data/mock"):
        self.mock_data_dir = Path(mock_data_dir)
        self.mock_data_dir.mkdir(parents=True, exist_ok=True)

    def get_mock_ml_result(self) -> Dict[str, Any]:
        """Mock ML 분석 결과 반환"""
        mock_file = self.mock_data_dir / "ml_result.json"

        if mock_file.exists():
            with open(mock_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        # 기본 Mock 데이터
        mock_data = {
            "analysis_type": "sentiment_analysis",
            "total_reviews": 1500,
            "avg_rating": 4.2,
            "sentiment": {
                "positive": 0.65,
                "neutral": 0.25,
                "negative": 0.10
            },
            "keywords": ["보습", "촉촉", "가성비", "추천", "만족"],
            "insights": [
                "보습 효과에 대한 긍정적 반응이 높음",
                "가성비가 좋다는 평가가 많음",
                "재구매 의향이 높은 편"
            ],
            "sentiment_score": 0.78,
            "timestamp": "2026-01-08T14:30:00",
            "mock": True
        }

        # 저장
        with open(mock_file, 'w', encoding='utf-8') as f:
            json.dump(mock_data, f, ensure_ascii=False, indent=2)

        return mock_data

    def get_mock_storyboard(self) -> Dict[str, Any]:
        """Mock 스토리보드 반환"""
        mock_file = self.mock_data_dir / "storyboard.json"

        if mock_file.exists():
            with open(mock_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        # 기본 Mock 데이터
        mock_data = {
            "id": "mock_story_001",
            "title": "라네즈 워터뱅크 광고",
            "platform": "Instagram",
            "duration_sec": 15,
            "scenes": [
                {
                    "scene_id": 1,
                    "duration": 3,
                    "description": "제품 클로즈업 - 워터뱅크 패키징",
                    "visual": "파란색 배경, 제품 중앙 배치",
                    "text": "라네즈 워터뱅크",
                    "seed": 42
                },
                {
                    "scene_id": 2,
                    "duration": 5,
                    "description": "사용 장면 - 손등에 크림 발림",
                    "visual": "부드러운 텍스처 강조",
                    "text": "촉촉한 보습",
                    "seed": 43
                },
                {
                    "scene_id": 3,
                    "duration": 4,
                    "description": "효과 - 빛나는 피부",
                    "visual": "Before/After 비교",
                    "text": "24시간 보습 지속",
                    "seed": 44
                },
                {
                    "scene_id": 4,
                    "duration": 3,
                    "description": "CTA - 구매 유도",
                    "visual": "제품 이미지 + 링크",
                    "text": "지금 바로 만나보세요",
                    "seed": 45
                }
            ],
            "target_audience": "20-30대 여성",
            "mood": "청량하고 상쾌한",
            "mock": True
        }

        # 저장
        with open(mock_file, 'w', encoding='utf-8') as f:
            json.dump(mock_data, f, ensure_ascii=False, indent=2)

        return mock_data

    def get_mock_product_data(self) -> Dict[str, Any]:
        """Mock 제품 데이터 반환"""
        mock_file = self.mock_data_dir / "product_data.json"

        if mock_file.exists():
            with open(mock_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        mock_data = {
            "product_id": "LANEIGE_WB_CREAM",
            "name": "라네즈 워터뱅크 블루 히알루로닉 크림",
            "category": "스킨케어",
            "price": 38000,
            "features": ["보습", "진정", "수분충전"],
            "target_age": "20-40",
            "ingredients": ["히알루론산", "글리세린", "나이아신아마이드"],
            "mock": True
        }

        # 저장
        with open(mock_file, 'w', encoding='utf-8') as f:
            json.dump(mock_data, f, ensure_ascii=False, indent=2)

        return mock_data

    def get_mock_comfyui_response(
        self,
        workflow_id: str,
        scene_count: int
    ) -> Dict[str, Any]:
        """Mock ComfyUI 응답 반환"""
        from datetime import datetime

        mock_file = self.mock_data_dir / "comfyui_response.json"

        if mock_file.exists():
            with open(mock_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        mock_data = {
            "job_id": f"mock_job_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "status": "COMPLETED",
            "workflow_id": workflow_id,
            "scenes_generated": scene_count,
            "output": {
                "video_url": "https://mock-cdn.example.com/videos/laneige_ad_v1.mp4",
                "thumbnail_url": "https://mock-cdn.example.com/thumbnails/laneige_ad_thumb.jpg",
                "frames": [
                    {
                        "scene_id": i + 1,
                        "image_url": f"https://mock-cdn.example.com/frames/scene_{i+1}.jpg"
                    }
                    for i in range(scene_count)
                ]
            },
            "metadata": {
                "resolution": "1080p",
                "fps": 30,
                "duration_sec": 15,
                "processing_time_sec": 0.1
            },
            "cost": 0.0,
            "mock": True,
            "created_at": datetime.now().isoformat()
        }

        # 저장
        with open(mock_file, 'w', encoding='utf-8') as f:
            json.dump(mock_data, f, ensure_ascii=False, indent=2)

        return mock_data


# ============================================================
# Tool 버전 (LangGraph Tools로 사용)
# ============================================================

@tool
def get_mock_ml_result() -> Dict[str, Any]:
    """Mock ML 분석 결과를 반환하는 Tool"""
    provider = MockDataProvider()
    return provider.get_mock_ml_result()


@tool
def get_mock_storyboard() -> Dict[str, Any]:
    """Mock 스토리보드를 반환하는 Tool"""
    provider = MockDataProvider()
    return provider.get_mock_storyboard()


@tool
def get_mock_product_data() -> Dict[str, Any]:
    """Mock 제품 데이터를 반환하는 Tool"""
    provider = MockDataProvider()
    return provider.get_mock_product_data()


@tool
def get_mock_comfyui_response(workflow_id: str, scene_count: int) -> Dict[str, Any]:
    """Mock ComfyUI 응답을 반환하는 Tool"""
    provider = MockDataProvider()
    return provider.get_mock_comfyui_response(workflow_id, scene_count)
