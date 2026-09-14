import { test, expect } from "@playwright/test";
import { createPublishedTask, loginSession, registerUser, uniqueEmail } from "./helpers/api.mjs";

test.describe("Legal pages", () => {
  test("are reachable from the footer and the registration form requires agreement", async ({ page }) => {
    await page.goto("/");
    // Only the footer's link set exists yet — one match.
    await page.getByRole("link", { name: "Terms of Service" }).click();
    await expect(page.getByRole("heading", { name: "Terms of Service" })).toBeVisible();
    await expect(page.getByText("Draft for review, not legal advice")).toBeVisible();

    // Now both the footer and the in-page legal sidebar carry the same links; the sidebar
    // (inside <main>) comes first in the DOM, so .first() reliably means "in-page nav".
    await page.getByRole("link", { name: "Privacy Policy" }).first().click();
    await expect(page.getByRole("heading", { name: "Privacy Policy" })).toBeVisible();

    await page.getByRole("link", { name: "Community Guidelines" }).first().click();
    await expect(page.getByRole("heading", { name: "Community Guidelines" })).toBeVisible();

    await page.getByRole("link", { name: "Cancellation Policy" }).first().click();
    await expect(page.getByRole("heading", { name: "Cancellation Policy" })).toBeVisible();

    // Registration is blocked until the Terms/Privacy checkbox is checked.
    await page.goto("/login");
    await page.getByRole("button", { name: "Register" }).click();
    await page.getByLabel("Email Address").fill(uniqueEmail("legal_check"));
    await page.getByLabel("Password").fill("TestPass123!");
    await page.getByRole("button", { name: "Create Account" }).click();
    await expect(page.getByText(/please agree to the terms of service/i)).toBeVisible();
  });
});

test.describe("Public task questions", () => {
  test("a tasker asks a question and the poster answers it", async ({ page, request }) => {
    const poster = await registerUser(request, { email: uniqueEmail("qa_poster"), role: "POSTER" });
    const tasker = await registerUser(request, { email: uniqueEmail("qa_tasker"), role: "TASKER" });
    const taskId = await createPublishedTask(request, poster.token);

    await loginSession(page, tasker);
    await page.goto(`/tasks/${taskId}`);
    await page.getByPlaceholder("Ask the poster a question about this task…").fill("Is the ladder needed?");
    await page.getByRole("button", { name: "Ask", exact: true }).click();
    await expect(page.getByText("Is the ladder needed?")).toBeVisible();
    await expect(page.getByText("Waiting for the poster to answer.")).toBeVisible();

    await loginSession(page, poster);
    await page.goto(`/tasks/${taskId}`);
    await expect(page.getByText("Is the ladder needed?")).toBeVisible();
    await page.getByPlaceholder("Write an answer…").fill("No, I'll provide one.");
    await page.getByRole("button", { name: "Answer" }).click();
    await expect(page.getByText("No, I'll provide one.")).toBeVisible();

    await loginSession(page, tasker);
    await page.goto(`/tasks/${taskId}`);
    await expect(page.getByText("No, I'll provide one.")).toBeVisible();
  });
});

test.describe("Remote tasks", () => {
  test("a remote task is labeled Remote instead of a PIN code", async ({ page, request }) => {
    const poster = await registerUser(request, { email: uniqueEmail("remote_poster"), role: "POSTER" });
    const taskId = await createPublishedTask(
      request,
      poster.token,
      "remote electrical consultation over video call, budget up to 1500 INR"
    );

    await loginSession(page, poster);
    await page.goto(`/tasks/${taskId}`);
    await expect(page.getByText("Remote", { exact: true })).toBeVisible();
  });
});
