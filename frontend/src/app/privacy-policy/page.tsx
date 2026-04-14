import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy | PostBandit",
  description: "PostBandit privacy policy covering data collection, social publishing, retention, and user rights.",
  alternates: {
    canonical: "https://postbandit.com/privacy-policy",
  },
  robots: {
    index: true,
    follow: true,
  },
};

const EFFECTIVE_DATE = "April 12, 2026";

export default function PrivacyPolicyPage() {
  return (
    <main className="min-h-screen bg-[#0F172A] text-slate-100 px-4 py-10 sm:px-6">
      <div className="mx-auto w-full max-w-4xl">
        <header className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">PostBandit Privacy Policy</h1>
          <p className="mt-3 text-sm text-slate-300">Effective date: {EFFECTIVE_DATE}</p>
        </header>

        <div className="space-y-8 text-sm leading-7 text-slate-200 sm:text-base">
          <section>
            <h2 className="text-xl font-semibold text-white">1. Who We Are</h2>
            <p className="mt-2">
              PostBandit is a web application that helps users upload long-form videos, generate short clips, create
              exports with captions, and publish content to connected social platforms. This policy describes how
              PostBandit collects, uses, and handles information when you use the service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">2. Information We Collect</h2>
            <div className="mt-2 space-y-2">
              <p>
                <span className="font-semibold text-white">Account information:</span> email address, login-related
                information, and account identifiers.
              </p>
              <p>
                <span className="font-semibold text-white">Uploaded media:</span> videos you upload or import for
                processing.
              </p>
              <p>
                <span className="font-semibold text-white">Generated content:</span> transcripts, clip suggestions,
                thumbnails, captions, rendered exports, and publishing metadata created from your uploaded videos.
              </p>
              <p>
                <span className="font-semibold text-white">Social connection data:</span> connected account IDs,
                profile metadata from connected platforms, and token metadata needed to perform requested publishing
                actions.
              </p>
              <p>
                <span className="font-semibold text-white">Operational and technical data:</span> service logs, job
                status data, error diagnostics, and request metadata used for reliability and security.
              </p>
            </div>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">3. How We Use Information</h2>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              <li>Provide and operate PostBandit features, including upload, clipping, transcription, captioning, and export.</li>
              <li>Run queued background jobs for processing media and publishing actions you request.</li>
              <li>Connect and manage third-party social accounts you authorize.</li>
              <li>Publish content to selected third-party platforms only when you initiate publishing.</li>
              <li>Maintain platform security, detect abuse, troubleshoot failures, and improve service performance.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">4. Third-Party Services and Platforms</h2>
            <p className="mt-2">
              PostBandit integrates with third-party services to deliver product functionality, including social
              platforms such as YouTube/Google and X, with planned support for Meta properties (Facebook and
              Instagram), TikTok, and LinkedIn. Depending on your configuration and usage, PostBandit also uses cloud
              infrastructure and object storage providers to store and process media assets.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">5. Social Account Permissions and Tokens</h2>
            <p className="mt-2">
              When you connect a social account, PostBandit stores access credentials needed to perform actions you
              request, such as publishing content. In the current implementation, connected social tokens are encrypted
              at rest before storage in PostBandit&apos;s database.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">6. Data Sharing and Disclosures</h2>
            <p className="mt-2">
              PostBandit shares your content and selected metadata with third-party platforms when you choose to
              publish through those integrations. PostBandit may also disclose information to service providers that
              support hosting, storage, and infrastructure operations required to run the service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">7. Data Retention</h2>
            <p className="mt-2">
              PostBandit retains account, media, generated outputs, and publish job records for as long as needed to
              provide the service, support account operations, and maintain operational integrity. Retention duration
              can vary based on feature use, user actions, and operational needs. When content is deleted by a user or
              account data is removed, associated records are removed or deactivated according to system constraints and
              operational requirements.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">8. Your Choices and Rights</h2>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              <li>You can disconnect connected social accounts in the PostBandit application.</li>
              <li>You can delete uploaded videos and related project content from your account workspace.</li>
              <li>You can request account or data deletion support by contacting: admin@clipbandit.com.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">9. Security</h2>
            <p className="mt-2">
              PostBandit uses administrative, technical, and operational safeguards intended to protect user data.
              However, no method of transmission or storage is completely secure, and absolute security cannot be
              guaranteed.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">10. Children&apos;s Privacy</h2>
            <p className="mt-2">
              PostBandit is not intended for children under 13, and we do not knowingly collect personal information
              from children under 13.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">11. Changes to This Policy</h2>
            <p className="mt-2">
              We may update this policy from time to time. When we do, we will update the effective date on this page.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white">12. Contact</h2>
            <p className="mt-2">
              For privacy questions, data requests, or account deletion requests, contact:
              <span className="font-semibold text-white"> admin@clipbandit.com</span>.
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}
