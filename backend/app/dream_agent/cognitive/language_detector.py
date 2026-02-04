"""Language Detector - 다국어 감지

한국어, 영어, 일본어, 중국어를 감지하고 코드 스위칭을 처리합니다.
"""

import re
from enum import Enum
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


# ============================================================
# Language Code
# ============================================================

class LanguageCode(str, Enum):
    """언어 코드"""
    KO = "ko"    # 한국어
    EN = "en"    # 영어
    JA = "ja"    # 일본어
    ZH = "zh"    # 중국어
    MIXED = "mixed"  # 혼합


# ============================================================
# Detection Result
# ============================================================

class LanguageSegment(BaseModel):
    """언어 세그먼트"""
    text: str
    language: LanguageCode
    start: int
    end: int
    confidence: float = 1.0


class LanguageDetectionResult(BaseModel):
    """언어 감지 결과"""
    primary_language: LanguageCode
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    language_distribution: Dict[LanguageCode, float] = Field(default_factory=dict)
    segments: List[LanguageSegment] = Field(default_factory=list)
    is_code_switching: bool = False
    original_text: str = ""


# ============================================================
# Language Detector
# ============================================================

class LanguageDetector:
    """
    다국어 감지기

    한국어, 영어, 일본어, 중국어를 감지합니다.
    코드 스위칭(언어 혼합)도 감지합니다.
    """

    # Unicode 범위
    UNICODE_RANGES = {
        LanguageCode.KO: [
            (0xAC00, 0xD7AF),  # 한글 음절
            (0x1100, 0x11FF),  # 한글 자모
            (0x3130, 0x318F),  # 한글 호환 자모
        ],
        LanguageCode.JA: [
            (0x3040, 0x309F),  # 히라가나
            (0x30A0, 0x30FF),  # 가타카나
            (0x31F0, 0x31FF),  # 가타카나 확장
        ],
        LanguageCode.ZH: [
            (0x4E00, 0x9FFF),  # CJK 통합 한자 기본
            (0x3400, 0x4DBF),  # CJK 확장 A
            (0x20000, 0x2A6DF),  # CJK 확장 B
        ],
        LanguageCode.EN: [
            (0x0041, 0x005A),  # A-Z
            (0x0061, 0x007A),  # a-z
        ],
    }

    # 언어별 특징 패턴
    LANGUAGE_PATTERNS = {
        LanguageCode.KO: [
            r'[가-힣]+',  # 한글 음절
            r'[ㄱ-ㅎㅏ-ㅣ]+',  # 한글 자모
        ],
        LanguageCode.JA: [
            r'[ぁ-んァ-ン]+',  # 히라가나 + 가타카나
            r'[一-龯]+',  # 일본어에서 자주 쓰는 한자
        ],
        LanguageCode.ZH: [
            r'[\u4e00-\u9fff]+',  # 한자
        ],
        LanguageCode.EN: [
            r'[a-zA-Z]+',  # 알파벳
        ],
    }

    # 한국어 고빈도 어절
    KO_COMMON_WORDS = {
        "이", "가", "은", "는", "을", "를", "의", "에", "에서", "으로", "로",
        "하다", "있다", "되다", "없다", "보다", "같다", "좋다", "많다",
        "해주세요", "알려주세요", "분석", "생성", "확인", "결과"
    }

    # 영어 고빈도 단어
    EN_COMMON_WORDS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "can", "could", "should", "may", "might", "must",
        "and", "or", "but", "if", "then", "because", "so", "that", "which",
        "please", "analyze", "create", "show", "report"
    }

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """패턴 컴파일"""
        self._compiled_patterns = {}
        for lang, patterns in self.LANGUAGE_PATTERNS.items():
            self._compiled_patterns[lang] = [re.compile(p) for p in patterns]

    def detect(self, text: str) -> LanguageDetectionResult:
        """
        언어 감지

        Args:
            text: 감지할 텍스트

        Returns:
            LanguageDetectionResult
        """
        if not text or not text.strip():
            return LanguageDetectionResult(
                primary_language=LanguageCode.EN,
                confidence=0.0,
                original_text=text
            )

        # 문자 수 카운트
        char_counts = self._count_characters(text)
        total_chars = sum(char_counts.values())

        if total_chars == 0:
            return LanguageDetectionResult(
                primary_language=LanguageCode.EN,
                confidence=0.0,
                original_text=text
            )

        # 언어 분포 계산
        distribution = {
            lang: count / total_chars
            for lang, count in char_counts.items()
            if count > 0
        }

        # 주요 언어 결정
        primary_lang, confidence = self._determine_primary_language(
            text, distribution, char_counts
        )

        # 코드 스위칭 감지
        is_code_switching = self._detect_code_switching(distribution)

        # 세그먼트 분석 (코드 스위칭인 경우)
        segments = []
        if is_code_switching:
            segments = self._segment_text(text)

        return LanguageDetectionResult(
            primary_language=primary_lang,
            confidence=confidence,
            language_distribution=distribution,
            segments=segments,
            is_code_switching=is_code_switching,
            original_text=text
        )

    def _count_characters(self, text: str) -> Dict[LanguageCode, int]:
        """언어별 문자 수 카운트"""
        counts = {lang: 0 for lang in LanguageCode if lang != LanguageCode.MIXED}

        for char in text:
            code = ord(char)
            for lang, ranges in self.UNICODE_RANGES.items():
                for start, end in ranges:
                    if start <= code <= end:
                        counts[lang] += 1
                        break

        return counts

    def _determine_primary_language(
        self,
        text: str,
        distribution: Dict[LanguageCode, float],
        char_counts: Dict[LanguageCode, int]
    ) -> Tuple[LanguageCode, float]:
        """주요 언어 결정"""
        if not distribution:
            return LanguageCode.EN, 0.5

        # 최대 비율 언어
        max_lang = max(distribution.keys(), key=lambda x: distribution[x])
        max_ratio = distribution[max_lang]

        # 한국어/영어 혼합 처리
        ko_ratio = distribution.get(LanguageCode.KO, 0)
        en_ratio = distribution.get(LanguageCode.EN, 0)

        # 한국어 조사/어미 체크로 주요 언어 보정
        if ko_ratio > 0.1:
            ko_word_score = self._check_korean_words(text)
            if ko_word_score > 0.3:
                return LanguageCode.KO, min(ko_ratio + ko_word_score * 0.3, 1.0)

        # 영어 단어 체크
        if en_ratio > 0.3:
            en_word_score = self._check_english_words(text)
            if en_word_score > 0.5 and ko_ratio < 0.2:
                return LanguageCode.EN, min(en_ratio + en_word_score * 0.3, 1.0)

        # 일본어: 히라가나/가타카나가 있으면 일본어
        ja_ratio = distribution.get(LanguageCode.JA, 0)
        if ja_ratio > 0.1:
            return LanguageCode.JA, ja_ratio

        # 중국어: 한자만 있고 한글/일본어 문자가 없으면
        zh_ratio = distribution.get(LanguageCode.ZH, 0)
        if zh_ratio > 0.3 and ko_ratio < 0.1 and ja_ratio < 0.1:
            return LanguageCode.ZH, zh_ratio

        return max_lang, max_ratio

    def _check_korean_words(self, text: str) -> float:
        """한국어 단어 점수 계산"""
        words = text.split()
        if not words:
            return 0.0

        ko_word_count = 0
        for word in words:
            # 한글 포함 단어
            if re.search(r'[가-힣]', word):
                ko_word_count += 1
            # 한국어 고빈도 어절
            for common in self.KO_COMMON_WORDS:
                if common in word:
                    ko_word_count += 0.5
                    break

        return min(ko_word_count / len(words), 1.0)

    def _check_english_words(self, text: str) -> float:
        """영어 단어 점수 계산"""
        words = re.findall(r'[a-zA-Z]+', text.lower())
        if not words:
            return 0.0

        en_word_count = sum(
            1 for word in words
            if word in self.EN_COMMON_WORDS or len(word) > 3
        )

        return min(en_word_count / len(words), 1.0)

    def _detect_code_switching(self, distribution: Dict[LanguageCode, float]) -> bool:
        """코드 스위칭 감지"""
        # 2개 이상 언어가 10% 이상 차지하면 코드 스위칭
        significant_langs = [
            lang for lang, ratio in distribution.items()
            if ratio >= 0.1
        ]
        return len(significant_langs) >= 2

    def _segment_text(self, text: str) -> List[LanguageSegment]:
        """텍스트를 언어별 세그먼트로 분리"""
        segments = []
        current_lang = None
        current_start = 0
        current_text = ""

        for i, char in enumerate(text):
            char_lang = self._detect_char_language(char)

            if char_lang is None:
                current_text += char
                continue

            if current_lang is None:
                current_lang = char_lang
                current_start = i
                current_text = char
            elif char_lang == current_lang:
                current_text += char
            else:
                # 세그먼트 저장
                if current_text.strip():
                    segments.append(LanguageSegment(
                        text=current_text,
                        language=current_lang,
                        start=current_start,
                        end=i
                    ))
                current_lang = char_lang
                current_start = i
                current_text = char

        # 마지막 세그먼트
        if current_text.strip() and current_lang:
            segments.append(LanguageSegment(
                text=current_text,
                language=current_lang,
                start=current_start,
                end=len(text)
            ))

        return segments

    def _detect_char_language(self, char: str) -> Optional[LanguageCode]:
        """단일 문자의 언어 감지"""
        code = ord(char)

        for lang, ranges in self.UNICODE_RANGES.items():
            for start, end in ranges:
                if start <= code <= end:
                    return lang

        return None

    def get_response_language(self, detection_result: LanguageDetectionResult) -> str:
        """응답에 사용할 언어 결정"""
        # 코드 스위칭인 경우 주 언어 사용
        primary = detection_result.primary_language

        # 혼합이면 한국어 우선
        if primary == LanguageCode.MIXED:
            ko_ratio = detection_result.language_distribution.get(LanguageCode.KO, 0)
            if ko_ratio > 0.2:
                return "ko"
            return "en"

        return primary.value


# ============================================================
# Global Instance
# ============================================================

_detector: Optional[LanguageDetector] = None


def get_detector() -> LanguageDetector:
    """전역 Detector 인스턴스 반환"""
    global _detector
    if _detector is None:
        _detector = LanguageDetector()
    return _detector
