"""Inventory Tool - 재고 관리

재고 현황 조회 및 재고 관리 도구를 제공합니다.

Phase 0: Stub 구현 (ImportError 방지)
Phase 2: 완전 구현 예정

(기존 biz_execution/inventory/에서 이전 - 원본이 거의 비어있음)
"""

import logging
from typing import Dict, Any, List, Optional

from langchain_core.tools import tool

from ..base_tool import BaseTool, register_tool

logger = logging.getLogger(__name__)


# ============================================================
# LangGraph Tools (@tool 데코레이터)
# ============================================================

@tool
def get_inventory_status(
    product_ids: Optional[List[str]] = None,
    category: Optional[str] = None
) -> Dict[str, Any]:
    """
    재고 현황 조회

    Phase 0: Stub 모드 - Mock 데이터 반환
    Phase 2: Full 모드 - 실제 재고 시스템 연동

    Args:
        product_ids: 조회할 제품 ID 목록 (None이면 전체)
        category: 필터링할 카테고리

    Returns:
        재고 현황:
        {
            "items": [...],         # 재고 항목 리스트
            "total_count": int,     # 총 항목 수
            "low_stock_count": int, # 부족 재고 수
            "stub": bool            # Stub 모드 여부
        }
    """
    logger.info(f"[Inventory] Getting status (products={product_ids}, category={category})")

    # Stub 모드 - Mock 데이터 반환
    mock_items = [
        {
            "product_id": "SKU001",
            "name": "[Stub] 수분 에센스",
            "category": "skincare",
            "quantity": 150,
            "status": "normal"
        },
        {
            "product_id": "SKU002",
            "name": "[Stub] 비타민 세럼",
            "category": "skincare",
            "quantity": 25,
            "status": "low"
        },
        {
            "product_id": "SKU003",
            "name": "[Stub] 선크림 SPF50",
            "category": "suncare",
            "quantity": 200,
            "status": "normal"
        }
    ]

    # 필터링
    filtered_items = mock_items
    if product_ids:
        filtered_items = [i for i in filtered_items if i["product_id"] in product_ids]
    if category:
        filtered_items = [i for i in filtered_items if i["category"] == category]

    low_stock = [i for i in filtered_items if i["status"] == "low"]

    return {
        "items": filtered_items,
        "total_count": len(filtered_items),
        "low_stock_count": len(low_stock),
        "stub": True,
        "summary": "[Phase 0 Stub] 재고 관리 기능은 Phase 2에서 구현 예정입니다."
    }


@tool
def check_reorder_needs(threshold: int = 50) -> Dict[str, Any]:
    """
    재주문 필요 항목 확인

    Args:
        threshold: 재주문 기준 수량

    Returns:
        재주문 필요 항목 리스트
    """
    logger.info(f"[Inventory] Checking reorder needs (threshold={threshold})")

    # Stub 모드 - Mock 데이터
    return {
        "reorder_needed": [
            {
                "product_id": "SKU002",
                "name": "[Stub] 비타민 세럼",
                "current_quantity": 25,
                "recommended_order": 100
            }
        ],
        "count": 1,
        "threshold": threshold,
        "stub": True
    }


@tool
def update_inventory(
    product_id: str,
    quantity_change: int,
    reason: str = "adjustment"
) -> Dict[str, Any]:
    """
    재고 수량 업데이트

    Args:
        product_id: 제품 ID
        quantity_change: 수량 변경 (+/-)
        reason: 변경 사유

    Returns:
        업데이트 결과
    """
    logger.info(f"[Inventory] Updating {product_id}: {quantity_change} ({reason})")

    # Stub 모드 - 항상 성공 반환
    return {
        "success": True,
        "product_id": product_id,
        "quantity_change": quantity_change,
        "reason": reason,
        "stub": True,
        "message": "[Phase 0 Stub] 재고 업데이트 기능은 Phase 2에서 구현 예정입니다."
    }


# ============================================================
# BaseTool 클래스 (신규 패턴)
# ============================================================

@register_tool("inventory")
class InventoryTool(BaseTool):
    """재고 관리 도구

    BaseTool 패턴으로 구현된 Inventory Manager.
    재고 현황 조회 및 관리 기능을 제공합니다.

    Phase 0: Stub 구현
    Phase 2: 실제 재고 시스템 연동 예정
    """

    name: str = "inventory"
    description: str = "재고 현황 조회 및 관리"
    category: str = "business"
    version: str = "0.1.0"  # Phase 0: Stub

    def execute(
        self,
        action: str = "status",
        product_ids: Optional[List[str]] = None,
        category: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """재고 관리 실행

        Args:
            action: 실행 액션 (status, reorder, update)
            product_ids: 제품 ID 목록
            category: 카테고리 필터

        Returns:
            실행 결과
        """
        if action == "status":
            return get_inventory_status.invoke({
                "product_ids": product_ids,
                "category": category
            })
        elif action == "reorder":
            return check_reorder_needs.invoke({
                "threshold": kwargs.get("threshold", 50)
            })
        elif action == "update":
            return update_inventory.invoke({
                "product_id": kwargs.get("product_id", ""),
                "quantity_change": kwargs.get("quantity_change", 0),
                "reason": kwargs.get("reason", "adjustment")
            })
        else:
            return {"error": f"Unknown action: {action}"}

    async def aexecute(
        self,
        action: str = "status",
        product_ids: Optional[List[str]] = None,
        category: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """비동기 재고 관리 실행"""
        if action == "status":
            return await get_inventory_status.ainvoke({
                "product_ids": product_ids,
                "category": category
            })
        elif action == "reorder":
            return await check_reorder_needs.ainvoke({
                "threshold": kwargs.get("threshold", 50)
            })
        elif action == "update":
            return await update_inventory.ainvoke({
                "product_id": kwargs.get("product_id", ""),
                "quantity_change": kwargs.get("quantity_change", 0),
                "reason": kwargs.get("reason", "adjustment")
            })
        else:
            return {"error": f"Unknown action: {action}"}


# ============================================================
# Direct Function Calls (without Agent)
# ============================================================

def get_inventory_direct(
    product_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Agent 없이 직접 재고 조회"""
    return get_inventory_status.invoke({
        "product_ids": product_ids,
        "category": None
    })


def check_reorder_direct(threshold: int = 50) -> Dict[str, Any]:
    """Agent 없이 직접 재주문 확인"""
    return check_reorder_needs.invoke({"threshold": threshold})


# ============================================================
# Export 할 @tool 함수 목록
# ============================================================

INVENTORY_TOOLS = [
    get_inventory_status,
    check_reorder_needs,
    update_inventory,
]
