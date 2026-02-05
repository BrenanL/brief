#!/bin/bash
# Brief SessionStart hook - refresh analysis and prime agent with workflow

# Read and discard stdin
cat > /dev/null

# Refresh analysis to catch any files changed since last session
brief analyze refresh > /dev/null 2>&1

cat << 'EOF'
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"[Brief Workflow] This project uses Brief for context management.\n\nWHEN YOU NEED TO UNDERSTAND CODE:\n1. FIRST run: brief context get \"<what you need to understand>\"\n2. Brief returns: file descriptions, signatures, relationships, and related files\n3. THEN use Read only for specific files you need to edit\n\nStart with: brief status && brief task list"}}
EOF

exit 0
