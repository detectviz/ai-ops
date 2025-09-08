# services/sre-assistant/src/sre_assistant/workflow.py
"""
SRE 工作流程協調器 (已重構以支援非同步任務)
"""

import asyncio
import functools
import structlog
import uuid
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

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

from .tools.prometheus_tool import PrometheusQueryTool
from .tools.loki_tool import LokiLogQueryTool
from .tools.control_plane_tool import ControlPlaneTool

# Define a union type for all possible request models
SREWorkflowRequest = Union[DiagnosticRequest, AlertAnalysisRequest, CapacityAnalysisRequest, ExecuteRequest]

logger = structlog.get_logger(__name__)


class SREWorkflow:
    """
    主要的 SRE 工作流程協調器
    
    負責：
    1. 接收診斷請求
    2. 並行執行多個診斷工具
    3. 整合分析結果
    4. 更新共享的任務狀態字典
    """
    
    def __init__(self, config, redis_client, http_client: httpx.AsyncClient):
        """初始化工作流程"""
        self.config = config
        self.redis_client = redis_client
        self.http_client = http_client # 儲存共享的 HTTP 客戶端

        # 將共享的客戶端和 redis_client 傳遞給工具
        self.prometheus_tool = PrometheusQueryTool(config, self.http_client, self.redis_client)
        self.loki_tool = LokiLogQueryTool(config, self.http_client)
        self.control_plane_tool = ControlPlaneTool(config, self.http_client)
        self.parallel_diagnosis = config.workflow.get("parallel_diagnosis", True)
        self.diagnosis_timeout = config.workflow.get("diagnosis_timeout_seconds", 120)
        self.max_retries = config.workflow.get("max_retries", 2)  # 2 retries = 3 total attempts
        self.retry_delay = config.workflow.get("retry_delay_seconds", 1)
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
        """
        start_time = datetime.now(timezone.utc)
        logger.info(f"🚀 [Session: {session_id}] 開始執行 {request_type} 工作流程...")
        
        try:
            status = await self._get_task_status(session_id)
            if not status:
                logger.error(f"無法從 Redis 中找到任務狀態: {session_id}")
                return

            result_data: Optional[Union[DiagnosticResult, CapacityAnalysisResponse]] = None
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
            if final_status:
                if isinstance(result_data, DiagnosticResult):
                    final_status.result = result_data
                    final_status.result.execution_time = execution_time
                # Note: CapacityAnalysisResponse is a direct return, not part of DiagnosticStatus
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
            ("prometheus", functools.partial(self.prometheus_tool.execute, {"service": request.affected_services[0]})),
            ("loki", functools.partial(self.loki_tool.execute, {"service": request.affected_services[0]})),
            ("audit", functools.partial(self.control_plane_tool.query_audit_logs, {"resource_type": "deployment", "search": request.affected_services[0]})),
            ("incidents", functools.partial(self.control_plane_tool.query_incidents, {"search": request.affected_services[0], "status": "new,acknowledged"}))
        ]
        
        status.current_step = "並行執行診斷工具 (含重試)"
        status.progress = 50
        await self._update_task_status(session_id, status)

        results = await self._execute_parallel_tasks(tool_tasks)
        
        status.current_step = "分析診斷結果"
        status.progress = 80
        await self._update_task_status(session_id, status)
        
        return self._analyze_deployment_results(results)

    async def _run_task_with_retry(self, name: str, coro_factory) -> Any:
        """
        執行單一任務，並帶有重試和指數退避邏輯。
        """
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                task_coro = coro_factory()
                result = await asyncio.wait_for(task_coro, timeout=self.diagnosis_timeout)
                if attempt > 0:
                    logger.info(f"✅ 工具 {name} 在第 {attempt + 1} 次嘗試後成功。")
                return result
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"⚠️ 工具 {name} 第 {attempt + 1}/{self.max_retries + 1} 次執行失敗: {e}. "
                        f"將在 {delay:.2f} 秒後重試..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"❌ 工具 {name} 在 {self.max_retries + 1} 次嘗試後最終失敗。"
                    )
                    raise last_exception

    async def _execute_parallel_tasks(self, tool_tasks: List[tuple]) -> Dict[str, ToolResult]:
        """
        並行執行多個異步診斷工具任務。
        """
        results = {}

        tasks_to_gather = [
            self._run_task_with_retry(name, coro_factory) for name, coro_factory in tool_tasks
        ]

        task_results = await asyncio.gather(*tasks_to_gather, return_exceptions=True)
        
        for i, (name, _) in enumerate(tool_tasks):
            result = task_results[i]
            if isinstance(result, Exception):
                error_code = "TOOL_TIMEOUT_ERROR" if isinstance(result, asyncio.TimeoutError) else "TOOL_EXECUTION_ERROR"
                results[name] = ToolResult(success=False, error=ToolError(code=error_code, message=str(result)))
            else:
                results[name] = result
        return results
    
    def _analyze_deployment_results(self, results: Dict[str, ToolResult]) -> DiagnosticResult:
        """分析部署診斷結果"""
        all_findings = []
        tools_used = []
        
        if "prometheus" in results and results["prometheus"].success:
            tools_used.append("PrometheusQueryTool")
            metrics = results["prometheus"].data
            if metrics and float(metrics.get("cpu_usage", "0%").replace("%", "")) > 80:
                all_findings.append(Finding(source="Prometheus", severity="critical", message="CPU 使用率過高", evidence=metrics))
            if metrics and float(metrics.get("memory_usage", "0%").replace("%", "")) > 90:
                all_findings.append(Finding(source="Prometheus", severity="critical", message="記憶體使用率過高", evidence=metrics))

        if "loki" in results and results["loki"].success:
            tools_used.append("LokiLogQueryTool")
            logs = results["loki"].data
            analysis = logs.get("analysis", {})
            critical_indicators = analysis.get("critical_indicators")
            if critical_indicators:
                all_findings.append(Finding(source="Loki", severity="critical", message=f"發現嚴重日誌指標: {', '.join(critical_indicators)}", evidence=logs))

        if "audit" in results and results["audit"].success:
            tools_used.append("ControlPlaneTool (Audit)")
            audit = results["audit"].data
            if audit.get("logs"):
                all_findings.append(Finding(source="Control-Plane", severity="info", message=f"發現 {len(audit['logs'])} 筆相關審計日誌。", evidence=audit))

        if "incidents" in results and results["incidents"].success:
            tools_used.append("ControlPlaneTool (Incidents)")
            incidents = results["incidents"].data
            if incidents.get("incidents"):
                all_findings.append(Finding(source="Control-Plane", severity="warning", message=f"發現 {len(incidents['incidents'])} 件相關的活躍事件。", evidence=incidents))

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

    async def _analyze_capacity(self, session_id: uuid.UUID, request: CapacityAnalysisRequest, status: DiagnosticStatus) -> CapacityAnalysisResponse:
        """
        分析指定資源的容量使用情況和趨勢。
        """
        logger.info(f"📈 [Session: {session_id}] 開始分析容量: {request.resource_ids}")

        if not request.resource_ids:
            # 雖然 API 契約要求至少一個 ID，但還是做個防禦性檢查
            raise ValueError("CapacityAnalysisRequest 中必須至少提供一個 resource_id。")

        # 暫時只處理第一個 resource_id
        resource_id = request.resource_ids[0]

        # 1. 從 Control Plane 獲取資源詳情，以得到服務名稱
        resource_details_result = await self.control_plane_tool.get_resource_details(resource_id)
        if not resource_details_result.success:
            logger.error(f"無法獲取資源詳情 {resource_id}: {resource_details_result.error.message}")
            # 這裡可以根據錯誤類型決定是否要拋出異常或回傳一個錯誤的回應
            # 為了簡單起見，我們直接拋出異常，讓外層的 try-except 捕捉
            raise Exception(f"獲取資源 {resource_id} 詳情失敗。")

        service_name = resource_details_result.data.get("name")
        if not service_name:
            raise ValueError(f"資源 {resource_id} 的詳細資料中缺少 'name' 欄位。")

        # 2. 使用服務名稱從 Prometheus 查詢飽和度指標
        prometheus_params = {"service": service_name, "metric_type": "saturation"}
        saturation_result = await self.prometheus_tool.execute(prometheus_params)
        if not saturation_result.success:
            logger.error(f"無法獲取服務 {service_name} 的飽和度指標: {saturation_result.error.message}")
            raise Exception(f"獲取服務 {service_name} 的飽和度指標失敗。")

        metrics = saturation_result.data

        # 3. 進行簡單的分析和預測
        # 注意：這是一個非常簡化的模型，真實世界中會使用更複雜的時間序列預測演算法
        cpu_usage = float(metrics.get("cpu_usage", "0%").strip('%'))
        mem_usage = float(metrics.get("memory_usage", "0%").strip('%'))

        recommendations = []
        if cpu_usage > 85.0:
            recommendations.append({
                "type": "scale_up",
                "resource": resource_id,
                "priority": "high",
                "reasoning": f"當前 CPU 使用率 ({cpu_usage:.1f}%) 已超過 85% 的閾值。"
            })
        if mem_usage > 85.0:
            recommendations.append({
                "type": "scale_up",
                "resource": resource_id,
                "priority": "high",
                "reasoning": f"當前記憶體使用率 ({mem_usage:.1f}%) 已超過 85% 的閾值。"
            })

        # 4. 建立並回傳回應
        return CapacityAnalysisResponse(
            current_usage={"peak": cpu_usage, "average": mem_usage},
            forecast={"trend": "stable", "days_to_capacity": 90}, # 預測部分暫時使用假資料
            recommendations=recommendations
        )

    async def _diagnose_alerts(self, session_id: uuid.UUID, request: AlertAnalysisRequest, status: DiagnosticStatus) -> DiagnosticResult:
        """
        診斷告警問題
        """
        logger.info(f"🔍 [Session: {session_id}] 開始診斷告警: {request.alert_ids}")
        return DiagnosticResult(summary="告警分析功能尚未完全實作。", findings=[], recommended_actions=[])

    async def _execute_query(self, session_id: uuid.UUID, request: ExecuteRequest, status: DiagnosticStatus) -> DiagnosticResult:
        """
        執行自然語言查詢 (骨架)
        """
        logger.info(f"🤖 [Session: {session_id}] 執行查詢: {request.query}")
        return DiagnosticResult(summary=f"已執行查詢: '{request.query}'", findings=[], recommended_actions=["無"])
