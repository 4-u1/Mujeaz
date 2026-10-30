import { expect, test } from '@playwright/test';

// M1 exit criterion: sign in → cases come from the database → open a case → server verifies its audit chain.
test('sign in, list cases from the API, verify an audit chain', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'English' }).click();
  await page.getByRole('button', { name: /sara\.auth/ }).click();

  await expect(page.getByText('73 cases from the database')).toBeVisible();

  await page.getByRole('button', { name: /Digital Twin|التوأم/ }).first().click();
  await page.getByRole('button', { name: /Audit|سجل التدقيق/ }).first().click();
  await page.getByRole('button', { name: /Verify Audit Integrity/ }).click();
  await expect(page.getByText('Chain intact: recomputed and matched')).toBeVisible();
});

test('roles without metrics:read see an explanation, not zeros', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'English' }).click();
  await page.getByRole('button', { name: /omar\.coder/ }).click();
  await expect(page.getByText('73 cases from the database')).toBeVisible();
  await expect(page.getByText(/Financial metrics are available to authorization officers/)).toBeVisible();
  await expect(page.getByText('Revenue Protected Today')).toHaveCount(0);
});

// M2 exit criterion: analyze a case in the UI → agents run → verified facts, evidence status and CDI question appear.
test('analyze a case: progress, verified facts and a physician documentation query', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'English' }).click();
  await page.getByRole('button', { name: /sara\.auth/ }).click();
  await expect(page.getByText('73 cases from the database')).toBeVisible();

  await page.getByRole('button', { name: /Digital Twin|التوأم/ }).first().click();
  await page.getByTestId('analyze-button').click();

  await expect(page.getByTestId('analysis-mode')).toHaveText('Deterministic baseline', { timeout: 30_000 });
  await expect(page.getByTestId('analysis-progress').getByText('Readiness & risk')).toBeVisible();
  await expect(page.getByTestId('analysis-evidence').getByText('MISSING')).toBeVisible();
  await expect(page.getByTestId('cdi-question')).toContainText('at least 6 weeks of conservative therapy');
  await expect(page.getByTestId('analysis-facts').locator('li')).toHaveCount(3);
});

// M3 exit criterion: risk detected → physician answers the documentation query → automatic re-analysis
// → decision ready → the authorization officer approves the submission gate.
test('close the loop: physician addendum turns a risky request into an approved submission', async ({ page }) => {
  const signIn = async (user: RegExp) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'English' }).click();
    await page.getByRole('button', { name: user }).click();
    await expect(page.getByText('73 cases from the database')).toBeVisible();
  };

  // 1. Officer analyses the legacy MRI case: no documented therapy → risk + an open query.
  await signIn(/sara\.auth/);
  await page.getByRole('button', { name: /Digital Twin|التوأم/ }).first().click();
  await page.getByTestId('analyze-button').click();
  await expect(page.getByTestId('readiness-explanation')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('case-queries').getByText('OPEN')).toBeVisible();

  // 2. What-if (nothing saved): 7 weeks of physiotherapy before the request.
  const whatIf = page.getByTestId('what-if-form');
  await whatIf.getByLabel('Therapy start').fill('2026-06-01');
  await whatIf.getByLabel('Therapy end').fill('2026-07-20');
  await whatIf.getByLabel('Provider').fill('Demo Physio Center');
  await whatIf.getByRole('button', { name: 'Simulate' }).click();
  await expect(page.getByTestId('what-if-result')).toContainText('DECISION_READY');
  await page.getByRole('button', { name: 'Sign out' }).click();

  // 3. Physician answers the query with a structured addendum → automatic re-analysis.
  await signIn(/dr\.khalid/);
  await page.getByRole('button', { name: 'Work Queue' }).first().click();
  const form = page.getByTestId('answer-form-AUTH-2026-4922');
  await form.getByLabel('Therapy start').fill('2026-06-01');
  await form.getByLabel('Therapy end').fill('2026-07-20');
  await form.getByLabel('Provider').fill('Demo Physio Center');
  await form.getByRole('button', { name: 'Sign and submit addendum' }).click();
  await expect(page.getByTestId('work-message')).toContainText('DECISION_READY', { timeout: 30_000 });
  await page.getByRole('button', { name: 'Sign out' }).click();

  // 4. Officer sees the cited addendum and approves the human submission gate.
  await signIn(/sara\.auth/);
  await page.getByRole('button', { name: /Digital Twin|التوأم/ }).first().click();
  await expect(page.getByTestId('document-viewer').getByText('post-request addendum')).toBeVisible();
  await page.getByTestId('approve-submission').click();
  await expect(page.getByTestId('approve-submission')).toHaveCount(0);
});
