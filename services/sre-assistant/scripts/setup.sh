#!/bin/bash
# services/sre-assistant/scripts/setup.sh
#
# SRE Assistant 初始化腳本
# 用於快速設置本地開發環境
#

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 輔助函式
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# 檢查前置需求
check_requirements() {
    log_info "檢查前置需求..."
    
    # 檢查 Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 未安裝。請安裝 Python 3.11 或更高版本。"
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    required_version="3.11"
    
    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
        log_error "Python 版本過低。需要 Python $required_version 或更高版本，當前版本：$python_version"
    fi
    
    # 檢查 Poetry
    if ! command -v poetry &> /dev/null; then
        log_warning "Poetry 未安裝。正在安裝 Poetry..."
        curl -sSL https://install.python-poetry.org | python3 -
        export PATH="$HOME/.local/bin:$PATH"
    fi
    
    # 檢查 Docker
    if ! command -v docker &> /dev/null; then
        log_warning "Docker 未安裝。請安裝 Docker 以執行依賴服務。"
    fi
    
    # 檢查 Make
    if ! command -v make &> /dev/null; then
        log_warning "Make 未安裝。部分自動化指令可能無法使用。"
    fi
    
    log_success "前置需求檢查完成"
}

# 建立必要目錄
create_directories() {
    log_info "建立必要目錄..."
    
    mkdir -p src/sre_assistant/tools
    mkdir -p src/sre_assistant/config/environments
    mkdir -p tests
    mkdir -p scripts
    mkdir -p logs
    mkdir -p .github/workflows
    
    # 建立 __init__.py 檔案
    touch src/__init__.py
    touch src/sre_assistant/__init__.py
    touch src/sre_assistant/tools/__init__.py
    touch src/sre_assistant/config/__init__.py
    touch tests/__init__.py
    
    log_success "目錄結構建立完成"
}

# 設置環境變數
setup_environment() {
    log_info "設置環境變數..."
    
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            log_success "已從 .env.example 建立 .env 檔案"
            log_warning "請編輯 .env 檔案並填入實際的配置值"
        else
            log_warning ".env.example 不存在，建立基本 .env 檔案..."
            cat > .env << EOF
ENVIRONMENT=development
LOG_LEVEL=INFO
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sre_assistant
REDIS_URL=redis://localhost:6379
EOF
            log_success "已建立基本 .env 檔案"
        fi
    else
        log_info ".env 檔案已存在，跳過建立"
    fi
}

# 安裝 Python 依賴
install_dependencies() {
    log_info "安裝 Python 依賴..."
    
    # 配置 Poetry
    poetry config virtualenvs.in-project true
    
    # 安裝依賴
    poetry install --no-interaction --no-ansi
    
    log_success "Python 依賴安裝完成"
}

# 設置 Git hooks
setup_git_hooks() {
    log_info "設置 Git hooks..."
    
    # Pre-commit hook
    cat > ../../.git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Pre-commit hook for SRE Assistant

# 只檢查 sre-assistant 相關的變更
if git diff --cached --name-only | grep -q "services/sre-assistant/"; then
    cd services/sre-assistant
    
    # 執行格式化檢查
    echo "執行程式碼格式化檢查..."
    poetry run black --check src/ tests/
    poetry run isort --check-only src/ tests/
    
    # 執行 linting
    echo "執行程式碼品質檢查..."
    poetry run flake8 src/ tests/
    
    # 執行類型檢查
    echo "執行類型檢查..."
    poetry run mypy src/
    
    cd ../..
fi
EOF
    
    chmod +x ../../.git/hooks/pre-commit
    
    log_success "Git hooks 設置完成"
}

# 初始化資料庫
init_database() {
    log_info "初始化資料庫..."
    
    # 檢查 PostgreSQL 是否在執行
    if command -v psql &> /dev/null; then
        if psql -U postgres -h localhost -p 5432 -c "SELECT 1" &> /dev/null; then
            # 建立資料庫
            psql -U postgres -h localhost -p 5432 << EOF
CREATE DATABASE IF NOT EXISTS sre_assistant;
CREATE DATABASE IF NOT EXISTS sre_assistant_test;
EOF
            log_success "資料庫初始化完成"
        else
            log_warning "PostgreSQL 未執行或無法連接，跳過資料庫初始化"
        fi
    else
        log_warning "psql 未安裝，跳過資料庫初始化"
    fi
}

# 執行測試
run_tests() {
    log_info "執行測試..."
    
    # 執行 pytest
    if poetry run pytest --version &> /dev/null; then
        poetry run pytest -v --tb=short || {
            log_warning "部分測試失敗，請檢查錯誤訊息"
        }
    else
        log_warning "pytest 未安裝，跳過測試"
    fi
}

# 顯示下一步指示
show_next_steps() {
    echo ""
    echo "=========================================="
    echo -e "${GREEN}✅ SRE Assistant 初始化完成！${NC}"
    echo "=========================================="
    echo ""
    echo "下一步："
    echo ""
    echo "1. 編輯環境變數："
    echo "   vim .env"
    echo ""
    echo "2. 啟動依賴服務（從專案根目錄）："
    echo "   cd ../.."
    echo "   make up"
    echo ""
    echo "3. 執行服務："
    echo "   poetry run python -m src.sre_assistant.main"
    echo ""
    echo "4. 訪問 API 文件："
    echo "   http://localhost:8000/docs"
    echo ""
    echo "5. 執行測試："
    echo "   poetry run pytest"
    echo ""
    echo "有用的指令："
    echo "  poetry run black src/ tests/     # 格式化程式碼"
    echo "  poetry run pytest --cov          # 執行測試覆蓋率"
    echo "  poetry shell                     # 進入虛擬環境"
    echo ""
}

# 主函式
main() {
    echo "=========================================="
    echo "SRE Assistant 開發環境初始化"
    echo "=========================================="
    echo ""
    
    # 確認在正確的目錄
    if [ ! -f "pyproject.toml" ]; then
        log_error "請在 services/sre-assistant 目錄下執行此腳本"
    fi
    
    check_requirements
    create_directories
    setup_environment
    install_dependencies
    setup_git_hooks
    init_database
    run_tests
    show_next_steps
}

# 執行主函式
main "$@"