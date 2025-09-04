// services/control-plane/go.mod
module github.com/detectviz/control-plane

go 1.24

require (
	github.com/coreos/go-oidc/v3 v3.15.0
	github.com/google/uuid v1.6.0
	github.com/gorilla/mux v1.8.1
	github.com/lib/pq v1.10.9
	github.com/rs/cors v1.10.1
	go.opentelemetry.io/otel v1.38.0
	go.opentelemetry.io/otel/exporters/stdout/stdouttrace v1.38.0
	go.opentelemetry.io/otel/sdk v1.38.0
	go.uber.org/zap v1.27.0
	golang.org/x/oauth2 v0.28.0
)

require (
	github.com/go-jose/go-jose/v4 v4.0.5 // indirect
	github.com/go-logr/logr v1.4.3 // indirect
	github.com/go-logr/stdr v1.2.2 // indirect
	github.com/uptrace/opentelemetry-go-extra/otelutil v0.3.2 // indirect
	go.opentelemetry.io/auto/sdk v1.1.0 // indirect
	go.opentelemetry.io/otel/log v0.6.0 // indirect
	go.opentelemetry.io/otel/metric v1.38.0 // indirect
	go.opentelemetry.io/otel/trace v1.38.0 // indirect
	golang.org/x/sys v0.35.0 // indirect
)

require (
	github.com/caarlos0/env/v6 v6.10.1
	github.com/uptrace/opentelemetry-go-extra/otelzap v0.3.2
	go.uber.org/multierr v1.11.0 // indirect
	golang.org/x/crypto v0.36.0 // indirect
)
