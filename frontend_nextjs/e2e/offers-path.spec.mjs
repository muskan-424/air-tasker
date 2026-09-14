import { test, expect } from "@playwright/test";
import { createPublishedTask, loginSession, registerUser, uniqueEmail } from "./helpers/api.mjs";

test.describe("Offers", () => {
  test("tasker sends an offer in the UI → poster accepts it → task is assigned", async ({ page, request }) => {
    page.on("dialog", (dialog) => dialog.accept());

    const poster = await registerUser(request, { email: uniqueEmail("poster_offer"), role: "POSTER" });
    const tasker = await registerUser(request, { email: uniqueEmail("tasker_offer"), role: "TASKER" });
    const taskId = await createPublishedTask(request, poster.token);

    // Tasker makes an offer from the task page and sees their payout after fees.
    await loginSession(page, tasker);
    await page.goto(`/tasks/${taskId}`);
    await expect(page.getByRole("heading", { name: "Make an offer" })).toBeVisible();
    await page.getByLabel("Your price (INR)").fill("1500");
    await page.getByLabel("Message to the poster (optional)").fill("Licensed electrician, free today");
    await expect(page.getByText(/You receive ₹1,350/)).toBeVisible();
    await page.getByRole("button", { name: "Send offer" }).click();
    await expect(page.getByRole("heading", { name: "Your offer" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Update offer" })).toBeVisible();

    // Poster compares offers and accepts.
    await loginSession(page, poster);
    await page.goto(`/tasks/${taskId}`);
    await expect(page.getByText("Licensed electrician, free today")).toBeVisible();
    await expect(page.getByText(/You pay ₹1,575/)).toBeVisible();
    await page.getByRole("button", { name: "Accept" }).click();

    await expect(page.getByText("Agreed price:")).toBeVisible();
    await expect(page.getByText(/You pay ₹1575\.00 \(includes ₹75\.00 service fee\)/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Cancel task" })).toBeVisible();
  });
});
