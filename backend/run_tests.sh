#!/bin/bash

# Test runner script for backend test suite
# Usage: ./run_tests.sh [option]
#
# Options:
#   all       - Run all tests (default)
#   fast      - Run only fast tests (no API calls)
#   unit      - Run only unit tests
#   integration - Run only integration tests
#   e2e       - Run only end-to-end tests
#   consistency - Run only consistency tests
#   coverage  - Run tests with coverage report

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the backend directory
if [ ! -f "pytest.ini" ]; then
    echo -e "${RED}Error: pytest.ini not found. Are you in the backend directory?${NC}"
    exit 1
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo "Install with: pip install -r tests/requirements-test.txt"
    exit 1
fi

# Check if OPENAI_API_KEY is set for slow tests
check_api_key() {
    if [ -z "$OPENAI_API_KEY" ]; then
        echo -e "${YELLOW}Warning: OPENAI_API_KEY not set. Slow tests will be skipped.${NC}"
        return 1
    fi
    return 0
}

# Default to all tests
TEST_TYPE="${1:-all}"

echo -e "${GREEN}Running backend tests...${NC}"
echo ""

case $TEST_TYPE in
    all)
        echo "Running all tests..."
        check_api_key || echo "Proceeding without API key (some tests may be skipped)"
        pytest tests/ -v
        ;;

    fast)
        echo "Running fast tests only (no API calls)..."
        pytest tests/unit/ tests/consistency/ -v
        ;;

    unit)
        echo "Running unit tests..."
        pytest tests/unit/ -v
        ;;

    integration)
        echo "Running integration tests..."
        check_api_key && pytest tests/integration/ -v || pytest tests/integration/ -m "not slow" -v
        ;;

    e2e)
        echo "Running end-to-end tests..."
        if check_api_key; then
            pytest tests/e2e/ -v
        else
            echo -e "${RED}Error: OPENAI_API_KEY required for e2e tests${NC}"
            exit 1
        fi
        ;;

    consistency)
        echo "Running consistency tests..."
        pytest tests/consistency/ -v
        ;;

    coverage)
        echo "Running tests with coverage report..."
        pytest tests/ --cov=. --cov-report=html --cov-report=term -v
        echo ""
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;

    *)
        echo -e "${RED}Unknown option: $TEST_TYPE${NC}"
        echo ""
        echo "Usage: ./run_tests.sh [option]"
        echo ""
        echo "Options:"
        echo "  all         - Run all tests (default)"
        echo "  fast        - Run only fast tests (no API calls)"
        echo "  unit        - Run only unit tests"
        echo "  integration - Run only integration tests"
        echo "  e2e         - Run only end-to-end tests"
        echo "  consistency - Run only consistency tests"
        echo "  coverage    - Run tests with coverage report"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Tests completed!${NC}"
