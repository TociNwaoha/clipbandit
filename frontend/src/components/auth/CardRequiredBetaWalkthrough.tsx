"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { ApiError, api } from "@/lib/api";
import { BillingStatus } from "@/types";

const steps = [
  {
    eyebrow: "PostBandit beta",
    title: "You're in. Welcome to the PostBandit beta.",
    body: "You've been given 30 days of full access because we want real feedback from people actually doing this work.",
  },
  {
    eyebrow: "How it works",
    title: "Turn one recording into a week of posts.",
    body: "Drop in a video or a Twitch VOD, and PostBandit finds the moments worth posting. It transcribes the whole thing, cuts vertical clips, burns in captions, and writes the copy to go with them. Then it publishes for you — YouTube, TikTok, Instagram, Facebook, Threads, and X, all from one place.",
  },
  {
    eyebrow: "What we're asking",
    title: "Use it like you'd use anything you pay for.",
    body: "If something breaks, feels slow, or just doesn't make sense, tell us. Beta testers who report real issues may receive AI credits as a thank-you.",
  },
  {
    eyebrow: "Set up your access",
    title: "Your 30 days start now.",
    body: "We'll ask for a card to hold your spot. You won't be charged until day 30, when the Creator plan will be charged at $18/month. You can cancel anytime before then from your billing settings.",
  },
];

export function CardRequiredBetaWalkthrough() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const checkoutCompleted = searchParams.get("status") === "checkout_success";
  const checkoutCancelled = searchParams.get("status") === "checkout_cancelled";
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState(0);
  const [walkthroughComplete, setWalkthroughComplete] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let attempts = 0;
    let retry: ReturnType<typeof setTimeout> | undefined;

    async function load() {
      try {
        const status = await api.get<BillingStatus>("/api/billing/status");
        if (!active) return;
        if (status.beta_variant !== "card_required") {
          router.replace("/dashboard");
          return;
        }
        if (status.subscription_status !== "pending_checkout") {
          router.replace("/dashboard");
          return;
        }
        setWalkthroughComplete(Boolean(status.beta_card_walkthrough_completed_at));
        if (checkoutCompleted && attempts < 8) {
          attempts += 1;
          retry = setTimeout(() => void load(), 1500);
        }
      } catch (err) {
        if (active) setError(err instanceof ApiError ? err.message : "Unable to load your beta access.");
      } finally {
        if (active) setLoading(false);
      }
    }

    void load();
    return () => {
      active = false;
      if (retry) clearTimeout(retry);
    };
  }, [checkoutCompleted, router]);

  async function startCheckout() {
    setBusy(true);
    setError(null);
    try {
      const response = await api.post<{ checkout_url: string }>("/api/billing/beta-card-checkout", {});
      window.location.assign(response.checkout_url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not open checkout. Please try again.");
      setBusy(false);
    }
  }

  async function completeWalkthroughAndStartCheckout() {
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/auth/beta-card/walkthrough-complete", {});
      setWalkthroughComplete(true);
      await startCheckout();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save your beta setup. Please try again.");
      setBusy(false);
    }
  }

  if (loading) {
    return <main className="flex min-h-[100dvh] items-center justify-center bg-[#F4F8FF] text-sm text-[#4A6080]">Loading beta access...</main>;
  }

  if (checkoutCompleted) {
    return <main className="flex min-h-[100dvh] items-center justify-center bg-[#F4F8FF] px-5 text-center text-sm text-[#4A6080]">Checkout completed. Unlocking your workspace as Stripe confirms your trial.</main>;
  }

  const current = steps[step];
  const isLastStep = step === steps.length - 1;

  return (
    <main className="min-h-[100dvh] bg-[radial-gradient(circle_at_top,#DCE8FF_0%,#F4F8FF_42%,#FFFFFF_100%)] px-5 py-10 text-[#091528] sm:py-16">
      <section className="mx-auto w-full max-w-2xl rounded-[2rem] border border-[#CFE0FF] bg-white p-7 shadow-[0_24px_90px_rgba(9,21,40,0.10)] sm:p-11">
        <div className="flex items-center justify-between gap-4 text-xs font-bold uppercase tracking-[0.12em] text-[#1D3FD0]">
          <span>{walkthroughComplete ? "Finish setting up" : `Step ${step + 1} of ${steps.length}`}</span>
          {!walkthroughComplete ? <div className="flex gap-1.5" aria-hidden>{steps.map((_, index) => <span key={index} className={`h-1.5 w-7 rounded-full ${index <= step ? "bg-[#1D3FD0]" : "bg-[#D6E2F5]"}`} />)}</div> : null}
        </div>

        {walkthroughComplete ? (
          <div className="mt-10">
            <h1 className="app-display text-4xl font-extrabold tracking-[-0.04em]">Set up your 30-day beta access.</h1>
            <p className="mt-5 text-base leading-7 text-[#4A6080]">We&apos;ll ask for a card to hold your spot. You won&apos;t be charged until day 30, when the Creator plan will be charged at $18/month. You can cancel anytime before then from your billing settings.</p>
            <button type="button" onClick={() => void startCheckout()} disabled={busy} className="mt-9 w-full rounded-xl bg-[#1D3FD0] px-5 py-3.5 text-sm font-bold text-white transition hover:bg-[#1633B8] disabled:cursor-not-allowed disabled:opacity-60">{busy ? "Opening checkout..." : "Continue to setup →"}</button>
          </div>
        ) : (
          <div className="mt-10">
            <p className="text-sm font-bold text-[#1D3FD0]">{current.eyebrow}</p>
            <h1 className="app-display mt-3 text-4xl font-extrabold tracking-[-0.04em] sm:text-5xl">{current.title}</h1>
            <p className="mt-6 text-base leading-8 text-[#4A6080]">{current.body}</p>
            {checkoutCancelled ? <p className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">Checkout was cancelled. Your beta invitation is still available whenever you are ready.</p> : null}
            {error ? <p className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
            <div className="mt-10 flex items-center justify-between gap-4">
              <button type="button" onClick={() => setStep((currentStep) => Math.max(0, currentStep - 1))} disabled={step === 0 || busy} className="rounded-xl px-4 py-3 text-sm font-bold text-[#4A6080] hover:bg-[#F4F8FF] disabled:opacity-0">Back</button>
              {isLastStep ? <button type="button" onClick={() => void completeWalkthroughAndStartCheckout()} disabled={busy} className="rounded-xl bg-[#1D3FD0] px-5 py-3 text-sm font-bold text-white transition hover:bg-[#1633B8] disabled:cursor-not-allowed disabled:opacity-60">{busy ? "Opening checkout..." : "Continue to setup →"}</button> : <button type="button" onClick={() => setStep((currentStep) => currentStep + 1)} className="rounded-xl bg-[#1D3FD0] px-5 py-3 text-sm font-bold text-white transition hover:bg-[#1633B8]">Continue</button>}
            </div>
          </div>
        )}
        {walkthroughComplete && error ? <p className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
      </section>
    </main>
  );
}
