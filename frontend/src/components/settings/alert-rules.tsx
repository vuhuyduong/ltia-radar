"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, ToggleLeft, ToggleRight, Bell, Save, Play, X } from "lucide-react";
import { alertRulesApi } from "@/lib/api";

interface AlertRule {
  _id: string;
  rule_name: string;
  condition_query: Record<string, any>;
  telegram_chat_id: string;
  is_active: boolean;
  created_at?: string;
}

const CATEGORIES = ["Tiến độ", "Kỹ thuật", "Môi trường", "Đấu thầu", "Bồi thường/GPMB", "Pháp lý", "Khác"];

export default function AlertRulesPage() {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null);

  // Form inputs
  const [ruleName, setRuleName] = useState("");
  const [telegramChatId, setTelegramChatId] = useState("");
  const [isActive, setIsActive] = useState(true);
  
  // Conditions
  const [selectedImpact, setSelectedImpact] = useState("");
  const [selectedSentiment, setSelectedSentiment] = useState("");
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [selectedRumor, setSelectedRumor] = useState("all"); // "all" | "rumor" | "no_rumor"

  // Feedback states
  const [submitting, setSubmitting] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchRules = async () => {
    try {
      const res = await alertRulesApi.list();
      setRules((res.data as AlertRule[]) || []);
    } catch (err) {
      console.error("Failed to fetch alert rules:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const openAddForm = () => {
    setEditingRule(null);
    setRuleName("");
    setTelegramChatId("");
    setIsActive(true);
    setSelectedImpact("");
    setSelectedSentiment("");
    setSelectedCategories([]);
    setSelectedRumor("all");
    setShowForm(true);
  };

  const openEditForm = (rule: AlertRule) => {
    setEditingRule(rule);
    setRuleName(rule.rule_name);
    setTelegramChatId(rule.telegram_chat_id);
    setIsActive(rule.is_active);
    
    const cond = rule.condition_query || {};
    setSelectedImpact(cond.impact_level || "");
    setSelectedSentiment(cond.sentiment || "");
    
    if (Array.isArray(cond.category)) {
      setSelectedCategories(cond.category);
    } else if (typeof cond.category === "string") {
      setSelectedCategories([cond.category]);
    } else {
      setSelectedCategories([]);
    }
    
    if (cond.is_rumor === true) {
      setSelectedRumor("rumor");
    } else if (cond.is_rumor === false) {
      setSelectedRumor("no_rumor");
    } else {
      setSelectedRumor("all");
    }
    
    setShowForm(true);
  };

  const handleToggleCategory = (cat: string) => {
    setSelectedCategories(prev => 
      prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]
    );
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruleName.trim()) return;
    if (!telegramChatId.trim()) return;

    setSubmitting(true);
    setFeedback(null);

    const conditionQuery: Record<string, any> = {};
    if (selectedImpact) conditionQuery.impact_level = selectedImpact;
    if (selectedSentiment) conditionQuery.sentiment = selectedSentiment;
    if (selectedCategories.length > 0) conditionQuery.category = selectedCategories;
    if (selectedRumor !== "all") conditionQuery.is_rumor = selectedRumor === "rumor";

    const payload = {
      rule_name: ruleName.trim(),
      telegram_chat_id: telegramChatId.trim(),
      condition_query: conditionQuery,
      is_active: isActive,
    };

    try {
      if (editingRule) {
        await alertRulesApi.update(editingRule._id, payload);
        setFeedback({ type: "success", text: "Cập nhật quy tắc cảnh báo thành công!" });
      } else {
        await alertRulesApi.create(payload);
        setFeedback({ type: "success", text: "Thêm quy tắc cảnh báo mới thành công!" });
      }
      setTimeout(() => {
        setShowForm(false);
        setFeedback(null);
      }, 1500);
      fetchRules();
    } catch (err) {
      console.error("Failed to save alert rule:", err);
      setFeedback({ type: "error", text: "Không thể lưu quy tắc cảnh báo. Kiểm tra kết nối." });
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleActive = async (rule: AlertRule) => {
    try {
      await alertRulesApi.update(rule._id, { is_active: !rule.is_active });
      fetchRules();
    } catch (err) {
      console.error("Failed to toggle alert rule:", err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Bạn có chắc muốn xóa quy tắc cảnh báo này?")) return;
    try {
      await alertRulesApi.delete(id);
      fetchRules();
    } catch (err) {
      console.error("Failed to delete alert rule:", err);
    }
  };

  const handleTest = async (ruleId: string) => {
    setTestingId(ruleId);
    try {
      await alertRulesApi.test(ruleId);
      alert("Đã gửi tin nhắn test thành công tới Telegram Chat ID của luật này!");
    } catch (err) {
      console.error("Failed to run test alert:", err);
      alert("Gửi tin nhắn test thất bại. Hãy kiểm tra Bot Token trong .env và Chat ID của luật.");
    } finally {
      setTestingId(null);
    }
  };

  const getConditionSummary = (cond: Record<string, any>) => {
    const summary: string[] = [];
    if (cond.impact_level) summary.push(`Mức độ: ${cond.impact_level}`);
    if (cond.sentiment) summary.push(`Sắc thái: ${cond.sentiment}`);
    if (cond.category) {
      const cats = Array.isArray(cond.category) ? cond.category.join(", ") : cond.category;
      summary.push(`Danh mục: [${cats}]`);
    }
    if (cond.is_rumor !== undefined) summary.push(cond.is_rumor ? "Chỉ tin đồn" : "Chính thống");
    return summary.length > 0 ? summary.join(" AND ") : "Gửi tất cả bài viết";
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-[hsl(var(--foreground))]">Quy tắc cảnh báo (Alert Rules)</h2>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Thiết lập điều kiện lọc và tự động gửi tin nhắn báo động tới Telegram
          </p>
        </div>
        {!showForm && (
          <button
            onClick={openAddForm}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cyan-500/20 transition-all hover:shadow-cyan-500/30 hover:brightness-110"
          >
            <Plus className="h-4 w-4" />
            Thêm quy tắc
          </button>
        )}
      </div>

      {/* Editor Form Modal/Section */}
      {showForm && (
        <form onSubmit={handleSave} className="glass-card rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-6 space-y-6 max-w-2xl">
          <div className="flex items-center justify-between border-b border-[hsl(var(--border))] pb-4">
            <h3 className="text-lg font-semibold text-[hsl(var(--foreground))]">
              {editingRule ? "Sửa quy tắc cảnh báo" : "Thêm quy tắc cảnh báo mới"}
            </h3>
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg p-1 text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--secondary))]">
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Rule Name */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-[hsl(var(--foreground))]">Tên quy tắc</label>
              <input
                type="text"
                value={ruleName}
                onChange={(e) => setRuleName(e.target.value)}
                placeholder="VD: Cảnh báo tin rủi ro khẩn cấp"
                className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none"
                required
              />
            </div>

            {/* Telegram Chat ID */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-[hsl(var(--foreground))]">Telegram Chat ID (nhóm hoặc cá nhân)</label>
              <input
                type="text"
                value={telegramChatId}
                onChange={(e) => setTelegramChatId(e.target.value)}
                placeholder="VD: -100123456789 hoặc 987654321"
                className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none"
                required
              />
            </div>
          </div>

          {/* Condition Builder (AND query builder) */}
          <div className="border border-[hsl(var(--border))] rounded-xl p-4 space-y-4 bg-[hsl(var(--secondary))]/30">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
              Điều kiện kích hoạt cảnh báo (Tất cả điều kiện chọn phải thỏa mãn - AND logic)
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Impact Level Selection */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[hsl(var(--foreground))]">Mức độ rủi ro</label>
                <select
                  value={selectedImpact}
                  onChange={(e) => setSelectedImpact(e.target.value)}
                  className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-3 py-2 text-xs text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none"
                >
                  <option value="">Tất cả mức độ</option>
                  <option value="CRITICAL">CRITICAL</option>
                  <option value="HIGH">HIGH</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="LOW">LOW</option>
                </select>
              </div>

              {/* Sentiment Selection */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[hsl(var(--foreground))]">Sắc thái tin bài</label>
                <select
                  value={selectedSentiment}
                  onChange={(e) => setSelectedSentiment(e.target.value)}
                  className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-3 py-2 text-xs text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none"
                >
                  <option value="">Tất cả sắc thái</option>
                  <option value="NEGATIVE">Tiêu cực (NEGATIVE)</option>
                  <option value="POSITIVE">Tích cực (POSITIVE)</option>
                  <option value="NEUTRAL">Trung lập (NEUTRAL)</option>
                </select>
              </div>

              {/* Is Rumor Selection */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[hsl(var(--foreground))]">Tính xác thực</label>
                <select
                  value={selectedRumor}
                  onChange={(e) => setSelectedRumor(e.target.value)}
                  className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-3 py-2 text-xs text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none"
                >
                  <option value="all">Tất cả bài viết</option>
                  <option value="rumor">Chỉ tin đồn (is_rumor == true)</option>
                  <option value="no_rumor">Không phải tin đồn (is_rumor == false)</option>
                </select>
              </div>
            </div>

            {/* Categories Selection */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-[hsl(var(--foreground))] block">Lọc theo phân loại danh mục (Khớp bất kỳ mục nào được tích)</label>
              <div className="flex flex-wrap gap-2">
                {CATEGORIES.map((cat) => {
                  const isChecked = selectedCategories.includes(cat);
                  return (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => handleToggleCategory(cat)}
                      className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-all duration-200 ${
                        isChecked
                          ? "bg-cyan-600 border-cyan-500 text-white"
                          : "bg-[hsl(var(--card))] border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] hover:border-cyan-500/50"
                      }`}
                    >
                      {cat}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Active status */}
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-[hsl(var(--foreground))] block">Kích hoạt quy tắc</label>
              <span className="text-xs text-[hsl(var(--muted-foreground))]">Bật để hệ thống tự động kiểm tra và gửi cảnh báo khi rà quét tin.</span>
            </div>
            <button
              type="button"
              onClick={() => setIsActive(!isActive)}
              className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                isActive ? "bg-cyan-500" : "bg-[hsl(var(--muted))]"
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow transition duration-200 ease-in-out ${
                  isActive ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
          </div>

          {feedback && (
            <div className={`p-3.5 rounded-lg border text-xs ${
              feedback.type === "success"
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                : "bg-rose-500/10 border-rose-500/30 text-rose-400"
            }`}>
              {feedback.text}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-xl bg-[hsl(var(--secondary))] px-5 py-2.5 text-sm font-semibold text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:brightness-110 shadow-lg shadow-cyan-500/25 transition-all"
            >
              <Save className="h-4 w-4" />
              Lưu cấu hình
            </button>
          </div>
        </form>
      )}

      {/* Rules list */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
        </div>
      ) : rules.length === 0 ? (
        <div className="glass-card rounded-xl py-16 text-center">
          <Bell className="mx-auto h-10 w-10 text-[hsl(var(--muted-foreground))]" />
          <p className="mt-3 text-sm text-[hsl(var(--muted-foreground))]">
            Chưa có quy tắc cảnh báo nào được cấu hình.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden glass-card rounded-xl border border-[hsl(var(--border))]">
          <table className="data-table w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wider text-[hsl(var(--muted-foreground))] border-b border-[hsl(var(--border))]">
                <th className="px-5 py-3 font-medium">Tên quy tắc</th>
                <th className="px-5 py-3 font-medium">Telegram Chat ID</th>
                <th className="px-5 py-3 font-medium">Điều kiện kích hoạt (AND Query)</th>
                <th className="px-5 py-3 font-medium text-center">Trạng thái</th>
                <th className="px-5 py-3 font-medium text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[hsl(var(--border))]">
              {rules.map((rule) => (
                <tr key={rule._id} className="hover:bg-[hsl(var(--accent))]/5 transition-colors">
                  <td className="px-5 py-4 font-semibold text-[hsl(var(--foreground))]">
                    {rule.rule_name}
                  </td>
                  <td className="px-5 py-4 text-xs font-mono text-[hsl(var(--muted-foreground))]">
                    {rule.telegram_chat_id}
                  </td>
                  <td className="px-5 py-4 text-xs text-[hsl(var(--muted-foreground))] max-w-sm break-words whitespace-normal leading-relaxed">
                    {getConditionSummary(rule.condition_query)}
                  </td>
                  <td className="px-5 py-4 text-center">
                    <button
                      onClick={() => handleToggleActive(rule)}
                      className="rounded-lg p-1.5 transition-colors inline-block"
                    >
                      {rule.is_active ? (
                        <ToggleRight className="h-5 w-5 text-emerald-400" />
                      ) : (
                        <ToggleLeft className="h-5 w-5 text-gray-500" />
                      )}
                    </button>
                  </td>
                  <td className="px-5 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleTest(rule._id)}
                        disabled={testingId !== null}
                        className="flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wide rounded-md bg-cyan-500/10 dark:bg-cyan-600/10 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-600/20 transition-all"
                        title="Gửi payload test qua Telegram"
                      >
                        <Play className="h-3 w-3" />
                        Test Alert
                      </button>
                      <button
                        onClick={() => openEditForm(rule)}
                        className="text-xs font-medium text-cyan-600 dark:text-cyan-400 hover:text-cyan-500 dark:hover:text-cyan-300 px-2 py-1 rounded hover:bg-[hsl(var(--secondary))]"
                      >
                        Sửa
                      </button>
                      <button
                        onClick={() => handleDelete(rule._id)}
                        className="rounded-lg p-1.5 text-gray-500 hover:bg-red-500/10 hover:text-red-400 transition-colors"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
