#!/bin/bash
# Dumont Cloud - Test Commands Reference
# Script com todos os comandos executados durante os testes

BASE_URL="http://localhost:8000"
DEMO="?demo=true"

echo "=================================="
echo "DUMONT CLOUD - TEST COMMANDS"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run test
run_test() {
    local name=$1
    local cmd=$2
    echo -e "${YELLOW}Testing:${NC} $name"
    echo -e "${GREEN}Command:${NC} $cmd"
    eval $cmd
    echo ""
}

echo "=== CORE INFRASTRUCTURE ==="
run_test "Health Check" "curl -s $BASE_URL/health | python3 -m json.tool"
run_test "API Docs Available" "curl -s $BASE_URL/docs | grep -o '<title>.*</title>'"
run_test "OpenAPI Schema" "curl -s $BASE_URL/api/v1/openapi.json | python3 -c 'import sys, json; print(\"Endpoints:\", len(json.load(sys.stdin).get(\"paths\", {})))'"

echo "=== DATABASE ==="
run_test "PostgreSQL Connection" "PGPASSWORD=dumont123 psql -h localhost -U dumont -d dumont_cloud -c 'SELECT COUNT(*) FROM market_snapshots;'"
run_test "Redis Connection" "redis-cli ping"

echo "=== AUTHENTICATION ==="
run_test "Register User" "curl -s -X POST $BASE_URL/api/auth/register -H 'Content-Type: application/json' -d '{\"email\":\"test@dumont.cloud\",\"password\":\"test123\",\"name\":\"Test User\"}' | python3 -m json.tool"
run_test "Login" "curl -s -X POST $BASE_URL/api/auth/login -H 'Content-Type: application/json' -d '{\"email\":\"test@dumont.cloud\",\"password\":\"test123\"}' | python3 -m json.tool"
run_test "Get User (Demo)" "curl -s '$BASE_URL/api/auth/me$DEMO' | python3 -m json.tool"

echo "=== INSTANCES ==="
run_test "List Instances" "curl -s '$BASE_URL/api/instances$DEMO' | python3 -m json.tool | head -20"
run_test "List GPU Offers" "curl -s '$BASE_URL/api/instances/offers$DEMO' | python3 -c 'import sys, json; d=json.load(sys.stdin); print(\"Total offers:\", len(d.get(\"offers\", [])))'"

echo "=== SERVERLESS GPU ==="
run_test "Serverless Status" "curl -s '$BASE_URL/api/serverless/status$DEMO' | python3 -m json.tool | head -15"
run_test "Serverless List" "curl -s '$BASE_URL/api/serverless/list$DEMO' | python3 -m json.tool | head -15"
run_test "Serverless Pricing" "curl -s '$BASE_URL/api/serverless/pricing$DEMO' | python3 -m json.tool | head -15"

echo "=== CPU STANDBY ==="
run_test "Standby Status" "curl -s '$BASE_URL/api/standby/status$DEMO' | python3 -m json.tool | head -15"
run_test "Standby Associations" "curl -s '$BASE_URL/api/standby/associations$DEMO' | python3 -m json.tool | head -15"

echo "=== WARM POOL ==="
run_test "Warmpool Hosts" "curl -s '$BASE_URL/api/warmpool/hosts$DEMO' | python3 -m json.tool | head -15"

echo "=== FAILOVER ==="
run_test "Failover Strategies" "curl -s '$BASE_URL/api/failover/strategies$DEMO' | python3 -m json.tool"
run_test "Failover Settings" "curl -s '$BASE_URL/api/failover/settings/global$DEMO' | python3 -m json.tool | head -15"

echo "=== HIBERNATION ==="
run_test "Hibernation Stats" "curl -s '$BASE_URL/api/hibernation/stats$DEMO' | python3 -m json.tool"

echo "=== JOBS ==="
run_test "List Jobs" "curl -s '$BASE_URL/api/jobs/$DEMO' | python3 -m json.tool | head -15"

echo "=== MODELS ==="
run_test "List Model Deployments" "curl -s '$BASE_URL/api/models/$DEMO' | python3 -m json.tool | head -15"
run_test "Model Templates" "curl -s '$BASE_URL/api/models/templates$DEMO' | python3 -m json.tool | head -20"

echo "=== METRICS ==="
run_test "GPU Metrics" "curl -s '$BASE_URL/api/metrics/gpus$DEMO' | python3 -m json.tool | head -20"
run_test "Market Summary" "curl -s '$BASE_URL/api/metrics/market/summary$DEMO' | python3 -c 'import sys, json; d=json.load(sys.stdin); print(\"GPUs tracked:\", len(d.get(\"data\", {})))'"
run_test "Spot Monitor" "curl -s '$BASE_URL/api/metrics/spot/monitor$DEMO' | python3 -m json.tool | head -20"

echo "=== SAVINGS ==="
run_test "Savings Summary" "curl -s '$BASE_URL/api/savings/summary$DEMO' | python3 -m json.tool"
run_test "Savings History" "curl -s '$BASE_URL/api/savings/history$DEMO' | python3 -m json.tool | head -15"

echo "=== MACHINE HISTORY ==="
run_test "History Summary" "curl -s '$BASE_URL/api/machines/history/summary$DEMO' | python3 -m json.tool"
run_test "Reliable Machines" "curl -s '$BASE_URL/api/machines/history/reliable$DEMO' | python3 -m json.tool | head -15"
run_test "Blacklist" "curl -s '$BASE_URL/api/machines/history/blacklist$DEMO' | python3 -m json.tool"

echo "=== SPOT DEPLOY ==="
run_test "Spot Instances" "curl -s '$BASE_URL/api/spot/instances$DEMO' | python3 -m json.tool | head -15"
run_test "Spot Templates" "curl -s '$BASE_URL/api/spot/templates$DEMO' | python3 -m json.tool | head -15"

echo "=== FINETUNE ==="
run_test "Finetune Jobs" "curl -s '$BASE_URL/api/finetune/jobs$DEMO' | python3 -m json.tool | head -15"
run_test "Finetune Models" "curl -s '$BASE_URL/api/finetune/models$DEMO' | python3 -m json.tool | head -15"

echo "=== CLI ==="
run_test "CLI Help" "dumont --help | head -20"
run_test "CLI Instance List" "dumont --base-url $BASE_URL instance list"
run_test "CLI Auth Me" "dumont --base-url $BASE_URL auth me"

echo "=== VAST.AI INTEGRATION ==="
run_test "VAST API Direct" "python3 << 'PYTHON'
import os, requests
api_key = os.environ.get('VAST_API_KEY', 'a9df8f732d9b1b8a6bb54fd43c477824254552b0d964c58bd92b16c6f25ca3dd')
headers = {'Authorization': f'Bearer {api_key}'}
response = requests.get('https://console.vast.ai/api/v0/bundles/', headers=headers)
print(f'Status: {response.status_code}')
if response.status_code == 200:
    data = response.json()
    print(f'Total offers: {len(data.get(\"offers\", []))}')
    if data.get('offers'):
        print(f'Cheapest GPU: {data[\"offers\"][0].get(\"gpu_name\", \"N/A\")} @ \${data[\"offers\"][0].get(\"dph_total\", \"N/A\")}/hr')
PYTHON"

echo ""
echo "=================================="
echo "ALL TESTS COMPLETED"
echo "=================================="
echo ""
echo "For detailed results, see:"
echo "  - TESTE_REPORT.md (full report)"
echo "  - TESTE_SUMMARY.md (quick overview)"
echo ""
