"use client";

import { useEffect, useState } from "react";
import {
  Plus,
  Trash2,
  Bell,
  TestTube,
  ToggleLeft,
  ToggleRight,
  Check,
  X,
} from "lucide-react";
import { alertRulesApi } from "@/lib/api";

interface AlertRule {
  _id: string;
  rule_name: string;
  condition_query: Record<string, string>;
  telegram_chat_id: string;
  is_active: boolean;
  created_at: string;
}

export default function SettingsPage() {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{
    id: string;
    success: boolean;
  } | null>(null);
  const [formData, setFormData] = useState({
    rule_name: "",
    impact_level: "CRITICAL",
    sentiment: "",
    telegram_chat_id: "",
  });

  const fetchRules = async () => {
    try {
      const res = await alertRulesApi.list();
      setRules((res.data as AlertRule[]) || []);
    } catch (err) {
      console.error("Failed to load rules:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const condition_query: Record<string, string> = {};
    if (formData.impact_level) condition_query.impact_level = formData.impact_level;
    if (formData.sentiment) condition_query.sentiment = formData.sentiment;

    try {
      await alertRulesApi.create({
        rule_name: formData.rule_name,
        condition_query,
        telegram_chat_id: formData.telegram_chat_id,
      });
      setShowForm(false);
      setFormData({
        rule_name: "",
        impact_level: "CRITICAL",
        sentiment: "",
        telegram_chat_id: "",
      });
      fetchRules();
    } catch (err) {
      console.error("Failed to create rule:", err);
    }
  };

  const handleTest = async (ruleId: string) => {
    setTestingId(ruleId);
    setTestResult(null);
    try {
      await alertRulesApi.test(ruleId);
      setTestResult({ id: ruleId, success: true });
    } catch {
      setTestResult({ id: ruleId, success: false });
    } finally {
      setTestingId(null);
      setTimeout(() => setTestResult(null), 3000);
    }
  };

  const handleToggle = async (rule: AlertRule) => {
    try {
      await alertRulesApi.update(rule._id, { is_active: !rule.is_active });
      fetchRules();
    } catch (err) {
      console.error("Failed to toggle rule:", err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Xóa quy tắc cảnh báo này?")) return;
    try {
      await alertRulesApi.delete(id);
      fetchRules();
    } catch (err) {
      console.error("Failed to delete rule:", err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Quy tắc Cảnh báo</h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Cấu hình điều kiện gửi thông báo Telegram khi phát hiện tin tức
            khớp quy tắc
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2.5 text-sm font-medium text-white shadow-lg shadow-cyan-500/20 transition-all hover:shadow-cyan-500/30 hover:brightness-110"
        >
          <Plus className="h-4 w-4" />
          Thêm quy tắc
        </button>
      </div>

      {/* Create Rule Form */}
      {showForm && (
        <form
          onSubmit={handleCreate}
          className="glass-card space-y-4 rounded-xl p-5"
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-[hsl(var(--muted-foreground))]">
                Tên quy tắc
              </label>
              <input
                type="text"
                value={formData.rule_name}
                onChange={(e) =>
                  setFormData({ ...formData, rule_name: e.target.value })
                }
                placeholder='VD: "Cảnh báo sự cố nghiêm trọng"'
                className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-white placeholder:text-[hsl(var(--muted-foreground))] focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                required
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-[hsl(var(--muted-foreground))]">
                Telegram Chat ID
              </label>
              <input
                type="text"
                value={formData.telegram_chat_id}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    telegram_chat_id: e.target.value,
                  })
                }
                placeholder="-1001234567890"
                className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-white placeholder:text-[hsl(var(--muted-foreground))] focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-[hsl(var(--muted-foreground))]">
                Mức độ ảnh hưởng
              </label>
              <select
                value={formData.impact_level}
                onChange={(e) =>
                  setFormData({ ...formData, impact_level: e.target.value })
                }
                className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
              >
                <option value="">Tất cả</option>
                <option value="CRITICAL">CRITICAL (Nguy kịch)</option>
                <option value="HIGH">HIGH (Cao)</option>
                <option value="MEDIUM">MEDIUM (Trung bình)</option>
                <option value="LOW">LOW (Thấp)</option>
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-[hsl(var(--muted-foreground))]">
                Sắc thái
              </label>
              <select
                value={formData.sentiment}
                onChange={(e) =>
                  setFormData({ ...formData, sentiment: e.target.value })
                }
                className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
              >
                <option value="">Tất cả</option>
                <option value="NEGATIVE">NEGATIVE (Tiêu cực)</option>
                <option value="POSITIVE">POSITIVE (Tích cực)</option>
                <option value="NEUTRAL">NEUTRAL (Trung lập)</option>
              </select>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500"
            >
              Tạo quy tắc
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-lg bg-[hsl(var(--secondary))] px-4 py-2 text-sm font-medium text-[hsl(var(--muted-foreground))] hover:text-white"
            >
              Hủy
            </button>
          </div>
        </form>
      )}

      {/* Rules List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
        </div>
      ) : rules.length === 0 ? (
        <div className="glass-card rounded-xl py-16 text-center">
          <Bell className="mx-auto h-10 w-10 text-[hsl(var(--muted-foreground))]" />
          <p className="mt-3 text-sm text-[hsl(var(--muted-foreground))]">
            Chưa có quy tắc cảnh báo. Tạo quy tắc để nhận thông báo Telegram.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {rules.map((rule) => (
            <div
              key={rule._id}
              className="glass-card flex items-center justify-between rounded-xl p-5"
            >
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Bell className="h-4 w-4 text-cyan-400" />
                  <h3 className="text-sm font-semibold text-white">
                    {rule.rule_name}
                  </h3>
                  {!rule.is_active && (
                    <span className="rounded-md bg-gray-700 px-2 py-0.5 text-[10px] text-gray-400">
                      Tạm dừng
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
                  <span>Điều kiện:</span>
                  {Object.entries(rule.condition_query).map(([key, val]) => (
                    <span
                      key={key}
                      className="rounded-md bg-[hsl(var(--secondary))] px-2 py-0.5"
                    >
                      {key} = {val}
                    </span>
                  ))}
                  <span className="ml-2">
                    → Chat ID: {rule.telegram_chat_id}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-1">
                {/* Test Button */}
                <button
                  onClick={() => handleTest(rule._id)}
                  disabled={testingId === rule._id}
                  className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium text-amber-400 transition-colors hover:bg-amber-500/10 disabled:opacity-50"
                >
                  {testingId === rule._id ? (
                    <div className="h-3 w-3 animate-spin rounded-full border border-amber-400 border-t-transparent" />
                  ) : testResult?.id === rule._id ? (
                    testResult.success ? (
                      <Check className="h-3 w-3 text-emerald-400" />
                    ) : (
                      <X className="h-3 w-3 text-red-400" />
                    )
                  ) : (
                    <TestTube className="h-3 w-3" />
                  )}
                  Test
                </button>

                {/* Toggle */}
                <button
                  onClick={() => handleToggle(rule)}
                  className="rounded-lg p-1.5 transition-colors hover:bg-[hsl(var(--secondary))]"
                >
                  {rule.is_active ? (
                    <ToggleRight className="h-5 w-5 text-emerald-400" />
                  ) : (
                    <ToggleLeft className="h-5 w-5 text-gray-500" />
                  )}
                </button>

                {/* Delete */}
                <button
                  onClick={() => handleDelete(rule._id)}
                  className="rounded-lg p-1.5 text-gray-500 transition-colors hover:bg-red-500/10 hover:text-red-400"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
