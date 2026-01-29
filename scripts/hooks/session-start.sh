#!/bin/bash
# Brief SessionStart hook - prime agent with workflow on session start/resume/compact

# Read and discard stdin
cat > /dev/null

cat << 'EOF'
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"[Brief Workflow] This project uses Brief for context management.\n\nWHEN YOU NEED TO UNDERSTAND CODE:\n1. FIRST run: brief context get \"<what you need to understand>\"\n2. Brief returns: file descriptions, signatures, relationships, and related files\n3. THEN use Read only for specific files you need to edit\n\nStart with: brief status && brief task list"}}
EOF

exit 0
