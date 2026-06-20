"use client";

import { useState, useEffect } from "react";
import { Globe, Brain, Clock, Shield, Bell } from "lucide-react";
import SourcesPage from "@/app/sources/page";
import KeywordsPage from "@/app/keywords/page";
import LLMConfigsPage from "@/components/settings/llm-configs";
import SettingsPage from "@/app/settings/page";
import AlertRulesPage from "@/components/settings/alert-rules";
import { generalApi } from "@/lib/api";

type TabId = "general" | "sources" | "ai" | "crawler" | "rules";

export default function AdminSettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>("general");

  // General Settings States
  const [pinEnabled, setPinEnabled] = useState(true);
  const [pinCode, setPinCode] = useState("2026");
  const [adminPinCode, setAdminPinCode] = useState("LT2026");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    async function fetchGeneral() {
      try {
        const res = await generalApi.getSettings();
        if (res) {
          setPinEnabled(res.pin_enabled !== false);
          setPinCode((res.pin_code as string) || "2026");
          setAdminPinCode((res.admin_pin_code as string) || "LT2026");
        }
      } catch (err) {
        console.error("Failed to load settings:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchGeneral();
  }, []);

  const handleSaveGeneral = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMsg(null);

    try {
      await generalApi.updateSettings({
        pin_enabled: pinEnabled,
        pin_code: pinCode,
        admin_pin_code: adminPinCode,
      });
      setMsg({ type: "success", text: "Đã lưu cài đặt chung thành công!" });
      setTimeout(() => setMsg(null), 5000);
    } catch (err) {
      console.error("Failed to save settings:", err);
      setMsg({ type: "error", text: "Đã xảy ra lỗi khi lưu cài đặt." });
    } finally {
      setSaving(false);
    }
  };

  const tabs = [
    { id: "general", label: "Cài đặt chung", icon: Shield },
    { id: "sources", label: "Nguồn tin & Từ khóa", icon: Globe },
    { id: "ai", label: "Cấu hình AI", icon: Brain },
    { id: "crawler", label: "Cấu hình quét", icon: Clock },
    { id: "rules", label: "Quy tắc cảnh báo", icon: Bell },
  ];

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold text-[hsl(var(--foreground))]">Cấu hình Hệ thống</h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Quản lý toàn bộ thông số hoạt động, kết nối AI và thu thập dữ liệu của LTIA Radar.
        </p>
      </div>

      {/* Tabs list */}
      <div className="flex border-b border-[hsl(var(--border))] overflow-x-auto gap-2">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabId)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all -mb-px whitespace-nowrap ${
                isActive
                  ? "border-cyan-500 text-cyan-600 dark:text-cyan-400 font-semibold"
                  : "border-transparent text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab contents */}
      <div className="mt-4">
        {activeTab === "general" && (
          <div className="space-y-6 max-w-xl">
            {loading ? (
              <div className="flex justify-center py-12">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
              </div>
            ) : (
              <form onSubmit={handleSaveGeneral} className="glass-card rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-6 space-y-6">
                <div className="border-b border-[hsl(var(--border))] pb-4">
                  <h2 className="text-lg font-semibold text-[hsl(var(--foreground))]">Bảo mật & Truy cập</h2>
                  <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">Cấu hình mã PIN truy cập cho trang chủ.</p>
                </div>

                {/* Toggle PIN Enabled */}
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-sm font-medium text-[hsl(var(--foreground))] block">Yêu cầu PIN khi vào trang chủ</label>
                    <span className="text-xs text-[hsl(var(--muted-foreground))]">Bắt buộc người dùng nhập PIN truy cập (mặc định: 2026) khi truy cập hệ thống công cộng.</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setPinEnabled(!pinEnabled)}
                    className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      pinEnabled ? "bg-cyan-500" : "bg-[hsl(var(--muted))]"
                    }`}
                  >
                    <span
                      className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        pinEnabled ? "translate-x-5" : "translate-x-0"
                      }`}
                    />
                  </button>
                </div>

                {/* PIN Code Input */}
                {pinEnabled && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-[hsl(var(--foreground))]">Mã PIN trang chủ</label>
                    <input
                      type="text"
                      maxLength={10}
                      value={pinCode}
                      onChange={(e) => setPinCode(e.target.value)}
                      placeholder="2026"
                      className="w-48 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))]/50 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                      required
                    />
                  </div>
                )}

                <div className="space-y-2">
                  <label className="text-sm font-medium text-[hsl(var(--foreground))]">Mã PIN Quản trị (Admin)</label>
                  <input
                    type="text"
                    maxLength={20}
                    value={adminPinCode}
                    onChange={(e) => setAdminPinCode(e.target.value)}
                    placeholder="LT2026"
                    className="w-48 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))]/50 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                    required
                  />
                  <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Bảo vệ quyền truy cập vào trang thiết lập này.</p>
                </div>

                {msg && (
                  <div className={`flex items-start gap-2.5 rounded-lg border p-3.5 text-xs ${
                    msg.type === "success"
                      ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                      : "bg-rose-500/10 border-rose-500/30 text-rose-400"
                  }`}>
                    <span>{msg.text}</span>
                  </div>
                )}

                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    disabled={saving}
                    className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cyan-500/25 hover:brightness-110 hover:shadow-cyan-500/35 transition-all disabled:opacity-50"
                  >
                    {saving && <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />}
                    Lưu cài đặt
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {activeTab === "sources" && (
          <div className="space-y-12">
            <SourcesPage />
            <div className="border-t border-[hsl(var(--border))] pt-6">
              <KeywordsPage />
            </div>
          </div>
        )}

        {activeTab === "ai" && (
          <div>
            <LLMConfigsPage />
          </div>
        )}

        {activeTab === "crawler" && (
          <div>
            <SettingsPage />
          </div>
        )}

        {activeTab === "rules" && (
          <div>
            <AlertRulesPage />
          </div>
        )}
      </div>
    </div>
  );
}
