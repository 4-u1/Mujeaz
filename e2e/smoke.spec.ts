import { expect, test } from '@playwright/test';

// M1 exit criterion: sign in → cases come from the database → open a case → server verifies its audit chain.
test('sign in, list cases from the API, verify an audit chain', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'English' }).click();
  await page.getByRole('button', { name: /sara\.auth/ }).click();

  await expect(page.getByText('53 cases from the database')).toBeVisible();

  await page.getByRole('button', { name: /Digital Twin|التوأم/ }).first().click();
  await page.getByRole('button', { name: /Audit|سجل التدقيق/ }).first().click();
  await page.getByRole('button', { name: /Verify Audit Integrity/ }).click();
  await expect(page.getByText('Chain intact: recomputed and matched')).toBeVisible();
});
