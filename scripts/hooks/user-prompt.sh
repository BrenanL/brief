#!/bin/bash
# Brief UserPromptSubmit hook - remind agent to use context get first

# Read and discard stdin
cat > /dev/null

# Simple, actionable reminder injected into context
echo '[Brief] Before exploring code, run: brief context get "<topic>" to get structured context.'

exit 0
