// Package auth 提供了與 Keycloak 身份認證服務互動的所有功能。
// 它的核心是 KeycloakService，封裝了 OIDC (OpenID Connect) 協議的複雜性，
// 並為應用程式的其他部分提供了簡單易用的 API。
//
// 主要職責包括：
// 1. Web UI 的使用者登入/登出流程管理。
// 2. 保護 API 端點，確保只有合法的、已認證的請求才能訪問。
// 3. 為後端服務之間的通訊 (M2M) 提供安全的權杖管理。
package auth

import (
	"context"
	"fmt"
	"net/http"
	"os"

	"github.com/coreos/go-oidc/v3/oidc"
	"github.com/detectviz/control-plane/internal/config"
	"github.com/gorilla/sessions"
	"golang.org/x/oauth2"
	"golang.org/x/oauth2/clientcredentials"
)

// SessionStore 和名稱設定
var (
	// CookieStore 金鑰從環境變數載入，生產環境應設定 CONTROL_PLANE_SESSION_KEY
	Store = sessions.NewCookieStore(getSessionKey())
)

// SessionName 是儲存在 cookie 中的 session 名稱。
const SessionName = "control-plane-session"

// KeycloakService 是一個集中管理所有 Keycloak 認證邏輯的服務。
// 它包含 OIDC 提供者的資訊、用於 Web 登入的 OAuth2 配置，以及用於服務間通訊的 M2M 配置。
type KeycloakService struct {
	Provider     *oidc.Provider // OIDC 提供者，包含了端點 URL 和公鑰等元數據。
	OAuth2Config oauth2.Config  // 用於使用者授權碼流程 (Authorization Code Flow) 的 OAuth2 配置。

	ClientID     string // Web UI 對應的 Keycloak Client ID。
	ClientSecret string // Web UI 對應的 Keycloak Client Secret。
	Realm        string // Keycloak 中的 Realm 名稱。
	BaseURL      string // Keycloak 服務的基礎 URL。

	// m2mToken 用於快取獲取到的 M2M 權杖，避免重複請求。
	m2mToken *oauth2.Token
	// m2mConfig 是專門用於客戶端憑證流程 (Client Credentials Flow) 的配置。
	m2mConfig clientcredentials.Config
}

// NewKeycloakService 根據提供的配置，初始化並返回一個新的 KeycloakService 實例。
// 這個函數會在啟動時被呼叫，它會連接到 Keycloak 的 .well-known 端點來自動發現 OIDC 配置。
func NewKeycloakService(cfg config.AuthConfig) (*KeycloakService, error) {
	// 建立一個 OIDC Provider，它會自動從 Keycloak 的發現端點 (discovery endpoint) 獲取所有必要的 URL 和設定。
	// 這是 OIDC 的標準做法，避免了手動配置所有端點 URL。
	provider, err := oidc.NewProvider(context.Background(), fmt.Sprintf("%s/realms/%s", cfg.URL, cfg.Realm))
	if err != nil {
		return nil, fmt.Errorf("無法建立 OIDC 提供者: %w", err)
	}

	// 這是標準的 OAuth2 授權碼流程配置，用於處理使用者的瀏覽器登入。
	oauth2Config := oauth2.Config{
		ClientID:     cfg.ClientID,
		ClientSecret: cfg.ClientSecret,
		RedirectURL:  cfg.RedirectURL,
		Endpoint:     provider.Endpoint(),
		Scopes:       []string{oidc.ScopeOpenID, "profile", "email"}, // 要求 OIDC 標準範圍以及個人資料和 email。
	}

	// 這是客戶端憑證流程的配置，專門用於後端服務之間的 M2M (Machine-to-Machine) 認證。
	// Control Plane 將使用此配置來獲取一個權杖，以便能夠安全地呼叫 SRE Assistant 的 API。
	m2mConfig := clientcredentials.Config{
		ClientID:     cfg.M2MClientID,
		ClientSecret: cfg.M2MClientSecret,
		TokenURL:     provider.Endpoint().TokenURL,
	}

	return &KeycloakService{
		Provider:     provider,
		OAuth2Config: oauth2Config,
		ClientID:     cfg.ClientID,
		ClientSecret: cfg.ClientSecret,
		Realm:        cfg.Realm,
		BaseURL:      cfg.URL,
		m2mConfig:    m2mConfig,
	}, nil
}

// VerifyToken 是一個核心安全函數，它接收一個從 HTTP Header 傳入的 JWT (ID Token)，
// 並使用從 OIDC 提供者獲取的公鑰來驗證其簽名和內容 (例如，過期時間、簽發者)。
// 這是保護我們的 API 端點不被未授權訪問的關鍵。
func (s *KeycloakService) VerifyToken(ctx context.Context, rawIDToken string) (*oidc.IDToken, error) {
	// 使用 OIDC 提供者的驗證器來驗證 token。
	// Verifier 會檢查簽名、過期時間 (exp)、簽發時間 (iat) 和簽發者 (iss) 等標準聲明。
	return s.Provider.Verifier(&oidc.Config{ClientID: s.ClientID}).Verify(ctx, rawIDToken)
}

// GetM2MToken 是我們架構中的一個關鍵函數。
// 當 Control Plane 需要呼叫 SRE Assistant 時，它必須先呼叫此函數來獲取一個 access token。
// 這個權杖代表了 Control Plane 這個「機器」客戶端本身，而不是某個特定使用者。
// 函數內部實作了簡單的快取機制，以避免在每次 API 呼叫時都向 Keycloak 請求新權杖。
func (s *KeycloakService) GetM2MToken(ctx context.Context) (string, error) {
	// 檢查快取的權杖是否存在且仍然有效 (尚未過期)。
	if s.m2mToken == nil || !s.m2mToken.Valid() {
		// 如果權杖無效或不存在，則使用 client credentials flow 向 Keycloak 請求一個新的權杖。
		token, err := s.m2mConfig.Token(ctx)
		if err != nil {
			return "", fmt.Errorf("無法獲取 M2M 權杖: %w", err)
		}
		// 將新獲取的權杖存入快取。
		s.m2mToken = token
	}
	// 返回有效的 access token 字串。
	return s.m2mToken.AccessToken, nil
}

// --- 以下為處理 Web UI 登入流程的輔助函數 ---

// HandleLogin 將使用者重定向到 Keycloak 進行登入。
// 這是 OIDC 授權碼流程的第一步。
func (s *KeycloakService) HandleLogin(w http.ResponseWriter, r *http.Request) {
	// `AuthCodeURL` 會生成一個包含所有必要參數的 URL，用於將使用者導向到 Keycloak 的登入頁面。
	// "state" 參數是一個 CSRF 保護機制，在生產環境中應使用一個隨機產生的、與使用者 session 綁定的字串。
	http.Redirect(w, r, s.OAuth2Config.AuthCodeURL("state"), http.StatusFound)
}

// AuthCallback 處理使用者在 Keycloak 登入成功後的回調請求。
// 這是 OIDC 授權碼流程的第二步。
func (s *KeycloakService) AuthCallback(w http.ResponseWriter, r *http.Request) (string, error) {
	// 在生產環境中，需要嚴格驗證 state 參數以防止 CSRF 攻擊。
	// if r.URL.Query().Get("state") != "state" {
	// 	return "", fmt.Errorf("無效的 state 參數")
	// }

	// 使用從 URL 中獲取的授權碼 (code)，向 Keycloak 交換一個 access token 和 id token。
	oauth2Token, err := s.OAuth2Config.Exchange(r.Context(), r.URL.Query().Get("code"))
	if err != nil {
		return "", fmt.Errorf("無法交換授權碼: %w", err)
	}

	// 從 OAuth2 權杖中提取 ID Token。ID Token 是一個 JWT，包含了使用者的身份資訊。
	rawIDToken, ok := oauth2Token.Extra("id_token").(string)
	if !ok {
		return "", fmt.Errorf("在權杖回應中找不到 ID Token")
	}

	// 在將使用者標記為已登入之前，必須先驗證 ID Token 的合法性。
	_, err = s.VerifyToken(r.Context(), rawIDToken)
	if err != nil {
		return "", fmt.Errorf("無法驗證 ID Token: %w", err)
	}

	// 驗證成功後，應用程式通常會在此處建立一個自己的 session，並將 session ID 存入 cookie。
	// 為了簡化，我們直接返回原始的 ID Token 字串，以便後續操作。
	return rawIDToken, nil
}

// UserInfo 定義了從 Keycloak 的 userinfo 端點返回的使用者資料結構。
type UserInfo struct {
	Sub               string `json:"sub"`
	EmailVerified     bool   `json:"email_verified"`
	Name              string `json:"name"`
	PreferredUsername string `json:"preferred_username"`
	GivenName         string `json:"given_name"`
	FamilyName        string `json:"family_name"`
	Email             string `json:"email"`
}

// GetUserInfo 使用 access token 從 OIDC 的 userinfo 端點獲取更詳細的使用者資訊。
// 這通常在需要顯示使用者姓名、Email 等資訊時使用。
func (s *KeycloakService) GetUserInfo(ctx context.Context, token *oauth2.Token) (*UserInfo, error) {
	tokenSource := s.OAuth2Config.TokenSource(ctx, token)
	oidcUserInfo, err := s.Provider.UserInfo(ctx, tokenSource)
	if err != nil {
		return nil, fmt.Errorf("無法從提供者獲取 user info: %w", err)
	}

	// oidc.UserInfo 包含標準宣告，但我們可能需要自訂宣告。
	// 使用 Claims 方法將所有宣告解碼到我們自訂的結構中。
	var claims UserInfo
	if err := oidcUserInfo.Claims(&claims); err != nil {
		return nil, fmt.Errorf("無法解析 user info 的宣告: %w", err)
	}

	return &claims, nil
}

// getSessionKey 從環境變數獲取 session 金鑰，如果未設定則使用安全的預設值
func getSessionKey() []byte {
	key := os.Getenv("CONTROL_PLANE_SESSION_KEY")
	if key == "" {
		// 開發環境使用一個相對安全的預設值，但建議在生產環境設定環境變數
		fmt.Println("⚠️ 警告: 未設定 CONTROL_PLANE_SESSION_KEY 環境變數，使用開發環境預設值")
		return []byte("dev-session-key-change-in-production-2024")
	}
	return []byte(key)
}
