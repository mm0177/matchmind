"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { matchesApi, MatchDetail, MatchMessage } from "@/lib/api";

/* ─── Match Chat Panel ──────────────────────────────────────────────────────── */

function MatchChat({
  match,
  userId,
  onBack,
}: {
  match: MatchDetail;
  userId: string;
  onBack: () => void;
}) {
  const [messages, setMessages] = useState<MatchMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadMessages = useCallback(async () => {
    if (!match.conversation_id) return;
    try {
      const msgs = await matchesApi.getMessages(match.conversation_id);
      setMessages(msgs);
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, [match.conversation_id]);

  useEffect(() => {
    loadMessages();
    // Poll for new messages every 3 seconds
    pollRef.current = setInterval(loadMessages, 3000);
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
      }
    };
  }, [loadMessages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || !match.conversation_id || sending) return;
    setSending(true);
    try {
      const msg = await matchesApi.sendMessage(match.conversation_id, input.trim());
      setMessages((prev) => [...prev, msg]);
      setInput("");
    } catch {
      /* show nothing — will retry */
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-5rem)] flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-gray-800 px-4 py-3">
        <button
          onClick={onBack}
          className="text-gray-400 hover:text-white transition"
        >
          ← Back
        </button>
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-linear-to-br from-purple-600 to-pink-500 text-sm font-bold text-white">
          {match.partner_display_name.charAt(0).toUpperCase()}
        </div>
        <div>
          <span className="font-medium text-white">
            {match.partner_display_name}
          </span>
          {match.partner_age && (
            <span className="ml-2 text-sm text-gray-500">
              {match.partner_age}
            </span>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {loading ? (
          <div className="flex justify-center py-20">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-gray-500 text-sm">
              Say hi to {match.partner_display_name}!
            </p>
          </div>
        ) : (
          messages.map((msg) => {
            const isMine = msg.sender_id === userId;
            return (
              <div
                key={msg.id}
                className={`flex ${isMine ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                    isMine
                      ? "bg-purple-600 text-white rounded-br-sm"
                      : "bg-gray-800 text-gray-200 rounded-bl-sm"
                  }`}
                >
                  {msg.content}
                  <div
                    className={`mt-1 text-[10px] ${
                      isMine ? "text-purple-200" : "text-gray-500"
                    }`}
                  >
                    {new Date(msg.created_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </div>
                </div>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-800 px-4 py-3">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder="Type a message..."
            className="flex-1 rounded-xl bg-gray-800 px-4 py-2.5 text-sm text-white placeholder-gray-500 outline-none focus:ring-1 focus:ring-purple-500"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sending}
            className="rounded-xl bg-purple-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-purple-500 disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Match Card (name + age only) ──────────────────────────────────────────── */

function MatchCard({
  match,
  onChat,
}: {
  match: MatchDetail;
  onChat: () => void;
}) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-gray-800 bg-gray-900 p-5 transition hover:border-purple-500/40">
      <div className="flex items-center gap-4">
        {/* Avatar */}
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-linear-to-br from-purple-600 to-pink-500 text-lg font-bold text-white">
          {match.partner_display_name.charAt(0).toUpperCase()}
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">
            {match.partner_display_name}
          </h3>
          {match.partner_age && (
            <p className="text-sm text-gray-500">
              {match.partner_age} years old
            </p>
          )}
        </div>
      </div>

      <button
        onClick={onChat}
        className="rounded-xl bg-purple-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-purple-500"
      >
        Chat
      </button>
    </div>
  );
}

/* ─── Main Page ─────────────────────────────────────────────────────────────── */

export default function MatchesPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [matches, setMatches] = useState<MatchDetail[]>([]);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeChat, setActiveChat] = useState<MatchDetail | null>(null);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
    if (!loading && user && !user.onboarding_completed) router.replace("/profile");
  }, [user, loading, router]);

  const loadMatches = useCallback(async () => {
    try {
      setError(null);
      const data = await matchesApi.list();
      setMatches(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load matches");
    } finally {
      setFetching(false);
    }
  }, []);

  useEffect(() => {
    if (user) loadMatches();
  }, [user, loadMatches]);

  if (loading || !user || !user.onboarding_completed) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-950">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
      </div>
    );
  }

  // If a chat is active, show the chat panel full-screen
  if (activeChat) {
    return (
      <div className="min-h-screen bg-gray-950">
        <MatchChat
          match={activeChat}
          userId={user.id}
          onBack={() => setActiveChat(null)}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="mb-2 text-2xl font-bold text-white">Your Matches</h1>
      <p className="mb-8 text-sm text-gray-500">
        People who complement who you are — based on your 10-day journey.
      </p>

      {fetching ? (
        <div className="flex justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-red-800 bg-red-900/20 py-10 text-center">
          <p className="text-sm text-red-400">{error}</p>
          <button
            onClick={loadMatches}
            className="mt-3 text-sm text-purple-400 hover:underline"
          >
            Try again
          </button>
        </div>
      ) : matches.length === 0 ? (
        <div className="rounded-2xl border border-gray-800 bg-gray-900 py-16 text-center">
          <p className="text-4xl">💜</p>
          <p className="mt-4 text-sm text-gray-400">
            No matches yet — complete your 10-day journey and check back!
          </p>
          <button
            onClick={() => router.push("/chat")}
            className="mt-4 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-500 transition"
          >
            Continue chatting
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {matches.map((m) => (
            <MatchCard
              key={m.id}
              match={m}
              onChat={() => setActiveChat(m)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
