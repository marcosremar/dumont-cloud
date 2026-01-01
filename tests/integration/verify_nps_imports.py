#!/usr/bin/env python3
"""Quick verification script for NPS imports"""

import sys
sys.path.insert(0, '.')

try:
    from src.models.nps import NPSResponse, NPSSurveyConfig, NPSUserInteraction
    print("[OK] Models imported successfully")
except ImportError as e:
    print(f"[FAIL] Models import error: {e}")
    sys.exit(1)

try:
    from src.api.v1.schemas.nps import (
        NPSSubmissionRequest,
        NPSTrendsResponse,
        NPSShouldShowResponse
    )
    print("[OK] Schemas imported successfully")
except ImportError as e:
    print(f"[FAIL] Schemas import error: {e}")
    sys.exit(1)

try:
    from src.domain.services.nps_service import NPSService
    print("[OK] Service imported successfully")
except ImportError as e:
    print(f"[FAIL] Service import error: {e}")
    sys.exit(1)

try:
    from src.api.v1.endpoints.nps import router
    print("[OK] Router imported successfully")
except ImportError as e:
    print(f"[FAIL] Router import error: {e}")
    sys.exit(1)

print("\n[SUCCESS] All NPS imports verified!")
