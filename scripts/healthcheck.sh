#!/usr/bin/env bash
# ============================================================
# Script de monitoreo — verifica la salud del sistema
# ============================================================
set -euo pipefail

API_URL="${1:-http://localhost:5000}"
ALERT_ENDPOINT="${2:-}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_service() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}

    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")

    if [ "$response" = "$expected_code" ]; then
        echo -e "  ${GREEN}✓${NC} ${name}: OK (${response})"
        return 0
    else
        echo -e "  ${RED}✗${NC} ${name}: FAILED (got ${response}, expected ${expected_code})"
        return 1
    fi
}

echo "══════════════════════════════════════════"
echo " BookVault Health Check — $(date)"
echo "══════════════════════════════════════════"
echo ""

FAILURES=0

echo "API Endpoints:"
check_service "Liveness  (/health)" "${API_URL}/health" || ((FAILURES++))
check_service "Readiness (/ready)"  "${API_URL}/ready"  || ((FAILURES++))
check_service "Metrics   (/metrics)" "${API_URL}/metrics" || ((FAILURES++))
check_service "Books API (/api/v1/books)" "${API_URL}/api/v1/books" || ((FAILURES++))

echo ""
echo "Docker Containers:"
for container in bookvault-api bookvault-db; do
    status=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null || echo "not found")
    if [ "$status" = "running" ]; then
        echo -e "  ${GREEN}✓${NC} ${container}: ${status}"
    else
        echo -e "  ${RED}✗${NC} ${container}: ${status}"
        ((FAILURES++))
    fi
done

echo ""
echo "Disk Usage:"
usage=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$usage" -lt 80 ]; then
    echo -e "  ${GREEN}✓${NC} Root filesystem: ${usage}%"
elif [ "$usage" -lt 90 ]; then
    echo -e "  ${YELLOW}⚠${NC} Root filesystem: ${usage}% (warning)"
else
    echo -e "  ${RED}✗${NC} Root filesystem: ${usage}% (critical)"
    ((FAILURES++))
fi

echo ""
echo "══════════════════════════════════════════"
if [ "$FAILURES" -gt 0 ]; then
    echo -e " Result: ${RED}${FAILURES} FAILURES${NC}"
    exit 1
else
    echo -e " Result: ${GREEN}ALL CHECKS PASSED${NC}"
    exit 0
fi
