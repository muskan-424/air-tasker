import { test, expect } from "@playwright/test";
import {
  uniqueEmail,
  registerUser,
  createPublishedTask,
  acceptTask,
  startEscrow,
  openDispute,
  resolveDispute,
} from "./helpers/api.mjs";

test.describe("Dispute path", () => {
  test("escrow held → dispute opened → admin resolves with cancel", async ({ request }) => {
    const poster = await registerUser(request, {
      email: uniqueEmail("poster_dispute"),
      role: "POSTER",
    });
    const tasker = await registerUser(request, {
      email: uniqueEmail("tasker_dispute"),
      role: "TASKER",
    });
    const admin = await registerUser(request, {
      email: uniqueEmail("admin_dispute"),
      role: "ADMIN",
    });

    const taskId = await createPublishedTask(request, poster.token);
    await acceptTask(request, tasker.token, taskId);
    const escrow = await startEscrow(request, poster.token, taskId);
    expect(escrow.status).toMatch(/HELD|RELEASE_ELIGIBLE|RELEASED/);

    const dispute = await openDispute(
      request,
      tasker.token,
      taskId,
      "Work quality mismatch — E2E dispute path"
    );
    expect(dispute.status).toBe("OPEN");
    expect(dispute.dispute_id).toBeTruthy();

    const resolved = await resolveDispute(
      request,
      admin.token,
      dispute.dispute_id,
      "cancel",
      "Refund approved in E2E test"
    );
    expect(resolved.status).toBe("RESOLVED");
    expect(resolved.escrow_status).toBe("CANCELLED");
  });
});
