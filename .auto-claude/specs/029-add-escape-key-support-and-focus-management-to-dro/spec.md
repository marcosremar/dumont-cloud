# Add Escape key support and focus management to DropdownMenu

## Overview

Implement keyboard support for DropdownMenu including Escape to close, Arrow keys for navigation, Enter/Space to select, and proper focus management when opening/closing.

## Rationale

DropdownMenu component only handles click-outside to close (line 586-595). Keyboard-only users cannot close the dropdown with Escape, navigate items with Arrow keys, or have focus properly managed. This fails WCAG 2.1.1 Keyboard accessibility.

---
*This spec was created from ideation and is pending detailed specification.*
