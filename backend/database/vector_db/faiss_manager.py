"""FAISS Vector Database Manager"""
import faiss
import numpy as np
import pickle
import os
from typing import List, Tuple


class FAISSManager:
    """FAISS 벡터 데이터베이스 관리 클래스

    벡터 저장, 검색, 로드 기능 제공
    """

    def __init__(self, index_path: str, dimension: int = 384):
        """FAISS Manager 초기화

        Args:
            index_path: FAISS 인덱스 저장 경로
            dimension: 벡터 차원 (기본값: 384, sentence-transformers/all-MiniLM-L6-v2)
        """
        self.index_path = index_path
        self.dimension = dimension
        self.index = None
        self.metadata = []  # 벡터에 대응하는 메타데이터 리스트

        # 디렉토리 생성
        os.makedirs(index_path, exist_ok=True)

        # 기존 인덱스 로드 시도
        if self._index_exists():
            self.load()
        else:
            # 새 인덱스 생성 (L2 distance)
            self.index = faiss.IndexFlatL2(dimension)

    def _index_exists(self) -> bool:
        """인덱스 파일 존재 여부 확인"""
        index_file = os.path.join(self.index_path, "index.faiss")
        metadata_file = os.path.join(self.index_path, "metadata.pkl")
        return os.path.exists(index_file) and os.path.exists(metadata_file)

    def add_vectors(self, vectors: np.ndarray, metadata: List[dict]):
        """벡터와 메타데이터 추가

        Args:
            vectors: numpy array (N, dimension)
            metadata: 각 벡터에 대응하는 메타데이터 리스트
        """
        if vectors.shape[1] != self.dimension:
            raise ValueError(f"벡터 차원이 {self.dimension}이어야 합니다. 현재: {vectors.shape[1]}")

        if len(vectors) != len(metadata):
            raise ValueError("벡터 개수와 메타데이터 개수가 일치해야 합니다.")

        # 벡터를 float32로 변환 (FAISS 요구사항)
        vectors = vectors.astype(np.float32)

        # 인덱스에 벡터 추가
        self.index.add(vectors)

        # 메타데이터 저장
        self.metadata.extend(metadata)

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[dict, float]]:
        """벡터 유사도 검색

        Args:
            query_vector: 검색할 벡터 (dimension,)
            top_k: 반환할 상위 결과 개수

        Returns:
            List of (metadata, distance) tuples
        """
        if self.index.ntotal == 0:
            return []

        # 벡터를 (1, dimension) 형태로 변환
        query_vector = query_vector.reshape(1, -1).astype(np.float32)

        # 검색 수행
        distances, indices = self.index.search(query_vector, min(top_k, self.index.ntotal))

        # 결과 반환
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.metadata):
                results.append((self.metadata[idx], float(dist)))

        return results

    def save(self):
        """인덱스와 메타데이터 저장"""
        # FAISS 인덱스 저장
        index_file = os.path.join(self.index_path, "index.faiss")
        faiss.write_index(self.index, index_file)

        # 메타데이터 저장
        metadata_file = os.path.join(self.index_path, "metadata.pkl")
        with open(metadata_file, "wb") as f:
            pickle.dump(self.metadata, f)

        print(f"✓ FAISS 인덱스 저장 완료: {self.index_path}")

    def load(self):
        """인덱스와 메타데이터 로드"""
        index_file = os.path.join(self.index_path, "index.faiss")
        metadata_file = os.path.join(self.index_path, "metadata.pkl")

        # FAISS 인덱스 로드
        self.index = faiss.read_index(index_file)

        # 메타데이터 로드
        with open(metadata_file, "rb") as f:
            self.metadata = pickle.load(f)

        print(f"✓ FAISS 인덱스 로드 완료: {self.index_path} (벡터 {self.index.ntotal}개)")

    def clear(self):
        """인덱스와 메타데이터 초기화"""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []

    def get_total_count(self) -> int:
        """저장된 벡터 개수 반환"""
        return self.index.ntotal if self.index else 0
