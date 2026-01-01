# Gotchas & Pitfalls

Things to watch out for in this codebase.

## [2026-01-01 06:23]
FastAPI route ordering matters: static path routes like /availability must be defined BEFORE path parameter routes like /{id}, otherwise FastAPI will try to parse "availability" as the id parameter

_Context: src/api/v1/endpoints/reservations.py - Fixed in subtask-4-3_
