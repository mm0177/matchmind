"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useAuth as useClerkAuth, useClerk } from "@clerk/nextjs";
import { authApi, User, setAuthTokenProvider } from "@/lib/api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  refreshUser: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { isLoaded, isSignedIn, getToken } = useClerkAuth();
  const { signOut } = useClerk();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    if (!isLoaded) {
      setLoading(true);
      return;
    }
    if (!isSignedIn) {
      setAuthTokenProvider(null);
      setUser(null);
      setLoading(false);
      return;
    }

    setAuthTokenProvider(async () => {
      const template = process.env.NEXT_PUBLIC_CLERK_JWT_TEMPLATE;
      if (template) {
        try {
          const scoped = await getToken({ template });
          if (scoped) return scoped;
        } catch {
          // fallback to default token below
        }
      }
      try {
        return await getToken();
      } catch {
        return null;
      }
    });

    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [getToken, isLoaded, isSignedIn]);

  useEffect(() => { loadUser(); }, [loadUser]);

  const logout = () => {
    void signOut({ redirectUrl: "/login" });
  };

  return (
    <AuthContext.Provider value={{ user, loading, refreshUser: loadUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
