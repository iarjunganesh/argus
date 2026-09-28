import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import scenarios from "../../tests/fixtures/demo_scenarios.json" with { type: "json" };

// The API's recorded outcomes for the six demo scenarios, shared with the Python test
// tests/test_demo_scenarios.py, so the UI is checked against the same expectations.

async function expectNoAxeViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(results.violations).toEqual([]);
}

test("the start page has no accessibility violations", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "New assessment", level: 1 })).toBeVisible();
  await expectNoAxeViolations(page);
});

test("the form explains what is missing", async ({ page }) => {
  await page.goto("/");
  // The form's own alert; Next.js adds a second, empty one for route announcements.
  const problem = page.locator("#form-error");
  await page.getByRole("button", { name: "Run assessment" }).click();
  await expect(problem).toHaveText("Enter the entity's name.");
  await page.getByLabel("Entity name").fill("Jane Synthetic");
  await page.getByLabel("Jurisdiction").fill("D");
  await page.getByRole("button", { name: "Run assessment" }).click();
  await expect(problem).toContainText("two-letter country code");
});

test("an unknown assessment ID says so", async ({ page }) => {
  await page.goto("/assessments/argus-rpt-000000000000");
  await expect(page.getByRole("status")).toHaveText("No assessment has this ID.");
});

for (const scenario of scenarios) {
  const { entity_name: name } = scenario.request;
  const summary = scenario.risk_summary;

  test(`${name}: ${summary.overall_risk_tier}`, async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: `Run the assessment of ${name}` }).click();
    await expect(page).toHaveURL(/\/assessments\/argus-rpt-/);
    await expect(page.getByRole("status")).toHaveText("Assessment complete. The report follows.");

    await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();
    await expect(page.getByTestId("risk-tier")).toHaveText(summary.overall_risk_tier);
    await expect(page.getByTestId("risk-score")).toHaveText(String(summary.overall_risk_score));
    await expect(page.getByText(summary.decision_recommendation, { exact: true })).toBeVisible();
    for (const finding of scenario.key_findings) {
      await expect(page.getByText(finding, { exact: true }).first()).toBeVisible();
    }

    // Every agent finished, and says where its result came from.
    const flow = page.getByRole("region", { name: "Investigation" });
    await expect(flow.getByText("Done")).toHaveCount(5);
    await expect(flow.getByText("Recorded demo profile")).toHaveCount(4);
    await expect(flow.getByText("Computed from the data plane")).toHaveCount(1);

    await expect(page.getByRole("heading", { name: "Regulations cited" })).toBeVisible();
    await expect(page.getByText(/^Document:/).first()).toBeVisible();
    await expectNoAxeViolations(page);
  });
}
