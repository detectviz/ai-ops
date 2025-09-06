import connexion
import six

from swagger_server.models.health_status import HealthStatus  # noqa: E501
from swagger_server.models.readiness_status import ReadinessStatus  # noqa: E501
from swagger_server import util


def sa_check_health():  # noqa: E501
    """服務健康檢查

    檢查服務是否存活 # noqa: E501


    :rtype: HealthStatus
    """
    return 'do some magic!'


def sa_check_readiness():  # noqa: E501
    """服務就緒檢查

    檢查服務及其依賴是否就緒 # noqa: E501


    :rtype: ReadinessStatus
    """
    return 'do some magic!'


def sa_get_metrics():  # noqa: E501
    """Prometheus 指標

    獲取 Prometheus 格式的系統指標 # noqa: E501


    :rtype: str
    """
    return 'do some magic!'
