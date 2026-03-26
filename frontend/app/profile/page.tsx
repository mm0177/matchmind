"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { authApi } from "@/lib/api";
import { STATE_NAMES, getCities } from "@/lib/india-locations";

export default function ProfilePage() {
  const { user, loading, refreshUser } = useAuth();
  const router = useRouter();

  const [form, setForm] = useState({
    display_name: "",
    gender: "other",
    preferred_gender: "any",
    birth_date: "",
    state: "",
    city: "",
    age_pref_max: 45,
    is_open_to_long_distance: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cities = useMemo(() => getCities(form.state), [form.state]);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
      return;
    }
    if (!loading && user?.onboarding_completed) {
      router.replace("/chat");
      return;
    }
    if (user) {
      const [city = "", state = ""] = (user.location || "").split(",").map((x) => x.trim());
      setForm((prev) => ({
        ...prev,
        display_name: user.display_name || prev.display_name,
        gender: user.gender || prev.gender,
        preferred_gender: user.preferred_gender || prev.preferred_gender,
        birth_date: user.birth_date || prev.birth_date,
        state,
        city,
        age_pref_max: user.age_pref_max || prev.age_pref_max,
        is_open_to_long_distance: user.is_open_to_long_distance || false,
      }));
    }
  }, [loading, router, user]);

  function setField<K extends keyof typeof form>(field: K, value: (typeof form)[K]) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!form.display_name.trim()) {
      setError("Display name is required.");
      return;
    }
    if (!form.birth_date) {
      setError("Date of birth is required.");
      return;
    }
    if (!form.state || !form.city) {
      setError("Please select your state and city.");
      return;
    }

    setSubmitting(true);
    try {
      await authApi.completeProfile({
        display_name: form.display_name.trim(),
        gender: form.gender,
        preferred_gender: form.preferred_gender,
        birth_date: form.birth_date,
        location: `${form.city}, ${form.state}`,
        age_pref_min: 18,
        age_pref_max: form.age_pref_max,
        is_open_to_long_distance: form.is_open_to_long_distance,
      });
      await refreshUser();
      router.replace("/chat");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not save profile.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-950">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
      </div>
    );
  }

  const inputClass =
    "w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-white placeholder-gray-500 outline-none transition focus:border-purple-500 focus:ring-1 focus:ring-purple-500";
  const labelClass = "mb-1.5 block text-sm font-medium text-gray-300";

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-950 px-4 py-16">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-white">Complete your profile</h1>
          <p className="mt-2 text-sm text-gray-400">
            One-time setup before you start chatting
          </p>
        </div>

        <form onSubmit={handleSubmit} className="rounded-2xl border border-gray-800 bg-gray-900 p-8 shadow-xl">
          {error && (
            <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <div className="mb-4">
            <label htmlFor="display_name" className={labelClass}>Display Name</label>
            <input
              id="display_name"
              type="text"
              required
              value={form.display_name}
              onChange={(e) => setField("display_name", e.target.value)}
              className={inputClass}
            />
          </div>

          <div className="mb-4">
            <label htmlFor="birth_date" className={labelClass}>Date of Birth</label>
            <input
              id="birth_date"
              type="date"
              required
              value={form.birth_date}
              onChange={(e) => setField("birth_date", e.target.value)}
              className={inputClass}
            />
          </div>

          <div className="mb-4">
            <label htmlFor="gender" className={labelClass}>I identify as</label>
            <select
              id="gender"
              value={form.gender}
              onChange={(e) => setField("gender", e.target.value)}
              className={inputClass}
            >
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other / Prefer not to say</option>
            </select>
          </div>

          <div className="mb-6">
            <label htmlFor="preferred_gender" className={labelClass}>I am interested in</label>
            <select
              id="preferred_gender"
              value={form.preferred_gender}
              onChange={(e) => setField("preferred_gender", e.target.value)}
              className={inputClass}
            >
              <option value="any">Anyone</option>
              <option value="male">Men</option>
              <option value="female">Women</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div className="mb-4">
            <label htmlFor="state" className={labelClass}>State / UT</label>
            <select
              id="state"
              value={form.state}
              onChange={(e) => {
                setField("state", e.target.value);
                setField("city", "");
              }}
              className={inputClass}
            >
              <option value="">Select state...</option>
              {STATE_NAMES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {form.state && (
            <div className="mb-4">
              <label htmlFor="city" className={labelClass}>City</label>
              <select
                id="city"
                value={form.city}
                onChange={(e) => setField("city", e.target.value)}
                className={inputClass}
              >
                <option value="">Select city...</option>
                {cities.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          )}

          <div className="mb-6">
            <label className={labelClass}>
              Match with ages up to <span className="font-semibold text-purple-400">{form.age_pref_max} yrs</span>
            </label>
            <div className="mt-2 flex items-center gap-3">
              <span className="text-xs text-gray-500">18</span>
              <input
                type="range"
                min={18}
                max={80}
                value={form.age_pref_max}
                onChange={(e) => setField("age_pref_max", Number(e.target.value))}
                className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-gray-700 accent-purple-500"
              />
              <span className="text-xs text-gray-500">80</span>
            </div>
          </div>

          <div className="mb-6 rounded-lg border border-gray-700 bg-gray-800/60 px-4 py-3">
            <label className="flex cursor-pointer items-center justify-between gap-3 text-sm text-gray-200">
              <span>Open to long-distance matches</span>
              <input
                type="checkbox"
                checked={form.is_open_to_long_distance}
                onChange={(e) => setField("is_open_to_long_distance", e.target.checked)}
                className="h-4 w-4 accent-purple-500"
              />
            </label>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-full bg-purple-600 py-2.5 text-sm font-semibold text-white shadow transition hover:bg-purple-500 disabled:opacity-50"
          >
            {submitting ? "Saving profile..." : "Save and Continue"}
          </button>
        </form>
      </div>
    </div>
  );
}
