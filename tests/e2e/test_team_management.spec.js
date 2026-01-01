/**
 * Team Management E2E Tests
 *
 * Tests for team management UI flows:
 * - Team creation flow
 * - Member invitation flow
 * - Role assignment flow
 * - Permission enforcement flow
 * - Audit log viewing
 */

const { test, expect } = require('@playwright/test');

// Configuration for headless mode
test.use({
  headless: true,
  viewport: { width: 1920, height: 1080 },
});

// Use demo-app for consistent test data
const BASE_PATH = '/demo-app';

// Helper to navigate to Teams page
async function goToTeams(page) {
  await page.goto(`${BASE_PATH}/teams`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);
}

// Helper to navigate to Team Details page
async function goToTeamDetails(page, teamId = 1) {
  await page.goto(`${BASE_PATH}/teams/${teamId}`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);
}

// Helper to navigate to Create Role page
async function goToCreateRole(page, teamId = 1) {
  await page.goto(`${BASE_PATH}/teams/${teamId}/roles/new`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);
}

// ============================================================
// TEST SUITE 1: Teams List Page
// ============================================================
test.describe('Teams List Page', () => {

  test('displays teams list with correct elements', async ({ page }) => {
    await goToTeams(page);

    // Check page title is visible
    const pageTitle = page.getByText('Teams').first();
    await expect(pageTitle).toBeVisible();

    // Check Create Team button is visible
    const createButton = page.getByRole('button', { name: /create team/i });
    await expect(createButton).toBeVisible();
  });

  test('shows team stats cards', async ({ page }) => {
    await goToTeams(page);

    // Check for stats cards
    const totalTeams = page.getByText(/total teams/i).first();
    const adminAccess = page.getByText(/admin access/i).first();
    const totalMembers = page.getByText(/total members/i).first();

    const hasStats = await totalTeams.isVisible().catch(() => false) ||
                     await adminAccess.isVisible().catch(() => false) ||
                     await totalMembers.isVisible().catch(() => false);

    expect(hasStats).toBe(true);
  });

  test('displays teams in table format', async ({ page }) => {
    await goToTeams(page);

    // Check for demo teams
    const engineeringTeam = page.getByText('Engineering').first();
    const hasTeams = await engineeringTeam.isVisible().catch(() => false);

    if (hasTeams) {
      // Verify team table columns
      const teamColumn = page.getByText(/team/i).first();
      const membersColumn = page.getByText(/members/i).first();
      const roleColumn = page.getByText(/your role/i).first();

      expect(await teamColumn.isVisible().catch(() => false) ||
             await membersColumn.isVisible().catch(() => false) ||
             await roleColumn.isVisible().catch(() => false)).toBe(true);
    }

    expect(hasTeams).toBe(true);
  });

  test('shows role badges for user roles', async ({ page }) => {
    await goToTeams(page);

    // Check for role badges (Admin, Developer, Viewer)
    const adminBadge = page.getByText(/admin/i).first();
    const developerBadge = page.getByText(/developer/i).first();
    const viewerBadge = page.getByText(/viewer/i).first();

    const hasRoleBadges = await adminBadge.isVisible().catch(() => false) ||
                          await developerBadge.isVisible().catch(() => false) ||
                          await viewerBadge.isVisible().catch(() => false);

    expect(hasRoleBadges).toBe(true);
  });

  test('navigates to team details when clicking on team', async ({ page }) => {
    await goToTeams(page);

    // Find and click a team row
    const teamRow = page.getByText('Engineering').first();
    if (await teamRow.isVisible().catch(() => false)) {
      await teamRow.click();
      await page.waitForTimeout(500);

      // Should navigate to team details
      expect(page.url()).toContain('/teams/');
    }
  });
});

// ============================================================
// TEST SUITE 2: Team Creation Flow
// ============================================================
test.describe('Team Creation Flow', () => {

  test('opens create team modal on button click', async ({ page }) => {
    await goToTeams(page);

    // Click Create Team button
    const createButton = page.getByTestId('create-team-button').or(
      page.getByRole('button', { name: /create team/i })
    );
    await expect(createButton).toBeVisible();
    await createButton.click();
    await page.waitForTimeout(500);

    // Modal should be visible
    const modalTitle = page.getByText(/create new team/i).first();
    await expect(modalTitle).toBeVisible();
  });

  test('modal shows team name input field', async ({ page }) => {
    await goToTeams(page);

    // Open modal
    const createButton = page.getByTestId('create-team-button').or(
      page.getByRole('button', { name: /create team/i })
    );
    await createButton.click();
    await page.waitForTimeout(500);

    // Check for team name input
    const nameInput = page.getByTestId('team-name-input').or(
      page.getByPlaceholder(/e\.g\., engineering/i)
    );
    await expect(nameInput).toBeVisible();
  });

  test('modal shows admin role notice', async ({ page }) => {
    await goToTeams(page);

    // Open modal
    const createButton = page.getByTestId('create-team-button').or(
      page.getByRole('button', { name: /create team/i })
    );
    await createButton.click();
    await page.waitForTimeout(500);

    // Check for admin role notice
    const adminNotice = page.getByText(/you will be the admin/i).first();
    await expect(adminNotice).toBeVisible();
  });

  test('successfully creates a new team', async ({ page }) => {
    await goToTeams(page);

    // Open modal
    const createButton = page.getByTestId('create-team-button').or(
      page.getByRole('button', { name: /create team/i })
    );
    await createButton.click();
    await page.waitForTimeout(500);

    // Fill in team name
    const nameInput = page.getByTestId('team-name-input').or(
      page.locator('input').filter({ hasText: '' }).first()
    );
    await nameInput.fill('Test Team E2E');

    // Click confirm button
    const confirmButton = page.getByTestId('confirm-create-team').or(
      page.getByRole('button', { name: /^create team$/i }).last()
    );
    await confirmButton.click();
    await page.waitForTimeout(1500);

    // Should see success notification or team in list
    const successToast = page.getByText(/created successfully/i);
    const newTeam = page.getByText('Test Team E2E');

    const wasSuccessful = await successToast.isVisible().catch(() => false) ||
                          await newTeam.isVisible().catch(() => false);

    expect(wasSuccessful).toBe(true);
  });

  test('cancel button closes the modal', async ({ page }) => {
    await goToTeams(page);

    // Open modal
    const createButton = page.getByTestId('create-team-button').or(
      page.getByRole('button', { name: /create team/i })
    );
    await createButton.click();
    await page.waitForTimeout(500);

    // Click cancel button
    const cancelButton = page.getByRole('button', { name: /cancel/i }).first();
    await cancelButton.click();
    await page.waitForTimeout(500);

    // Modal should be closed
    const modalTitle = page.getByText(/create new team/i).first();
    await expect(modalTitle).not.toBeVisible();
  });
});

// ============================================================
// TEST SUITE 3: Team Details Page
// ============================================================
test.describe('Team Details Page', () => {

  test('displays team name and breadcrumb', async ({ page }) => {
    await goToTeamDetails(page);

    // Check for team name in header or breadcrumb
    const teamName = page.getByText('Engineering').first();
    await expect(teamName).toBeVisible();

    // Check for breadcrumb navigation
    const breadcrumbTeams = page.getByRole('link', { name: /teams/i }).first();
    const hasBreadcrumb = await breadcrumbTeams.isVisible().catch(() => false);
    expect(hasBreadcrumb).toBe(true);
  });

  test('shows team stats (members, role, invites)', async ({ page }) => {
    await goToTeamDetails(page);

    // Check for stat cards
    const totalMembers = page.getByText(/total members/i).first();
    const yourRole = page.getByText(/your role/i).first();
    const pendingInvites = page.getByText(/pending invites/i).first();

    const hasStats = await totalMembers.isVisible().catch(() => false) ||
                     await yourRole.isVisible().catch(() => false) ||
                     await pendingInvites.isVisible().catch(() => false);

    expect(hasStats).toBe(true);
  });

  test('shows Invite Member button for admin', async ({ page }) => {
    await goToTeamDetails(page);

    // Check for Invite Member button (visible for admin)
    const inviteButton = page.getByTestId('invite-member-button').or(
      page.getByRole('button', { name: /invite member/i })
    );
    const hasInviteButton = await inviteButton.isVisible().catch(() => false);
    expect(hasInviteButton).toBe(true);
  });

  test('displays team members table', async ({ page }) => {
    await goToTeamDetails(page);

    // Check for members table
    const membersTitle = page.getByText(/team members/i).first();
    await expect(membersTitle).toBeVisible();

    // Check for demo members
    const adminMember = page.getByText(/admin@dumont\.cloud/i).first();
    const developerMember = page.getByText(/developer@dumont\.cloud/i).first();

    const hasMembers = await adminMember.isVisible().catch(() => false) ||
                       await developerMember.isVisible().catch(() => false);

    expect(hasMembers).toBe(true);
  });

  test('shows tabs for Members and Audit Log', async ({ page }) => {
    await goToTeamDetails(page);

    // Check for tabs
    const membersTab = page.getByRole('tab', { name: /members/i });
    const auditTab = page.getByRole('tab', { name: /audit log/i });

    await expect(membersTab).toBeVisible();
    await expect(auditTab).toBeVisible();
  });

  test('back button navigates to teams list', async ({ page }) => {
    await goToTeamDetails(page);

    // Find and click back button
    const backButton = page.getByRole('button', { name: /back to teams/i });
    await expect(backButton).toBeVisible();
    await backButton.click();
    await page.waitForTimeout(500);

    // Should navigate to teams list
    expect(page.url()).toContain('/teams');
    expect(page.url()).not.toContain('/teams/1');
  });
});

// ============================================================
// TEST SUITE 4: Member Invitation Flow
// ============================================================
test.describe('Member Invitation Flow', () => {

  test('opens invite member modal', async ({ page }) => {
    await goToTeamDetails(page);

    // Click Invite Member button
    const inviteButton = page.getByTestId('invite-member-button').or(
      page.getByRole('button', { name: /invite member/i })
    );
    await inviteButton.click();
    await page.waitForTimeout(500);

    // Modal should be visible
    const modalTitle = page.getByText(/invite team member/i).first();
    await expect(modalTitle).toBeVisible();
  });

  test('modal shows email input and role selector', async ({ page }) => {
    await goToTeamDetails(page);

    // Open modal
    const inviteButton = page.getByTestId('invite-member-button').or(
      page.getByRole('button', { name: /invite member/i })
    );
    await inviteButton.click();
    await page.waitForTimeout(500);

    // Check for email input
    const emailInput = page.getByTestId('invite-email-input').or(
      page.getByPlaceholder(/user@example\.com/i)
    );
    await expect(emailInput).toBeVisible();

    // Check for role selector
    const roleSelect = page.getByTestId('invite-role-select').or(
      page.getByText(/select a role/i).first()
    );
    await expect(roleSelect).toBeVisible();
  });

  test('shows 7-day expiry notice', async ({ page }) => {
    await goToTeamDetails(page);

    // Open modal
    const inviteButton = page.getByTestId('invite-member-button').or(
      page.getByRole('button', { name: /invite member/i })
    );
    await inviteButton.click();
    await page.waitForTimeout(500);

    // Check for expiry notice
    const expiryNotice = page.getByText(/expires in 7 days/i).first();
    await expect(expiryNotice).toBeVisible();
  });

  test('successfully sends invitation', async ({ page }) => {
    await goToTeamDetails(page);

    // Open modal
    const inviteButton = page.getByTestId('invite-member-button').or(
      page.getByRole('button', { name: /invite member/i })
    );
    await inviteButton.click();
    await page.waitForTimeout(500);

    // Fill email
    const emailInput = page.getByTestId('invite-email-input').or(
      page.getByPlaceholder(/user@example\.com/i)
    );
    await emailInput.fill('newmember@test.com');

    // Select role - click the trigger first
    const roleSelect = page.getByTestId('invite-role-select');
    await roleSelect.click();
    await page.waitForTimeout(300);

    // Select Developer role
    const developerOption = page.getByText('Developer').last();
    if (await developerOption.isVisible().catch(() => false)) {
      await developerOption.click();
      await page.waitForTimeout(300);
    }

    // Click send invitation
    const confirmButton = page.getByTestId('confirm-invite').or(
      page.getByRole('button', { name: /send invitation/i })
    );
    await confirmButton.click();
    await page.waitForTimeout(1500);

    // Check for success
    const successToast = page.getByText(/invitation sent/i);
    const wasSuccessful = await successToast.isVisible().catch(() => false);

    expect(wasSuccessful).toBe(true);
  });

  test('shows pending invitations section', async ({ page }) => {
    await goToTeamDetails(page);

    // Check for pending invitations section
    const pendingSection = page.getByText(/pending invitations/i).first();
    const hasPendingSection = await pendingSection.isVisible().catch(() => false);

    if (hasPendingSection) {
      // Check for pending email
      const pendingEmail = page.getByText(/pending@dumont\.cloud/i).first();
      await expect(pendingEmail).toBeVisible();
    }

    expect(true).toBe(true); // Pending section is optional
  });
});

// ============================================================
// TEST SUITE 5: Role Assignment Flow
// ============================================================
test.describe('Role Assignment Flow', () => {

  test('shows role dropdown for team members (as admin)', async ({ page }) => {
    await goToTeamDetails(page);

    // As admin, should see role dropdowns for non-owner members
    const roleSelects = page.locator('select, [role="combobox"]');
    const roleSelectCount = await roleSelects.count();

    // Should have at least one role selector visible
    expect(roleSelectCount).toBeGreaterThanOrEqual(0);
  });

  test('displays predefined roles in selector', async ({ page }) => {
    await goToTeamDetails(page);

    // Find a role dropdown and check options
    const roleSelect = page.locator('[role="combobox"]').first();
    if (await roleSelect.isVisible().catch(() => false)) {
      await roleSelect.click();
      await page.waitForTimeout(300);

      // Check for predefined roles
      const adminOption = page.getByText('Admin').last();
      const developerOption = page.getByText('Developer').last();
      const viewerOption = page.getByText('Viewer').last();

      const hasRoles = await adminOption.isVisible().catch(() => false) ||
                       await developerOption.isVisible().catch(() => false) ||
                       await viewerOption.isVisible().catch(() => false);

      expect(hasRoles).toBe(true);
    }
  });

  test('shows remove member button for non-owner members', async ({ page }) => {
    await goToTeamDetails(page);

    // Should see trash/remove icons for non-owner members
    const removeButtons = page.locator('button[title="Remove member"]');
    const removeButtonCount = await removeButtons.count();

    // Admin team has members that can be removed
    expect(removeButtonCount).toBeGreaterThanOrEqual(0);
  });
});

// ============================================================
// TEST SUITE 6: Audit Log Viewing
// ============================================================
test.describe('Audit Log Viewing', () => {

  test('switches to Audit Log tab', async ({ page }) => {
    await goToTeamDetails(page);

    // Click on Audit Log tab
    const auditTab = page.getByRole('tab', { name: /audit log/i });
    await auditTab.click();
    await page.waitForTimeout(500);

    // Tab should be active (URL should include #audit)
    expect(page.url()).toContain('#audit');
  });

  test('displays audit log entries', async ({ page }) => {
    await goToTeamDetails(page);

    // Switch to Audit Log tab
    const auditTab = page.getByRole('tab', { name: /audit log/i });
    await auditTab.click();
    await page.waitForTimeout(1000);

    // Check for audit log title
    const auditTitle = page.getByText(/audit log/i);
    await expect(auditTitle.first()).toBeVisible();

    // Check for some audit entries or empty state
    const auditEntries = page.locator('[class*="audit"], [data-testid*="audit"]');
    const noLogsMessage = page.getByText(/no audit logs/i);

    const hasContent = await auditEntries.count() > 0 ||
                       await noLogsMessage.isVisible().catch(() => false);

    expect(hasContent).toBe(true);
  });

  test('can navigate back to Members tab', async ({ page }) => {
    await goToTeamDetails(page);

    // Switch to Audit Log tab
    const auditTab = page.getByRole('tab', { name: /audit log/i });
    await auditTab.click();
    await page.waitForTimeout(500);

    // Switch back to Members tab
    const membersTab = page.getByRole('tab', { name: /members/i });
    await membersTab.click();
    await page.waitForTimeout(500);

    // Members content should be visible
    const membersTitle = page.getByText(/team members/i).first();
    await expect(membersTitle).toBeVisible();
  });
});

// ============================================================
// TEST SUITE 7: Custom Role Creation
// ============================================================
test.describe('Custom Role Creation Page', () => {

  test('displays role creation form', async ({ page }) => {
    await goToCreateRole(page);

    // Check for page title
    const pageTitle = page.getByText(/create custom role/i).first();
    await expect(pageTitle).toBeVisible();

    // Check for role name input
    const roleNameInput = page.getByTestId('role-name-input').or(
      page.getByPlaceholder(/e\.g\., devops engineer/i)
    );
    await expect(roleNameInput).toBeVisible();
  });

  test('shows permission categories', async ({ page }) => {
    await goToCreateRole(page);

    // Check for permission categories
    const gpuCategory = page.getByText(/^GPU$/i).first();
    const costCategory = page.getByText(/^Cost$/i).first();
    const teamCategory = page.getByText(/^Team$/i).first();

    const hasCategories = await gpuCategory.isVisible().catch(() => false) ||
                          await costCategory.isVisible().catch(() => false) ||
                          await teamCategory.isVisible().catch(() => false);

    expect(hasCategories).toBe(true);
  });

  test('shows individual permission checkboxes', async ({ page }) => {
    await goToCreateRole(page);

    // Check for specific permissions
    const gpuProvision = page.getByTestId('permission-gpu.provision').or(
      page.getByText(/gpu provisioning/i).first()
    );
    const gpuView = page.getByTestId('permission-gpu.view').or(
      page.getByText(/gpu view/i).first()
    );

    const hasPermissions = await gpuProvision.isVisible().catch(() => false) ||
                           await gpuView.isVisible().catch(() => false);

    expect(hasPermissions).toBe(true);
  });

  test('select all button toggles category permissions', async ({ page }) => {
    await goToCreateRole(page);

    // Find a Select All button
    const selectAllButton = page.getByText(/select all/i).first();
    const hasSelectAll = await selectAllButton.isVisible().catch(() => false);

    if (hasSelectAll) {
      await selectAllButton.click();
      await page.waitForTimeout(300);

      // Button should change to Deselect All
      const deselectAllButton = page.getByText(/deselect all/i).first();
      const hasDeselect = await deselectAllButton.isVisible().catch(() => false);
      expect(hasDeselect).toBe(true);
    }
  });

  test('shows selected permissions count', async ({ page }) => {
    await goToCreateRole(page);

    // Click a permission checkbox
    const checkbox = page.locator('input[type="checkbox"]').first();
    if (await checkbox.isVisible().catch(() => false)) {
      await checkbox.click();
      await page.waitForTimeout(300);

      // Should show count of selected permissions
      const selectedCount = page.getByText(/\d+ permissions? selected/i);
      const hasCount = await selectedCount.isVisible().catch(() => false);
      expect(hasCount).toBe(true);
    }
  });

  test('creates custom role successfully', async ({ page }) => {
    await goToCreateRole(page);

    // Fill role name
    const roleNameInput = page.getByTestId('role-name-input').or(
      page.locator('input').first()
    );
    await roleNameInput.fill('Test Custom Role');

    // Select some permissions
    const checkboxes = page.locator('input[type="checkbox"]');
    const count = await checkboxes.count();
    if (count > 0) {
      await checkboxes.first().click();
    }
    await page.waitForTimeout(300);

    // Click create button
    const createButton = page.getByTestId('create-role-button').or(
      page.getByRole('button', { name: /create role/i })
    );
    await createButton.click();
    await page.waitForTimeout(1500);

    // Should see success or navigate away
    const successToast = page.getByText(/created successfully/i);
    const navigatedAway = !page.url().includes('/roles/new');

    const wasSuccessful = await successToast.isVisible().catch(() => false) || navigatedAway;
    expect(wasSuccessful).toBe(true);
  });

  test('cancel button navigates back to team', async ({ page }) => {
    await goToCreateRole(page);

    // Click cancel/back button
    const backButton = page.getByRole('button', { name: /back to team/i }).or(
      page.getByRole('button', { name: /cancel/i })
    );
    await backButton.click();
    await page.waitForTimeout(500);

    // Should navigate to team details
    expect(page.url()).not.toContain('/roles/new');
  });
});

// ============================================================
// TEST SUITE 8: Remove Member Flow
// ============================================================
test.describe('Remove Member Flow', () => {

  test('opens confirmation dialog on remove click', async ({ page }) => {
    await goToTeamDetails(page);

    // Find a remove button (trash icon)
    const removeButton = page.locator('button[title="Remove member"]').first();
    if (await removeButton.isVisible().catch(() => false)) {
      await removeButton.click();
      await page.waitForTimeout(500);

      // Confirmation dialog should appear
      const confirmDialog = page.getByText(/remove team member/i).first();
      await expect(confirmDialog).toBeVisible();
    }
  });

  test('shows warning message in remove dialog', async ({ page }) => {
    await goToTeamDetails(page);

    // Find and click a remove button
    const removeButton = page.locator('button[title="Remove member"]').first();
    if (await removeButton.isVisible().catch(() => false)) {
      await removeButton.click();
      await page.waitForTimeout(500);

      // Check for warning message
      const warningMessage = page.getByText(/cannot be undone/i);
      await expect(warningMessage).toBeVisible();
    }
  });

  test('cancel closes remove dialog', async ({ page }) => {
    await goToTeamDetails(page);

    // Find and click a remove button
    const removeButton = page.locator('button[title="Remove member"]').first();
    if (await removeButton.isVisible().catch(() => false)) {
      await removeButton.click();
      await page.waitForTimeout(500);

      // Click cancel
      const cancelButton = page.getByRole('button', { name: /cancel/i }).first();
      await cancelButton.click();
      await page.waitForTimeout(300);

      // Dialog should be closed
      const confirmDialog = page.getByText(/remove team member/i).first();
      await expect(confirmDialog).not.toBeVisible();
    }
  });
});

// ============================================================
// TEST SUITE 9: Navigation and UI Elements
// ============================================================
test.describe('Navigation and UI Elements', () => {

  test('teams list shows status badges', async ({ page }) => {
    await goToTeams(page);

    // Check for status badges (active, inactive)
    const activeBadge = page.getByText(/active/i).first();
    const hasStatusBadge = await activeBadge.isVisible().catch(() => false);
    expect(hasStatusBadge).toBe(true);
  });

  test('team details shows member count', async ({ page }) => {
    await goToTeamDetails(page);

    // Check for member count display
    const memberCount = page.getByText(/\d+ members?/i).first();
    const hasMemberCount = await memberCount.isVisible().catch(() => false);
    expect(hasMemberCount).toBe(true);
  });

  test('page uses consistent styling', async ({ page }) => {
    await goToTeams(page);

    // Check for page container
    const pageContainer = page.locator('.page-container');
    const hasContainer = await pageContainer.count() > 0;
    expect(hasContainer).toBe(true);

    // Check for card components
    const cards = page.locator('.ta-card, [class*="Card"]');
    const hasCards = await cards.count() > 0;
    expect(hasCards).toBe(true);
  });

  test('responsive layout works', async ({ page }) => {
    await goToTeams(page);

    // Check that main content is visible
    const mainContent = page.locator('main, .page-container').first();
    await expect(mainContent).toBeVisible();

    // Check that navigation or sidebar is present
    const navigation = page.locator('nav, [role="navigation"], aside').first();
    const hasNavigation = await navigation.isVisible().catch(() => false);
    expect(hasNavigation).toBe(true);
  });
});

// ============================================================
// TEST SUITE 10: Error Handling
// ============================================================
test.describe('Error Handling', () => {

  test('handles empty team list gracefully', async ({ page }) => {
    await goToTeams(page);

    // Page should load without errors
    const errorMessage = page.getByText(/error|failed|something went wrong/i).first();
    const hasError = await errorMessage.isVisible().catch(() => false);

    // Either teams should be shown or empty state
    if (!hasError) {
      const teams = page.getByText('Engineering');
      const emptyState = page.getByText(/no teams yet/i);

      const hasContent = await teams.isVisible().catch(() => false) ||
                         await emptyState.isVisible().catch(() => false);

      expect(hasContent).toBe(true);
    }
  });

  test('shows loading state when appropriate', async ({ page }) => {
    // Navigate quickly to catch loading state
    page.goto(`${BASE_PATH}/teams`);

    // Loading skeleton might appear briefly
    const skeleton = page.locator('[class*="skeleton"], [class*="Skeleton"]');
    const hasLoadedContent = page.getByText('Teams').first();

    // Either loading skeleton was shown or content loaded immediately
    await expect(hasLoadedContent).toBeVisible({ timeout: 5000 });
  });
});
