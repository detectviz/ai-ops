package services

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/detectviz/control-plane/internal/auth"
	"github.com/uptrace/opentelemetry-go-extra/otelzap"
	"go.uber.org/zap"
)

// SreAssistantClientImpl 是與 SRE Assistant 服務通訊的具體實現。
type SreAssistantClientImpl struct {
	baseURL    string
	httpClient *http.Client
	authSvc    *auth.KeycloakService
	logger     *otelzap.Logger
}

// NewSreAssistantClient 建立一個新的 SRE Assistant 客戶端實例。
func NewSreAssistantClient(baseURL string, authSvc *auth.KeycloakService, logger *otelzap.Logger) *SreAssistantClientImpl {
	return &SreAssistantClientImpl{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
		authSvc: authSvc,
		logger:  logger,
	}
}

// DiagnoseDeploymentRequest 定義了發送到 SRE Assistant 的請求體結構。
// 這對應於 openapi.yaml 中的 DeploymentRequestContext。
type DiagnoseDeploymentRequest struct {
	Context struct {
		DeploymentID string `json:"deployment_id"`
		ServiceName  string `json:"service_name"`
		Namespace    string `json:"namespace"`
	} `json:"context"`
}

// DiagnoseDeploymentResponse 定義了從 SRE Assistant 返回的響應體結構。
// 這對應於 openapi.yaml 中的 SessionResponse。
type DiagnoseDeploymentResponse struct {
	SessionID string `json:"session_id"`
	Message   string `json:"message"`
}

// DiagnoseDeployment 呼叫 SRE Assistant 的 /diagnostics/deployment 端點。
func (c *SreAssistantClientImpl) DiagnoseDeployment(ctx context.Context, deploymentID string, serviceName string, namespace string) (*DiagnoseDeploymentResponse, error) {
	c.logger.Ctx(ctx).Info("準備呼叫 SRE Assistant 進行部署診斷", zap.String("deploymentID", deploymentID))

	// 1. 獲取 M2M 權杖
	token, err := c.authSvc.GetM2MToken(ctx)
	if err != nil {
		c.logger.Ctx(ctx).Error("無法獲取 M2M 權杖", zap.Error(err))
		return nil, fmt.Errorf("無法獲取 M2M 權杖: %w", err)
	}

	// 2. 建立請求體
	reqBody := DiagnoseDeploymentRequest{}
	reqBody.Context.DeploymentID = deploymentID
	reqBody.Context.ServiceName = serviceName
	reqBody.Context.Namespace = namespace

	payload, err := json.Marshal(reqBody)
	if err != nil {
		c.logger.Ctx(ctx).Error("無法序列化請求體", zap.Error(err))
		return nil, fmt.Errorf("無法序列化請求體: %w", err)
	}

	// 3. 建立 HTTP 請求
	url := fmt.Sprintf("%s/diagnostics/deployment", c.baseURL)
	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(payload))
	if err != nil {
		c.logger.Ctx(ctx).Error("無法建立 HTTP 請求", zap.Error(err))
		return nil, fmt.Errorf("無法建立 HTTP 請求: %w", err)
	}

	// 4. 設定標頭
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+token)

	// 5. 發送請求
	c.logger.Ctx(ctx).Info("正在向 SRE Assistant 發送請求", zap.String("url", url))
	resp, err := c.httpClient.Do(req)
	if err != nil {
		c.logger.Ctx(ctx).Error("向 SRE Assistant 發送請求失敗", zap.Error(err))
		return nil, fmt.Errorf("向 SRE Assistant 發送請求失敗: %w", err)
	}
	defer resp.Body.Close()

	// 6. 處理響應
	if resp.StatusCode != http.StatusAccepted {
		bodyBytes, _ := io.ReadAll(resp.Body)
		c.logger.Ctx(ctx).Error("SRE Assistant 返回非預期的狀態碼",
			zap.Int("statusCode", resp.StatusCode),
			zap.String("body", string(bodyBytes)),
		)
		return nil, fmt.Errorf("SRE Assistant 返回非預期的狀態碼: %d", resp.StatusCode)
	}

	var respBody DiagnoseDeploymentResponse
	if err := json.NewDecoder(resp.Body).Decode(&respBody); err != nil {
		c.logger.Ctx(ctx).Error("無法解碼 SRE Assistant 的響應", zap.Error(err))
		return nil, fmt.Errorf("無法解碼 SRE Assistant 的響應: %w", err)
	}

	c.logger.Ctx(ctx).Info("成功收到 SRE Assistant 的響應", zap.String("sessionID", respBody.SessionID))
	return &respBody, nil
}
