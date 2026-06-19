"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { generalApi } from "@/lib/api";
import { Lock, Radar } from "lucide-react";

export function ClientLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "";
  const isAdminPath = pathname.startsWith("/admin");

  const [settings, setSettings] = useState<{ pin_enabled: boolean } | null>(null);
  const [loading, setLoading] = useState(true);

  // Authentication states
  const [userVerified, setUserVerified] = useState(false);
  const [adminVerified, setAdminVerified] = useState(false);

  // PIN input form state
  const [pin, setPin] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState("");

  const fetchGeneralSettings = async () => {
    try {
      const res = await generalApi.getSettings();
      setSettings(res as any);
    } catch (err) {
      console.error("Failed to load settings:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGeneralSettings();

    // Check localStorage on mount
    const isUserAuth = localStorage.getItem("homepage_pin_verified") === "true";
    const isAdminAuth = localStorage.getItem("admin_pin_verified") === "true";
    setUserVerified(isUserAuth);
    setAdminVerified(isAdminAuth);
  }, []);

  const handleVerifyPin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setVerifying(true);

    try {
      const type = isAdminPath ? "admin" : "user";
      const res = await generalApi.verifyPin(pin, type);
      if (res.success) {
        if (isAdminPath) {
          localStorage.setItem("admin_pin_verified", "true");
          setAdminVerified(true);
        } else {
          localStorage.setItem("homepage_pin_verified", "true");
          setUserVerified(true);
        }
        setPin("");
      } else {
        setError(res.message || "Mã PIN không chính xác.");
      }
    } catch (err: any) {
      setError(err.message || "Lỗi kết nối máy chủ.");
    } finally {
      setVerifying(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[hsl(var(--background))]">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Đang kiểm tra bảo mật...</p>
        </div>
      </div>
    );
  }

  // Determine if active path requires authentication
  const needsAdminAuth = isAdminPath && !adminVerified;
  const needsUserAuth = !isAdminPath && settings?.pin_enabled && !userVerified;

  if (needsAdminAuth || needsUserAuth) {
    return (
      <div className="flex h-screen items-center justify-center bg-[hsl(var(--background))] px-4 transition-colors duration-200">
        <div className="glass-card w-full max-w-md rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-8 shadow-2xl space-y-6">
          <div className="flex flex-col items-center text-center space-y-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/20">
              <Radar className="h-6 w-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-[hsl(var(--foreground))]">
                {isAdminPath ? "LTIA RADAR — ADMIN" : "LTIA RADAR SECURITY"}
              </h2>
              <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
                {isAdminPath
                  ? "Vui lòng nhập mã PIN quản trị viên để tiếp tục"
                  : "Hệ thống yêu cầu mã PIN truy cập"}
              </p>
            </div>
          </div>

          <form onSubmit={handleVerifyPin} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide flex items-center gap-1">
                <Lock className="h-3.5 w-3.5 text-cyan-500" />
                Mã PIN truy cập
              </label>
              <input
                type="password"
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                placeholder="••••••"
                className="w-full text-center tracking-widest text-lg font-bold rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-4 py-3 text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))]/40 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                required
                autoFocus
              />
            </div>

            {error && (
              <p className="text-center text-xs font-medium text-rose-500">{error}</p>
            )}

            <button
              type="submit"
              disabled={verifying}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-cyan-500/25 hover:brightness-110 hover:shadow-cyan-500/35 transition-all disabled:opacity-50"
            >
              {verifying ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                "Xác minh"
              )}
            </button>
          </form>

          {!isAdminPath && (
            <div className="text-center">
              <a
                href="/admin"
                className="text-xs text-cyan-500 hover:underline"
              >
                Truy cập khu vực Quản trị
              </a>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Render main layout shell once authenticated
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="lg:ml-64 flex-1 min-w-0">
        <Header />
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}
