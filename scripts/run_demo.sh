#!/bin/bash
# End-to-end demo: start a research session and pretty-print the result.
#
# Prerequisites:
#   - docker compose up (web + db healthy)
#   - .env populated with a valid OPENAI_API_KEY or ANTHROPIC_API_KEY
#   - jq installed (brew install jq)
#
# Usage:
#   bash scripts/run_demo.sh
#   BASE_URL=http://localhost:8000 bash scripts/run_demo.sh

set -e

BASE_URL=${BASE_URL:-http://localhost:8000}
REPO_URL="https://github.com/psf/requests"
QUESTION="How does requests handle SSL certificate verification?"

echo "→ Starting research session…"
echo "  repo     : $REPO_URL"
echo "  question : $QUESTION"
echo ""

RESPONSE=$(curl -s -X POST "$BASE_URL/api/sessions/" \
  -H "Content-Type: application/json" \
  -d "{\"repo_url\":\"$REPO_URL\",\"question\":\"$QUESTION\"}")

# Bail out with the raw response if jq parsing fails.
echo "$RESPONSE" | jq . > /dev/null 2>&1 || {
  echo "ERROR: unexpected response:"
  echo "$RESPONSE"
  exit 1
}

echo "$RESPONSE" | jq '{
  id:            .id,
  status:        .status,
  iterations:    .iterations,
  tokens:        (.input_tokens + .output_tokens),
  answer_preview: (.final_answer // "" | .[0:300]),
  tool_calls:    [.tool_calls[] | "\(.sequence): \(.tool_name)"],
  findings:      [.findings[]   | {file: .file_path, lines: "\(.line_start)-\(.line_end)"}]
}'
