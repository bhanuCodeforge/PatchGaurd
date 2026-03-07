import { test, expect } from '@playwright/test';

test('login flow', async ({ page }) => {
  await page.goto('/auth/login');
  
  // Verify login page title
  await expect(page).toHaveTitle(/PatchGuard/);
  
  // Fill login form
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'password123');
  
  // Click login button
  await page.click('button[type="submit"]');
  
  // Expect to redirect to dashboard
  await expect(page).toHaveURL(/.*dashboard/);
  
  // Verify dashboard sidebar is visible
  await expect(page.locator('nav#sidebar')).toBeVisible();
});
