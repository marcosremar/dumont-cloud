# Add focus trapping and role attributes to AlertDialog modal components

## Overview

Implement proper focus management in AlertDialog components including focus trapping, role="dialog", aria-modal="true", and automatic focus return to trigger element on close.

## Rationale

AlertDialog uses React Portal for proper z-index stacking but lacks focus management. When a modal opens, focus doesn't move into the dialog, and pressing Tab can focus elements behind the modal overlay. This violates WCAG 2.4.3 Focus Order.

---
*This spec was created from ideation and is pending detailed specification.*
