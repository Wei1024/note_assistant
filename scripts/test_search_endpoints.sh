#!/bin/bash
# Quick test script for Phase 4 search endpoints
# Usage: ./scripts/test_search_endpoints.sh

API_BASE="http://localhost:8000"

echo "Testing Phase 4 Search Endpoints"
echo "================================="
echo ""

# Test 1: Health check
echo "1. Health check..."
curl -s "$API_BASE/health" | jq . 2>/dev/null || curl -s "$API_BASE/health"
echo ""
echo ""

# Test 2: Hybrid search
echo "2. Testing hybrid search..."
curl -s -X POST "$API_BASE/search?query=memory&top_k=3&expand_graph=false" | jq '.query, .total_results, .execution_time_ms' 2>/dev/null || echo "Failed - endpoint not found or server not restarted"
echo ""
echo ""

# Test 3: Graph nodes (verify data exists)
echo "3. Checking if notes exist..."
curl -s "$API_BASE/graph/nodes" | jq '.count' 2>/dev/null || echo "Failed"
echo ""
echo ""

# Test 4: Graph stats
echo "4. Graph statistics..."
curl -s "$API_BASE/graph/stats" | jq '.nodes.total, .edges.total' 2>/dev/null || echo "Failed"
echo ""
echo ""

echo "================================="
echo "If you see 404 errors above, restart the server:"
echo "  1. Kill existing: lsof -ti:8000 | xargs kill -9"
echo "  2. Restart: .venv/bin/uvicorn api.main:app --reload --port 8000"
echo "================================="
