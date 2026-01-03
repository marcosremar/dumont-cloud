#!/bin/bash

# Script to remove all isDemoMode references from the codebase
# This script removes demo mode completely

echo "Removing isDemoMode references from all files..."

# Files to process (excluding api.js and already processed files)
FILES=(
  "src/components/Layout.jsx"
  "src/components/MobileMenu.jsx"
  "src/components/InviteMemberModal.jsx"
  "src/components/AuditLogTable.jsx"
  "src/components/dashboard/WizardForm.jsx"
  "src/pages/Playground.jsx"
  "src/pages/TeamsPage.jsx"
  "src/pages/TeamDetailsPage.jsx"
  "src/pages/TemplateDetailPage.jsx"
  "src/pages/TemplatePage.jsx"
  "src/pages/CreateRolePage.jsx"
)

for file in "${FILES[@]}"; do
  if [ -f "$file" ]; then
    echo "Processing $file..."

    # Create a backup
    cp "$file" "$file.bak"

    # Remove isDemoMode from imports
    sed -i '' 's/, *isDemoMode//g' "$file"
    sed -i '' 's/isDemoMode, *//g' "$file"
    sed -i '' 's/import.*isDemoMode.*from.*api.*//g' "$file"

    # Remove isDemo variable declarations
    sed -i '' '/const isDemo = isDemoMode()/d' "$file"
    sed -i '' '/const.*isDemo.*=.*isDemoMode()/d' "$file"
    sed -i '' '/const.*isDemoMode.*=.*isDemoMode()/d' "$file"

    echo "  - Removed imports and variable declarations"
  else
    echo "File not found: $file"
  fi
done

echo ""
echo "Demo mode references removed from imports and declarations."
echo "Backup files created with .bak extension"
echo ""
echo "NOTE: You will need to manually remove the conditional logic blocks:"
echo "  - Remove 'if (isDemo) { ... }' blocks"
echo "  - Keep only the real API call paths"
echo "  - Remove demo data constants (DEMO_TEAMS, DEMO_MACHINES, etc.)"
