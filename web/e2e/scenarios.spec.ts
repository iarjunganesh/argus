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

test("an API that stops answering is reported, not waited on forever", async ({ page }) => {
  // The browser keeps reconnecting to a stream that fails at the network level.
  await page.route("**/api/v1/kyc/**", (route) => route.abort("connectionrefused"));
  await page.goto("/assessments/argus-rpt-000000000000");
  await expect(page.getByRole("status")).toHaveText("The ARGUS API could not be reached.", {
    timeout: 20_000,
  });
});

async function openAll(page: Page) {
  // Open every collapsed section, so its content can be read and checked with axe.
  await page.evaluate(() => document.querySelectorAll("details").forEach((d) => (d.open = true)));
}

const withoutWarningSign = (text: string) => text.replace(/^⚠️\s*/u, "");

for (const scenario of scenarios) {
  const { entity_name: name } = scenario.request;
  const summary = scenario.risk_summary;
  const hold = summary.tier_basis === "sanctions_match";

  test(`${name}: ${summary.overall_risk_tier}`, async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: `Run the assessment of ${name}` }).click();
    // The URL holds the report ID only: never the entity's name.
    await expect(page).toHaveURL(/\/assessments\/argus-rpt-[\w-]+$/);
    await expect(page.getByRole("status")).toHaveText("Assessment complete. The report follows.");

    // The case header: the outcome, what sets it, and the next step.
    await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();
    await expect(page.getByTestId("risk-tier")).toHaveText(summary.overall_risk_tier);
    await expect(page.getByTestId("risk-score")).toHaveText(String(summary.overall_risk_score));
    await expect(
      page.getByText(summary.decision_recommendation, { exact: true }).first(),
    ).toBeVisible();
    if (hold) {
      await expect(page.getByRole("note")).toHaveText(summary.decision_recommendation);
      await expect(page.getByRole("link", { name: "Review the match" })).toBeVisible();
      const match = page.getByRole("region", { name: "Potential sanctions match" });
      await expect(match.getByText("Listing")).toBeVisible();
      await expect(match.getByText("Customer")).toBeVisible();
    } else {
      await expect(page.getByRole("link", { name: "Decide the case" })).toBeVisible();
      await expect(page.getByRole("region", { name: "Potential sanctions match" })).toHaveCount(0);
    }

    // The score's working: exact points per dimension, and the overall score as their total. Where
    // the points' sum has two decimal places, the page says the score keeps one.
    await expect(page.getByTestId("working-total")).toHaveText(String(summary.overall_risk_score));
    const points = Object.values(scenario.dimension_scores).reduce(
      (sum, dimension) => sum + (dimension.score * Number.parseFloat(dimension.weight)) / 100,
      0,
    );
    const sum = Math.round(points * 100) / 100;
    const note = page.getByText(/^The points add up to /);
    if (sum === summary.overall_risk_score) {
      await expect(note).toHaveCount(0);
    } else {
      await expect(note).toHaveText(
        `The points add up to ${sum}; the overall score keeps one decimal place.`,
      );
    }

    // Every finding is filed under its dimension, with its evidence one step away.
    await openAll(page);
    const working = page.getByRole("region", { name: "Why this score" });
    for (const finding of scenario.key_findings) {
      await expect(
        working.getByText(withoutWarningSign(finding), { exact: true }).first(),
      ).toBeVisible();
    }
    if (scenario.key_findings.length) {
      await expect(working.getByText(/^Evidence \(\d+\)$/).first()).toBeVisible();
    }

    // Every agent finished, and says where its result came from.
    const flow = page.getByRole("region", { name: "Investigation" });
    await expect(
      flow.getByText(/^5 agents finished in [\d.]+ s; 4 from recorded demo profiles$/),
    ).toBeVisible();
    // "Done", followed by the agent's time in a nested span.
    await expect(flow.getByText(/^Done( in .+ s)?$/)).toHaveCount(5);
    await expect(flow.getByText(/^Result: Recorded demo profile$/)).toHaveCount(4);
    await expect(flow.getByText(/^Result: Computed from the data plane$/)).toHaveCount(1);

    await expect(page.getByRole("heading", { name: "Regulations cited" })).toBeVisible();
    await expect(page.getByText(/^Document:/).first()).toBeVisible();
    // Each cited rule is a whole sentence, or marked where a long one was cut.
    const rules = page.getByRole("region", { name: "Regulations cited" }).getByRole("listitem");
    for (const rule of await rules.all()) {
      await expect(rule.locator("p").first()).toHaveText(/[.…]$/);
    }
    await expectNoAxeViolations(page);
  });
}

test("the start page keeps each demo case's last run, riskiest first", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("queue-result").filter({ hasText: "Not run" })).toHaveCount(6);
  await page.getByRole("button", { name: "Run the assessment of Cayman Synth Capital" }).click();
  await expect(page.getByRole("status")).toHaveText("Assessment complete. The report follows.");
  await page.goto("/");
  const first = page.getByRole("listitem").filter({ hasText: "Cayman Synth Capital" });
  await expect(first.getByTestId("queue-result")).toHaveText("CRITICAL76");
  await expect(first.getByTestId("queue-review")).toHaveText("Awaiting analyst");
  await expect(page.getByTestId("queue-result").filter({ hasText: "Not run" })).toHaveCount(5);
  await first.getByRole("link", { name: "Open the assessment of Cayman Synth Capital" }).click();
  await expect(page.getByTestId("risk-score")).toHaveText("76");
});

test("a slow API start is explained, not left silent", async ({ page }) => {
  await page.route("**/api/v1/kyc/assess", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 4000));
    await route.continue();
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Run the assessment of Jane Synthetic" }).click();
  await expect(
    page.getByText(/^Starting the API: it sleeps when nobody is using it/),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/assessments\/argus-rpt-[\w-]+$/);
});

// The simulated review, kept in this browser only.

async function runCase(page: Page, name: string) {
  await page.goto("/");
  await page.getByRole("button", { name: `Run the assessment of ${name}` }).click();
  await expect(page.getByRole("status")).toHaveText("Assessment complete. The report follows.");
}

async function recordStep(section: ReturnType<Page["getByRole"]>, action: string, reason?: string) {
  await section.getByRole("radio", { name: action, exact: true }).check();
  if (reason !== undefined)
    await section.getByLabel(/^(Reason|Comment \(optional\))$/).fill(reason);
  await section.getByRole("button", { name: "Record the step" }).click();
}

const DEMO_LABEL =
  "Demo review: kept in this browser only and sent nowhere. ARGUS recommends; a person decides.";

test("Cayman Synth Capital: the match, the decision and the approver's sign-off", async ({
  page,
}) => {
  await runCase(page, "Cayman Synth Capital");
  await expect(page.getByText(DEMO_LABEL).first()).toBeVisible();
  const header = page.getByText(/^Review: /);
  await expect(header).toHaveText("Review: Awaiting analyst");

  // The decision waits for the match.
  const review = page.getByRole("region", { name: "Review", exact: true });
  await expect(review.getByText(/^Resolve the potential sanctions match first/)).toBeVisible();
  await expect(review.getByRole("radio")).toHaveCount(0);

  const match = page.getByRole("region", { name: "Potential sanctions match" });
  await recordStep(match, "Clear: false positive", "Registration and jurisdiction differ.");
  await expect(match.getByText("Registration and jurisdiction differ.")).toBeVisible();
  // A recorded step is announced, not only drawn: the form it came from is gone.
  const live = '[aria-live="polite"]';
  await expect(match.locator(live, { hasText: "Clear: false positive" })).toHaveCount(1);

  // With enhanced due diligence required, it is the only approval offered.
  await expect(review.getByRole("radio", { name: "Approve", exact: true })).toHaveCount(0);
  await recordStep(review, "Approve with enhanced due diligence", "Onboard with EDD.");
  await expect(review.getByText(/^State:/)).toHaveText("State: Awaiting approver");
  await expect(
    review.locator(live, { hasText: "Approve with enhanced due diligence" }),
  ).toHaveCount(1);
  await expect(header).toHaveText("Review: Awaiting approver");

  // The analyst cannot sign off their own decision.
  await expect(review.getByRole("radio", { name: "Sign off" })).toHaveCount(0);
  await expect(review.getByText(/^Waiting for the approver/)).toBeVisible();
  await expectNoAxeViolations(page);

  await page.getByLabel("Role", { exact: true }).selectOption("approver");
  await recordStep(review, "Sign off");
  await expect(review.getByText(/^State:/)).toHaveText("State: Decided");

  // Kept in this browser: a reload shows the same review and its three steps.
  await page.reload();
  await expect(page.getByText(/^Review: /)).toHaveText("Review: Decided");
  await openAll(page);
  const steps = page.getByRole("region", { name: "Review steps (this browser only)" });
  await expect(steps.getByRole("listitem")).toHaveCount(3);
  await expect(steps.getByRole("listitem").nth(2)).toContainText("Sign off · Approver");
  await expectNoAxeViolations(page);
});

test("Jane Synthetic: a LOW case is decided without a second sign-off", async ({ page }) => {
  await runCase(page, "Jane Synthetic");
  await page.getByRole("link", { name: "Decide the case" }).click();
  const review = page.getByRole("region", { name: "Review", exact: true });

  // A decision needs a reason.
  await recordStep(review, "Approve");
  await expect(review.getByRole("alert")).toHaveText(
    "Give a reason: the review records why each step was taken.",
  );
  await expectNoAxeViolations(page);

  await review.getByLabel("Reason").fill("Identity verified; no adverse findings.");
  await review.getByRole("button", { name: "Record the step" }).click();
  await expect(review.getByText(/^State:/)).toHaveText("State: Decided");
  await expect(review.getByText(/^Waiting for/)).toHaveCount(0);
  await expect(review.getByRole("radio")).toHaveCount(0);
  await expectNoAxeViolations(page);
});

test("a browser that blocks storage still reviews the open page and says nothing is kept", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "localStorage", {
      get() {
        throw new DOMException("Storage is blocked", "SecurityError");
      },
    });
  });
  await runCase(page, "Jane Synthetic");
  const review = page.getByRole("region", { name: "Review", exact: true });
  await expect(review.getByText("Not kept: this browser blocks storage.")).toBeVisible();
  await recordStep(review, "Decline", "Testing a blocked browser.");
  await expect(review.getByText(/^State:/)).toHaveText("State: Decided");
  await expectNoAxeViolations(page);
});
