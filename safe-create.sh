#!/bin/bash
# Safe Jira Issue Creation Script
# Forces dry-run first, then requires confirmation before creating

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <csv-file> [sprint-id] [component]"
    echo ""
    echo "This script safely creates Jira issues by:"
    echo "  1. Running dry-run first"
    echo "  2. Asking for confirmation"
    echo "  3. Creating issues only after approval"
    echo "  4. Exporting each issue to YAML"
    echo "  5. Running deduplication cleanup"
    exit 1
fi

CSV_FILE="$1"
SPRINT_ID="${2:-66887}"
COMPONENT="${3:-CNF Integration}"

if [ ! -f "$CSV_FILE" ]; then
    echo "Error: File not found: $CSV_FILE"
    exit 1
fi

# Use unified script
SCRIPT="$SCRIPT_DIR/jira-create.py"

echo "======================================"
echo "SAFE JIRA ISSUE CREATION"
echo "======================================"
echo "File: $CSV_FILE"
echo "Sprint: $SPRINT_ID"
echo "Component: $COMPONENT"
echo ""

# Step 1: Dry run
echo "Step 1: Running DRY-RUN to preview..."
echo ""
python3 "$SCRIPT" "$CSV_FILE" "$SPRINT_ID" "$COMPONENT" --dry-run

echo ""
echo "======================================"
echo "DRY-RUN COMPLETE"
echo "======================================"
echo ""

# Step 2: Check for existing issues
echo "Step 2: Checking for potential duplicates in sprint..."
echo ""
jira sprint list --state active --plain | head -3
echo ""
echo "Recent issues with inbound-int-50 label:"
jira issue list -pCNF -linbound-int-50 --plain 2>/dev/null | tail -10 || echo "  (no recent issues found)"
echo ""

# Step 3: Confirmation
echo "======================================"
echo "CONFIRMATION REQUIRED"
echo "======================================"
echo ""
echo "Have you verified that these issues don't already exist?"
echo ""
read -p "Do you want to CREATE these issues for real? (yes/NO): " confirm

if [[ "$confirm" != "yes" ]]; then
    echo ""
    echo "❌ Cancelled. No issues were created."
    exit 0
fi

# Step 4: Create for real
echo ""
echo "======================================"
echo "CREATING ISSUES..."
echo "======================================"
echo ""

# Create a log file
LOG_FILE="$SCRIPT_DIR/creation-log-$(date +%Y%m%d-%H%M%S).txt"

python3 "$SCRIPT" "$CSV_FILE" "$SPRINT_ID" "$COMPONENT" | tee "$LOG_FILE"

echo ""
echo "======================================"
echo "CHECKING FOR DUPLICATES..."
echo "======================================"
echo ""
echo "Waiting for Jira to index new issues and API rate limits to reset..."
echo "(This takes 10 seconds to avoid rate limiting issues)"
echo ""

# Give Jira time to index AND let rate limits reset
sleep 10

echo "Running automatic duplicate detection..."
echo ""

# Run deduplication
python3 "$SCRIPT_DIR/deduplicate.py" --label inbound-int-50

echo ""
echo "⚠️  IMPORTANT: If duplicate detection failed due to rate limits,"
echo "   wait a few minutes and run manually:"
echo "   python3 $SCRIPT_DIR/deduplicate.py --label inbound-int-50"

echo ""
echo "======================================"
echo "COMPLETE"
echo "======================================"
echo ""
echo "Log saved to: $LOG_FILE"
echo ""
echo "✅ Done! Review the issues in Jira:"
echo "   Sprint: https://redhat.atlassian.net/browse/CNF"
