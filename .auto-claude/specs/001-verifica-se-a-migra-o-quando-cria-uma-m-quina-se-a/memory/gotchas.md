# Gotchas & Pitfalls

Things to watch out for in this codebase.

## [2025-12-31 21:50]
npm and npx commands are blocked in the sandbox environment - Playwright tests cannot be executed directly

_Context: Phase 2 investigation requires manual test execution outside the sandbox or using a different environment_
