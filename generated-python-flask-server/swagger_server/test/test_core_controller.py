# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.health_status import HealthStatus  # noqa: E501
from swagger_server.models.readiness_status import ReadinessStatus  # noqa: E501
from swagger_server.test import BaseTestCase


class TestCoreController(BaseTestCase):
    """CoreController integration test stubs"""

    def test_sa_check_health(self):
        """Test case for sa_check_health

        服務健康檢查
        """
        response = self.client.open(
            '/api/v1/healthz',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_sa_check_readiness(self):
        """Test case for sa_check_readiness

        服務就緒檢查
        """
        response = self.client.open(
            '/api/v1/readyz',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_sa_get_metrics(self):
        """Test case for sa_get_metrics

        Prometheus 指標
        """
        response = self.client.open(
            '/api/v1/metrics',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
