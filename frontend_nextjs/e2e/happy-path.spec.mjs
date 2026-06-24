import { test, expect } from "@playwright/test";
import {
  uniqueEmail,
  registerUser,
  loginSession,
  createPublishedTask,
  acceptTask,
  uploadEvidenceUrls,
} from "./helpers/api.mjs";

test.describe("Marketplace happy path", () => {
  test("register → publish → accept → escrow → evidence → verify → release", async ({
    page,
    request,
  }) => {
    page.on("dialog", (dialog) => dialog.accept());

    const poster = await registerUser(request, {
      email: uniqueEmail("poster"),
      role: "POSTER",
    });
    const tasker = await registerUser(request, {
      email: uniqueEmail("tasker"),
      role: "TASKER",
    });

    const taskId = await createPublishedTask(request, poster.token);
    await acceptTask(request, tasker.token, taskId);

    // Poster locks escrow (Razorpay skipped when not configured)
    await loginSession(page, poster);
    await page.goto(`/payments?task_id=${taskId}`);
    await page.getByRole("button", { name: /Lock Escrow via API/i }).click();
    await expect(page.getByText(/Escrow Locked/i)).toBeVisible({ timeout: 15_000 });

    await page.getByRole("button", { name: /Pay with Razorpay Checkout/i }).click();
    await expect(page.getByRole("button", { name: /Mark In Progress/i })).toBeVisible({
      timeout: 15_000,
    });

    await page.getByRole("button", { name: /Mark In Progress/i }).click();

    await uploadEvidenceUrls(request, tasker.token, taskId);

    // Poster runs AI verification from verify UI
    await loginSession(page, poster);
    await page.goto(`/verify?task_id=${taskId}`);
    await page.getByRole("button", { name: /Run AI Verification/i }).click();
    await expect(page.getByText(/VERIFIED|LOW CONFIDENCE|FAILED/i)).toBeVisible({
      timeout: 30_000,
    });

    // Poster releases escrow
    await page.goto(`/payments?task_id=${taskId}`);
    await page.getByRole("button", { name: /Lock Escrow via API/i }).click();
    await page.getByRole("button", { name: /Pay with Razorpay Checkout/i }).click();
    await page.getByRole("button", { name: /Mark In Progress/i }).click();
    await page.getByRole("button", { name: /Release Funds via API/i }).click();
    await expect(page.getByText(/Escrow Released/i)).toBeVisible({ timeout: 15_000 });
  });

  test("poster can generate and publish a draft from the UI", async ({ page, request }) => {
    page.on("dialog", (dialog) => dialog.accept());

    const poster = await registerUser(request, {
      email: uniqueEmail("poster_ui"),
      role: "POSTER",
    });

    await loginSession(page, poster);
    await page.goto("/poster");
    await page.waitForFunction(() => localStorage.getItem("vayutask_token"));

    const textarea = page.locator("textarea.input-textarea");
    await textarea.fill(
      "E2E UI draft: fix ceiling fan in Dehradun PIN 248001, budget 800 INR"
    );
    await expect(page.getByRole("button", { name: /Generate Task Draft via API/i })).toBeEnabled();
    await page.getByRole("button", { name: /Generate Task Draft via API/i }).click();
    await expect(page.getByRole("button", { name: /Publish Task to Radar/i })).toBeVisible({
      timeout: 60_000,
    });
    await page.getByRole("button", { name: /Publish Task to Radar/i }).click();
    await expect(page).toHaveURL(/\/tasker/);
  });
});
