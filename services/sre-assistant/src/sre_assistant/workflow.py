# services/sre-assistant/src/sre_assistant/workflow.py
"""
SRE 工作流程協調器 (已重構以支援非同步任務)
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .contracts import (
    DiagnosticRequest,
    DiagnosticResult,
    DiagnosticStatus,
    ToolResult,
    ToolError,
    Finding
)
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
    
    def __init__(self, config):
        """初始化工作流程"""
        self.config = config
        self.prometheus_tool = PrometheusQueryTool(config)
        self.loki_tool = LokiLogQueryTool(config)
        self.control_plane_tool = ControlPlaneTool(config)
        self.parallel_diagnosis = config.workflow.get("parallel_diagnosis", True)
        self.diagnosis_timeout = config.workflow.get("diagnosis_timeout_seconds", 120)
        logger.info("✅ SRE 工作流程初始化完成")
    
    async def execute(self, session_id: uuid.UUID, request: DiagnosticRequest, tasks: Dict[uuid.UUID, DiagnosticStatus]):
        """
        執行主要工作流程 (背景任務)
        
        Args:
            session_id: 此任務的唯一會話 ID
            request: SRE 請求物件
            tasks: 用於更新狀態的共享字典
        """
        start_time = datetime.now(timezone.utc)
        logger.info(f"🚀 [Session: {session_id}] 開始執行工作流程...")
        
        try:
            # 根據請求類型決定執行策略
            # TODO: 為 alerts, capacity, execute 等實現不同的診斷流程
            result_data = await self._diagnose_deployment(session_id, request, tasks)
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            result_data.execution_time = execution_time
            
            # 更新最終結果
            tasks[session_id].status = "completed"
            tasks[session_id].progress = 100
            tasks[session_id].result = result_data
            tasks[session_id].current_step = "診斷完成"
            
            logger.info(f"✅ [Session: {session_id}] 工作流程完成 (耗時 {execution_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"❌ [Session: {session_id}] 工作流程執行失敗: {e}", exc_info=True)
            tasks[session_id].status = "failed"
            tasks[session_id].error = f"工作流程發生未預期錯誤: {e}"
    
    async def _diagnose_deployment(self, session_id: uuid.UUID, request: DiagnosticRequest, tasks: Dict[uuid.UUID, DiagnosticStatus]) -> DiagnosticResult:
        """
        診斷部署問題
        """
        logger.info(f"🔍 [Session: {session_id}] 診斷部署: {request.affected_services[0]}")
        
        tasks[session_id].current_step = "準備診斷任務"
        tasks[session_id].progress = 20
        
        # 準備診斷任務
        tool_tasks = [
            ("prometheus", self.prometheus_tool.execute({"service": request.affected_services[0]})),
            ("loki", self.loki_tool.execute({"service": request.affected_services[0]})),
            ("audit", self.control_plane_tool.execute({"service": request.affected_services[0]}))
        ]
        
        tasks[session_id].current_step = "並行執行診斷工具"
        tasks[session_id].progress = 50

        # 並行執行所有診斷
        results = await self._execute_parallel_tasks(tool_tasks)
        
        tasks[session_id].current_step = "分析診斷結果"
        tasks[session_id].progress = 80
        
        # 分析結果並生成報告
        return self._analyze_deployment_results(results, request)
    
    async def _execute_parallel_tasks(self, tool_tasks: List[tuple]) -> Dict[str, ToolResult]:
        """並行執行診斷工具任務"""
        results = {}
        tasks_to_run = [task for _, task in tool_tasks]
        task_results = await asyncio.gather(*tasks_to_run, return_exceptions=True)
        
        for i, (name, _) in enumerate(tool_tasks):
            result = task_results[i]
            if isinstance(result, Exception):
                logger.warning(f"工具 {name} 執行失敗: {result}")
                results[name] = ToolResult(success=False, error=ToolError(code="TOOL_EXECUTION_ERROR", message=str(result)))
            else:
                results[name] = result
        return results
    
    def _analyze_deployment_results(self, results: Dict[str, ToolResult], request: DiagnosticRequest) -> DiagnosticResult:
        """分析部署診斷結果"""
        all_findings = []
        tools_used = []
        
        # 分析 Prometheus 結果
        if "prometheus" in results and results["prometheus"].success:
            tools_used.append("PrometheusQueryTool")
            metrics = results["prometheus"].data
            if float(metrics.get("cpu_usage", "0%").replace("%", "")) > 80:
                all_findings.append(Finding(source="Prometheus", severity="critical", message="CPU 使用率過高", evidence=metrics))
            if float(metrics.get("memory_usage", "0%").replace("%", "")) > 90:
                all_findings.append(Finding(source="Prometheus", severity="critical", message="記憶體使用率過高", evidence=metrics))

        # 分析 Loki 結果
        if "loki" in results and results["loki"].success:
            tools_used.append("LokiLogQueryTool")
            logs = results["loki"].data
            if logs.get("critical_errors"):
                all_findings.append(Finding(source="Loki", severity="critical", message=f"發現嚴重錯誤日誌: {logs['critical_errors']}", evidence=logs))

        # 分析審計日誌
        if "audit" in results and results["audit"].success:
            tools_used.append("ControlPlaneTool")
            audit = results["audit"].data
            if audit.get("recent_changes"):
                all_findings.append(Finding(source="Control-Plane", severity="warning", message=f"發現最近有配置變更", evidence=audit))

        # 生成摘要
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