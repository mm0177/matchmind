"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

const steps = [
  {
    number: "01",
    title: "Start Chatting",
    description:
      "Begin a natural conversation with our AI. There are no forms to fill out — just talk about what matters to you.",
  },
  {
    number: "02",
    title: "We Learn Who You Are",
    description:
      "Over 10 days, our AI quietly builds a deep personality profile from your conversations — your values, communication style, and relationship needs.",
  },
  {
    number: "03",
    title: "Meet Your Match",
    description:
      "Our matching engine compares personality vectors across all users and surfaces your most compatible connections.",
  },
];

export default function HomePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      router.replace(user.onboarding_completed ? "/chat" : "/profile");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-950">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Hero */}
      <section className="flex flex-col items-center justify-center px-6 pt-28 pb-20 text-center">
        <span className="mb-4 inline-block rounded-full border border-purple-500/40 bg-purple-500/10 px-4 py-1 text-xs font-semibold uppercase tracking-widest text-purple-400">
          AI-Powered Matchmaking
        </span>
        <h1 className="max-w-2xl text-4xl font-bold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
          Find Your Match Through{" "}
          <span className="bg-linear-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            Real Conversation
          </span>
        </h1>
        <p className="mt-6 max-w-xl text-lg text-gray-400">
          MatchMind doesn&apos;t use swipes or questionnaires. You chat naturally for
          10 days and our AI builds a deep understanding of who you are — then
          finds people who truly complement you.
        </p>
        <div className="mt-10 flex flex-col gap-4 sm:flex-row">
          <Link
            href="/signup"
            className="rounded-full bg-purple-600 px-8 py-3 text-sm font-semibold text-white shadow-lg transition hover:bg-purple-500"
          >
            Get Started — It&apos;s Free
          </Link>
          <Link
            href="/login"
            className="rounded-full border border-gray-700 px-8 py-3 text-sm font-semibold text-gray-300 transition hover:border-gray-500 hover:text-white"
          >
            Sign In
          </Link>
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-5xl px-6 pb-28">
        <h2 className="mb-12 text-center text-2xl font-bold text-gray-100">
          How It Works
        </h2>
        <div className="grid gap-8 sm:grid-cols-3">
          {steps.map((step) => (
            <div
              key={step.number}
              className="rounded-2xl border border-gray-800 bg-gray-900/60 p-8 transition hover:border-purple-500/50"
            >
              <span className="mb-4 block text-3xl font-black text-purple-500/50">
                {step.number}
              </span>
              <h3 className="mb-2 text-lg font-semibold text-white">
                {step.title}
              </h3>
              <p className="text-sm leading-relaxed text-gray-400">
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-8 text-center text-xs text-gray-600">
        &copy; {new Date().getFullYear()} MatchMind &mdash; Built with AI, for
        humans.
      </footer>
    </div>
  );
}
