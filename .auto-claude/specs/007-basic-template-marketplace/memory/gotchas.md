# Gotchas & Pitfalls

Things to watch out for in this codebase.

## [2025-12-31 22:11]
services/deploy_wizard.py had broken imports pointing to src.services.vast_service which doesn't exist - fixed to use relative imports (.vast_service)

_Context: When working with the root-level services/ package, always use relative imports (from .module import X) not absolute imports (from src.services.module import X)_
