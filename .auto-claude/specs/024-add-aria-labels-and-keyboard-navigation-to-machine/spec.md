# Add ARIA labels and keyboard navigation to MachineCard interactive elements

## Overview

Add proper accessibility attributes (aria-label, aria-expanded, aria-haspopup) to all interactive elements in MachineCard including failover dropdown, backup info popup, and action buttons. Implement keyboard navigation support for nested dropdown menus.

## Rationale

MachineCard contains 15+ interactive elements including nested dropdowns, copy buttons, and status badges but most lack proper ARIA labels. This makes the component inaccessible to screen reader users and keyboard-only navigation.

---
*This spec was created from ideation and is pending detailed specification.*
