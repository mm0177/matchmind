"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { notificationsApi, Notification } from "@/lib/api";

export default function NotificationsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
    if (!loading && user && !user.onboarding_completed) router.replace("/profile");
  }, [user, loading, router]);

  const loadNotifications = useCallback(async () => {
    try {
      const data = await notificationsApi.list();
      setNotifications(data);
    } finally {
      setFetching(false);
    }
  }, []);

  useEffect(() => {
    if (user) loadNotifications();
  }, [user, loadNotifications]);

  async function markRead(id: string) {
    await notificationsApi.markRead(id);
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
    );
  }

  if (loading || !user || !user.onboarding_completed) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-950">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="mb-6 text-2xl font-bold text-white">Notifications</h1>

      {fetching ? (
        <div className="flex justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
        </div>
      ) : notifications.length === 0 ? (
        <div className="rounded-2xl border border-gray-800 bg-gray-900 py-16 text-center text-sm text-gray-500">
          No notifications yet.
        </div>
      ) : (
        <ul className="space-y-3">
          {notifications.map((n) => (
            <li
              key={n.id}
              onClick={() => !n.is_read && markRead(n.id)}
              className={`cursor-pointer rounded-2xl border px-5 py-4 transition ${
                n.is_read
                  ? "border-gray-800 bg-gray-900/50 opacity-60"
                  : "border-purple-500/30 bg-gray-900 shadow-md hover:border-purple-400/60"
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-semibold text-white">{n.title}</p>
                  <p className="mt-1 text-sm text-gray-400">{n.body}</p>
                </div>
                {!n.is_read && (
                  <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-purple-500" />
                )}
              </div>
              <p className="mt-2 text-xs text-gray-600">
                {new Date(n.created_at).toLocaleString()}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
