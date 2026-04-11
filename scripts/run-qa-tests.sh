#!/bin/bash
#
# QA Test Runner Script
# 
# This script runs various levels of QA tests based on the argument provided.
#
# Usage: ./scripts/run-qa-tests.sh [test-level]
#
# Test levels:
#   fast      - Quick tests (contract tests only) ~30s
#   standard  - Contract + integration tests ~2min
#   validation - All validation tests ~5min
#   e2e       - End-to-end browser tests ~10min
#   e2e-smoke - E2E smoke tests only (includes admin smoke) ~2min
#   full      - All tests including E2E ~15min
#   coverage  - Full tests with coverage report
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Function to print colored output
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    print_warning "Virtual environment not activated. Activating..."
    source .venv/bin/activate || {
        print_error "Failed to activate virtual environment"
        exit 1
    }
fi

# Parse test level argument
TEST_LEVEL="${1:-standard}"

# Run tests based on level
case "$TEST_LEVEL" in
    fast)
        print_header "Running Fast Tests (Contract Tests Only)"
        pytest tests/contract/ -v --tb=short
        print_success "Fast tests completed"
        ;;
    
    standard)
        print_header "Running Standard Tests (Contract + Integration)"
        pytest tests/contract/ tests/integration/ -v --tb=short
        print_success "Standard tests completed"
        ;;
    
    validation)
        print_header "Running Validation Tests"
        pytest tests/validation/ -v --tb=short
        print_success "Validation tests completed"
        ;;
    
    e2e)
        print_header "Running E2E Tests"
        print_warning "Starting test server if not running..."
        
        # Check if server is running
        if ! curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
            print_warning "Server not running. Please start it first:"
            echo "  make run"
            exit 1
        fi
        
        export E2E_BASE_URL="http://localhost:8000"
        pytest tests/e2e/ -v --headed --screenshot on --video retain-on-failure
        print_success "E2E tests completed"
        ;;

    e2e-smoke)
        print_header "Running E2E Smoke Tests"

        # Default to deterministic sqlite test admin unless explicitly overridden.
        export E2E_ADMIN_USERNAME="${E2E_ADMIN_USERNAME:-admin}"
        export E2E_ADMIN_PASSWORD="${E2E_ADMIN_PASSWORD:-admin1234}"

        pytest tests/e2e/test_smoke_public_pages.py \
               tests/e2e/test_smoke_user_pages.py \
               tests/e2e/test_smoke_admin_pages.py \
               -v --tb=short
        print_success "E2E smoke tests completed"
        ;;
    
    full)
        print_header "Running Full Test Suite"
        
        print_header "1/3: Contract & Integration Tests"
        pytest tests/contract/ tests/integration/ -v --tb=short
        
        print_header "2/3: Validation Tests"
        pytest tests/validation/ -v --tb=short
        
        print_header "3/3: E2E Tests"
        if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
            export E2E_BASE_URL="http://localhost:8000"
            pytest tests/e2e/ -v --screenshot on --video retain-on-failure
        else
            print_warning "Skipping E2E tests - server not running"
        fi
        
        print_success "Full test suite completed"
        ;;
    
    coverage)
        print_header "Running Tests with Coverage"
        pytest tests/contract/ tests/integration/ tests/validation/ \
            --cov=src/backend \
            --cov-report=html \
            --cov-report=term-missing \
            --cov-report=json \
            -v
        
        print_success "Coverage report generated at htmlcov/index.html"
        
        # Display coverage summary
        if command -v jq &> /dev/null && [ -f coverage.json ]; then
            COVERAGE=$(jq '.totals.percent_covered' coverage.json)
            echo -e "${BLUE}Total Coverage: ${COVERAGE}%${NC}"
        fi
        ;;
    
    smoke)
        print_header "Running Smoke Tests (Critical Paths Only)"
        pytest tests/contract/ tests/integration/ -m "smoke" -v --tb=short
        print_success "Smoke tests completed"
        ;;
    
    security)
        print_header "Running Security Tests"
        pytest tests/validation/ -k "sql_injection or xss or security" -v --tb=short
        print_success "Security tests completed"
        ;;
    
    *)
        print_error "Unknown test level: $TEST_LEVEL"
        echo ""
        echo "Usage: $0 [test-level]"
        echo ""
        echo "Available test levels:"
        echo "  fast       - Quick tests (contract tests only) ~30s"
        echo "  standard   - Contract + integration tests ~2min"
        echo "  validation - All validation tests ~5min"
        echo "  e2e        - End-to-end browser tests ~10min"
        echo "  e2e-smoke  - E2E smoke tests only ~2min"
        echo "  full       - All tests including E2E ~15min"
        echo "  coverage   - Full tests with coverage report"
        echo "  smoke      - Critical path tests only"
        echo "  security   - Security-focused tests only"
        exit 1
        ;;
esac

# Exit with success
exit 0
