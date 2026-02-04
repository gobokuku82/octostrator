"""File I/O - 파일 읽기/쓰기 도구

JSON 및 텍스트 파일 I/O 기능 제공
(기존 biz_execution/toolkit/file_tools.py에서 이전)
"""

from typing import Dict, Any
from pathlib import Path
import json
from langchain_core.tools import tool


@tool
def read_json_file(file_path: str) -> Dict[str, Any]:
    """
    JSON 파일 읽기

    Args:
        file_path: JSON 파일 경로

    Returns:
        파일 내용 (dict)
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


@tool
def write_json_file(file_path: str, data: Dict[str, Any]) -> str:
    """
    JSON 파일 쓰기

    Args:
        file_path: 저장할 파일 경로
        data: 저장할 데이터

    Returns:
        저장된 파일 경로
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return str(path)


@tool
def read_text_file(file_path: str) -> str:
    """
    텍스트 파일 읽기

    Args:
        file_path: 파일 경로

    Returns:
        파일 내용
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


@tool
def write_text_file(file_path: str, content: str) -> str:
    """
    텍스트 파일 쓰기

    Args:
        file_path: 저장할 파일 경로
        content: 저장할 내용

    Returns:
        저장된 파일 경로
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    return str(path)
