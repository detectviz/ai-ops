# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.test import BaseTestCase


class TestToolsController(BaseTestCase):
    """ToolsController integration test stubs"""

    def test_get_tools_status(self):
        """Test case for get_tools_status

        獲取工具狀態
        """
        response = self.client.open(
            '/api/v1/tools/status',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
