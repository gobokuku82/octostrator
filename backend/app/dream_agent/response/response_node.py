"""Response Layer - 최종 응답 생성 노드"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from backend.app.core.logging import get_logger, LogContext
from backend.app.dream_agent.states.accessors import (
    get_user_input,
    get_language,
    get_ml_result,
    get_biz_result,
)
from backend.app.dream_agent.llm_manager import (
    get_llm_client,
    RESPONSE_SYSTEM_PROMPT,
    format_response_prompt,
    agent_config,
)

logger = get_logger(__name__)

# 결과 저장 경로
RESULT_TREND_DIR = Path("data/result_trend")


def _save_trend_report(
    user_input: str,
    ml_result: Dict[str, Any],
    biz_result: Dict[str, Any],
    response: str,
    language: str = "ko"
) -> Optional[str]:
    """
    트렌드 분석 결과를 JSON 파일로 저장

    Args:
        user_input: 사용자 입력
        ml_result: ML 분석 결과
        biz_result: Biz 실행 결과
        response: 생성된 응답
        language: 언어 코드

    Returns:
        저장된 파일 경로 또는 None
    """
    try:
        # 디렉토리 생성
        RESULT_TREND_DIR.mkdir(parents=True, exist_ok=True)

        # 파일명 생성 (trend_report_20260118_143052.json)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trend_report_{timestamp}.json"
        filepath = RESULT_TREND_DIR / filename

        # 저장할 데이터 구성
        report_data = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "language": language,
                "user_input": user_input,
            },
            "ml_result": ml_result,
            "biz_result": biz_result if biz_result else None,
            "generated_response": response,
        }

        # JSON 파일 저장
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Trend report saved: {filepath}")
        return str(filepath)

    except Exception as e:
        logger.error(f"Failed to save trend report: {e}", exc_info=True)
        return None


def _summarize_ml_result(ml_result: Dict[str, Any], max_items: int = 5) -> Dict[str, Any]:
    """
    ML 결과를 LLM context에 맞게 공격적으로 요약

    Args:
        ml_result: 전체 ML 결과
        max_items: 리스트 항목 최대 개수 (기본 5개)

    Returns:
        요약된 ML 결과 (최대 ~10KB)
    """
    if not ml_result:
        return {}

    # 제외할 키 (원시 데이터 - 대용량)
    exclude_keys = {
        "intermediate_results",
        "preprocessed_reviews",
        "collected_reviews",
        "negative_reviews",
        "reviews",
        "raw_data",
        "data",  # stage별 data 필드도 제외
        "result",  # 원시 result도 제외
        "stages",  # 전체 stages도 제외
        "pipeline_result",  # 파이프라인 상세 결과 제외
    }

    # 핵심 요약 필드만 추출
    summarized = {}

    # 1. final_report가 있으면 우선 사용 (가장 중요)
    if "final_report" in ml_result:
        report = ml_result["final_report"]
        if isinstance(report, dict):
            # final_report 내부도 요약
            summarized["final_report"] = _extract_summary_from_dict(report, max_items)
        else:
            summarized["final_report"] = str(report)[:2000]

    # 2. insight_generator 결과
    if "insight_generator" in ml_result:
        insight = ml_result["insight_generator"]
        if isinstance(insight, dict):
            summarized["insights"] = _extract_summary_from_dict(insight, max_items)

    # 3. extractor (키워드) 결과 - 상위 키워드만
    if "extractor" in ml_result:
        ext = ml_result["extractor"]
        if isinstance(ext, dict):
            ext_data = ext.get("data", ext)
            summarized["keywords"] = {
                "top_keywords": _safe_slice(ext_data.get("top_keywords", []), max_items),
                "stats": ext_data.get("stats", {})
            }

    # 4. absa_analyzer (감성 분석) 결과 - 통계만
    if "absa_analyzer" in ml_result:
        absa = ml_result["absa_analyzer"]
        if isinstance(absa, dict):
            absa_data = absa.get("data", absa)
            summarized["sentiment"] = {
                "stats": absa_data.get("stats", {}),
                "success": absa.get("success", True)
            }

    # 5. google_trends 결과
    if "google_trends" in ml_result:
        trends = ml_result["google_trends"]
        if isinstance(trends, dict):
            trends_data = trends.get("data", trends)
            summarized["trends"] = {
                "trend_direction": trends_data.get("trend_direction", "unknown"),
                "change_percent": trends_data.get("change_percent", 0),
                "top_queries": _safe_slice(trends_data.get("top_queries", []), 3),
            }

    # 6. hashtag_analyzer 결과
    if "hashtag_analyzer" in ml_result:
        hashtag = ml_result["hashtag_analyzer"]
        if isinstance(hashtag, dict):
            hashtag_data = hashtag.get("data", hashtag)
            summarized["hashtags"] = {
                "top_hashtags": _safe_slice(hashtag_data.get("top_hashtags", []), max_items),
            }

    # 7. kbeauty_trend_report (K-Beauty 트렌드 RAG 인사이트) - 가장 중요!
    if "kbeauty_trend_report" in ml_result:
        kbeauty = ml_result["kbeauty_trend_report"]
        if isinstance(kbeauty, dict):
            summarized["kbeauty_trend_report"] = {
                "success": kbeauty.get("success", True),
                "insights": kbeauty.get("insights", "")[:3000],  # 인사이트 텍스트 (최대 3KB)
                "trend_context": kbeauty.get("trend_context", {}),
                "review_analysis": kbeauty.get("review_analysis", {}),
                "model_used": kbeauty.get("model_used", ""),
            }

    # 8. 메타 정보
    if "_meta" in ml_result:
        summarized["_meta"] = ml_result["_meta"]

    # 요약이 비어있으면 기본 정보 추가
    if not summarized:
        summarized["status"] = "completed"
        summarized["available_keys"] = list(ml_result.keys())[:10]

    return summarized


def _extract_summary_from_dict(data: Dict[str, Any], max_items: int = 5) -> Dict[str, Any]:
    """dict에서 요약 정보만 추출"""
    if not isinstance(data, dict):
        return {"value": str(data)[:500]}

    summary = {}
    exclude_nested = {"reviews", "data", "raw", "items", "results", "records"}

    for key, value in data.items():
        if key.lower() in exclude_nested:
            if isinstance(value, list):
                summary[f"{key}_count"] = len(value)
            continue

        if isinstance(value, list):
            summary[key] = _safe_slice(value, max_items)
        elif isinstance(value, dict):
            # 1단계만 더 들어감
            inner = {}
            for k, v in list(value.items())[:10]:
                if isinstance(v, (str, int, float, bool)) or v is None:
                    inner[k] = v
                elif isinstance(v, list):
                    inner[k] = _safe_slice(v, 3)
            summary[key] = inner
        elif isinstance(value, str):
            summary[key] = value[:500]  # 문자열 길이 제한
        else:
            summary[key] = value

    return summary


def _safe_slice(lst: Any, max_items: int) -> List:
    """리스트 안전하게 슬라이스"""
    if not isinstance(lst, list):
        return []
    return lst[:max_items]


def _truncate_json_string(data: Any, max_chars: int = 20000) -> str:
    """JSON 문자열을 최대 길이로 제한 (기본 20KB)"""
    try:
        json_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    except Exception:
        json_str = str(data)

    if len(json_str) <= max_chars:
        return json_str
    return json_str[:max_chars] + "\n... (truncated)"


async def response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Response Layer - 최종 응답 생성

    Args:
        state: AgentState

    Returns:
        Dict with 'response'
    """
    log = LogContext(logger, node="response")
    user_input = get_user_input(state)
    language = get_language(state).lower()  # 소문자 변환 (KOR → ko)

    # ML/Biz 결과 요약 (context length 제한 방지)
    # intermediate_results는 원시 데이터를 포함하므로 명시적으로 제외
    raw_ml_result = dict(get_ml_result(state))  # copy
    raw_ml_result.pop("intermediate_results", None)
    raw_ml_result.pop("stages", None)  # stages도 대용량 가능성

    raw_biz_result = dict(get_biz_result(state))  # copy

    # 요약 적용
    ml_result = _summarize_ml_result(raw_ml_result)
    biz_result = _summarize_ml_result(raw_biz_result)

    # JSON 크기 확인 (디버깅용)
    ml_json_size = len(json.dumps(ml_result, default=str)) if ml_result else 0
    log.info(f"ML result size: raw_keys={list(raw_ml_result.keys())[:5]}, summarized_size={ml_json_size} chars")

    # ML/Biz 결과 유무 확인 (다양한 결과 구조 지원)
    has_ml = bool(ml_result and (
        ml_result.get("summary") or
        ml_result.get("final_report") or
        ml_result.get("extractor") or
        ml_result.get("absa_analyzer") or
        ml_result.get("insight_generator") or
        ml_result.get("kbeauty_trend_report")  # K-Beauty 트렌드 RAG 인사이트
    ))
    has_biz = bool(biz_result and (
        biz_result.get("summary") or
        biz_result.get("report") or
        biz_result.get("result")
    ))

    # 적절한 템플릿 선택
    try:
        lang_instructions = agent_config.get_prompt("response", "language_instructions")

        if has_ml and has_biz:
            # ML + Biz 결합 응답
            instruction_key = "with_ml_and_biz"
            # 전체 요약된 ml_result 사용 (kbeauty_trend_report 포함)
            ml_summary = _truncate_json_string(ml_result, max_chars=8000)
            biz_summary = _truncate_json_string(biz_result, max_chars=8000)
            lang_instruction = lang_instructions.get(language, lang_instructions.get("ko", {})).get(instruction_key, "").format(
                ml_summary=ml_summary,
                biz_summary=biz_summary
            )
        elif has_ml:
            # ML 결과 기반 응답
            instruction_key = "with_ml_result"
            # 전체 요약된 ml_result 사용 (kbeauty_trend_report 포함)
            ml_summary = _truncate_json_string(ml_result, max_chars=10000)
            lang_instruction = lang_instructions.get(language, lang_instructions.get("ko", {})).get(instruction_key, "").format(
                ml_summary=ml_summary
            )
        elif has_biz:
            # Biz 결과 기반 응답
            instruction_key = "with_biz_result"
            # 전체 요약된 biz_result 사용
            biz_summary = _truncate_json_string(biz_result, max_chars=10000)
            lang_instruction = lang_instructions.get(language, lang_instructions.get("ko", {})).get(instruction_key, "").format(
                biz_summary=biz_summary
            )
        else:
            # 기본 지시문 (결과 없음)
            lang_instruction = lang_instructions.get(language, lang_instructions.get("ko", {})).get("base", "")

    except Exception as e:
        log.warning(f"Failed to load language instructions from config: {e}. Using fallback.")
        # Fallback: 기본 지시문
        lang_instruction = "반드시 한국어로 응답하세요." if language == "ko" else "You must respond in English."

    log.info(f"Generating final response (language: {language}, has_ml: {has_ml}, has_biz: {has_biz})")

    # LLM 호출
    llm_client = get_llm_client()
    prompt = format_response_prompt(user_input, ml_result, biz_result)
    system_prompt = f"{RESPONSE_SYSTEM_PROMPT}\n\n{lang_instruction}"

    try:
        log.debug("Calling LLM for response generation")
        response = await llm_client.chat_with_system(
            system_prompt=system_prompt,
            user_message=prompt,
            max_tokens=2500  # 맥락 기반 심층 분석을 위해 토큰 증가
        )
        log.info("Response generation completed")
    except Exception as e:
        log.error(f"Response generation error: {e}", exc_info=True)
        # Config에서 fallback 응답 로드
        try:
            fallback_responses = agent_config.get_prompt("response", "fallback_responses")
            response = fallback_responses.get(language, fallback_responses.get("ko", "요청을 처리했습니다."))
        except Exception:
            # Fallback의 fallback
            response = "요청을 처리했습니다. 결과를 확인해주세요." if language == "ko" else "I've processed your request."

    # ML 결과가 있으면 트렌드 리포트 저장
    saved_report_path = None
    if has_ml:
        saved_report_path = _save_trend_report(
            user_input=user_input,
            ml_result=ml_result,
            biz_result=biz_result,
            response=response,
            language=language
        )
        if saved_report_path:
            log.info(f"Trend report saved to: {saved_report_path}")

    return {
        "response": response,
        "saved_report_path": saved_report_path
    }
