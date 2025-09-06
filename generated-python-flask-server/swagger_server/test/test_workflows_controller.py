# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.test import BaseTestCase


class TestWorkflowsController(BaseTestCase):
    """WorkflowsController integration test stubs"""

    def test_list_workflow_templates(self):
        """Test case for list_workflow_templates

        獲取工作流模板
        """
        response = self.client.open(
            '/api/v1/workflows/templates',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
