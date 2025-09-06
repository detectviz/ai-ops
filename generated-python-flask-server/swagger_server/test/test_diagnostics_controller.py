# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.alert_analysis_request import AlertAnalysisRequest  # noqa: E501
from swagger_server.models.capacity_analysis_request import CapacityAnalysisRequest  # noqa: E501
from swagger_server.models.capacity_analysis_response import CapacityAnalysisResponse  # noqa: E501
from swagger_server.models.diagnostic_history_list import DiagnosticHistoryList  # noqa: E501
from swagger_server.models.diagnostic_request import DiagnosticRequest  # noqa: E501
from swagger_server.models.diagnostic_status import DiagnosticStatus  # noqa: E501
from swagger_server.models.diagnostic_task_response import DiagnosticTaskResponse  # noqa: E501
from swagger_server.models.v1_execute_body import V1ExecuteBody  # noqa: E501
from swagger_server.test import BaseTestCase


class TestDiagnosticsController(BaseTestCase):
    """DiagnosticsController integration test stubs"""

    def test_analyze_alerts(self):
        """Test case for analyze_alerts

        告警分析
        """
        body = AlertAnalysisRequest()
        response = self.client.open(
            '/api/v1/diagnostics/alerts',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_analyze_capacity(self):
        """Test case for analyze_capacity

        容量分析
        """
        body = CapacityAnalysisRequest()
        response = self.client.open(
            '/api/v1/diagnostics/capacity',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_diagnose_deployment(self):
        """Test case for diagnose_deployment

        部署診斷
        """
        body = DiagnosticRequest()
        response = self.client.open(
            '/api/v1/diagnostics/deployment',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_execute_natural_language_query(self):
        """Test case for execute_natural_language_query

        自然語言查詢
        """
        body = V1ExecuteBody()
        response = self.client.open(
            '/api/v1/execute',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_diagnostic_history(self):
        """Test case for get_diagnostic_history

        診斷歷史
        """
        query_string = [('page', 2),
                        ('page_size', 100),
                        ('start_time', '2013-10-20T19:20:30+01:00'),
                        ('end_time', '2013-10-20T19:20:30+01:00')]
        response = self.client.open(
            '/api/v1/diagnostics/history',
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_diagnostic_status(self):
        """Test case for get_diagnostic_status

        查詢診斷狀態
        """
        response = self.client.open(
            '/api/v1/diagnostics/{sessionId}/status'.format(session_id='38400000-8cf0-11bd-b23e-10b96e4ef00d'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
