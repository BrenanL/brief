#!/bin/bash
# Brief PreCompact hook - ensure compaction summary includes resume instructions

# Read and discard stdin
cat > /dev/null

cat << 'EOF'
{"systemMessage":"[Compaction Note] Include in your summary: After resuming, run `brief resume` first, then use `brief context get` before exploring code with Read/Grep/Glob."}
EOF

exit 0
