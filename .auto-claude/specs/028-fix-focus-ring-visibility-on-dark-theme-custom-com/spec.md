# Fix focus ring visibility on dark theme custom components

## Overview

Update focus ring styles across custom components to use visible colors on dark backgrounds by changing focus:ring-offset-2 background color to match dark surface.

## Rationale

Custom Button and Input components use focus:ring-offset-2 which creates a 2px offset using the page background color. On dark theme (bg-dark-surface: #0a0d0a), the default white offset creates a jarring visual gap. Some components also lack visible focus states entirely.

---
*This spec was created from ideation and is pending detailed specification.*
