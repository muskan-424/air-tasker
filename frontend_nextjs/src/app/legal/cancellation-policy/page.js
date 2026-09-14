import LegalDoc from "@/components/LegalDoc";

export const metadata = { title: "Cancellation Policy | VayuTask AI" };

export default function CancellationPolicyPage() {
  return (
    <LegalDoc title="Cancellation Policy" updated="14 September 2026">
      <p>
        This page explains what happens when a task is cancelled, and when a cancellation fee applies.
        The exact fee percentage is configured by VayuTask AI and shown in the app before you cancel, so
        you always see the amount before you confirm.
      </p>

      <h2>Before a tasker is assigned</h2>
      <p>
        A task that hasn&apos;t been assigned to a tasker yet can be cancelled by the poster at any time,
        free of charge. Any pending offers on it are automatically declined and the taskers who made them
        are notified.
      </p>

      <h2>After a tasker is assigned</h2>
      <p>
        Once a poster has accepted an offer, both the poster and the assigned tasker can cancel — but a
        cancellation fee (a percentage of the agreed task price) applies, because the other side may have
        already set aside time or turned down other work:
      </p>
      <ul>
        <li>
          <strong>If the poster cancels,</strong> the cancellation fee is kept from their escrow refund —
          they receive the task price back minus the fee.
        </li>
        <li>
          <strong>If the tasker cancels,</strong> the poster is refunded the full amount held in escrow.
          The fee is recorded against the tasker and repeated cancellations affect their standing on the
          Platform.
        </li>
      </ul>
      <p>
        Refunds are issued to the original payment method through our payment partner, Razorpay, and can
        take a few business days to appear depending on your bank.
      </p>

      <h2>Once work is verified or under dispute</h2>
      <p>
        A task can no longer be cancelled through this flow once the poster has confirmed the work is
        done (or our verification has passed) or a dispute has been opened on it. From that point,
        disagreements are handled through the dispute process instead, where our team reviews the
        evidence submitted by both sides and decides how escrow funds are released.
      </p>

      <h2>No-shows and repeated cancellations</h2>
      <p>
        If a tasker repeatedly cancels after being assigned, or a poster repeatedly cancels after
        accepting an offer, our trust and safety checks may flag the account and limit their ability to
        post or accept tasks.
      </p>
    </LegalDoc>
  );
}
