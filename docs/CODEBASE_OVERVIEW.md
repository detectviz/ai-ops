# SRE Platform - Codebase Overview

This document provides a high-level overview of the source code structure for the SRE Platform project. It is intended to help developers quickly understand the purpose of each service and the key files within them.

## Project Architecture

The SRE Platform follows a microservices architecture, consisting of two main backend services:

1.  **Control Plane (`services/control-plane`)**: A Go-based service that acts as the central API gateway and persistence layer for the platform. It manages resources, incidents, and other core data models.
2.  **SRE Assistant (`services/sre-assistant`)**: A Python-based AI agent service that performs intelligent diagnostics, analysis, and automation. It is a consumer of the Control Plane's API.

The frontend is developed in a separate repository and interacts with the `control-plane` service via its headless API.

---

## 🎯 Control Plane (Go Service)

The Control Plane is the core backend service responsible for data management and providing the primary API for the platform.

**Location**: `services/control-plane/`

### Key Directories & Files

#### `cmd/server/main.go`

*   **Purpose**: Main application entry point.
*   **Responsibilities**:
    *   Initializes the logger, configuration, and database connection.
    *   Sets up the OpenTelemetry tracer for distributed tracing.
    *   Initializes all services and HTTP handlers.
    *   Defines the API routes using `gorilla/mux`.
    *   Configures and starts the main HTTP server, including CORS and timeout settings.
    *   Handles graceful shutdown of the server and its resources.

#### `internal/handlers/handlers.go`

*   **Purpose**: Contains all HTTP handler functions for the API endpoints.
*   **Responsibilities**:
    *   Receives HTTP requests from the router.
    *   Parses request data (e.g., path parameters, query strings, request bodies).
    *   Calls the appropriate methods in the business logic layer (`services`).
    *   Formats the response (e.g., writing JSON data and setting HTTP status codes).
    *   Currently contains mock implementations for many API endpoints, which serve as placeholders until the real business logic is implemented.

#### `internal/services/services.go`

*   **Purpose**: Implements the core business logic of the service.
*   **Responsibilities**:
    *   Acts as an intermediary between the HTTP handlers and the data layer.
    *   Contains the logic for operations like creating, retrieving, updating, and deleting resources.
    *   Communicates with other services (like the `sre-assistant`) via dedicated clients.
    *   *Note*: This layer is currently minimal and will be expanded as business logic is moved from mock handlers to real implementations.

#### `internal/models/models.go`

*   **Purpose**: Defines the data structures for the application, which map to database tables.
*   **Responsibilities**:
    *   Contains Go structs for all primary data models (e.g., `Resource`, `Incident`, `AuditLog`).
    *   These structs use GORM tags for database schema mapping and JSON tags for API serialization.
    *   Also includes structs for API request and response bodies that are not directly mapped to the database.

#### `internal/database/database.go`

*   **Purpose**: Manages the database connection and schema migrations.
*   **Responsibilities**:
    *   Establishes a connection pool to the PostgreSQL database using the provided configuration.
    *   Uses GORM's `AutoMigrate` feature to automatically create or update the database schema based on the structs in the `models` package.

#### `internal/auth/keycloak.go`

*   **Purpose**: Handles authentication logic, specifically for validating JWTs from Keycloak.
*   **Responsibilities**:
    *   Initializes the Keycloak service with configuration details (URL, realm).
    *   Fetches the public keys from Keycloak required to verify JWT signatures.
    *   Provides a function to verify the signature and claims of an incoming JWT.

#### `internal/config/config.go`

*   **Purpose**: Manages application configuration.
*   **Responsibilities**:
    *   Defines a struct that holds all configuration parameters for the application (server port, database URL, OTel endpoint, etc.).
    *   Uses a library (like `viper` or a custom implementation) to load these parameters from environment variables or a configuration file.

#### `internal/middleware/*.go`

*   **Purpose**: Contains reusable HTTP middleware functions.
*   **Responsibilities**:
    *   Implements cross-cutting concerns for API requests, such as:
        *   **Logging**: Records details for every incoming request.
        *   **Authentication**: Checks for a valid JWT on protected routes.
        *   **Recovery**: Catches panics and prevents the server from crashing.
        *   **Request ID**: Injects a unique ID into each request for improved traceability.
    *   These middlewares are applied to the router in `main.go`.

---

## 🤖 SRE Assistant (Python Service)

The SRE Assistant is a Python-based service that acts as an intelligent agent. It consumes data from various sources (via its tools) to perform complex diagnostics and analysis.

**Location**: `services/sre-assistant/`

### Key Directories & Files

#### `src/sre_assistant/main.py`

*   **Purpose**: Main application entry point using the FastAPI framework.
*   **Responsibilities**:
    *   Defines the FastAPI application instance.
    *   Manages the application's lifecycle (`lifespan`) to initialize and clean up resources like database connections, HTTP clients, and the main `SREWorkflow` instance.
    *   Sets up all middlewares, including CORS, OpenTelemetry for tracing, and custom middlewares for audit logging and request context.
    *   Defines all API endpoints (`/api/v1/diagnostics/*`, `/api/v1/execute`, etc.).
    *   Handles incoming requests, validates them using Pydantic models, and kicks off background tasks for asynchronous operations.

#### `src/sre_assistant/workflow.py`

*   **Purpose**: The "brain" of the assistant. This file contains the core orchestration logic.
*   **Responsibilities**:
    *   Defines the `SREWorkflow` class, which holds the primary business logic for handling diagnostic tasks.
    *   Contains methods like `_diagnose_deployment`, `_analyze_alerts`, and `_execute_query` which are the entry points for the different types of analysis.
    *   Coordinates calls to the various tools (Prometheus, Loki, etc.) to gather data.
    *   Analyzes the results from the tools to generate findings and recommendations.
    *   *Note*: This file is currently a placeholder for the core intelligent logic, which is the next major development task.

#### `src/sre_assistant/tools/`

*   **Purpose**: This directory contains individual "tool" modules that the `SREWorkflow` can use to interact with the outside world. Each tool is a wrapper around a specific data source's API.
*   **Key Files**:
    *   `prometheus_tool.py`: Interacts with a Prometheus server to query metrics.
    *   `loki_tool.py`: Interacts with a Loki server to query logs.
    *   `control_plane_tool.py`: Interacts with the `control-plane` service's API to fetch data about resources, incidents, etc. This is the primary way the two services communicate.
*   **Responsibilities**:
    *   Encapsulates the logic for making API calls to a specific service.
    *   Handles authentication, error handling, and retries for its target service.
    *   Uses Pydantic models to validate the data it receives from the APIs.
    *   Provides a clean, high-level interface for the `SREWorkflow` to use (e.g., `get_audit_logs()` instead of a raw HTTP call).

#### `src/sre_assistant/contracts.py`

*   **Purpose**: Defines all Pydantic data models used for API requests and responses.
*   **Responsibilities**:
    *   Ensures that all data flowing into and out of the `sre-assistant`'s API is strongly typed and validated.
    *   Provides a single source of truth for the data structures the service understands.
    *   Includes models for requests (e.g., `DiagnosticRequest`, `ExecuteRequest`) and responses/internal state (e.g., `DiagnosticStatus`, `Finding`).

#### `src/sre_assistant/auth.py`

*   **Purpose**: Handles security and authentication concerns.
*   **Responsibilities**:
    *   Contains the logic to verify JWTs passed in the `Authorization` header of incoming requests.
    *   This is used as a dependency in FastAPI endpoints to protect them from unauthorized access.

#### `src/sre_assistant/dependencies.py`

*   **Purpose**: Manages dependency injection for the FastAPI application.
*   **Responsibilities**:
    *   Initializes and provides singleton instances of shared resources, such as the configuration manager (`ConfigManager`).
    *   This allows different parts of the application to easily access shared state and configuration without using global variables.
