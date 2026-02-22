#!/bin/bash
#
# Pre-commit hook for running fast tests
#
# To install: ln -s ../../scripts/pre-commit.sh .git/hooks/pre-commit
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running pre-commit checks...${NC}"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Not in a git repository${NC}"
    exit 1
fi

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    if [ -f .venv/bin/activate ]; then
        source .venv/bin/activate
    else
        echo -e "${RED}Virtual environment not found. Run 'make venv' first.${NC}"
        exit 1
    fi
fi

# Run fast tests
echo -e "${YELLOW}Running fast tests...${NC}"
if pytest tests/contract/ -q --tb=short; then
    echo -e "${GREEN}✓ Fast tests passed${NC}"
else
    echo -e "${RED}✗ Fast tests failed${NC}"
    echo -e "${YELLOW}Fix the failing tests before committing.${NC}"
    exit 1
fi

# Check for common issues
echo -e "${YELLOW}Checking for common issues...${NC}"

# Check for print statements in production code (optional)
if git diff --cached --name-only | grep -E '\.py$' | xargs grep -n "print(" 2>/dev/null; then
    echo -e "${YELLOW}Warning: Found print() statements. Consider using logging instead.${NC}"
    # Don't fail, just warn
fi

# Check for TODO comments (optional)
if git diff --cached --name-only | grep -E '\.py$' | xargs grep -n "TODO:" 2>/dev/null; then
    echo -e "${YELLOW}Warning: Found TODO comments.${NC}"
    # Don't fail, just warn
fi

echo -e "${GREEN}✓ All pre-commit checks passed${NC}"
exit 0
