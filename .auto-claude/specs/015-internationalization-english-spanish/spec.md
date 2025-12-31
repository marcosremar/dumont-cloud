# Specification: Full Internationalization - English + Spanish

## Overview

This feature implements comprehensive internationalization (i18n) support across the Dumont Cloud platform, with Spanish as the first additional language beyond English. The implementation targets all user-facing components including the React web dashboard, Python CLI tool, documentation, and email templates. This expansion enables the platform to serve Spanish-speaking developers and educational institutions across Latin America and Spain, addressing a known product gap with relatively low effort for significant market expansion.

## Workflow Type

**Type**: feature

**Rationale**: This is a new capability that adds multi-language support to the platform. It requires new infrastructure (i18n libraries), new user-facing features (language selector), and systematic modification of existing components to externalize strings. This is not a refactor (existing functionality changes minimally) nor a bug fix, but rather a feature addition that expands the platform's addressable market.

## Task Scope

### Services Involved
- **web** (primary) - React frontend requiring translation of all UI strings, language selector component, and runtime language switching
- **cli** (primary) - Python CLI requiring translation of help text, error messages, and --language flag support
- **backend** (primary) - Email template service requiring Jinja2 i18n for localized emails
- **tests** (integration) - E2E tests must verify language switching functionality

### This Task Will:
- [x] Install and configure i18n libraries (react-i18next for web, Flask-Babel/gettext for CLI)
- [x] Extract all hardcoded UI strings from React components into translation files
- [x] Extract all CLI help text and messages into gettext-compatible format
- [x] Create translation file structure (JSON for React, .po/.mo for Python)
- [x] Translate all strings to Spanish
- [x] Implement language selector component in user preferences (web)
- [x] Add --language CLI flag for command-line language selection
- [x] Configure locale detection (browser for web, env vars for CLI)
- [x] Implement user preference persistence for language choice
- [x] Translate email templates to support user's preferred language
- [x] Create Spanish version of documentation
- [x] Add E2E tests for language switching

### Out of Scope:
- Additional languages beyond Spanish (future expansion)
- Right-to-left (RTL) language support (not needed for Spanish)
- Automatic machine translation (Spanish translations will be manual/human-reviewed)
- Translation of log files or debug output (developer-facing only)
- Localization of dates, numbers, currency formats (Phase 2 enhancement)
- SDK-client library error messages (will be addressed in separate follow-up if needed)

## Service Context

### Web (React Frontend)

**Tech Stack:**
- Language: JavaScript
- Framework: React 18+
- Build Tool: Vite
- State Management: Redux (@reduxjs/toolkit)
- Styling: Tailwind CSS
- UI Components: Radix UI

**Entry Point:** `src/App.jsx`

**How to Run:**
```bash
cd web
npm run dev
```

**Port:** 8000

**Key Directories:**
- `src/` - Source code (components, state, utilities)
- `public/` - Static assets (will house translation files)

### CLI (Python Command-Line Tool)

**Tech Stack:**
- Language: Python
- Framework: None (standard argparse/click likely)
- Package Manager: pip

**Entry Point:** `__main__.py`

**How to Run:**
```bash
cd cli
python -m cli [command]
```

**Key Directories:**
- `utils/` - Utility functions
- `tests/` - Unit tests

### Backend (Email Service)

**Tech Stack:**
- Language: Python
- Framework: Flask (likely, based on Flask-Babel requirement)
- Template Engine: Jinja2
- Package Manager: pip

**Purpose:** Handles email template rendering with i18n support

**Key Directories:**
- `templates/email/` - Email templates (likely location)
- `translations/` - Shared with CLI for .po/.mo files

### Tests (E2E Testing)

**Tech Stack:**
- Framework: Playwright
- Language: JavaScript

**Purpose:** End-to-end testing of web UI and CLI functionality

## Files to Modify

| File | Service | What to Change |
|------|---------|---------------|
| `web/package.json` | web | Add dependencies: react-i18next@^13.0.0, i18next@^23.0.0, i18next-http-backend@^2.0.0 |
| `web/src/App.jsx` | web | Wrap app with I18nextProvider or initialize i18n before render |
| `web/src/i18n.js` | web | **CREATE**: i18n configuration and initialization |
| `web/public/locales/en/translation.json` | web | **CREATE**: English translation strings (extracted from components) |
| `web/public/locales/es/translation.json` | web | **CREATE**: Spanish translation strings |
| `web/src/components/**/*.jsx` | web | Replace hardcoded strings with `t('key')` calls using useTranslation hook |
| `web/src/store/**/*.js` | web | Replace hardcoded strings in Redux state/actions with translation keys |
| `cli/requirements.txt` | cli | Add dependencies: Flask-Babel>=4.0.0, Babel>=2.14.0 |
| `cli/babel.cfg` | cli | **CREATE**: Babel extraction configuration |
| `cli/__main__.py` | cli | Initialize gettext, add --language flag argument |
| `cli/translations/en/LC_MESSAGES/messages.po` | cli | **CREATE**: English source strings |
| `cli/translations/es/LC_MESSAGES/messages.po` | cli | **CREATE**: Spanish translations |
| `cli/**/*.py` | cli | Replace hardcoded strings with `_('string')` gettext calls |
| Email template service file | backend | Enable Jinja2 i18n extension, install gettext translations |
| Email template files (*.html, *.txt) | backend | Wrap translatable strings with `{% trans %}...{% endtrans %}` or `{{ _('...') }}` |
| `docs/**/*.md` | root | **DUPLICATE**: Create Spanish versions (es/ directory) |

## Files to Reference

These files show patterns to follow:

| File | Pattern to Copy |
|------|----------------|
| `web/src/components/**/*.jsx` | React component structure, hook usage patterns |
| `web/src/store/**/*.js` | Redux state management patterns |
| `cli/**/*.py` | CLI argument parsing, error handling patterns |
| `cli/utils/*.py` | Python utility function structure |

## Patterns to Follow

### React i18n Integration

**Pattern**: Initialize i18n before React renders

```javascript
// web/src/i18n.js
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import HttpBackend from 'i18next-http-backend';

i18n
  .use(HttpBackend)
  .use(initReactI18next)
  .init({
    lng: localStorage.getItem('language') || 'en',
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false, // React already handles XSS
    },
    backend: {
      loadPath: '/locales/{{lng}}/translation.json',
    },
  });

export default i18n;
```

**Key Points:**
- Initialize BEFORE React renders (import in main.jsx before App)
- Set `escapeValue: false` for React (XSS protection built-in)
- Use localStorage to persist user's language preference
- Translation files in `public/locales/{lng}/translation.json` for Vite

### React Component Translation

**Pattern**: Use useTranslation hook

```javascript
import { useTranslation } from 'react-i18next';

function MyComponent() {
  const { t, i18n } = useTranslation();

  const changeLanguage = (lng) => {
    i18n.changeLanguage(lng);
    localStorage.setItem('language', lng);
  };

  return (
    <div>
      <h1>{t('welcome.title')}</h1>
      <button onClick={() => changeLanguage('es')}>Español</button>
    </div>
  );
}
```

**Key Points:**
- Destructure `t` function and `i18n` instance from hook
- Use `t('key.path')` to translate strings
- Call `i18n.changeLanguage(lng)` to switch languages
- Persist choice to localStorage for next visit

### Python CLI i18n

**Pattern**: Use Python gettext

```python
import gettext
import os

# Get language from env or CLI flag
lang = os.getenv('LANGUAGE', 'en').split(':')[0]

# Initialize gettext
t = gettext.translation(
    'messages',
    localedir='./translations',
    languages=[lang],
    fallback=True
)
_ = t.gettext

# Usage
print(_('Welcome to Dumont Cloud'))
print(_('Error: Invalid configuration'))
```

**Key Points:**
- Use `gettext.translation()` to load .mo files
- Domain name 'messages' must match .po/.mo filenames
- Directory structure: `translations/{locale}/LC_MESSAGES/messages.mo`
- MUST compile .po to .mo using `pybabel compile -d translations`
- Use `_()` function (convention) for translations

### Jinja2 Email Template i18n

**Pattern**: Enable i18n extension and use translation tags

```python
# In email service initialization (where Jinja2 Environment is created)
from jinja2 import Environment, FileSystemLoader
import gettext

# Create Jinja2 environment
env = Environment(loader=FileSystemLoader('templates/email'))

# Enable i18n extension
env.add_extension('jinja2.ext.i18n')

# Load translations and install in Jinja2
def get_translations(locale):
    return gettext.translation(
        'messages',
        localedir='./translations',
        languages=[locale],
        fallback=True
    )

# Install translations for specific user's locale
user_locale = user.preferred_language or 'en'
env.install_gettext_translations(get_translations(user_locale))

# Render template
template = env.get_template('welcome_email.html')
html = template.render(user=user)
```

**Email Template Syntax:**

```html
<!-- templates/email/welcome_email.html -->
<!DOCTYPE html>
<html>
<head>
    <title>{% trans %}Welcome to Dumont Cloud{% endtrans %}</title>
</head>
<body>
    <h1>{% trans %}Hello{% endtrans %}, {{ user.name }}!</h1>

    <p>{% trans %}Thank you for joining Dumont Cloud. We're excited to have you on board.{% endtrans %}</p>

    <!-- With variables -->
    <p>{% trans count=user.credits %}You have {{ count }} credits remaining.{% endtrans %}</p>

    <!-- Alternative syntax using _() function -->
    <p>{{ _('Visit your dashboard to get started.') }}</p>
</body>
</html>
```

**Key Points:**
- Must enable i18n extension: `env.add_extension('jinja2.ext.i18n')`
- Must install translations: `env.install_gettext_translations()`
- Use `{% trans %}...{% endtrans %}` blocks for translatable text
- Use `{{ _('string') }}` for inline translations
- Variables work inside trans blocks: `{% trans var=value %}Text {{ var }}{% endtrans %}`
- Email templates use the same .po/.mo files as CLI (domain: 'messages')
- Load user's preferred language before rendering each email

### Translation File Structure (React)

**Pattern**: Nested JSON keys

```json
{
  "welcome": {
    "title": "Welcome to Dumont Cloud",
    "subtitle": "GPU cloud platform for AI workloads"
  },
  "navigation": {
    "dashboard": "Dashboard",
    "settings": "Settings",
    "logout": "Log Out"
  },
  "errors": {
    "network": "Network error. Please try again.",
    "auth": "Authentication failed"
  }
}
```

**Key Points:**
- Group related translations by feature/domain
- Use descriptive key paths (e.g., 'welcome.title' not 'wt')
- Keep values as strings (interpolation handled by i18next)
- Mirror structure in Spanish translation file

### Babel Configuration File

**Pattern**: Configure string extraction for Python files

```ini
# cli/babel.cfg
[python: **.py]
encoding = utf-8

[jinja2: **/templates/**.html]
encoding = utf-8
extensions=jinja2.ext.autoescape,jinja2.ext.with_,jinja2.ext.i18n
```

**Key Points:**
- Place this file at `cli/babel.cfg` (in the CLI directory)
- `[python: **.py]` tells Babel to extract strings from all Python files
- `[jinja2: **/templates/**.html]` tells Babel to extract from Jinja2 email templates
- The `extensions` line includes `jinja2.ext.i18n` for translation tag support
- Babel will find strings wrapped in `_()`, `gettext()`, `lazy_gettext()` in Python
- Babel will find `{% trans %}...{% endtrans %}` and `{{ _() }}` in Jinja2 templates
- When running `pybabel extract -F babel.cfg`, this config determines which files to scan

## Requirements

### Functional Requirements

1. **Web UI Language Switching**
   - Description: All React components display text in user's selected language
   - Acceptance: User can switch between English/Spanish via selector, preference persists across sessions

2. **CLI Language Support**
   - Description: CLI help text and messages respect --language flag or LANGUAGE env var
   - Acceptance: Running `cli --language es [command]` displays Spanish output

3. **Language Preference Persistence**
   - Description: User's language choice saved and restored on next visit/command
   - Acceptance: Web uses localStorage, CLI respects env var or config file

4. **Spanish Translation Completeness**
   - Description: All user-facing strings have Spanish equivalents
   - Acceptance: No English strings appear when Spanish is selected (except proper nouns)

5. **Email Template Localization**
   - Description: Emails sent to users use their preferred language
   - Acceptance: User with Spanish preference receives Spanish email notifications

6. **Documentation Availability**
   - Description: Full documentation exists in Spanish
   - Acceptance: docs/es/ directory contains complete Spanish versions of all docs

### Edge Cases

1. **Missing Translation Keys** - Fall back to English string gracefully, log warning in dev mode
2. **Partial Translations** - If Spanish translation incomplete, show English for missing keys
3. **Invalid Language Code** - Default to English if unsupported language requested
4. **Concurrent Language Changes** - If user changes language while async operation in progress, ensure consistent UI state
5. **Email Template Missing Translation** - Send email in English if user's preferred language template unavailable

## Implementation Notes

### DO
- Follow React hook patterns already established in existing components
- Reuse Redux patterns for storing language preference in global state
- Use lazy loading for translation files to reduce initial bundle size
- Create comprehensive translation keys upfront (avoid adding incrementally)
- Test language switching with E2E tests to catch missing translations
- Use descriptive translation keys (e.g., `dashboard.welcome.title` not `dw1`)
- Compile Python .po files to .mo BEFORE testing CLI (pybabel compile)
- Store translations in proper directory structure (public/locales for React, translations/ for Python)

### DON'T
- Don't translate proper nouns (Dumont Cloud, GPU, API, etc.)
- Don't hardcode language lists (make extensible for future languages)
- Don't forget to initialize i18n BEFORE React renders (import in main.jsx)
- Don't use `escapeValue: true` in React i18n config (causes double-escaping)
- Don't translate developer-facing content (logs, debug output, code comments)
- Don't skip the .po compilation step for Python (gettext requires .mo files)
- Don't use generic translation keys like `text1`, `label2` (unmaintainable)

## Development Environment

### Start Services

**Web Frontend:**
```bash
cd web
npm install
npm run dev
```

**CLI:**
```bash
cd cli
pip install -r requirements.txt
python -m cli --help
```

**E2E Tests:**
```bash
cd tests
npm install
npx playwright test
```

### Service URLs
- Web Frontend: http://localhost:8000

### Required Environment Variables
- `LANGUAGE`: CLI language preference (e.g., `en`, `es`)
- `DATABASE_URL`: Database connection (if user preferences stored in DB)

### Translation Workflow Commands

**React (no compilation needed):**
```bash
# Just edit JSON files in public/locales/{en,es}/translation.json
```

**Python CLI (requires compilation):**
```bash
# NOTE: Run these commands from the project root directory

# Extract translatable strings from CLI code and email templates
pybabel extract -F cli/babel.cfg -o cli/messages.pot cli/

# Initialize Spanish locale (first time only)
pybabel init -i cli/messages.pot -d cli/translations -l es

# Update existing translations (after code changes)
pybabel update -i cli/messages.pot -d cli/translations

# CRITICAL: Compile .po to .mo (REQUIRED before testing)
pybabel compile -d cli/translations
```

## Success Criteria

The task is complete when:

1. [x] All React components use `t()` function instead of hardcoded strings
2. [x] Language selector component exists in user preferences UI
3. [x] Web app switches between English/Spanish without page reload
4. [x] Language preference persists in localStorage
5. [x] CLI accepts `--language` flag (e.g., `--language es`)
6. [x] CLI help text displays in Spanish when requested
7. [x] All translation files created (en/es for React, en/es for CLI)
8. [x] Spanish translations complete and verified by native speaker
9. [x] Documentation translated to Spanish (docs/es/ directory)
10. [x] Email templates support Spanish
11. [x] No console errors related to missing translation keys
12. [x] Existing tests still pass
13. [x] New E2E tests verify language switching
14. [x] .po files compiled to .mo for Python CLI

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests
| Test | File | What to Verify |
|------|------|----------------|
| i18n initialization | `web/src/i18n.test.js` | i18n instance initializes correctly, fallback to 'en' works |
| Language switcher component | `web/src/components/LanguageSelector.test.jsx` | Component renders languages, calls changeLanguage on click |
| Translation function | `web/src/components/Dashboard.test.jsx` | useTranslation hook returns correct translation for key |
| CLI language flag | `cli/tests/test_i18n.py` | --language flag parsed correctly, translations loaded |
| gettext fallback | `cli/tests/test_i18n.py` | Missing translation falls back to English gracefully |

### Integration Tests
| Test | Services | What to Verify |
|------|----------|----------------|
| Preference persistence | web → localStorage | Language preference saved and restored across browser sessions |
| CLI env var support | cli | LANGUAGE env var overrides default locale |
| Email template selection | backend → email service | User's language preference determines email template used |

### End-to-End Tests
| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| Language switching | 1. Open dashboard 2. Navigate to preferences 3. Select Spanish 4. Navigate to different page | All UI text displays in Spanish, preference persists |
| CLI Spanish output | 1. Run `cli --language es --help` | Help text displays in Spanish |
| Mixed language content | 1. Set UI to Spanish 2. View API response with English field names | UI labels in Spanish, data field names unchanged (API contract) |

### Browser Verification (Frontend)
| Page/Component | URL | Checks |
|----------------|-----|--------|
| Dashboard | `http://localhost:8000/` | All navigation, titles, buttons translated when Spanish selected |
| Language Selector | `http://localhost:8000/settings` | Dropdown shows "English" and "Español", selection persists |
| User Preferences | `http://localhost:8000/preferences` | Form labels and help text translated |
| Error Messages | `http://localhost:8000/` (trigger error) | Error alerts display in selected language |

### CLI Verification
| Command | Expected Output | Language |
|---------|----------------|----------|
| `python -m cli --help` | English help text | en (default) |
| `python -m cli --language es --help` | Spanish help text | es |
| `LANGUAGE=es python -m cli --help` | Spanish help text | es (env var) |

### Translation Quality Checks
| Check | Method | Expected |
|-------|--------|----------|
| No missing keys | Browse UI in Spanish, check console | No "missing translation" warnings |
| Contextual accuracy | Native speaker review | Translations appropriate for technical context |
| String interpolation | Test dynamic values (e.g., "Welcome, {{name}}") | Variables correctly inserted in Spanish strings |
| Pluralization | Test singular/plural forms | Correct Spanish plural rules applied |

### File Structure Verification
| Check | Command | Expected |
|-------|---------|----------|
| React translations exist | `ls web/public/locales/{en,es}/translation.json` | Both files present, valid JSON |
| CLI translations compiled | `ls cli/translations/{en,es}/LC_MESSAGES/messages.mo` | .mo files exist (compiled from .po) |
| babel.cfg exists | `cat cli/babel.cfg` | Valid extraction configuration |
| Spanish docs exist | `ls docs/es/` | Full documentation hierarchy mirrored |

### QA Sign-off Requirements
- [x] All unit tests pass (web + CLI)
- [x] All integration tests pass (preference persistence, email templates)
- [x] All E2E tests pass (language switching, CLI flag)
- [x] Browser verification complete (all pages tested in both languages)
- [x] CLI verification complete (help text, error messages tested)
- [x] Translation quality verified by native Spanish speaker
- [x] No missing translation keys in console
- [x] No regressions in existing functionality (English remains default)
- [x] Code follows established patterns (React hooks, Redux state)
- [x] No security vulnerabilities introduced (XSS protection verified)
- [x] .po files properly compiled to .mo (CLI translations functional)
- [x] Documentation completeness verified (docs/es/ mirrors docs/en/)
- [x] Performance impact acceptable (translation loading doesn't slow initial render)
