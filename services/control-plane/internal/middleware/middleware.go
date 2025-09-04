// Package middleware 提供了 HTTP 中介軟體，用於處理所有傳入請求的通用功能，
// 例如日誌記錄、錯誤恢復、身份認證等。
package middleware

import (
	"context"
	"net/http"
	"strings"
	"time"

	"github.com/detectviz/control-plane/internal/auth"
	"github.com/google/uuid"
	"github.com/uptrace/opentelemetry-go-extra/otelzap"
	"go.uber.org/zap"
)

type contextKey string

const RequestIDKey contextKey = "requestID"

// RequestID 為每個請求附加一個唯一的 ID，以便追蹤和日誌記錄。
func RequestID() func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			requestID := uuid.New().String()
			ctx := context.WithValue(r.Context(), RequestIDKey, requestID)
			w.Header().Set("X-Request-ID", requestID)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

// Logging 記錄每個傳入請求的詳細資訊，如方法、路徑、處理時間和狀態碼。
func Logging(logger *otelzap.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()
			// 使用一個自訂的 responseWriter 來捕獲狀態碼
			rw := &responseWriter{ResponseWriter: w, statusCode: http.StatusOK}

			// otelzap 會自動處理從 context 提取 trace ID，我們無需手動添加
			next.ServeHTTP(w, r)
			duration := time.Since(start)

			logger.Ctx(r.Context()).Info("傳入請求",
				zap.String("method", r.Method),
				zap.String("path", r.URL.Path),
				zap.Int("status", rw.statusCode),
				zap.Duration("duration", duration),
				zap.String("remoteAddr", r.RemoteAddr),
				zap.String("userAgent", r.UserAgent()),
			)
		})
	}
}

// Recovery 從 panic 中恢復，記錄錯誤並回傳 500 錯誤，防止伺服器崩潰。
func Recovery(logger *otelzap.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			defer func() {
				if err := recover(); err != nil {
					// 使用 Ctx(r.Context()) 來確保日誌與追蹤 (trace) 關聯
					logger.Ctx(r.Context()).Error("Panic 恢復",
						zap.Any("error", err),
						zap.Stack("stack"),
					)
					http.Error(w, "內部伺服器錯誤", http.StatusInternalServerError)
				}
			}()
			next.ServeHTTP(w, r)
		})
	}
}

// RequireAuth 是一個保護 API 端點的中介軟體。
// 它會檢查請求的 Authorization 標頭中是否存在有效的 Bearer JWT。
// 這主要用於保護供 SRE Assistant 或其他機器客戶端呼叫的 API。
func RequireAuth(authSvc *auth.KeycloakService) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			authHeader := r.Header.Get("Authorization")
			if authHeader == "" {
				http.Error(w, "未提供授權標頭", http.StatusUnauthorized)
				return
			}

			parts := strings.Split(authHeader, " ")
			if len(parts) != 2 || strings.ToLower(parts[0]) != "bearer" {
				http.Error(w, "授權標頭格式錯誤", http.StatusUnauthorized)
				return
			}
			rawToken := parts[1]

			_, err := authSvc.VerifyToken(r.Context(), rawToken)
			if err != nil {
				http.Error(w, "無效的權杖: "+err.Error(), http.StatusUnauthorized)
				return
			}

			// 權杖有效，繼續處理請求
			next.ServeHTTP(w, r)
		})
	}
}

// RequireSession 是一個保護 Web UI 頁面的中介軟體。
// 在一個完整的應用中，它會檢查使用者的 session cookie。
// 為了簡化，我們暫時將其作為一個預留位置。
func RequireSession(authSvc *auth.KeycloakService) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			// TODO: 實作基於 cookie 的 session 管理
			// 目前，我們可以檢查 session cookie 是否存在
			// c, err := r.Cookie("session_token")
			// if err != nil {
			// 	if err == http.ErrNoCookie {
			// 		// 重定向到登入頁面
			// 		http.Redirect(w, r, "/auth/login", http.StatusFound)
			// 		return
			// 	}
			// 	http.Error(w, "內部錯誤", http.StatusBadRequest)
			// 	return
			// }
			//
			// sessionToken := c.Value
			// 可以在這裡驗證 session token

			// 簡化版：暫時允許所有請求通過
			next.ServeHTTP(w, r)
		})
	}
}


// responseWriter 是一個輔助結構，用於捕獲由處理器寫入的 HTTP 狀態碼。
type responseWriter struct {
	http.ResponseWriter
	statusCode int
}

func (rw *responseWriter) WriteHeader(code int) {
	rw.statusCode = code
	rw.ResponseWriter.WriteHeader(code)
}
