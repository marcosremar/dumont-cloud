#!/bin/bash

# Chat Arena Readiness Check
# Verifies all prerequisites are met before running tests

echo "========================================="
echo "Chat Arena Test Readiness Check"
echo "========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
all_ready=true

# 1. Check if Ollama is running
echo -n "1. Checking Ollama service... "
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    echo "   Start with: ollama serve"
    all_ready=false
fi

# 2. Check if models are installed
echo -n "2. Checking Ollama models... "
models_output=$(curl -s http://localhost:11434/api/tags 2>/dev/null)
if echo "$models_output" | grep -q "llama3.2:1b"; then
    llama_installed=true
else
    llama_installed=false
fi

if echo "$models_output" | grep -q "qwen2.5:0.5b"; then
    qwen_installed=true
else
    qwen_installed=false
fi

if [ "$llama_installed" = true ] && [ "$qwen_installed" = true ]; then
    echo -e "${GREEN}✓ Both models installed${NC}"
elif [ "$llama_installed" = true ] || [ "$qwen_installed" = true ]; then
    echo -e "${YELLOW}⚠ Only one model installed${NC}"
    [ "$llama_installed" = false ] && echo "   Missing: llama3.2:1b (run: ollama pull llama3.2:1b)"
    [ "$qwen_installed" = false ] && echo "   Missing: qwen2.5:0.5b (run: ollama pull qwen2.5:0.5b)"
else
    echo -e "${RED}✗ No required models installed${NC}"
    echo "   Install with:"
    echo "   ollama pull llama3.2:1b"
    echo "   ollama pull qwen2.5:0.5b"
    all_ready=false
fi

# 3. Check if web app is running
echo -n "3. Checking web app (port 4896)... "
if curl -s http://localhost:4896/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not responding${NC}"
    echo "   Start with: cd web && npm run dev"
    all_ready=false
fi

# 4. Check if backend API is accessible
echo -n "4. Checking backend API... "
api_response=$(curl -s http://localhost:4896/api/v1/chat/models 2>/dev/null)
if [ -n "$api_response" ]; then
    echo -e "${GREEN}✓ Accessible${NC}"
    # Count models from API
    model_count=$(echo "$api_response" | grep -o '"id"' | wc -l | tr -d ' ')
    echo "   Found $model_count model(s) in API response"
else
    echo -e "${YELLOW}⚠ No response${NC}"
    echo "   API may not be configured for models"
fi

# 5. Check if Chat Arena page is accessible
echo -n "5. Checking Chat Arena page... "
chat_arena_response=$(curl -s http://localhost:4896/chat-arena 2>/dev/null)
if echo "$chat_arena_response" | grep -q "Chat Arena"; then
    echo -e "${GREEN}✓ Accessible${NC}"
else
    echo -e "${YELLOW}⚠ May not be fully loaded${NC}"
    echo "   Page responds but content unclear"
fi

# 6. Check if Playwright is installed
echo -n "6. Checking Playwright... "
if command -v npx > /dev/null 2>&1; then
    if npx playwright --version > /dev/null 2>&1; then
        pw_version=$(npx playwright --version 2>/dev/null | head -1)
        echo -e "${GREEN}✓ Installed ($pw_version)${NC}"
    else
        echo -e "${RED}✗ Not installed${NC}"
        echo "   Install with: npm install -D @playwright/test"
        echo "   Then: npx playwright install chromium"
        all_ready=false
    fi
else
    echo -e "${RED}✗ npx not found${NC}"
    echo "   Install Node.js and npm first"
    all_ready=false
fi

# 7. Check screenshots directory
echo -n "7. Checking screenshots directory... "
if [ -d "tests/screenshots" ]; then
    echo -e "${GREEN}✓ Exists${NC}"
else
    echo -e "${YELLOW}⚠ Creating...${NC}"
    mkdir -p tests/screenshots
    echo "   Created tests/screenshots/"
fi

# 8. Check test files
echo -n "8. Checking test files... "
test_files_exist=true
[ ! -f "tests/chat-arena-local-test.spec.js" ] && test_files_exist=false
[ ! -f "tests/chat-arena-debug.spec.js" ] && test_files_exist=false

if [ "$test_files_exist" = true ]; then
    echo -e "${GREEN}✓ Found${NC}"
else
    echo -e "${RED}✗ Missing test files${NC}"
    all_ready=false
fi

echo ""
echo "========================================="
if [ "$all_ready" = true ]; then
    echo -e "${GREEN}✓ All checks passed! Ready to test.${NC}"
    echo ""
    echo "Run tests with:"
    echo "  ./run-chat-arena-test.sh          (headed mode)"
    echo "  ./run-chat-arena-test-headless.sh (headless mode)"
    echo ""
    echo "Or run specific tests:"
    echo "  npx playwright test tests/chat-arena-local-test.spec.js --headed"
    echo "  npx playwright test tests/chat-arena-debug.spec.js --headed"
else
    echo -e "${RED}✗ Some checks failed. Fix issues above before testing.${NC}"
fi
echo "========================================="
