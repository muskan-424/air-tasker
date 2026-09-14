import LegalDoc from "@/components/LegalDoc";

export const metadata = { title: "Terms of Service | VayuTask AI" };

export default function TermsPage() {
  return (
    <LegalDoc title="Terms of Service" updated="14 September 2026">
      <h2>1. What VayuTask AI is</h2>
      <p>
        VayuTask AI (&quot;we&quot;, &quot;us&quot;, the &quot;Platform&quot;) is an online marketplace that connects people who
        need a task done (&quot;Posters&quot;) with people who offer to do it (&quot;Taskers&quot;). Any account can act as
        both a Poster and a Tasker. We are not a party to the agreement between a Poster and a Tasker for
        the task itself — that agreement is between them. We provide the marketplace, escrow, identity
        verification, and dispute-resolution tools that make that agreement possible.
      </p>

      <h2>2. Eligibility and your account</h2>
      <p>
        You must be at least 18 years old and able to form a binding contract under Indian law to use
        VayuTask AI. You are responsible for the accuracy of the information on your account and for
        keeping your login credentials confidential. One account may not be shared between multiple
        people.
      </p>

      <h2>3. Posting and taking on tasks</h2>
      <ul>
        <li>Posters describe a task, its budget, and whether it is in person or remote.</li>
        <li>Taskers send an offer with their price; the Poster reviews offers and assigns the task to one Tasker.</li>
        <li>Once assigned, the price is fixed unless both sides agree to change it.</li>
        <li>Either side may cancel; a cancellation fee may apply once a Tasker has been assigned (see our Cancellation Policy).</li>
      </ul>

      <h2>4. Payments and fees</h2>
      <p>
        Funds for an assigned task are held in escrow through our payment partner (Razorpay) and released
        to the Tasker once the Poster confirms the work is done, or once our AI-assisted verification
        passes. The Poster pays the agreed task price plus a poster service fee; the Tasker receives the
        agreed price minus a tasker service fee. Current fee rates are shown before you make or accept an
        offer. We do not process cash payments made outside the Platform, and we cannot protect or
        mediate them.
      </p>

      <h2>5. Verification and trust</h2>
      <p>
        We may ask Taskers to complete identity verification (KYC) before they can receive payouts. We
        use before/after photos and, where available, AI-assisted review to check that a task was
        completed as described. These checks reduce risk but do not guarantee any outcome — always use
        good judgment when meeting someone or handing over access to your home, devices, or money.
      </p>

      <h2>6. Disputes</h2>
      <p>
        If a Poster and Tasker disagree about whether a task was completed satisfactorily, either party
        may open a dispute. Our team reviews the evidence submitted and decides whether escrow funds are
        released to the Tasker or refunded to the Poster. This decision is final on the Platform, though
        it does not limit either party&apos;s other legal rights.
      </p>

      <h2>7. Prohibited conduct</h2>
      <ul>
        <li>Posting illegal tasks, or tasks that require licenses you do not hold (e.g. certain electrical or medical work).</li>
        <li>Circumventing escrow by requesting payment outside the Platform for a task posted on it.</li>
        <li>Harassment, discrimination, or abusive behavior toward another user.</li>
        <li>Creating fake reviews, ratings, or multiple accounts to manipulate trust signals.</li>
      </ul>

      <h2>8. Liability</h2>
      <p>
        VayuTask AI is a marketplace, not an employer of Taskers or an insurer of task outcomes. To the
        extent permitted by law, our liability for any claim relating to the Platform is limited to the
        fees you paid us for the task in question in the preceding three months. We do not currently
        provide liability insurance for work performed through the Platform.
      </p>

      <h2>9. Changes to these terms</h2>
      <p>
        We may update these Terms as the Platform evolves. We&apos;ll post the updated date at the top of this
        page; continuing to use VayuTask AI after a change means you accept the updated terms.
      </p>

      <h2>10. Contact</h2>
      <p>Questions about these Terms can be sent through the in-app Feedback form.</p>
    </LegalDoc>
  );
}
