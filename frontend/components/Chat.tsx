"use client";

import {
  useState,
  useEffect,
  useRef,
  useCallback,
  KeyboardEvent,
} from "react";
import { chatApi, Session, Message, DayStatus } from "@/lib/api";

function DayBanner({ status }: { status: DayStatus }) {
  const pct = Math.round((status.current_day / 10) * 100);
  return (
    <div className="border-b border-gray-800 bg-gray-900/60 px-5 py-3">
      <div className="mb-1.5 flex items-center justify-between text-xs text-gray-400">
        <span>
          Day {status.current_day} of 10 &mdash;{" "}
          <span className="text-purple-400">{status.theme}</span>
        </span>
        <span>{pct}% complete</span>
      </div>
      <div className="h-1 w-full overflow-hidden rounded-full bg-gray-800">
        <div
          className="h-full rounded-full bg-purple-500 transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "rounded-br-none bg-purple-600 text-white"
            : "rounded-bl-none bg-gray-800 text-gray-100"
        }`}
      >
        {msg.content}
      </div>
    </div>
  );
}

export default function Chat() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [dayStatus, setDayStatus] = useState<DayStatus | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingMsgs, setLoadingMsgs] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [lowEffortCount, setLowEffortCount] = useState(0);
  const [showLowEffortWarning, setShowLowEffortWarning] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () =>
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });

  // Load sessions and day status on mount
  useEffect(() => {
    async function init() {
      const [sess, day] = await Promise.all([
        chatApi.listSessions(),
        chatApi.getDayStatus(),
      ]);
      setSessions(sess);
      setDayStatus(day);
      if (sess.length > 0) {
        setActiveId(sess[0].id);
      }
    }
    init();
  }, []);

  // Load messages whenever active session changes
  const loadMessages = useCallback(async (sessionId: string) => {
    setLoadingMsgs(true);
    try {
      const msgs = await chatApi.getMessages(sessionId);
      setMessages(msgs);
    } finally {
      setLoadingMsgs(false);
    }
  }, []);

  useEffect(() => {
    if (activeId) loadMessages(activeId);
  }, [activeId, loadMessages]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  async function createSession() {
    const session = await chatApi.createSession();
    setSessions((prev) => [session, ...prev]);
    setActiveId(session.id);
    setMessages([]);
  }

  async function sendMessage() {
    if (!input.trim() || !activeId || sending) return;
    const text = input.trim();
    setInput("");
    setSending(true);

    // ── Low-effort detection ──────────────────────────────────────────
    const LOW_EFFORT_PATTERNS = /^(ye+s*|no+|o+k+|okay+|yep+|yup+|ya+h*|yeah+|nah+|nope+|sure+|not sure|not really|idk|i ?dk|i don'?t know|maybe+|hm+|uhh*|umm*|correct|fine|good|great|nice|thanks|thank you|cool+|alright|right|true|false|lol+|haha+|ha+|k+|mhm+|dunno|i see|i guess|whatever|same|wow|ah+|oh+|eh+|well|yea+|like|ikr|tbh|i think so|kinda|sort of|kind of)[\.\!\?\,]*$/i;
    const wordCount = text.split(/\s+/).length;
    const isLowEffort = wordCount <= 4 && LOW_EFFORT_PATTERNS.test(text);

    if (isLowEffort) {
      const newCount = lowEffortCount + 1;
      setLowEffortCount(newCount);
      if (newCount >= 3) {
        setShowLowEffortWarning(true);
      }
    } else if (wordCount >= 5) {
      setLowEffortCount(0); // only reset on genuinely substantive answers
    }
    // ─────────────────────────────────────────────────────────────────

    // Optimistic user bubble
    const tempUser: Message = {
      id: `tmp-${Date.now()}`,
      role: "user",
      content: text,
      day_number: dayStatus?.current_day ?? 1,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUser]);

    try {
      const assistantMsg = await chatApi.sendMessage(activeId, text);
      // Confirm user bubble (keep it) and append assistant reply
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempUser.id),
        { ...tempUser },
        assistantMsg,
      ]);
      // Refresh day status in case day advanced
      const ds = await chatApi.getDayStatus();
      setDayStatus(ds);
    } catch {
      setMessages((prev) => prev.filter((m) => m.id !== tempUser.id));
      setInput(text); // restore input on error
    } finally {
      setSending(false);
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="flex flex-1 overflow-hidden bg-gray-950">
      {/* Sidebar */}
      <aside
        className={`flex flex-col border-r border-gray-800 bg-gray-900 transition-all duration-200 ${
          sidebarOpen ? "w-64" : "w-0 overflow-hidden"
        }`}
      >
        <div className="flex items-center justify-between p-4">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
            Sessions
          </span>
          <button
            onClick={createSession}
            className="rounded-lg border border-gray-700 px-3 py-1 text-xs text-gray-300 transition hover:border-purple-500 hover:text-purple-400"
          >
            + New
          </button>
        </div>

        <ul className="flex-1 overflow-y-auto">
          {sessions.map((s) => (
            <li key={s.id}>
              <button
                onClick={() => setActiveId(s.id)}
                className={`w-full px-4 py-3 text-left text-sm transition ${
                  s.id === activeId
                    ? "bg-purple-500/10 text-purple-300"
                    : "text-gray-400 hover:bg-gray-800 hover:text-white"
                }`}
              >
                <div className="truncate font-medium">
                  {s.title ?? `Session ${s.id.slice(0, 6)}`}
                </div>
                <div className="mt-0.5 text-xs text-gray-600">
                  {new Date(s.created_at).toLocaleDateString()}
                </div>
              </button>
            </li>
          ))}
          {sessions.length === 0 && (
            <li className="px-4 py-3 text-xs text-gray-600">
              No sessions yet.
            </li>
          )}
        </ul>
      </aside>

      {/* Chat area */}
      <div className="relative flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <div className="flex items-center gap-3 border-b border-gray-800 px-4 py-3">
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            className="rounded p-1 text-gray-500 transition hover:text-white"
            title="Toggle sidebar"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
          <span className="text-sm font-medium text-gray-300">
            {activeId
              ? sessions.find((s) => s.id === activeId)?.title ??
                "Conversation"
              : "Select or start a session"}
          </span>
        </div>

        {/* Day progress banner */}
        {dayStatus && <DayBanner status={dayStatus} />}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {!activeId && (
            <div className="mt-20 text-center text-sm text-gray-600">
              Create a new session to start chatting.
            </div>
          )}
          {loadingMsgs ? (
            <div className="flex justify-center pt-20">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
            </div>
          ) : (
            messages
              .filter((m) => m.role !== "system")
              .map((m) => <MessageBubble key={m.id} msg={m} />)
          )}
          {sending && (
            <div className="flex justify-start mb-3">
              <div className="rounded-2xl rounded-bl-none bg-gray-800 px-4 py-3">
                <span className="flex gap-1">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:0ms]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:150ms]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:300ms]" />
                </span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Low-effort warning pop-up */}
        {showLowEffortWarning && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="mx-4 max-w-md rounded-2xl border border-yellow-600/30 bg-gray-900 p-6 shadow-xl">
              <div className="mb-3 flex items-center gap-2 text-yellow-400">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <h3 className="text-lg font-semibold">Your responses are too brief</h3>
              </div>
              <p className="mb-2 text-sm leading-relaxed text-gray-300">
                We&apos;ve noticed your last few answers were very short. The more detail you share, the better match we can find for you.
              </p>
              <div className="mb-4 rounded-lg bg-gray-800/80 p-3">
                <p className="text-xs text-gray-400">
                  <span className="font-medium text-yellow-400/80">Tip:</span> Instead of &quot;yes&quot; or &quot;not sure&quot;, try sharing a specific example or explaining <em>why</em> you feel that way. Even 1-2 sentences make a huge difference.
                </p>
              </div>
              <button
                onClick={() => {
                  setShowLowEffortWarning(false);
                  setLowEffortCount(0);
                }}
                className="w-full rounded-lg bg-purple-600 py-2.5 text-sm font-medium text-white transition hover:bg-purple-500"
              >
                Got it, I&apos;ll share more
              </button>
            </div>
          </div>
        )}

        {/* Input */}
        {activeId && (
          <div className="border-t border-gray-800 p-4">
            <div className="flex items-end gap-3 rounded-xl border border-gray-700 bg-gray-800 px-4 py-3 focus-within:border-purple-500">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                rows={1}
                placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
                className="max-h-32 flex-1 resize-none bg-transparent text-sm text-white placeholder-gray-500 outline-none"
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || sending}
                className="shrink-0 rounded-full bg-purple-600 p-2 text-white transition hover:bg-purple-500 disabled:opacity-40"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-4 w-4 rotate-90"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                </svg>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
