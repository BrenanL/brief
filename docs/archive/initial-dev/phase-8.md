# Phase 8: Contract Extraction Checkpoint

## Prerequisites
- [x] Phase 7 completed (all steps marked done in phase-7.md)
- [x] Execution path tracing working
- [x] Descriptions generated for core files

## Current Status
- [x] Step 8.1: Design contract extraction approach - COMPLETE
- [x] Step 8.2: Implement pattern-based contract detection - COMPLETE
- [x] Step 8.3: Implement LLM-assisted contract inference - COMPLETE
- [x] Step 8.4: Implement `brief contracts` command - COMPLETE
- [x] Step 8.5: Write tests for contract extraction - COMPLETE

## PHASE 8 COMPLETED

All steps verified:
- Created src/brief/contracts/__init__.py
- Created src/brief/contracts/detector.py with Contract dataclass and ContractDetector class
- Created src/brief/contracts/inference.py for LLM-assisted contract inference
- Created src/brief/commands/contracts.py with detect, show, add, list, verify commands
- Updated cli.py to register contracts commands
- Created tests/brief/test_contracts.py - 22 tests passing
- All 180 brief tests passing

## Files Created
```
src/brief/
├── contracts/
│   ├── __init__.py
│   ├── detector.py         # Contract dataclass and ContractDetector
│   └── inference.py        # LLM-assisted inference
└── commands/
    └── contracts.py        # contracts commands
tests/brief/
└── test_contracts.py       # 22 contract tests
```

## Commands Available
- `brief contracts detect` - Detect contracts from code patterns
- `brief contracts detect --llm` - Also use LLM inference
- `brief contracts detect --category naming` - Filter by category
- `brief contracts show` - Display extracted contracts
- `brief contracts list` - Quick summary of contracts
- `brief contracts add "name" "rule"` - Manually add a contract
- `brief contracts verify` - Basic contract verification

## Contract Categories
- **naming**: Class/function naming conventions (suffixes, prefixes)
- **organization**: File and directory organization patterns
- **type**: Return type patterns, generators, async functions
- **behavioral**: Decorator patterns, method behaviors
- **api**: API usage contracts (added manually)

## Detection Methods
1. **detect_naming_conventions()** - Detects class suffixes (Command, Manager, Handler, etc.) and function prefixes (test_, get_, _private, etc.)
2. **detect_file_organization()** - Detects directory patterns (definitions/, commands/, tests/) and package structure
3. **detect_type_patterns()** - Detects generator functions, async functions, common return types
4. **detect_inheritance_patterns()** - Detects base class usage patterns
5. **detect_decorator_patterns()** - Detects common decorator usage (@staticmethod, @property, etc.)

## Contract Output Format
```markdown
## Contract: Command Naming Convention

**Category**: naming
**Confidence**: high

### Rule
Classes in this pattern should end with 'Command'

### Examples
- ✓ TableCommand
- ✓ WorkspaceCommand

### Files Affected
- `commands/table.py`
- `commands/workspace.py`

### Source
Detected from 3 classes in commands/
```

## Notes
- Pattern-based detection finds obvious conventions
- LLM inference (optional) can find subtler rules
- Manual entry captures human knowledge
- Contracts saved to context/contracts.md
- Confidence levels: high (3+ occurrences), medium (2 occurrences), low

## Ready for Phase 9
Continue to .brief/checkpoints/phase-9.md
