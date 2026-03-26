"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton } from "@clerk/nextjs";
import { useAuth } from "@/lib/auth-context";
import NotificationBell from "./NotificationBell";

export default function Header() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  if (!user) return null;
  const onboardingComplete = user.onboarding_completed;

  const navLink = (href: string, label: string) => (
    <Link
      href={href}
      className={`text-sm font-medium transition ${
        pathname === href
          ? "text-purple-400"
          : "text-gray-400 hover:text-white"
      }`}
    >
      {label}
    </Link>
  );

  return (
    <header className="sticky top-0 z-50 border-b border-gray-800 bg-gray-950/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        {/* Logo */}
        <Link href={onboardingComplete ? "/chat" : "/profile"} className="text-base font-bold text-white">
          Match<span className="text-purple-400">Mind</span>
        </Link>

        {/* Nav */}
        <nav className="flex items-center gap-6">
          {onboardingComplete ? (
            <>
              {navLink("/chat", "Chat")}
              {navLink("/matches", "Matches")}
              {navLink("/notifications", "Notifications")}
            </>
          ) : (
            navLink("/profile", "Complete Profile")
          )}
        </nav>

        {/* Right side */}
        <div className="flex items-center gap-4">
          {onboardingComplete ? <NotificationBell /> : null}
          <span className="text-sm text-gray-400">{user.display_name || "New User"}</span>
          <UserButton />
          <button
            onClick={logout}
            className="rounded-full border border-gray-700 px-3 py-1 text-xs font-medium text-gray-400 transition hover:border-gray-500 hover:text-white"
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
