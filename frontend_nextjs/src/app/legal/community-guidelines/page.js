import LegalDoc from "@/components/LegalDoc";

export const metadata = { title: "Community Guidelines | VayuTask AI" };

export default function CommunityGuidelinesPage() {
  return (
    <LegalDoc title="Community Guidelines" updated="14 September 2026">
      <p>
        VayuTask AI works because posters and taskers trust each other. These guidelines describe the
        behavior we expect from everyone on the Platform, whichever side of a task you&apos;re on.
      </p>

      <h2>Be honest</h2>
      <ul>
        <li>Describe the task accurately — don&apos;t leave out details that would change the price or whether someone accepts it.</li>
        <li>Only make an offer you intend to honor, and only accept work you&apos;re actually able to do.</li>
        <li>Upload real before/after photos for the task in front of you, not stock or reused images.</li>
        <li>Leave reviews based on your own experience. Fake or retaliatory reviews may be removed and can lead to account action.</li>
      </ul>

      <h2>Be respectful</h2>
      <ul>
        <li>No harassment, threats, hate speech, or discrimination based on religion, caste, gender, disability, or any other protected characteristic.</li>
        <li>Keep messages on-topic and professional. The in-app chat exists so we can help if something goes wrong — keep task discussions there.</li>
        <li>Show up on time, or message the other person as soon as you know you&apos;ll be late or need to cancel.</li>
      </ul>

      <h2>Keep the Platform safe</h2>
      <ul>
        <li>Don&apos;t ask for or agree to payment outside the Platform for a task posted on it — this removes escrow protection and dispute support for both sides.</li>
        <li>Don&apos;t post or accept tasks that are illegal, or that require a license or certification you don&apos;t hold.</li>
        <li>Don&apos;t share another user&apos;s personal contact details, KYC documents, or address outside what&apos;s needed to complete the task.</li>
        <li>Report anything that feels unsafe — a suspicious task, a person who won&apos;t use official Platform payment, or behavior that made you uncomfortable — using the report option on the task or profile.</li>
      </ul>

      <h2>What happens if these guidelines aren&apos;t followed</h2>
      <p>
        Depending on what happened, we may remove content, restrict specific features, suspend the
        account, or refer serious matters (fraud, safety threats) to law enforcement. Repeated
        cancellations, evidence failures, or reports against an account are reviewed by our trust and
        safety checks and may lead to limits on posting or accepting tasks.
      </p>

      <h2>Questions</h2>
      <p>If you&apos;re not sure whether something is okay, ask us first through the in-app Feedback form.</p>
    </LegalDoc>
  );
}
