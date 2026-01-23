#!/bin/bash
# Brief Feature Demonstration Script
# Run this script to see all the features implemented in this development session.
#
# Usage: ./scripts/demo-features.sh
#
# Each section shows a feature and its output. Press Enter to continue between sections.

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pause() {
    echo ""
    echo -e "${YELLOW}Press Enter to continue...${NC}"
    read -r
    clear
}

header() {
    echo ""
    echo -e "${BLUE}======================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""
}

# Ensure we're in the right directory and venv
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate 2>/dev/null || true

clear
header "Brief Feature Demonstration"
echo "This script demonstrates all the features implemented in the 2026-01-22 session."
echo ""
echo "Features covered:"
echo "  1. Status Dashboard (brief status)"
echo "  2. Colored File Tree (brief tree)"
echo "  3. Task System with Dependencies"
echo "  4. Function Signatures in Context"
echo "  5. Coverage with Freshness Tracking"
echo "  6. Import Relationship Extraction"
pause

# 1. Status Dashboard
header "1. Status Dashboard (brief status)"
echo "Shows project metrics at a glance: analysis stats, coverage, freshness, tasks."
echo ""
brief status
pause

# 2. Colored Tree
header "2. Colored File Tree (brief tree)"
echo "Shows project structure with status markers:"
echo "  ✓ green = Has description"
echo "  ○ yellow = Analyzed only"
echo "  ✗ red = Not analyzed"
echo ""
brief tree src/brief/reporting/
pause

# 3. Task System
header "3. Task System with Dependencies"
echo "Tasks can have dependencies. Tasks with incomplete deps are blocked."
echo ""
echo "=== All Tasks ==="
brief task list
echo ""
echo "=== Ready Tasks (no blockers) ==="
brief task ready
echo ""
echo "=== Blocked Tasks ==="
brief task blocked
pause

# 4. Context with Signatures
header "4. Function Signatures in Context Output"
echo "Running: brief context get 'task management' | head -80"
echo ""
brief context get "task management" | head -80
pause

# 5. Coverage with Freshness
header "5. Coverage with Freshness Tracking"
echo "Shows description coverage and staleness info."
echo ""
brief coverage
pause

# 6. Import Relationships
header "6. Import Relationship Extraction (Fixed)"
echo "Import relationships are now properly extracted, including relative imports."
echo "See 'Import relations' count in status above."
echo ""
echo "Example: Showing imports for src/brief/retrieval/context.py"
brief deps src/brief/retrieval/context.py
pause

# Summary
header "Demonstration Complete"
echo "All features demonstrated successfully."
echo ""
echo "For more details, see:"
echo "  - docs/status/work-summary-2026-01-22.md"
echo "  - docs/DEV_NOTES.md (ARCHIVE section)"
echo "  - docs/brief-workflow.md"
echo ""
echo "Run 'pytest tests/ -v --tb=short' to verify all tests pass."
