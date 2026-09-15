const { test, expect } = require('@playwright/test');

const base = () => process.env.PROJECT_HEALTH_URL || 'http://127.0.0.1:8767';

test.describe('project health Godot scene knowledge', () => {
  test('exposes the scene graph entry from Knowledge + Impact', async ({ page }) => {
    await page.goto(base() + '/knowledge/');
    await expect(page.getByRole('link', { name: 'Scene graph' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Scan local main' })).toBeVisible();
  });

  test('opens the recursive scene graph and scene detail dialog', async ({ page }) => {
    await page.goto(base() + '/knowledge/scenes');
    await expect(page.getByRole('heading', { name: 'Godot scene graph' })).toBeVisible();
    await expect(page.locator('#scene-graph')).toBeVisible();
    const scenes = page.locator('[data-scene-path]');
    await expect(scenes.first()).toBeVisible();
    await scenes.first().click();
    await expect(page.locator('#scene-detail')).toBeVisible();
  });

  test('renders route tree nodes with scene path metadata', async ({ page }) => {
    await page.goto(base() + '/knowledge/scenes');
    const sceneNode = page.locator('[data-scene-path]').first();
    await expect(sceneNode).toBeVisible();
    await expect(sceneNode).toHaveAttribute('aria-label', /\.tscn$/);
  });

  test('supports composition filtering, reachability inclusion and pagination controls', async ({ page }) => {
    await page.goto(base() + '/knowledge/scenes');
    await expect(page.locator('#scene-status')).toContainText('scenes');
    await page.getByRole('button', { name: 'Scene composition' }).click();
    await expect(page.locator('#scene-structure')).toBeVisible();
    await expect(page.locator('.scene-composition-table thead')).toContainText('Data dictionary');
    await expect(page.locator('#include-unreachable')).toBeVisible();
    await page.locator('select[aria-label="Resource type"]').selectOption('script');
    await expect(page.locator('tr[data-resource-type="script"]').first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Next' })).toBeVisible();
  });

  test('opens unconfirmed scene page and filters entries', async ({ page }) => {
    await page.goto(base() + '/knowledge/scenes/unreachable');
    await expect(page.getByRole('heading', { name: 'Unconfirmed Godot scenes' })).toBeVisible();
    await expect(page.locator('#scene-filter')).toBeVisible();
    await page.locator('#scene-filter').selectOption('with-scripts');
    await expect(page.locator('#unreachable-items')).toBeVisible();
  });

  test('restart probe posts to scan endpoint', async ({ page }) => {
    await page.route('**/api/knowledge/scan', async route => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok' }) });
    });
    await page.goto(base() + '/knowledge/scenes');
    const request = page.waitForRequest(request => request.url().endsWith('/api/knowledge/scan') && request.method() === 'POST');
    await page.locator('#scene-probe').click();
    await request;
  });
});
