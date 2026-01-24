#!/bin/bash
# Brief Feature Demo Script
# Run individual sections or the whole script to see new features

set -e
cd /home/user/dev/brief
source .venv/bin/activate

echo "========================================"
echo "BRIEF NEW FEATURES DEMONSTRATION"
echo "========================================"
echo ""

# ============================================
# P0: CRITICAL FEATURES
# ============================================

echo "=== P0-1: Cache Reset Command ==="
echo "Command: brief reset --help"
brief reset --help
echo ""
echo "Shows what would be cleared (dry run):"
echo "Command: brief reset --dry-run"
brief reset --dry-run
echo ""

echo "=== P0-2: Development Logging ==="
echo "Command log location: .brief-logs/"
ls -la .brief-logs/ 2>/dev/null | head -5 || echo "(No logs yet)"
echo ""
echo "Config setting:"
brief config show 2>&1 | grep command_logging
echo ""

# ============================================
# P1: IMPORTANT FEATURES
# ============================================

echo "=== P1-1: Auto-Generate Descriptions ==="
echo "Config setting (now defaults to true):"
brief config show 2>&1 | grep auto_generate
echo ""
echo "Disable with -G flag:"
echo "Command: brief context get 'query' -G  # No auto-generation"
echo ""

echo "=== P1-4: Signature vs Description Redundancy ==="
echo "Signatures only shown when no description exists."
echo "Use --show-signatures/-s to force showing both."
echo "Command: brief context get 'models' --compact"
brief context get "models" --compact 2>&1 | head -20
echo ""

echo "=== P1-5: Memory Command Rename ==="
echo "Old: brief memory remember -> New: brief memory add"
echo "Old: brief memory recall -> New: brief memory get"
echo "Top-level aliases still work:"
echo "  brief remember 'pattern' 'value'"
echo "  brief recall 'pattern'"
echo ""
echo "Command: brief memory --help"
brief memory --help 2>&1 | head -15
echo ""

echo "=== P1-6: Quick Context Shortcut ==="
echo "Command: brief q 'task management'"
brief q "task management" 2>&1 | head -30
echo ""

# ============================================
# P2: POLISH FEATURES
# ============================================

echo "=== P2-2: Fixed Overview Command ==="
echo "Command: brief overview"
brief overview 2>&1 | head -30
echo ""

echo "=== P2-3: Setup Wizard ==="
echo "Command: brief setup --help"
brief setup --help
echo ""

echo "=== P2-4: Date/Time Format Exclusions ==="
echo "Now supports multiple date formats in exclusions:"
echo "  - YYYY-MM-DD (ISO)"
echo "  - YYYYMMDD (compact)"
echo "  - YYYY_MM_DD (underscore)"
echo "  - MM-DD-YYYY (American)"
echo "  - DD-MM-YYYY (European)"
echo ""

echo "=== P2-5: Task System Disable Mode ==="
echo "Command: brief config show | grep enable_tasks"
brief config show 2>&1 | grep enable_tasks
echo ""
echo "To disable: brief config set enable_tasks false"
echo "When disabled, task commands show helpful message."
echo ""

echo "=== P2-6: LLM Provider Configuration ==="
echo "Command: brief config show | grep llm_provider"
brief config show 2>&1 | grep llm_provider
echo ""
echo "To switch providers, edit baml_src/clients.baml"
echo "and run: baml-cli generate"
echo ""

# ============================================
# P3: DOCUMENTATION FEATURES
# ============================================

echo "=== P3-1: Embeddings Architecture Documentation ==="
echo "New doc: docs/embeddings-architecture.md"
head -30 docs/embeddings-architecture.md
echo ""

echo "=== P3-2: Embeddings Generation UX ==="
echo "Command: brief context embed --help"
brief context embed --help
echo ""
echo "Command: brief describe batch --help | grep embed"
brief describe batch --help 2>&1 | grep -A2 embed
echo ""

echo "=== P3-3: Context Package Ruleset ==="
echo "New doc: docs/context-package-rules.md"
head -30 docs/context-package-rules.md
echo ""

# ============================================
# P4: NICE-TO-HAVE FEATURES
# ============================================

echo "=== P4-1: Config Show Command ==="
echo "Command: brief config show"
brief config show
echo ""

echo "=== P4-2: Token Counting ==="
echo "Command: brief context get 'cli commands' --tokens"
brief context get "cli commands" --tokens 2>&1 | tail -15
echo ""

echo "=== P4-3: Compact Summary Mode ==="
echo "Command: brief context get 'storage' --compact"
brief context get "storage" --compact
echo ""

echo "=== P4-4: Coverage Detailed ==="
echo "Command: brief coverage --detailed"
brief coverage --detailed
echo ""

echo "========================================"
echo "DEMONSTRATION COMPLETE"
echo "========================================"
