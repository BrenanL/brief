# Basic Manual Setup Test

Pre-release confirmation tests.

---

## Setup

```bash
# Create a fresh test directory
cd /tmp && rm -rf test-brief && mkdir test-brief && cd test-brief
git init && echo "x = 1" > app.py

# Create a fresh venv and install Brief
uv venv && source .venv/bin/activate
uv pip install -e /home/user/dev/brief
```

### Quick reset between tests

You can reuse the same test directory and venv between tests — just clean
Brief's generated files instead of starting from scratch:

```bash
rm -rf .brief .brief-logs .claude CLAUDE.md
# Optionally keep .gitignore (already has .brief/ entries)
# Then re-run brief setup -d with whatever flags you're testing
```

This avoids recreating the venv and reinstalling every time.

---

## Test 1: Default setup (no tasks, no API keys)

```bash
cd /tmp && rm -rf test-default && mkdir test-default && cd test-default
git init && echo "x = 1" > app.py
uv venv && source .venv/bin/activate
uv pip install -e /home/user/dev/brief

# Unset any API keys
unset OPENAI_API_KEY GOOGLE_API_KEY ANTHROPIC_API_KEY

brief setup -d
```

**Verify:**
- [ ] "No API keys detected in environment" message shown
- [ ] "No OPENAI_API_KEY — skipping embeddings" shown
- [ ] Search mode: keyword only
- [ ] `.gitignore` contains `.brief/` and `.brief-logs/`
- [ ] `CLAUDE.md` has "## Context Management (Brief)" section
- [ ] `CLAUDE.md` does NOT have "### Task Management" section
- [ ] `.claude/settings.json` has hooks (SessionStart, PreCompact, UserPromptSubmit, PreToolUse)
- [ ] `.claude/settings.local.json` has `Bash(brief:*)` permission
- [ ] `brief task list` says "Task system is not enabled"
- [ ] `brief status` works and shows dashboard
- [ ] `brief context get "anything"` runs without error

---

## Test 2: Setup with tasks enabled

```bash
cd /tmp && rm -rf test-tasks && mkdir test-tasks && cd test-tasks
git init && echo "x = 1" > app.py
uv venv && source .venv/bin/activate
uv pip install -e /home/user/dev/brief

brief setup -d --tasks
```

**Verify:**
- [ ] `CLAUDE.md` has "## Context Management (Brief)" section
- [ ] `CLAUDE.md` also has "### Task Management" section
- [ ] `brief task list` works (shows empty list, no "disabled" error)
- [ ] `brief task create "test task"` creates a task
- [ ] `brief task list` shows the created task

---

## Test 3: .env file API key detection

```bash
cd /tmp && rm -rf test-env && mkdir test-env && cd test-env
git init && echo "x = 1" > app.py
uv venv && source .venv/bin/activate
uv pip install -e /home/user/dev/brief

# Ensure no env vars set
unset OPENAI_API_KEY GOOGLE_API_KEY ANTHROPIC_API_KEY

# Create .env with key
echo "OPENAI_API_KEY=sk-proj-your-key-here" > .env

brief setup -d
```

**Verify:**
- [ ] "Detected API keys in your environment" message shown
- [ ] "✓ OpenAI (OPENAI_API_KEY)" shown
- [ ] Embeddings step runs (may fail if key is fake, but should attempt)

---

## Test 4: System environment variable (no .env)

```bash
cd /tmp && rm -rf test-sysenv && mkdir test-sysenv && cd test-sysenv
git init && echo "x = 1" > app.py
uv venv && source .venv/bin/activate
uv pip install -e /home/user/dev/brief

# Set key in environment, no .env file
export OPENAI_API_KEY=sk-proj-your-key-here

brief setup -d
```

**Verify:**
- [ ] "Detected API keys in your environment" message shown
- [ ] "✓ OpenAI (OPENAI_API_KEY)" shown
- [ ] Embeddings step runs (may fail if key is fake, but should attempt)
- [ ] No ".env" mentioned in output

---

## Test 5: Auto-staleness (ensure_manifest_current)

```bash
cd /tmp && rm -rf test-stale && mkdir test-stale && cd test-stale
git init
uv venv && source .venv/bin/activate
uv pip install -e /home/user/dev/brief

# Create initial file and setup
echo "def hello(): pass" > app.py
brief setup -d

# Verify initial state
brief context get "hello"
# Should find app.py

# Simulate agent creating a new file
echo -e "class AuthService:\n    def verify(self, token): return True" > auth.py
# Query again — new file should appear WITHOUT running analyze refresh
brief context get "auth"
# Should find auth.py (added by ensure_manifest_current)

# Simulate agent editing a file
echo -e "def hello(): pass\ndef goodbye(): pass" > app.py

brief context get "goodbye"
# Should find the new function (re-parsed by ensure_manifest_current)
```

**Verify:**
- [ ] New file `auth.py` appears in context results without manual refresh
- [ ] Edited function `goodbye` appears in results without manual refresh

---

## Test 6: Tab completion

```bash
brief --install-completion bash  # or zsh
# Restart terminal, then:
brief con<TAB>
# Should show context/contracts completions
```

**Verify:**
- [ ] Completions appear (may be slow, may show above the line — that's expected)

---

## Test 7: Hook verification

Start a Claude Code session in a test-default directory (from Test 1).

**Verify:**
- [ ] SessionStart hook fires — see "[Brief Workflow]" system reminder
- [ ] UserPromptSubmit hook fires — see "[Brief]" reminder on each message
- [ ] PreToolUse hook fires — see "[Brief Tip]" when reading code files
- [ ] PreCompact fires without error on `/compact` (no validation error in output)
