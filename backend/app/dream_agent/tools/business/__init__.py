"""Business Tools - 비즈니스 도구

세일즈, 재고 관리, 대시보드 관련 도구를 제공합니다.

모듈:
- sales.py: 세일즈 전략 도구
- inventory.py: 재고 관리 도구
- dashboard.py: 대시보드 데이터 도구
"""

# Sales Tools
from .sales import (
    # @tool 함수
    generate_sales_plan,
    generate_pitch_deck,
    SALES_TOOLS,
    # BaseTool 클래스
    SalesTool,
    # Direct 함수
    generate_sales_plan_direct,
)

# Inventory Tools
from .inventory import (
    # @tool 함수
    get_inventory_status,
    check_reorder_needs,
    update_inventory,
    INVENTORY_TOOLS,
    # BaseTool 클래스
    InventoryTool,
    # Direct 함수
    get_inventory_direct,
    check_reorder_direct,
)

# Dashboard Tools
from .dashboard import (
    # @tool 함수
    generate_dashboard,
    get_dashboard_metrics,
    DASHBOARD_TOOLS,
    # BaseTool 클래스
    DashboardTool,
    # Direct 함수
    generate_dashboard_direct,
    get_metrics_direct,
)

__all__ = [
    # Sales
    "generate_sales_plan",
    "generate_pitch_deck",
    "SALES_TOOLS",
    "SalesTool",
    "generate_sales_plan_direct",
    # Inventory
    "get_inventory_status",
    "check_reorder_needs",
    "update_inventory",
    "INVENTORY_TOOLS",
    "InventoryTool",
    "get_inventory_direct",
    "check_reorder_direct",
    # Dashboard
    "generate_dashboard",
    "get_dashboard_metrics",
    "DASHBOARD_TOOLS",
    "DashboardTool",
    "generate_dashboard_direct",
    "get_metrics_direct",
]
