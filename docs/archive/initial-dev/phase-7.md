# Phase 7: Execution Path Tracing Checkpoint

## Prerequisites
- [x] Phase 6 completed (all steps marked done in phase-6.md)
- [x] Memory/pattern system working
- [x] Context retrieval functional

## Current Status
- [x] Step 7.1: Design path tracing approach - COMPLETE
- [x] Step 7.2: Implement path tracer - COMPLETE
- [x] Step 7.3: Implement `brief trace` command - COMPLETE
- [x] Step 7.4: Implement trace list/delete commands - COMPLETE
- [x] Step 7.5: Link paths to context retrieval - COMPLETE (via paths_dir structure)
- [x] Step 7.6: Write tests for path tracing - COMPLETE

## PHASE 7 COMPLETED

All steps verified:
- Created src/brief/tracing/__init__.py
- Created src/brief/tracing/tracer.py with PathTracer, ExecutionPath, PathStep
- Implemented function finding, callee detection, code snippet extraction
- Created src/brief/commands/trace.py with create, show, list, delete commands
- Updated cli.py to register trace commands
- Created tests/brief/test_tracing.py - 23 tests passing
- All 158 brief tests passing

## Files Created
```
src/brief/
├── tracing/
│   ├── __init__.py
│   └── tracer.py           # PathTracer with call chain tracing
└── commands/
    └── trace.py            # trace create, show, list, delete commands
tests/brief/
└── test_tracing.py         # 23 tracing tests
```

## Commands Available
- `brief trace create "name" "entry_point"` - Trace and document execution path
- `brief trace show "name"` - Display a saved path
- `brief trace list` - List all traced paths
- `brief trace delete "name"` - Delete a traced path

## Key Features
- Static call graph analysis from manifest
- Code snippet extraction from source files
- Markdown documentation generation
- Saved paths in context/paths/ directory
- Recursive call tracing with depth limit

## Path Output Structure
```markdown
# Path: [name]

## Entry Point
`function_name`

## Steps
### 1. function_name
**File**: `file.py:line`
[description]
[code snippet]
**Calls**: [callees]

## Related Files
- `file1.py`
- `file2.py`
```

## Notes
- Static call graph may be incomplete - depends on relationships.jsonl
- Paths should be reviewed and enhanced manually for accuracy
- Most useful for documenting key workflows

## Ready for Phase 8
Continue to .brief/checkpoints/phase-8.md
