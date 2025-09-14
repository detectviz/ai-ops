// Package auth 提供了身份認證相關的功能。
// 這個檔案定義了通用的認證提供者介面和一個工廠函數，
// 使得應用程式可以輕鬆地在不同的 SSO 提供者之間切換。
package auth

import (
	"context"
	"fmt"
	"github.com/coreos/go-oidc/v3/oidc"
	"github.com/detectviz/control-plane/internal/config"
)

// AuthProvider 定義了一個通用的身份認證提供者介面。
// 任何 SSO 解決方案（如 Keycloak, Okta, Auth0）都應實現此介面。
type AuthProvider interface {
	// VerifyToken 驗證傳入的 JWT，如果驗證成功，返回一個已解析的 token。
	VerifyToken(ctx context.Context, rawIDToken string) (*oidc.IDToken, error)
	// GetM2MToken 獲取一個用於服務間 (Machine-to-Machine) 通訊的 access token。
	GetM2MToken(ctx context.Context) (string, error)
}

// DevProvider 是一個用於開發和測試的模擬認證提供者。
// 它實現了 AuthProvider 介面，但返回固定的或無操作的結果。
type DevProvider struct{}

// VerifyToken 在開發模式下不執行任何操作，直接返回 nil，表示驗證通過。
func (p *DevProvider) VerifyToken(ctx context.Context, rawIDToken string) (*oidc.IDToken, error) {
	// 在開發模式下，我們不驗證 token，直接放行。
	// 注意：這意味著任何 Bearer token 都會被接受。
	return nil, nil
}

// GetM2MToken 在開發模式下返回一個固定的假 token。
func (p *DevProvider) GetM2MToken(ctx context.Context) (string, error) {
	return "dev-m2m-token", nil
}

// NewAuthProvider 是一個工廠函數，它根據提供的配置創建並返回一個具體的 AuthProvider 實例。
// 這是實現 SSO 提供者可插拔性的關鍵。
func NewAuthProvider(cfg config.AuthConfig) (AuthProvider, error) {
	switch cfg.Mode {
	case "keycloak":
		// 如果配置為 "keycloak"，則創建一個 KeycloakService 實例。
		return NewKeycloakService(cfg)
	case "dev":
		// 在開發模式下，返回一個安全的模擬提供者。
		return &DevProvider{}, nil
	// case "okta":
	//     // 未來可以輕鬆地在這裡添加對 Okta 的支援。
	//     return NewOktaProvider(cfg)
	default:
		// 如果提供了未知的 provider 類型，返回一個錯誤。
		return nil, fmt.Errorf("未知的認證提供者類型: %s", cfg.Mode)
	}
}
