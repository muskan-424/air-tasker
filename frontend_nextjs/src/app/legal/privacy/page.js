import LegalDoc from "@/components/LegalDoc";

export const metadata = { title: "Privacy Policy | VayuTask AI" };

export default function PrivacyPage() {
  return (
    <LegalDoc title="Privacy Policy" updated="14 September 2026">
      <p>
        This policy explains what personal data VayuTask AI collects, why, and the choices you have. It
        is written to align with India&apos;s Digital Personal Data Protection Act, 2023 (DPDP Act) — as
        the &quot;Data Fiduciary&quot;, we process your data as the &quot;Data Principal&quot; for the purposes below,
        with your consent where required.
      </p>

      <h2>1. What we collect</h2>
      <ul>
        <li><strong>Account data:</strong> email, phone number, password (stored as a salted hash, never in plain text), and role (poster/tasker).</li>
        <li><strong>Profile data:</strong> display name, bio, skills, service area PIN codes, preferred language.</li>
        <li><strong>Task data:</strong> task descriptions, photos or voice recordings you submit to describe a task, offers, prices, and chat messages between poster and tasker.</li>
        <li><strong>Verification data:</strong> KYC documents and photos submitted for identity checks, and before/after photos submitted as proof of work.</li>
        <li><strong>Payment data:</strong> we do not store your card or bank details — these are handled directly by our payment partner, Razorpay. We store the resulting transaction and payout records.</li>
        <li><strong>Usage data:</strong> device information, IP address, and log data collected automatically when you use the app, for security and fraud prevention.</li>
      </ul>

      <h2>2. Why we collect it</h2>
      <ul>
        <li>To operate the marketplace: matching posters and taskers, processing offers, and running escrow.</li>
        <li>To verify identity and reduce fraud, including AI-assisted review of submitted photos.</li>
        <li>To communicate with you: task notifications, OTP codes, and support responses.</li>
        <li>To improve the Platform, including training and evaluating the AI features that draft tasks and verify work — this is done on de-identified or aggregated data where feasible.</li>
        <li>To meet legal obligations, such as retaining transaction records for tax and audit purposes.</li>
      </ul>

      <h2>3. AI features and your data</h2>
      <p>
        Some features (task drafting from voice or text, price suggestions, photo-based work verification,
        chat translation) call third-party AI models (currently Google Gemini). The content you submit for
        these features — text, voice, or images — is sent to that provider to generate a response. We do
        not knowingly send KYC documents to these AI providers.
      </p>

      <h2>4. Who we share data with</h2>
      <ul>
        <li><strong>The other party to a task:</strong> a poster and the tasker assigned to their task can see each other&apos;s relevant task details, messages, and public rating history.</li>
        <li><strong>Service providers:</strong> Razorpay for payments, our email/SMS providers for OTPs and notifications, and Google (Gemini) for AI features.</li>
        <li><strong>Law enforcement or regulators</strong>, when required by law.</li>
      </ul>
      <p>We do not sell your personal data.</p>

      <h2>5. Your rights</h2>
      <p>
        Under the DPDP Act you can ask us to confirm what personal data we hold about you, correct
        inaccurate data, or erase data we no longer need to retain (for example, once your account is
        closed and any legal retention period has passed). You can also withdraw consent for optional
        processing, such as marketing messages, at any time. Send these requests through the in-app
        Feedback form; we will confirm your identity before acting on them.
      </p>

      <h2>6. Data retention</h2>
      <p>
        We keep task, payment, and dispute records for as long as needed to resolve disputes, meet tax
        and audit requirements, and defend legal claims — typically several years after a task closes.
        OTP codes are deleted shortly after they expire.
      </p>

      <h2>7. Security</h2>
      <p>
        We use encryption in transit, hashed passwords, and access controls to protect your data. No
        system is perfectly secure; if we become aware of a breach affecting your personal data, we will
        notify you and the relevant authority as required by law.
      </p>

      <h2>8. Children</h2>
      <p>VayuTask AI is not intended for anyone under 18. We do not knowingly collect data from minors.</p>

      <h2>9. Changes to this policy</h2>
      <p>We&apos;ll update the date at the top of this page whenever this policy changes materially.</p>
    </LegalDoc>
  );
}
