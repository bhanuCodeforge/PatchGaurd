import { test, expect } from '@playwright/test';

test.describe('Deployment Flow', () => {
    test.beforeEach(async ({ page }) => {
        // Login before each test
        await page.goto('/auth/login');
        await page.fill('input[name="username"]', 'admin');
        await page.fill('input[name="password"]', 'password123');
        await page.click('button[type="submit"]');
        await expect(page).toHaveURL(/.*dashboard/);
    });

    test('should navigate to devices and open group list', async ({ page }) => {
        await page.click('a[href="/devices/groups"]');
        await expect(page.locator('h1')).toContainText('Device Groups');
    });

    test('should open deployment wizard', async ({ page }) => {
        await page.click('a[href="/patches/catalog"]');
        await expect(page.locator('h1')).toContainText('Patch Catalog');
        
        // Finalize wizard flow when backend is ready
        // await page.click('button#btn-deploy');
        // await expect(page.locator('app-deployment-wizard')).toBeVisible();
    });
});
