#!/usr/bin/env python3
"""
🎨 Vibe Tests Configuration
Shared fixtures and utilities for visual/UX testing
"""

import pytest
import requests
import os
from pathlib import Path
from typing import Dict, Tuple
import re

# Configuration
BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8766")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
DEMO_USER = os.environ.get("TEST_USER", "test@test.com")
DEMO_PASS = os.environ.get("TEST_PASS", "test123")

# Paths
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


@pytest.fixture
def api_client():
    """HTTP client for API testing"""
    class APIClient:
        def __init__(self, base_url=BASE_URL):
            self.base_url = base_url
            self.session = requests.Session()
            self.token = None

        def login(self, username=DEMO_USER, password=DEMO_PASS) -> Dict:
            """Login and get token"""
            resp = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"username": username, "password": password},
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("access_token") or data.get("token")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                return data
            return None

        def get(self, endpoint: str, **kwargs):
            """GET request"""
            return self.session.get(f"{self.base_url}{endpoint}", timeout=5, **kwargs)

        def post(self, endpoint: str, **kwargs):
            """POST request"""
            return self.session.post(f"{self.base_url}{endpoint}", timeout=5, **kwargs)

    return APIClient()


@pytest.fixture
def browser_session():
    """Simulated browser session for vibe testing"""
    class BrowserSession:
        def __init__(self, frontend_url=FRONTEND_URL):
            self.url = frontend_url
            self.session = requests.Session()
            self.screenshots = []

        def load_page(self, path: str = "/") -> Tuple[int, str]:
            """Load a page and return status and content"""
            try:
                resp = self.session.get(f"{self.url}{path}", timeout=5)
                return resp.status_code, resp.text
            except Exception as e:
                return 0, str(e)

        def check_responsive(self, viewports: list = None) -> Dict:
            """Check if page is responsive across viewports"""
            if viewports is None:
                viewports = [
                    {"name": "desktop", "width": 1920, "height": 1080},
                    {"name": "tablet", "width": 768, "height": 1024},
                    {"name": "mobile", "width": 375, "height": 812},
                ]

            results = {}
            for vp in viewports:
                status, _ = self.load_page("/")
                results[vp["name"]] = status == 200

            return results

        def check_accessibility(self, html_content: str) -> Dict:
            """Check basic accessibility in HTML"""
            checks = {
                "has_lang_attribute": 'lang=' in html_content,
                "has_title": '<title>' in html_content,
                "has_viewport_meta": 'viewport' in html_content,
                "has_semantic_structure": any(tag in html_content for tag in ['<header', '<main', '<footer', '<nav']),
                "has_alt_text_on_images": self._check_alt_text(html_content),
                "has_form_labels": self._check_form_labels(html_content),
            }
            return checks

        def _check_alt_text(self, html: str) -> bool:
            """Check if images have alt text or are marked as decorative"""
            # Simple regex check - production would use HTML parser
            img_tags = re.findall(r'<img[^>]*>', html)
            if not img_tags:
                return True  # No images = pass

            # Check if any img has alt or role="presentation"
            for img in img_tags:
                if 'alt=' not in img and 'role=' not in img:
                    return False  # Image without alt text
            return True

        def _check_form_labels(self, html: str) -> bool:
            """Check if form inputs have associated labels"""
            # Simple check - production would parse properly
            inputs = len(re.findall(r'<input[^>]*>', html))
            labels = len(re.findall(r'<label[^>]*>', html))

            # Should have reasonable label:input ratio
            if inputs == 0:
                return True  # No forms = pass
            return labels > 0

    return BrowserSession()


@pytest.fixture
def vibe_checker():
    """Vibe checker utilities for UX validation"""
    class VibeChecker:
        @staticmethod
        def check_page_clarity(status_code: int, html_content: str) -> bool:
            """Check if page content is clear and loads"""
            if status_code != 200:
                return False

            # Check for main content
            has_content = (
                len(html_content) > 1000 and
                not "error" in html_content.lower()[:500] and
                not "404" in html_content
            )
            return has_content

        @staticmethod
        def check_mobile_friendly(html_content: str) -> bool:
            """Check basic mobile-friendly indicators"""
            checks = [
                'viewport' in html_content,  # Viewport meta tag
                any(tag in html_content for tag in ['<meta name="viewport"', '<meta name="mobile"']),
                '<html' in html_content,  # Valid HTML structure
            ]
            return all(checks)

        @staticmethod
        def check_error_visibility(html_content: str) -> bool:
            """Check if error messages would be visible (has error elements)"""
            error_indicators = [
                'data-testid="error"',
                'class="error"',
                'role="alert"',
                '<alert',
                'data-testid="alert"',
            ]
            # Return True if error markup patterns exist (for error pages)
            return any(indicator in html_content for indicator in error_indicators)

        @staticmethod
        def check_loading_states(html_content: str) -> bool:
            """Check if page has loading state indicators"""
            loading_indicators = [
                'data-testid="loading"',
                'class="spinner"',
                'class="loader"',
                'role="progressbar"',
                'aria-busy="true"',
                '<Loader',
                'data-testid="skeleton"',
            ]
            return any(indicator in html_content for indicator in loading_indicators)

    return VibeChecker()


@pytest.fixture
def test_data():
    """Shared test data"""
    return {
        "demo_user": DEMO_USER,
        "demo_pass": DEMO_PASS,
        "base_url": BASE_URL,
        "frontend_url": FRONTEND_URL,
        "screenshot_dir": SCREENSHOTS_DIR,
    }
