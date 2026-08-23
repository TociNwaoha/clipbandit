"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { api } from "@/lib/api";
import { BillingStatus, PublicBillingPlan } from "@/types";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: "long", day: "numeric", year: "numeric" }).format(new Date(value));
}

function formatAmount(cents: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(cents / 100);
}

export function CardRequiredBetaTrialStatus() {
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [plans, setPlans] = useState<PublicBillingPlan[]>([]);

  useEffect(() => {
    let active = true;
    Promise.all([
      api.get<BillingStatus>("/api/billing/status"),
      api.get<PublicBillingPlan[]>("/api/billing/plans"),
    ])
      .then(([billing, planRows]) => {
        if (!active) return;
        setStatus(billing);
        setPlans(planRows);
      })
      .catch(() => {
        if (active) setStatus(null);
      });
    return () => {
      active = false;
    };
  }, []);

  const trial = useMemo(() => {
    if (!status?.trial_ends_at) return null;
    const remainingMs = new Date(status.trial_ends_at).getTime() - Date.now();
    return {
      daysRemaining: Math.max(0, Math.ceil(remainingMs / (1000 * 60 * 60 * 24))),
      endsAt: status.trial_ends_at,
    };
  }, [status]);

  if (
    !status ||
    status.beta_variant !== "card_required" ||
    status.subscription_status !== "trialing" ||
    !trial
  ) {
    return null;
  }

  const creatorPlan = plans.find((plan) => plan.tier === "creator");
  const amount = creatorPlan ? formatAmount(creatorPlan.monthly_price_cents) : "$18";
  const prominent = trial.daysRemaining <= 5;

  return (
    <section className={`mx-8 mt-4 rounded-xl border px-4 py-3 text-sm ${prominent ? "border-[#9CB8FF] bg-[#EAF0FF] text-[#13285E]" : "border-[#D6E2F5] bg-white text-[#334C6C]"}`} aria-label="Beta trial status">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="leading-6">
          Your PostBandit beta trial has <span className="font-semibold">{trial.daysRemaining} day{trial.daysRemaining === 1 ? "" : "s"} remaining</span>.
          {" "}The Creator plan will be charged {amount}/month on {formatDate(trial.endsAt)} unless you cancel before then.
        </p>
        <Link href="/billing" className="shrink-0 font-semibold text-[#1D3FD0] underline underline-offset-4 hover:text-[#1633B8]">
          Manage billing
        </Link>
      </div>
    </section>
  );
}
