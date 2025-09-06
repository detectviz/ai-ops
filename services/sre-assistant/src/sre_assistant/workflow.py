# services/sre-assistant/src/sre_assistant/workflow.py
"""
SRE 工作流程協調器 (已重構以支援非同步任務)
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from typing import Union
from .contracts import (
    DiagnosticRequest,
    DiagnosticResult,
    DiagnosticStatus,
    ToolResult,
    ToolError,
    Finding,
    AlertAnalysisRequest,
    CapacityAnalysisRequest,
    ExecuteRequest,
    CapacityAnalysisResponse,
)

# Define a union type for all possible request models
SREWorkflowRequest = Union[DiagnosticRequest, AlertAnalysisRequest, CapacityAnalysisRequest, ExecuteRequest]
from .tools.prometheus_tool import PrometheusQueryTool
from .tools.loki_tool import LokiLogQueryTool
from .tools.control_plane_tool import ControlPlaneTool

logger = logging.getLogger(__name__)


class SREWorkflow:
    """
    主要的 SRE 工作流程協調器
    
    負責：
    1. 接收診斷請求
    2. 並行執行多個診斷工具
    3. 整合分析結果
    4. 更新共享的任務狀態字典
    """
    
    def __init__(self, config, redis_client):
        """初始化工作流程"""
        self.config = config
        self.redis_client = redis_client
        self.prometheus_tool = PrometheusQueryTool(config)
        self.loki_tool = LokiLogQueryTool(config)
        self.control_plane_tool = ControlPlaneTool(config)
        self.parallel_diagnosis = config.workflow.get("parallel_diagnosis", True)
        self.diagnosis_timeout = config.workflow.get("diagnosis_timeout_seconds", 120)
        logger.info("✅ SRE 工作流程初始化完成")
    
    async def _get_task_status(self, session_id: uuid.UUID) -> Optional[DiagnosticStatus]:
        """Helper to get task status from Redis."""
        task_json = await self.redis_client.get(str(session_id))
        if task_json:
            return DiagnosticStatus.model_validate_json(task_json)
        return None

    async def _update_task_status(self, session_id: uuid.UUID, status: DiagnosticStatus):
        """Helper to update task status in Redis."""
        await self.redis_client.set(str(session_id), status.model_dump_json(), ex=86400)

    async def execute(self, session_id: uuid.UUID, request: SREWorkflowRequest, request_type: str):
        """
        執行主要工作流程 (背景任務)。

        這是工作流程的核心入口點，由背景任務呼叫。它會根據 `request_type`
        將請求路由到對應的處理函式 (例如 `_diagnose_deployment`)。

        它還負責：
        - 記錄執行時間。
        - 從 Redis 獲取和更新任務狀態。
        - 捕獲和記錄任何未預期的錯誤。
        
        Args:
            session_id: 此任務的唯一會話 ID。
            request: SRE 請求物件 (一個 Pydantic 模型)。
            request_type: 請求的類型，用於決定執行哪個子流程。
        """
        start_time = datetime.now(timezone.utc)
        logger.info(f"🚀 [Session: {session_id}] 開始執行 {request_type} 工作流程...")
        
        try:
            status = await self._get_task_status(session_id)
            if not status:
                logger.error(f"無法從 Redis 中找到任務狀態: {session_id}")
                return

            result_data = None
            if request_type == "deployment" and isinstance(request, DiagnosticRequest):
                result_data = await self._diagnose_deployment(session_id, request, status)
            elif request_type == "alert_analysis" and isinstance(request, AlertAnalysisRequest):
                result_data = await self._diagnose_alerts(session_id, request, status)
            elif request_type == "execute_query" and isinstance(request, ExecuteRequest):
                result_data = await self._execute_query(session_id, request, status)
            elif request_type == "capacity_analysis" and isinstance(request, CapacityAnalysisRequest):
                result_data = await self._analyze_capacity(session_id, request, status)
            else:
                raise ValueError(f"未知的請求類型或請求與類型不匹配: {request_type}")

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            final_status = await self._get_task_status(session_id)
            if final_status and isinstance(result_data, DiagnosticResult):
                final_status.result = result_data
                final_status.result.execution_time = execution_time
                final_status.status = "completed"
                final_status.progress = 100
                final_status.current_step = "診斷完成"
                await self._update_task_status(session_id, final_status)
            
            logger.info(f"✅ [Session: {session_id}] 工作流程完成 (耗時 {execution_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"❌ [Session: {session_id}] 工作流程執行失敗: {e}", exc_info=True)
            final_status = await self._get_task_status(session_id)
            if final_status:
                final_status.status = "failed"
                final_status.error = f"工作流程發生未預期錯誤: {e}"
                await self._update_task_status(session_id, final_status)
    
    async def _diagnose_deployment(self, session_id: uuid.UUID, request: DiagnosticRequest, status: DiagnosticStatus) -> DiagnosticResult:
        """
        診斷部署問題
        """
        logger.info(f"🔍 [Session: {session_id}] 診斷部署: {request.affected_services[0]}")
        
        status.current_step = "準備診斷任務"
        status.progress = 20
        await self._update_task_status(session_id, status)
        
        tool_tasks = [
            ("prometheus", self.prometheus_tool.execute({"service": request.affected_services[0]})),
            ("loki", self.loki_tool.execute({"service": request.affected_services[0]})),
            ("audit", self.control_plane_tool.execute({"service": request.affected_services[0]}))
        ]
        
        status.current_step = "並行執行診斷工具"
        status.progress = 50
        await self._update_task_status(session_id, status)

        results = await self._execute_parallel_tasks(tool_tasks)
        
        status.current_step = "分析診斷結果"
        status.progress = 80
        await self._update_task_status(session_id, status)
        
        return self._analyze_deployment_results(results, request)
    
    async def _execute_parallel_tasks(self, tool_tasks: List[tuple]) -> Dict[str, ToolResult]:
        """
        並行執行多個異步診斷工具任務，並對每個任務實施超時控制。

        使用 `asyncio.gather` 來並發執行所有工具，並透過 `return_exceptions=True`
        確保即使某個工具失敗或超時，其他工具也能繼續執行。

        Args:
            tool_tasks: 一個包含 (名稱, 協程) 的元組列表。

        Returns:
            一個字典，鍵是工具名稱，值是其 `ToolResult`。
        """
        results = {}

        tasks_with_timeout = [
            asyncio.wait_for(task, timeout=self.diagnosis_timeout) for _, task in tool_tasks
        ]

        task_results = await asyncio.gather(*tasks_with_timeout, return_exceptions=True)
        
        for i, (name, _) in enumerate(tool_tasks):
            result = task_results[i]
            if isinstance(result, asyncio.TimeoutError):
                logger.warning(f"工具 {name} 執行超時 (超過 {self.diagnosis_timeout} 秒)")
                results[name] = ToolResult(success=False, error=ToolError(code="TOOL_TIMEOUT_ERROR", message=f"執行超時，限制為 {self.diagnosis_timeout} 秒"))
            elif isinstance(result, Exception):
                logger.warning(f"工具 {name} 執行失敗: {result}")
                results[name] = ToolResult(success=False, error=ToolError(code="TOOL_EXECUTION_ERROR", message=str(result)))
            else:
                results[name] = result
        return results
    
    def _analyze_deployment_results(self, results: Dict[str, ToolResult], request: DiagnosticRequest) -> DiagnosticResult:
        """分析部署診斷結果"""
        all_findings = []
        tools_used = []
        
        if "prometheus" in results and results["prometheus"].success:
            tools_used.append("PrometheusQueryTool")
            metrics = results["prometheus"].data
            if float(metrics.get("cpu_usage", "0%").replace("%", "")) > 80:
                all_findings.append(Finding(source="Prometheus", severity="critical", message="CPU 使用率過高", evidence=metrics))
            if float(metrics.get("memory_usage", "0%").replace("%", "")) > 90:
                all_findings.append(Finding(source="Prometheus", severity="critical", message="記憶體使用率過高", evidence=metrics))

        if "loki" in results and results["loki"].success:
            tools_used.append("LokiLogQueryTool")
            logs = results["loki"].data
            if logs.get("critical_errors"):
                all_findings.append(Finding(source="Loki", severity="critical", message=f"發現嚴重錯誤日誌: {logs['critical_errors']}", evidence=logs))

        if "audit" in results and results["audit"].success:
            tools_used.append("ControlPlaneTool")
            audit = results["audit"].data
            if audit.get("recent_changes"):
                all_findings.append(Finding(source="Control-Plane", severity="warning", message=f"發現最近有配置變更", evidence=audit))

        if all_findings:
            summary = f"診斷完成，共發現 {len(all_findings)} 個問題點。"
            recommended_actions = ["請根據發現的詳細資訊進行深入調查。"]
            confidence_score = 0.8
        else:
            summary = "初步診斷未發現明顯問題。"
            recommended_actions = ["建議手動檢查服務日誌和監控儀表板。"]
            confidence_score = 0.5
            
        return DiagnosticResult(
            summary=summary,
            findings=all_findings,
            recommended_actions=recommended_actions,
            confidence_score=confidence_score,
            tools_used=tools_used
        )

    async def _diagnose_alerts(self, session_id: uuid.UUID, request: AlertAnalysisRequest, status: DiagnosticStatus) -> DiagnosticResult:
        """
        診斷告警問題 (骨架)
        """
        logger.info(f"🔍 [Session: {session_id}] 診斷告警: {request.alert_ids}")
        status.current_step = "分析告警關聯性"
        status.progress = 50
        await self._update_task_status(session_id, status)
        await asyncio.sleep(2) # 模擬工作

        status.current_step = "生成告警診斷報告"
        status.progress = 90
        await self._update_task_status(session_id, status)
        return DiagnosticResult(summary=f"已分析 {len(request.alert_ids)} 個告警。", findings=[], recommended_actions=["檢查關聯服務的日誌"])

    async def _analyze_capacity(self, session_id: uuid.UUID, request: CapacityAnalysisRequest, status: DiagnosticStatus) -> CapacityAnalysisResponse:
        """
        分析容量問題 (骨架)
        """
        logger.info(f"📈 [Session: {session_id}] 分析容量: {request.resource_ids}")
        return CapacityAnalysisResponse(
            current_usage={"average": 55.5, "peak": 80.2},
            forecast={"trend": "increasing", "days_to_capacity": 45},
            recommendations=[{"type": "scale_up", "resource": request.resource_ids[0], "priority": "high", "reasoning": "預測使用量將在 45 天後達到瓶頸"}]
        )

    async def _execute_query(self, session_id: uuid.UUID, request: ExecuteRequest, status: DiagnosticStatus) -> DiagnosticResult:
        """
        執行自然語言查詢 (骨架)
        """
        logger.info(f"🤖 [Session: {session_id}] 執行查詢: {request.query}")
        status.current_step = "解析自然語言查詢"
        status.progress = 30
        await self._update_task_status(session_id, status)
        await asyncio.sleep(1)

        status.current_step = "執行對應的工具"
        status.progress = 70
        await self._update_task_status(session_id, status)
        await asyncio.sleep(2)
        return DiagnosticResult(summary=f"已執行查詢: '{request.query}'", findings=[], recommended_actions=["無"])