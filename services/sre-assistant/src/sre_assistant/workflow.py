# services/sre-assistant/src/sre_assistant/workflow.py
"""
SRE 工作流程協調器
負責協調各種診斷工具並整合結果
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json

from .contracts import (
    SRERequest,
    ToolResult,
    ToolError,
    Finding,
    SeverityLevel
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
    4. 生成診斷報告
    """
    
    def __init__(self, config):
        """初始化工作流程"""
        self.config = config
        
        # 初始化工具
        self.prometheus_tool = PrometheusQueryTool(config)
        self.loki_tool = LokiLogQueryTool(config)
        self.control_plane_tool = ControlPlaneTool(config)
        
        # 工作流程設定
        self.parallel_diagnosis = config.workflow.get("parallel_diagnosis", True)
        self.diagnosis_timeout = config.workflow.get("diagnosis_timeout_seconds", 60)
        
        logger.info("✅ SRE 工作流程初始化完成")
    
    async def execute(self, request: SRERequest) -> Dict[str, Any]:
        """
        執行主要工作流程
        
        Args:
            request: SRE 請求物件
            
        Returns:
            包含診斷結果的字典
        """
        start_time = datetime.now(timezone.utc)
        logger.info(f"🚀 開始執行工作流程: {request.incident_id}")
        
        try:
            # 根據請求類型決定執行策略
            context_type = request.context.get("type", "unknown")
            
            if context_type == "deployment_diagnosis":
                result = await self._diagnose_deployment(request)
            elif context_type == "alert_diagnosis":
                result = await self._diagnose_alerts(request)
            elif context_type == "ad_hoc_query":
                result = await self._execute_ad_hoc_query(request)
            else:
                result = await self._generic_diagnosis(request)
            
            # 計算執行時間
            execution_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            result["execution_time_ms"] = execution_time_ms
            
            logger.info(f"✅ 工作流程完成: {request.incident_id} (耗時 {execution_time_ms}ms)")
            return result
            
        except Exception as e:
            logger.error(f"❌ 工作流程執行失敗: {e}")
            return {
                "status": "FAILED",
                "summary": f"診斷過程發生錯誤: {str(e)}",
                "findings": [],
                "recommended_action": "請聯繫系統管理員",
                "confidence_score": 0.0
            }
    
    async def _diagnose_deployment(self, request: SRERequest) -> Dict[str, Any]:
        """
        診斷部署問題
        
        執行並行診斷：
        1. 查詢 Prometheus 指標
        2. 查詢 Loki 日誌
        3. 查詢 Control Plane 變更歷史
        """
        logger.info(f"🔍 診斷部署: {request.context.get('service_name')}")
        
        # 準備診斷任務
        tasks = []
        
        # 1. Prometheus 指標查詢
        prometheus_task = self._query_metrics(
            service=request.context.get("service_name"),
            namespace=request.context.get("namespace", "default")
        )
        tasks.append(("prometheus", prometheus_task))
        
        # 2. Loki 日誌查詢
        loki_task = self._query_logs(
            service=request.context.get("service_name"),
            namespace=request.context.get("namespace", "default")
        )
        tasks.append(("loki", loki_task))
        
        # 3. Control Plane 審計日誌
        audit_task = self._query_audit_logs(
            service=request.context.get("service_name")
        )
        tasks.append(("audit", audit_task))
        
        # 並行執行所有診斷
        if self.parallel_diagnosis:
            results = await self._execute_parallel_tasks(tasks)
        else:
            results = await self._execute_sequential_tasks(tasks)
        
        # 分析結果並生成報告
        return self._analyze_deployment_results(results, request)
    
    async def _diagnose_alerts(self, request: SRERequest) -> Dict[str, Any]:
        """診斷告警事件"""
        logger.info(f"🚨 診斷告警: {request.context.get('incident_ids')}")
        
        # TODO: 實作告警診斷邏輯
        findings = []
        
        # 模擬診斷結果
        findings.append(Finding(
            source="AlertManager",
            severity=SeverityLevel.P1,
            data={
                "alert_count": len(request.context.get("incident_ids", [])),
                "pattern": "多個服務同時告警，可能是基礎設施問題"
            }
        ))
        
        return {
            "status": "COMPLETED",
            "summary": f"分析了 {len(request.context.get('incident_ids', []))} 個告警事件",
            "findings": [f.dict() for f in findings],
            "recommended_action": "檢查基礎設施狀態",
            "confidence_score": 0.75
        }
    
    async def _execute_ad_hoc_query(self, request: SRERequest) -> Dict[str, Any]:
        """執行臨機查詢"""
        logger.info(f"💬 執行查詢: {request.input[:50]}...")
        
        # TODO: 整合 LLM 進行自然語言理解和工具選擇
        
        return {
            "status": "COMPLETED",
            "summary": "查詢執行完成",
            "findings": [],
            "recommended_action": None,
            "confidence_score": 0.7
        }
    
    async def _generic_diagnosis(self, request: SRERequest) -> Dict[str, Any]:
        """通用診斷流程"""
        logger.info(f"🔧 執行通用診斷: {request.incident_id}")
        
        return {
            "status": "COMPLETED",
            "summary": "通用診斷完成",
            "findings": [],
            "recommended_action": "請提供更多上下文資訊",
            "confidence_score": 0.5
        }
    
    # === 工具查詢方法 ===
    
    async def _query_metrics(self, service: str, namespace: str) -> ToolResult:
        """查詢 Prometheus 指標"""
        try:
            # TODO: 實作實際的 Prometheus 查詢
            await asyncio.sleep(0.5)  # 模擬查詢延遲
            
            return ToolResult(
                success=True,
                data={
                    "cpu_usage": "85%",
                    "memory_usage": "92%",
                    "error_rate": "0.05",
                    "latency_p99": "1500ms"
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=ToolError(code="PROMETHEUS_ERROR", message=str(e))
            )
    
    async def _query_logs(self, service: str, namespace: str) -> ToolResult:
        """查詢 Loki 日誌"""
        try:
            # TODO: 實作實際的 Loki 查詢
            await asyncio.sleep(0.3)  # 模擬查詢延遲
            
            return ToolResult(
                success=True,
                data={
                    "error_count": 42,
                    "critical_errors": ["OOMKilled", "Connection timeout"],
                    "log_volume": "high"
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=ToolError(code="LOKI_ERROR", message=str(e))
            )
    
    async def _query_audit_logs(self, service: str) -> ToolResult:
        """查詢審計日誌"""
        try:
            # TODO: 實作實際的 Control Plane API 調用
            await asyncio.sleep(0.2)  # 模擬查詢延遲
            
            return ToolResult(
                success=True,
                data={
                    "recent_changes": [
                        {
                            "time": "2025-01-02T10:30:00Z",
                            "user": "admin",
                            "action": "UPDATE_CONFIG",
                            "details": "Modified resource limits"
                        }
                    ]
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=ToolError(code="AUDIT_ERROR", message=str(e))
            )
    
    # === 輔助方法 ===
    
    async def _execute_parallel_tasks(self, tasks: List[tuple]) -> Dict[str, ToolResult]:
        """並行執行診斷任務"""
        results = {}
        
        # 建立異步任務
        async_tasks = []
        for name, task in tasks:
            async_tasks.append((name, asyncio.create_task(task)))
        
        # 等待所有任務完成
        for name, task in async_tasks:
            try:
                result = await asyncio.wait_for(task, timeout=self.diagnosis_timeout)
                results[name] = result
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ 任務 {name} 超時")
                results[name] = ToolResult(
                    success=False,
                    error=ToolError(code="TIMEOUT", message=f"任務 {name} 執行超時")
                )
        
        return results
    
    async def _execute_sequential_tasks(self, tasks: List[tuple]) -> Dict[str, ToolResult]:
        """循序執行診斷任務"""
        results = {}
        
        for name, task in tasks:
            try:
                result = await asyncio.wait_for(task, timeout=self.diagnosis_timeout)
                results[name] = result
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ 任務 {name} 超時")
                results[name] = ToolResult(
                    success=False,
                    error=ToolError(code="TIMEOUT", message=f"任務 {name} 執行超時")
                )
        
        return results
    
    def _analyze_deployment_results(self, results: Dict[str, ToolResult], request: SRERequest) -> Dict[str, Any]:
        """分析部署診斷結果"""
        findings = []
        issues = []
        
        # 分析 Prometheus 結果
        if "prometheus" in results and results["prometheus"].success:
            metrics = results["prometheus"].data
            
            # 檢查 CPU 使用率
            if metrics.get("cpu_usage", "").replace("%", ""):
                cpu_usage = float(metrics["cpu_usage"].replace("%", ""))
                if cpu_usage > 80:
                    findings.append(Finding(
                        source="Prometheus",
                        severity=SeverityLevel.P1,
                        data={"cpu_usage": metrics["cpu_usage"]},
                        timestamp=datetime.now(timezone.utc)
                    ))
                    issues.append("CPU 使用率過高")
            
            # 檢查記憶體使用率
            if metrics.get("memory_usage", "").replace("%", ""):
                mem_usage = float(metrics["memory_usage"].replace("%", ""))
                if mem_usage > 90:
                    findings.append(Finding(
                        source="Prometheus",
                        severity=SeverityLevel.P1,
                        data={"memory_usage": metrics["memory_usage"]},
                        timestamp=datetime.now(timezone.utc)
                    ))
                    issues.append("記憶體使用率過高")
        
        # 分析 Loki 結果
        if "loki" in results and results["loki"].success:
            logs = results["loki"].data
            if logs.get("critical_errors"):
                findings.append(Finding(
                    source="Loki",
                    severity=SeverityLevel.P0,
                    data={"errors": logs["critical_errors"]},
                    timestamp=datetime.now(timezone.utc)
                ))
                issues.extend(logs["critical_errors"])
        
        # 分析審計日誌
        if "audit" in results and results["audit"].success:
            audit = results["audit"].data
            if audit.get("recent_changes"):
                findings.append(Finding(
                    source="Control-Plane",
                    severity=SeverityLevel.P2,
                    data={"changes": audit["recent_changes"]},
                    timestamp=datetime.now(timezone.utc)
                ))
                issues.append("最近有配置變更")
        
        # 生成摘要
        if issues:
            summary = f"發現 {len(issues)} 個問題: {', '.join(issues[:3])}"
            recommended_action = self._generate_recommendation(issues)
        else:
            summary = "未發現明顯問題，建議進一步調查"
            recommended_action = "檢查應用程式日誌和依賴服務狀態"
        
        return {
            "status": "COMPLETED",
            "summary": summary,
            "findings": [f.dict() for f in findings],
            "recommended_action": recommended_action,
            "confidence_score": self._calculate_confidence(findings)
        }
    
    def _generate_recommendation(self, issues: List[str]) -> str:
        """根據問題生成建議"""
        recommendations = []
        
        if "OOMKilled" in str(issues):
            recommendations.append("增加記憶體限制或優化記憶體使用")
        
        if "CPU 使用率過高" in str(issues):
            recommendations.append("增加 CPU 限制或優化程式效能")
        
        if "Connection timeout" in str(issues):
            recommendations.append("檢查網路連接和依賴服務")
        
        if "最近有配置變更" in str(issues):
            recommendations.append("審查最近的配置變更")
        
        return " | ".join(recommendations) if recommendations else "進行深入診斷"
    
    def _calculate_confidence(self, findings: List[Finding]) -> float:
        """計算診斷信心分數"""
        if not findings:
            return 0.3
        
        # 根據發現的嚴重程度計算信心分數
        severity_scores = {
            SeverityLevel.P0: 1.0,
            SeverityLevel.P1: 0.9,
            SeverityLevel.P2: 0.7,
            SeverityLevel.P3: 0.5
        }
        
        total_score = sum(severity_scores.get(f.severity, 0.5) for f in findings)
        return min(total_score / len(findings), 1.0)