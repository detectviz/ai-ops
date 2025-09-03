
package main

import (
	"context"
	"crypto/tls"
	"fmt"
	"net/http"
	"os"
	"testing"
	"time"

	"golang.org/x/oauth2"
	"golang.org/x/oauth2/clientcredentials"
)

// TestSREAssistantM2MAuth 是一個整合測試，用於驗證 control-plane 和 sre-assistant 之間的 M2M 認證流程。
func TestSREAssistantM2MAuth(t *testing.T) {
	// --- 組態設定 ---
	// 從環境變數獲取組態，若未設定則使用 docker-compose.yml 中的預設值
	keycloakURL := os.Getenv("KEYCLOAK_URL")
	if keycloakURL == "" {
		keycloakURL = "http://127.0.0.1:8080" // 從主機執行測試
	}
	keycloakRealm := os.Getenv("KEYCLOAK_REALM")
	if keycloakRealm == "" {
		keycloakRealm = "sre-platform"
	}
	clientID := os.Getenv("KEYCLOAK_CLIENT_ID")
	if clientID == "" {
		clientID = "control-plane"
	}
	clientSecret := os.Getenv("KEYCLOAK_CLIENT_SECRET")
	if clientSecret == "" {
		clientSecret = "control-plane-secret" // docker-compose 中的預設值
	}
	sreAssistantURL := os.Getenv("SRE_ASSISTANT_URL")
	if sreAssistantURL == "" {
		sreAssistantURL = "http://127.0.0.1:8000" // 從主機執行測試
	}

	tokenURL := fmt.Sprintf("%s/realms/%s/protocol/openid-connect/token", keycloakURL, keycloakRealm)
	secureEndpoint := fmt.Sprintf("%s/api/v1/health/secure", sreAssistantURL)

	// --- OAuth2 Client Credentials 流程 ---
	// 建立一個允許不安全 HTTP 連線的 http client，用於本地開發環境
	insecureTransport := &http.Transport{
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	}
	ctx := context.WithValue(context.Background(), oauth2.HTTPClient, &http.Client{Transport: insecureTransport})

	conf := &clientcredentials.Config{
		ClientID:     clientID,
		ClientSecret: clientSecret,
		TokenURL:     tokenURL,
		Scopes:       []string{"openid"}, // "openid" 是標準 scope
	}

	// 建立一個會自動處理 token 獲取的 HTTP 客戶端
	httpClient := conf.Client(ctx)
	httpClient.Timeout = 15 * time.Second

	// --- API 呼叫 ---
	t.Run("呼叫安全端點", func(t *testing.T) {
		req, err := http.NewRequestWithContext(ctx, "GET", secureEndpoint, nil)
		if err != nil {
			t.Fatalf("建立請求失敗: %v", err)
		}

		// 執行請求
		resp, err := httpClient.Do(req)
		if err != nil {
			t.Fatalf("呼叫 SRE Assistant 失敗: %v", err)
		}
		defer resp.Body.Close()

		// --- 驗證 ---
		if resp.StatusCode != http.StatusOK {
			t.Errorf("預期狀態碼 %d, 但得到 %d", http.StatusOK, resp.StatusCode)
			// 嘗試讀取回應內容以獲得更多資訊
			body := make([]byte, 512)
			n, _ := resp.Body.Read(body)
			t.Logf("回應內容: %s", body[:n])
		} else {
			t.Logf("成功呼叫安全端點. 狀態: %s", resp.Status)
		}
	})
}

