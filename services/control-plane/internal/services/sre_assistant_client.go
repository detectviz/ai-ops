// services/control-plane/internal/services/sre_assistant_client.go
package services

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"time"

	"github.com/detectviz/control-plane/internal/auth"
	"github.com/hashicorp/go-retryablehttp"
	"github.com/uptrace/opentelemetry-go-extra/otelzap"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.uber.org/zap"
)

// SreAssistantClient 定義了與 SRE Assistant 服務通訊的介面
type SreAssistantClient interface {
	DiagnoseDeployment(ctx context.Context, req *DiagnosticRequest) (*DiagnosticResponse, error)
	GetDiagnosticStatus(ctx context.Context, sessionID string) (*DiagnosticStatus, error)
	PollDiagnosticStatus(ctx context.Context, sessionID string) (*DiagnosticResult, error)
}

// SreAssistantClientImpl 是 SreAssistantClient 的具體實現
type SreAssistantClientImpl struct {
	baseURL       string
	httpClient    *http.Client
	tokenProvider auth.AuthProvider
	logger        *otelzap.Logger
}

var (
	// sharedHTTPClient 是一個強固且共享的客戶端，用於所有與 SRE Assistant 的通訊。
	// 它設定了合理的連線池、多層次的逾時和自動重試機制。
	sharedHTTPClient *http.Client
)

func init() {
	// 1. 設定 Transport 並使用 OTel 中間件進行包裝
	baseTransport := &http.Transport{
		Proxy: http.ProxyFromEnvironment,
		DialContext: (&net.Dialer{
			Timeout:   5 * time.Second,  // 連線逾時
			KeepAlive: 30 * time.Second, // 連線保持啟用
		}).DialContext,
		MaxIdleConns:          100,              // 最大閒置連線數
		MaxIdleConnsPerHost:   10,               // 對單一主機的最大閒置連線數
		IdleConnTimeout:       90 * time.Second, // 閒置連線逾時
		TLSHandshakeTimeout:   10 * time.Second, // TLS 交握逾時
		ResponseHeaderTimeout: 15 * time.Second, // 等待回應標頭的逾時
	}
	otelTransport := otelhttp.NewTransport(baseTransport)

	// 2. 建立一個可重試的 HTTP 客戶端
	retryClient := retryablehttp.NewClient()
	retryClient.HTTPClient = &http.Client{
		Transport: otelTransport, // 使用 OTel 包裝後的 transport
		Timeout:   60 * time.Second, // 設定涵蓋整個請求（包括重試）的總逾時
	}
	retryClient.RetryMax = 3   // 最多重試 3 次
	retryClient.Logger = nil   // 禁用函式庫的預設日誌，避免干擾我們的結構化日誌

	// 3. 將可重試客戶端轉換為標準的 http.Client，並將其賦值給共享變數
	sharedHTTPClient = retryClient.StandardClient()
}

// NewSreAssistantClient 建立一個新的 SRE Assistant 客戶端實例
func NewSreAssistantClient(baseURL string, tokenProvider auth.AuthProvider, logger *otelzap.Logger) SreAssistantClient {
	return &SreAssistantClientImpl{
		baseURL:       baseURL,
		httpClient:    sharedHTTPClient, // 使用全域共享的客戶端
		tokenProvider: tokenProvider,
		logger:        logger,
	}
}

// --- 資料結構 (對應 SRE Assistant API 契約) ---

type DiagnosticRequest struct {
	IncidentID       string            `json:"incident_id"`
	Severity         string            `json:"severity"`
	AffectedServices []string          `json:"affected_services"`
	Context          map[string]string `json:"context"`
}

type DiagnosticResponse struct {
	SessionID     string `json:"session_id"`
	Status        string `json:"status"`
	Message       string `json:"message"`
	EstimatedTime int    `json:"estimated_time"`
}

type DiagnosticResult struct {
	Summary            string    `json:"summary"`
	Findings           []Finding `json:"findings"`
	RecommendedActions []string  `json:"recommended_actions"`
	ConfidenceScore    float64   `json:"confidence_score"`
	ToolsUsed          []string  `json:"tools_used"`
	ExecutionTime      float64   `json:"execution_time"`
}

type Finding struct {
	Source    string                 `json:"source"`
	Severity  string                 `json:"severity"`
	Message   string                 `json:"message"`
	Evidence  map[string]interface{} `json:"evidence"`
	Timestamp time.Time              `json:"timestamp"`
}

type DiagnosticStatus struct {
	SessionID   string            `json:"session_id"`
	Status      string            `json:"status"`
	Progress    int               `json:"progress"`
	CurrentStep string            `json:"current_step"`
	Result      *DiagnosticResult `json:"result,omitempty"`
	Error       string            `json:"error,omitempty"`
}

// DiagnoseDeployment 呼叫 SRE Assistant 的 /api/v1/diagnostics/deployment 端點
func (c *SreAssistantClientImpl) DiagnoseDeployment(ctx context.Context, req *DiagnosticRequest) (*DiagnosticResponse, error) {
	c.logger.Ctx(ctx).Info("準備呼叫 SRE Assistant 進行部署診斷", zap.String("incidentID", req.IncidentID))

	var token string
	var err error
	if c.tokenProvider != nil {
		token, err = c.tokenProvider.GetM2MToken(ctx)
		if err != nil {
			c.logger.Ctx(ctx).Error("無法獲取 M2M 權杖", zap.Error(err))
			return nil, fmt.Errorf("無法獲取 M2M 權杖: %w", err)
		}
	} else {
		// DEV 模式下，使用一個假的 token
		token = "dev-mode-token"
		c.logger.Ctx(ctx).Info("在 DEV 模式下運行，使用假的 M2M token")
	}

	payload, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("無法序列化請求體: %w", err)
	}

	url := fmt.Sprintf("%s/api/v1/diagnostics/deployment", c.baseURL)
	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(payload))
	if err != nil {
		return nil, fmt.Errorf("無法建立 HTTP 請求: %w", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", "Bearer "+token)

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("向 SRE Assistant 發送請求失敗: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusAccepted {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("SRE Assistant 返回非預期的狀態碼: %d, body: %s", resp.StatusCode, string(body))
	}

	var respBody DiagnosticResponse
	if err := json.NewDecoder(resp.Body).Decode(&respBody); err != nil {
		return nil, fmt.Errorf("無法解碼 SRE Assistant 的響應: %w", err)
	}

	c.logger.Ctx(ctx).Info("成功收到 SRE Assistant 的非同步任務回應", zap.String("sessionID", respBody.SessionID))
	return &respBody, nil
}

// GetDiagnosticStatus 呼叫 SRE Assistant 的 /api/v1/diagnostics/{session_id}/status 端點
func (c *SreAssistantClientImpl) GetDiagnosticStatus(ctx context.Context, sessionID string) (*DiagnosticStatus, error) {
	var token string
	var err error
	if c.tokenProvider != nil {
		token, err = c.tokenProvider.GetM2MToken(ctx)
		if err != nil {
			return nil, fmt.Errorf("無法獲取 M2M 權杖: %w", err)
		}
	} else {
		token = "dev-mode-token"
	}

	url := fmt.Sprintf("%s/api/v1/diagnostics/%s/status", c.baseURL, sessionID)
	httpReq, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("無法建立 HTTP 請求: %w", err)
	}

	httpReq.Header.Set("Authorization", "Bearer "+token)

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("查詢狀態失敗: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("查詢狀態時返回非預期的狀態碼: %d, body: %s", resp.StatusCode, string(body))
	}

	var statusBody DiagnosticStatus
	if err := json.NewDecoder(resp.Body).Decode(&statusBody); err != nil {
		return nil, fmt.Errorf("無法解碼狀態響應: %w", err)
	}

	return &statusBody, nil
}

// PollDiagnosticStatus 輪詢診斷狀態直到完成或超時
func (c *SreAssistantClientImpl) PollDiagnosticStatus(ctx context.Context, sessionID string) (*DiagnosticResult, error) {
	c.logger.Ctx(ctx).Info("開始輪詢診斷狀態", zap.String("sessionID", sessionID))

	// 設定輪詢間隔與超時
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	timeoutCtx, cancel := context.WithTimeout(ctx, 5*time.Minute)
	defer cancel()

	for {
		select {
		case <-timeoutCtx.Done():
			return nil, fmt.Errorf("輪詢診斷結果超時 (5分鐘)")
		case <-ticker.C:
			c.logger.Ctx(ctx).Info("正在查詢任務狀態...", zap.String("sessionID", sessionID))
			status, err := c.GetDiagnosticStatus(timeoutCtx, sessionID)
			if err != nil {
				c.logger.Ctx(ctx).Warn("查詢狀態失敗，將重試", zap.Error(err))
				continue
			}

			switch status.Status {
			case "completed":
				c.logger.Ctx(ctx).Info("診斷任務完成", zap.String("sessionID", sessionID))
				return status.Result, nil
			case "failed":
				c.logger.Ctx(ctx).Error("診斷任務失敗", zap.String("sessionID", sessionID), zap.String("error", status.Error))
				return nil, fmt.Errorf("診斷任務失敗: %s", status.Error)
			case "processing":
				c.logger.Ctx(ctx).Info("任務仍在處理中", zap.String("sessionID", sessionID), zap.String("step", status.CurrentStep))
				// 繼續輪詢
			default:
				// 繼續輪詢
			}
		}
	}
}
