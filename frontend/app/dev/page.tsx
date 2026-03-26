"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { devApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

type DayPlan = Awaited<ReturnType<typeof devApi.dayPreview>>;
type AllDays  = Awaited<ReturnType<typeof devApi.allDays>>;
type MatchingResult   = Awaited<ReturnType<typeof devApi.triggerMatching>>;

type ExtractionResult = {
  message: string;
  snapshot_version?: number;
  overall_confidence?: number;
  mbti_label?: string;
  big_five?: Record<string, number>;
  communication?: Record<string, number>;
  relationship?: {
    attachment_style?: string;
    conflict_style?: string;
    pace?: string;
    religious_profile?: {
      affiliation?: string | null;
      observance_level?: string | null;
      partner_requirement?: string | null;
    };
    dealbreakers?: string[];
    must_haves?: string[];
  };
  authenticity?: {
    overall: number | null;
    social_desirability: number | null;
    specificity: number | null;
    self_awareness: number | null;
    consistency: number | null;
  };
  financial?: {
    scarcity_response: number | null;
    wealth_vision: number | null;
    risk_tolerance: number | null;
  };
  self_perception?: {
    self_perception_gap: number | null;
    empathy_vs_apathy: number | null;
  };
  entities?: Array<{
    label: string;
    relationship: string;
    emotional_weight: string;
    context_note: string;
    day_extracted: number;
  }>;
  has_embedding?: boolean;
};

export default function DevPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
    if (!authLoading && user && !user.onboarding_completed) router.push("/profile");
  }, [authLoading, user, router]);

  const [allDays, setAllDays] = useState<AllDays | null>(null);
  const [preview, setPreview] = useState<DayPlan | null>(null);
  const [previewDay, setPreviewDay] = useState(1);
  const [setDayNum, setSetDayNum] = useState(1);
  const [setDayResult, setSetDayResult] = useState<string | null>(null);
  const [extraction, setExtraction] = useState<ExtractionResult | null>(null);
  const [matching, setMatching] = useState<MatchingResult | null>(null);
  const [matchableMsg, setMatchableMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);

  const setLoad = (key: string, val: boolean) =>
    setLoading((p) => ({ ...p, [key]: val }));

  const run = async <T,>(key: string, fn: () => Promise<T>): Promise<T | null> => {
    setLoad(key, true);
    setError(null);
    try {
      return await fn();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
      return null;
    } finally {
      setLoad(key, false);
    }
  };

  useEffect(() => {
    devApi.allDays()
      .then(setAllDays)
      .catch((e: Error) => setError(e.message));
  }, []);

  const loadPreview = () =>
    run("preview", async () => {
      const d = await devApi.dayPreview(previewDay);
      setPreview(d);
    });

  const doSetDay = () =>
    run("setday", async () => {
      const r = await devApi.setDay(setDayNum);
      setSetDayResult(`${r.message} — ${r.theme}`);
    });

  const doExtraction = () =>
    run("extract", async () => {
      const r = await devApi.triggerExtraction();
      setExtraction(r);
    });

  const doMatching = () =>
    run("match", async () => {
      const r = await devApi.triggerMatching();
      setMatching(r);
    });

  const doMatchable = () =>
    run("matchable", async () => {
      const r = await devApi.makeMatchable();
      setMatchableMsg(r.message);
    });

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      {(authLoading || !user || !user.onboarding_completed) ? (
        <div className="flex items-center justify-center h-64 text-gray-400">
          {authLoading ? "Loading…" : "Redirecting to login…"}
        </div>
      ) : (
      <div className="max-w-4xl mx-auto space-y-6">

        {/* Header */}
        <div className="border border-yellow-500/40 bg-yellow-500/10 rounded-xl p-4">
          <h1 className="text-xl font-bold text-yellow-400">Dev Testing Dashboard</h1>
          <p className="text-sm text-yellow-300/70 mt-1">
            Only available when <code className="bg-gray-800 px-1 rounded">DEV_MODE=true</code>
          </p>
        </div>

        {error && (
          <div className="border border-red-500/40 bg-red-500/10 rounded-xl p-4 text-red-300 text-sm">
            {error}
          </div>
        )}

        {/* 10-day overview */}
        <Card title="10-Day Plan Overview">
          {allDays ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {Object.entries(allDays).map(([day, plan]) => (
                <div key={day} className="bg-gray-800 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold bg-indigo-600 rounded px-2 py-0.5">
                      Day {day}
                    </span>
                    <span className="font-semibold text-sm">{plan.theme}</span>
                  </div>
                  <p className="text-xs text-gray-400">{plan.goal}</p>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {plan.target_traits.map((t) => (
                      <span key={t} className="text-xs bg-gray-700 rounded px-1.5 py-0.5 text-gray-300">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">Loading…</p>
          )}
        </Card>

        {/* Day Preview */}
        <Card title="Preview a Day">
          <div className="flex gap-3 items-end mb-4">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Day number</label>
              <input
                type="number"
                min={1}
                max={10}
                value={previewDay}
                onChange={(e) => setPreviewDay(Number(e.target.value))}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 w-24 text-sm focus:outline-none focus:border-indigo-500"
              />
            </div>
            <Btn loading={loading.preview} onClick={loadPreview} color="indigo">
              Preview
            </Btn>
          </div>
          {preview && (
            <div className="space-y-3">
              <Row label="Theme" value={preview.theme} />
              <Row label="Goal" value={preview.goal} />
              <div>
                <p className="text-xs text-gray-400 mb-1">Target traits</p>
                <div className="flex flex-wrap gap-1">
                  {preview.target_traits.map((t) => (
                    <span key={t} className="text-xs bg-indigo-900/60 border border-indigo-500/30 rounded px-2 py-0.5">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-1">Sample prompts</p>
                <ul className="space-y-1">
                  {preview.sample_prompts.map((p, i) => (
                    <li key={i} className="text-sm text-gray-300 bg-gray-800 rounded p-2">
                      &quot;{p}&quot;
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </Card>

        {/* Set Day */}
        <Card title="Jump to Day">
          <div className="flex gap-3 items-end mb-3">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Day number</label>
              <input
                type="number"
                min={1}
                max={10}
                value={setDayNum}
                onChange={(e) => setSetDayNum(Number(e.target.value))}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 w-24 text-sm focus:outline-none focus:border-green-500"
              />
            </div>
            <Btn loading={loading.setday} onClick={doSetDay} color="green">
              Set Day
            </Btn>
          </div>
          {setDayResult && (
            <p className="text-sm text-green-400 bg-green-400/10 border border-green-500/30 rounded-lg p-3">
              ✓ {setDayResult}
            </p>
          )}
        </Card>

        {/* Make matchable */}
        <Card title="Account Controls">
          <div className="flex gap-3 items-center">
            <Btn loading={loading.matchable} onClick={doMatchable} color="purple">
              Make Me Matchable
            </Btn>
            <span className="text-xs text-gray-400">Sets is_verified &amp; is_matchable = true</span>
          </div>
          {matchableMsg && (
            <p className="mt-3 text-sm text-purple-300 bg-purple-400/10 border border-purple-500/30 rounded-lg p-3">
              ✓ {matchableMsg}
            </p>
          )}
        </Card>

        {/* Trigger extraction */}
        <Card title="Trigger Persona Extraction">
          <div className="flex gap-3 items-center mb-3">
            <Btn loading={loading.extract} onClick={doExtraction} color="orange">
              Run Extraction Now
            </Btn>
            <span className="text-xs text-gray-400">Skips the 01:00 UTC cron</span>
          </div>
          {extraction && (
            <div className="space-y-2 text-sm">
              <p className="text-orange-300">{extraction.message}</p>
              {extraction.snapshot_version !== undefined && (
                <div className="grid grid-cols-2 gap-2">
                  <Row label="Version" value={`v${extraction.snapshot_version}`} />
                  <Row label="Confidence" value={`${((extraction.overall_confidence ?? 0) * 100).toFixed(0)}%`} />
                  <Row label="MBTI" value={extraction.mbti_label ?? "—"} />
                  <Row label="Embedding" value={extraction.has_embedding ? "✓ generated" : "✗ skipped"} />
                </div>
              )}
              {extraction.big_five && (
                <div>
                  <p className="text-xs text-gray-400 mt-2 mb-1">Big Five</p>
                  <div className="grid grid-cols-5 gap-1">
                    {Object.entries(extraction.big_five).map(([k, v]) => (
                      <div key={k} className="bg-gray-800 rounded p-2 text-center">
                        <div className="text-xs text-gray-400 capitalize">{k.slice(0, 3)}</div>
                        <div className="font-bold">{(v * 100).toFixed(0)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {extraction.relationship && (
                <div>
                  <p className="text-xs text-gray-400 mt-2 mb-1">Relationship</p>
                  <Row label="Attachment" value={extraction.relationship.attachment_style ?? "—"} />
                  <Row label="Conflict" value={extraction.relationship.conflict_style ?? "—"} />
                  <Row label="Religion" value={extraction.relationship.religious_profile?.affiliation ?? "—"} />
                  <Row label="Observance" value={extraction.relationship.religious_profile?.observance_level ?? "—"} />
                  <Row label="Partner req." value={extraction.relationship.religious_profile?.partner_requirement ?? "—"} />
                  {extraction.relationship.must_haves?.length ? (
                    <Row label="Must-haves" value={extraction.relationship.must_haves.join(", ")} />
                  ) : null}
                  {extraction.relationship.dealbreakers?.length ? (
                    <Row label="Dealbreakers" value={extraction.relationship.dealbreakers.join(", ")} />
                  ) : null}
                </div>
              )}
              {extraction.authenticity && (
                <div>
                  <p className="text-xs text-gray-400 mt-2 mb-1">Authenticity Analysis</p>
                  <div className="grid grid-cols-5 gap-1">
                    {(["overall", "social_desirability", "specificity", "self_awareness", "consistency"] as const).map((k) => {
                      const val = (extraction.authenticity as Record<string, number | null>)?.[k];
                      const label = k === "social_desirability" ? "Soc.D" : k === "self_awareness" ? "Self" : k.slice(0, 4).charAt(0).toUpperCase() + k.slice(1, 4);
                      return (
                        <div key={k} className="bg-gray-800 rounded p-2 text-center">
                          <div className="text-xs text-gray-400 capitalize">{label}</div>
                          <div className={`font-bold ${val != null && val < 0.5 ? "text-red-400" : "text-green-400"}`}>
                            {val != null ? (val * 100).toFixed(0) : "—"}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              {extraction.financial && (
                <div>
                  <p className="text-xs text-gray-400 mt-2 mb-1">Financial Character</p>
                  <div className="grid grid-cols-3 gap-1">
                    {(["scarcity_response", "wealth_vision", "risk_tolerance"] as const).map((k) => {
                      const val = (extraction.financial as Record<string, number | null>)?.[k];
                      const labels: Record<string, string> = { scarcity_response: "Scarcity", wealth_vision: "Wealth", risk_tolerance: "Risk" };
                      return (
                        <div key={k} className="bg-gray-800 rounded p-2 text-center">
                          <div className="text-xs text-gray-400">{labels[k]}</div>
                          <div className="font-bold text-amber-400">
                            {val != null ? (val * 100).toFixed(0) : "—"}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              {extraction.self_perception && (
                <div>
                  <p className="text-xs text-gray-400 mt-2 mb-1">Self-Perception & Empathy</p>
                  <div className="grid grid-cols-2 gap-1">
                    {(["self_perception_gap", "empathy_vs_apathy"] as const).map((k) => {
                      const val = (extraction.self_perception as Record<string, number | null>)?.[k];
                      const labels: Record<string, string> = { self_perception_gap: "Perception Gap", empathy_vs_apathy: "Empathy" };
                      const color = k === "self_perception_gap"
                        ? (val != null && val > 0.6 ? "text-red-400" : "text-green-400")
                        : (val != null && val < 0.4 ? "text-red-400" : "text-green-400");
                      return (
                        <div key={k} className="bg-gray-800 rounded p-2 text-center">
                          <div className="text-xs text-gray-400">{labels[k]}</div>
                          <div className={`font-bold ${color}`}>
                            {val != null ? (val * 100).toFixed(0) : "—"}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              {extraction.entities && (extraction.entities as Array<{label: string; relationship: string; emotional_weight: string; context_note: string; day_extracted: number}>).length > 0 && (
                <div>
                  <p className="text-xs text-gray-400 mt-2 mb-1">Extracted Entities ({(extraction.entities as Array<unknown>).length})</p>
                  <div className="space-y-1">
                    {(extraction.entities as Array<{label: string; relationship: string; emotional_weight: string; context_note: string; day_extracted: number}>).map((ent, i) => (
                      <div key={i} className="bg-gray-800 rounded p-2 flex items-center gap-3 text-sm">
                        <span className="font-semibold text-cyan-400">{ent.label}</span>
                        <span className="text-xs bg-gray-700 rounded px-1.5 py-0.5">{ent.relationship}</span>
                        <span className={`text-xs ${ent.emotional_weight === "high" ? "text-red-400" : ent.emotional_weight === "medium" ? "text-yellow-400" : "text-gray-400"}`}>
                          {ent.emotional_weight}
                        </span>
                        {ent.context_note && <span className="text-xs text-gray-500 truncate">{ent.context_note}</span>}
                        <span className="text-xs text-gray-600 ml-auto">Day {ent.day_extracted}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>

        {/* Trigger matching */}
        <Card title="Trigger Matching Engine">
          <div className="flex gap-3 items-center mb-3">
            <Btn loading={loading.match} onClick={doMatching} color="pink">
              Run Matching Now
            </Btn>
            <span className="text-xs text-gray-400">Skips the 02:00 UTC cron</span>
          </div>
          {matching && (
            <div className="space-y-2 text-sm">
              <p className="text-pink-300">{matching.message}</p>
              {matching.run_date && (
                <div className="grid grid-cols-2 gap-2">
                  <Row label="Run date" value={matching.run_date} />
                  <Row label="Algorithm" value={matching.algorithm_ver ?? "—"} />
                  <Row label="Eligible users" value={String(matching.total_users_eligible ?? 0)} />
                  <Row label="Matches created" value={String(matching.total_matches_created ?? 0)} />
                </div>
              )}
            </div>
          )}
        </Card>

      </div>
      )}
    </div>
  );
}

// ─── tiny shared components ───────────────────────────────────────────────────

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border border-gray-700 bg-gray-900 rounded-xl p-5">
      <h2 className="font-semibold text-gray-200 mb-4">{title}</h2>
      {children}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2 text-sm">
      <span className="text-gray-400 w-28 shrink-0">{label}</span>
      <span className="text-gray-100">{value}</span>
    </div>
  );
}

const COLOR_CLASSES: Record<string, string> = {
  indigo: "bg-indigo-600 hover:bg-indigo-500",
  green:  "bg-green-700  hover:bg-green-600",
  purple: "bg-purple-700 hover:bg-purple-600",
  orange: "bg-orange-600 hover:bg-orange-500",
  pink:   "bg-pink-700   hover:bg-pink-600",
};

function Btn({
  children,
  onClick,
  loading,
  color,
}: {
  children: React.ReactNode;
  onClick: () => void;
  loading?: boolean;
  color: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={`${COLOR_CLASSES[color] ?? "bg-gray-600"} disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors`}
    >
      {loading ? "…" : children}
    </button>
  );
}
