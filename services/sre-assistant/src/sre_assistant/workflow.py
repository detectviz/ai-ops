# services/sre-assistant/src/sre_assistant/workflow.py
"""
SRE 工作流程協調器 (已重構以支援非同步任務)
"""

import asyncio
import functools
import structlog
import uuid
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
    
    def __init__(self, config, redis_client, http_client):
        """
        初始化工作流程

        Args:
            config: 應用程式設定物件。
            redis_client: 非同步 Redis 客戶端。
            http_client: 共享的 httpx.AsyncClient 實例。
        """
        self.config = config
        self.redis_client = redis_client
        self.http_client = http_client # 儲存共享客戶端

        # 將共享的 http_client 和其他依賴注入到所有工具中
        self.prometheus_tool = PrometheusQueryTool(config, http_client, self.redis_client)
        self.loki_tool = LokiLogQueryTool(config, http_client)
        self.control_plane_tool = ControlPlaneTool(config, http_client)

        self.parallel_diagnosis = config.workflow.get("parallel_diagnosis", True)
        self.diagnosis_timeout = config.workflow.get("diagnosis_timeout_seconds", 120)
        self.max_retries = config.workflow.get("max_retries", 2)
        self.retry_delay = config.workflow.get("retry_delay_seconds", 1)
        logger.info("✅ SRE 工作流程初始化完成 (使用共享 HTTP 客戶端)")
    
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
        
        # 使用 functools.partial 來創建可重複呼叫的任務工廠
        # 定義要並行執行的工具任務
        # 每個任務都是一個元組 (名稱, 可呼叫的協程工廠)
        # functools.partial 用於預先綁定參數，使所有工具的呼叫簽名一致
        # 定義要並行執行的工具任務
        # 每個任務都是一個元組 (名稱, 可呼叫的協程工廠)
        # functools.partial 用於預先綁定參數，使所有工具的呼叫簽名一致
        tool_tasks = [
            ("prometheus", functools.partial(self.prometheus_tool.execute, {"service": request.affected_services[0]})),
            ("loki", functools.partial(self.loki_tool.execute, {"service": request.affected_services[0]})),
            ("audit", functools.partial(self.control_plane_tool.query_audit_logs, {"resource_type": "deployment", "search": request.affected_services[0]})),
            # 新增：根據測試要求，加入對相關事件的查詢
            ("incidents", functools.partial(self.control_plane_tool.query_incidents, {"search": request.affected_services[0], "status": "new,acknowledged"}))
        ]
        
        status.current_step = "並行執行診斷工具 (含重試)"
        status.progress = 50
        await self._update_task_status(session_id, status)

        results = await self._execute_parallel_tasks(tool_tasks)
        
        status.current_step = "分析診斷結果"
        status.progress = 80
        await self._update_task_status(session_id, status)
        
        return self._analyze_deployment_results(results, request)

    async def _run_task_with_retry(self, name: str, coro_factory) -> Any:
        """
        執行單一任務，並帶有重試和指數退避邏輯。
        
        Args:
            name: 工具的名稱 (用於日誌)。
            coro_factory: 一個無參數的函數，每次呼叫都會返回一個新的協程物件。

        Returns:
            成功執行後的結果。
        
        Raises:
            Exception: 如果所有重試都失敗，則拋出最後一次的異常。
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
                    # 指數退避延遲
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
        並行執行多個異步診斷工具任務，每個任務都包含重試邏輯。

        使用 `asyncio.gather` 來並發執行所有工具，並透過 `return_exceptions=True`
        確保即使某個工具最終失敗，其他工具也能繼續執行。

        Args:
            tool_tasks: 一個包含 (名稱, 協程工廠) 的元組列表。

        Returns:
            一個字典，鍵是工具名稱，值是其 `ToolResult`。
        """
        results = {}

        tasks_to_gather = [
            self._run_task_with_retry(name, coro_factory) for name, coro_factory in tool_tasks
        ]

        task_results = await asyncio.gather(*tasks_to_gather, return_exceptions=True)
        
        for i, (name, _) in enumerate(tool_tasks):
            result = task_results[i]
            if isinstance(result, Exception):
                # The exception is already logged in _run_task_with_retry
                # We just need to format it for the final result.
                error_code = "TOOL_TIMEOUT_ERROR" if isinstance(result, asyncio.TimeoutError) else "TOOL_EXECUTION_ERROR"
                results[name] = ToolResult(success=False, error=ToolError(code=error_code, message=str(result)))
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
            # 修正：對齊測試中模擬的、更真實的巢狀資料結構
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

    async def analyze_capacity(self, request: CapacityAnalysisRequest) -> CapacityAnalysisResponse:
        """
        分析給定資源的容量。

        此方法會並行查詢所有請求資源的飽和度指標，
        計算平均使用率，並產生一個簡單的預測和建議。
        """
        logger.info(f"📈 開始分析容量，資源: {request.resource_ids}")

        # 為每個資源建立一個並行查詢任務
        tasks = [
            self._run_task_with_retry(
                name=f"saturation_check_{resource_id}",
                coro_factory=functools.partial(
                    self.prometheus_tool.execute,
                    {"service": resource_id, "metric_type": "saturation"}
                )
            )
            for resource_id in request.resource_ids
        ]

        # 執行所有查詢
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 處理和匯總結果
        total_cpu = 0
        total_mem = 0
        valid_results = 0

        for result in results:
            if isinstance(result, ToolResult) and result.success and result.data:
                saturation_data = result.data.get("saturation", {})
                try:
                    cpu_usage = float(saturation_data.get("cpu_usage", "0%").replace("%", ""))
                    mem_usage = float(saturation_data.get("memory_usage", "0%").replace("%", ""))
                    total_cpu += cpu_usage
                    total_mem += mem_usage
                    valid_results += 1
                except (ValueError, TypeError):
                    logger.warning(f"無法解析飽和度數據: {saturation_data}")
                    continue

        if valid_results == 0:
            logger.warning("所有資源的容量指標查詢均失敗。")
            # 返回一個表示失敗或數據不足的回應
            return CapacityAnalysisResponse(
                current_usage={"average": 0, "peak": 0},
                forecast={"trend": "unknown", "days_to_capacity": -1},
                recommendations=[{"type": "investigate", "resource": "all", "priority": "high", "reasoning": "無法獲取任何資源的容量指標。"}]
            )

        avg_cpu = total_cpu / valid_results
        avg_mem = total_mem / valid_results

        # 產生簡單的預測和建議
        trend = "stable"
        days_to_capacity = 999
        recommendations = []

        if avg_cpu > 85 or avg_mem > 85:
            trend = "critical"
            days_to_capacity = 1
            recommendations.append({
                "type": "scale_up",
                "resource": "all_requested",
                "priority": "critical",
                "reasoning": f"平均資源使用率過高 (CPU: {avg_cpu:.1f}%, Memory: {avg_mem:.1f}%)"
            })
        elif avg_cpu > 70 or avg_mem > 70:
            trend = "increasing"
            days_to_capacity = 30
            recommendations.append({
                "type": "scale_up",
                "resource": "all_requested",
                "priority": "high",
                "reasoning": f"平均資源使用率偏高 (CPU: {avg_cpu:.1f}%, Memory: {avg_mem:.1f}%)"
            })
        else:
            recommendations.append({
                "type": "none",
                "resource": "all_requested",
                "priority": "low",
                "reasoning": "目前資源使用率在正常範圍內。"
            })

        return CapacityAnalysisResponse(
            current_usage={"average": round((avg_cpu + avg_mem) / 2, 2), "peak": max(avg_cpu, avg_mem)},
            forecast={"trend": trend, "days_to_capacity": days_to_capacity},
            recommendations=recommendations
        )

    async def _diagnose_alerts(self, session_id: uuid.UUID, request: AlertAnalysisRequest, status: DiagnosticStatus) -> DiagnosticResult:
        """
        診斷告警問題。

        此方法會並行調查多個告警，收集相關的日誌和指標，
        並將結果匯總成一份診斷報告。
        """
        logger.info(f"🔍 [Session: {session_id}] 開始診斷告警: {request.alert_ids}")
        status.current_step = "建立並行告警調查任務"
        status.progress = 20
        await self._update_task_status(session_id, status)

        # 為每個告警 ID 建立一個調查任務
        investigation_tasks = [
            self._investigate_single_alert(alert_id, request.correlation_window)
            for alert_id in request.alert_ids
        ]

        # 並行執行所有調查
        all_findings_lists = await asyncio.gather(*investigation_tasks, return_exceptions=True)

        status.current_step = "整合與分析調查結果"
        status.progress = 80
        await self._update_task_status(session_id, status)

        # 處理並扁平化結果
        all_findings: List[Finding] = []
        tools_used = set()
        for result in all_findings_lists:
            if isinstance(result, Exception):
                logger.error(f"調查任務失敗: {result}", exc_info=True)
                all_findings.append(Finding(
                    source="SREWorkflow",
                    severity="warning",
                    message=f"一個告警調查子任務失敗: {result}"
                ))
            elif isinstance(result, tuple):
                findings, used_tool_names = result
                all_findings.extend(findings)
                tools_used.update(used_tool_names)

        # 產生最終報告
        if not all_findings:
            summary = "完成告警分析，未發現任何具體的日誌或指標異常。"
            recommended_actions = ["建議手動檢查告警儀表板以獲取更多上下文。"]
            confidence_score = 0.4
        else:
            summary = f"告警分析完成，共產生 {len(all_findings)} 條相關發現。"
            # TODO: Add more sophisticated summary logic
            recommended_actions = ["請檢閱下方的發現以了解詳細資訊。", "根據發現的嚴重性採取行動。"]
            confidence_score = 0.75

        return DiagnosticResult(
            summary=summary,
            findings=all_findings,
            recommended_actions=recommended_actions,
            confidence_score=confidence_score,
            tools_used=list(tools_used)
        )

    async def _investigate_single_alert(self, alert_id: str, window_seconds: int) -> tuple[List[Finding], List[str]]:
        """
        調查單一告警，獲取相關的日誌和指標。
        """
        findings: List[Finding] = []
        tools_used: List[str] = []

        # 1. 從 Control Plane 獲取告警詳情
        incident_result = await self.control_plane_tool.query_incidents(params={"search": alert_id, "limit": 1})
        tools_used.append("ControlPlaneTool (Incidents)")

        if not incident_result.success or not incident_result.data.get("incidents"):
            findings.append(Finding(source="ControlPlaneTool", severity="warning", message=f"無法獲取 ID 為 {alert_id} 的告警詳情。"))
            return findings, tools_used

        incident = incident_result.data["incidents"][0]
        service_name = incident.get("service_name", "unknown-service")
        alert_time_str = incident.get("created_at", datetime.now(timezone.utc).isoformat())
        alert_time = datetime.fromisoformat(alert_time_str)

        findings.append(Finding(
            source="ControlPlaneTool",
            severity="info",
            message=f"正在調查告警 '{incident.get('title', alert_id)}'，影響服務: {service_name}。",
            evidence=incident,
            timestamp=alert_time
        ))

        # 2. 準備並行查詢日誌和指標
        half_window = window_seconds / 2
        start_time = alert_time - timedelta(seconds=half_window)
        end_time = alert_time + timedelta(seconds=half_window)

        loki_params = {
            "service": service_name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "limit": 100
        }

        # 假設告警規則中可能包含 prometheus 查詢
        # 這部分邏輯可以根據實際的 `incident` 資料結構進行擴充
        prom_query = incident.get("details", {}).get("prometheus_query")

        tool_tasks = [
            ("loki", functools.partial(self.loki_tool.execute, loki_params))
        ]
        if prom_query:
            prom_params = {"query": prom_query, "time": alert_time.isoformat()}
            tool_tasks.append(("prometheus", functools.partial(self.prometheus_tool.execute, prom_params)))

        # 3. 執行查詢
        results = await self._execute_parallel_tasks(tool_tasks)

        # 4. 處理查詢結果
        if "loki" in results:
            tools_used.append("LokiLogQueryTool")
            if results["loki"].success and results["loki"].data.get("logs"):
                log_count = len(results["loki"].data["logs"])
                findings.append(Finding(
                    source="Loki",
                    severity="info",
                    message=f"在告警時間窗口內發現 {log_count} 條日誌。",
                    evidence=results["loki"].data
                ))

        if "prometheus" in results:
            tools_used.append("PrometheusQueryTool")
            if results["prometheus"].success and results["prometheus"].data.get("value"):
                findings.append(Finding(
                    source="Prometheus",
                    severity="info",
                    message="執行告警相關的 Prometheus 查詢成功。",
                    evidence=results["prometheus"].data
                ))

        return findings, tools_used

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