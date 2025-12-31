# Gotchas & Pitfalls

Things to watch out for in this codebase.

## [2025-12-31 21:18]
npm and npx commands are not allowed in this sandboxed environment - package installation must be done manually by user

_Context: Subtasks 1-1 and 1-2 require npm/npx commands which are blocked. User must run: cd tests && npm install && npx playwright install chromium_
