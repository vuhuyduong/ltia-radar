"use client";

import { useEffect, useState } from "react";
import { crawlerApi } from "@/lib/api";
import { formatVietnamDateTime } from "@/lib/date";
import {
  Clock,
  Save,
  Play,
  CheckCircle2,
  AlertCircle,
  Calendar,
  Settings,
  Activity,
  Layers,
  List,
  Database,
  RefreshCw,
  Cpu,
  Key,
  Info,
  X,
  FileText,
} from "lucide-react";

export default function SettingsPage() {
  // Settings State
  const [isEnabled, setIsEnabled] = useState(true);
  const [frequencyType, setFrequencyType] = useState<"interval" | "daily" | "fixed_hours" | "hourly_range">("interval");
  const [intervalMinutes, setIntervalMinutes] = useState(60);
  const [fixedHours, setFixedHours] = useState<string[]>(["07:00", "10:00", "12:00"]);
  const [startHour, setStartHour] = useState(7);
  const [endHour, setEndHour] = useState(19);
  const [stepHours, setStepHours] = useState(1);

  // Manual Trigger State
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  // UI Status
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [triggerMsg, setTriggerMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // System Logs State
  const [activeTab, setActiveTab] = useState<"news" | "schedule" | "history">("news");
  const [selectedRun, setSelectedRun] = useState<any | null>(null);
  const [logs, setLogs] = useState<{
    news_stats: {
      total_crawled: number;
      total_relevant: number;
      total_irrelevant: number;
    };
    schedule_stats: {
      is_enabled: boolean;
      frequency_type: string;
      frequency_description: string;
      last_run: string | null;
      next_run: string | null;
      timezone?: string;
      active_llm?: {
        provider: string;
        model_name: string;
        key_suffix: string;
        prompt_name: string;
      };
    };
    live_quota?: Record<string, {
      key_suffix: string;
      masked_key: string;
      model: string;
      rpm_used: number;
      rpm_limit: number;
      tpm_used: number;
      tpm_limit: number;
      rpd_used: number;
      rpd_limit: number;
      total_tokens_today: number;
      total_success: number;
      errors_429: number;
      errors_503: number;
      errors_other: number;
      cooldown_s: number;
      status: string;
    }>;
    quota_limits?: {
      rpm_limit: number;
      tpm_limit: number;
      rpd_limit: number;
    };
    recent_runs: {
      _id: string;
      timestamp: string;
      status: string;
      crawled_count: number;
      new_articles: number;
      processed_count: number;
      alerts_sent: number;
      errors: number;
      elapsed_seconds: number;
      trigger_type: string;
      llm_provider?: string;
      llm_model?: string;
      llm_key_suffix?: string;
      llm_calls_count?: number;
      llm_tokens_used?: number;
      llm_free_tpm_limit?: number;
      llm_free_rpd_limit?: number;
      llm_free_rpm_limit?: number;
      llm_errors_429?: number;
      llm_errors_503?: number;
      llm_errors_other?: number;
      llm_prompt_name?: string;
      llm_status?: string;
    }[];
  } | null>(null);

  // Available hours for Fixed Hours checklist (0 to 23)
  const availableHours = Array.from({ length: 24 }, (_, i) => {
    const hh = i.toString().padStart(2, "0");
    return `${hh}:00`;
  });

  const fetchLogs = async () => {
    try {
      const logRes = await crawlerApi.getLogs();
      if (logRes) {
        setLogs(logRes as any);
      }
    } catch (error) {
      console.error("Failed to load logs:", error);
    }
  };

  useEffect(() => {
    async function fetchSettings() {
      try {
        const res = await crawlerApi.getSettings();
        if (res) {
          setIsEnabled(res.is_enabled !== false);
          const freq = res.frequency_type as "interval" | "daily" | "fixed_hours" | "hourly_range" | undefined;
          if (freq) setFrequencyType(freq);
          if (res.interval_minutes) setIntervalMinutes(Number(res.interval_minutes));
          const hours = res.fixed_hours as string[] | undefined;
          if (hours) setFixedHours(hours);
          
          const hourlyRange = res.hourly_range as Record<string, number> | undefined;
          if (hourlyRange) {
            setStartHour(hourlyRange.start_hour ?? 7);
            setEndHour(hourlyRange.end_hour ?? 19);
            setStepHours(hourlyRange.interval_hours ?? 1);
          }
        }
      } catch (error) {
        console.error("Failed to load settings:", error);
        setMessage({ type: "error", text: "Không thể kết nối tới máy chủ để tải cấu hình." });
      } finally {
        setLoading(false);
      }
    }
    fetchSettings();
    fetchLogs();
  }, []);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const payload = {
        is_enabled: isEnabled,
        frequency_type: frequencyType,
        interval_minutes: Number(intervalMinutes),
        fixed_hours: fixedHours,
        hourly_range: {
          start_hour: Number(startHour),
          end_hour: Number(endHour),
          interval_hours: Number(stepHours),
        },
      };
      await crawlerApi.updateSettings(payload);
      setMessage({ type: "success", text: "Đã lưu và áp dụng cấu hình tần suất quét tin thành công!" });
      fetchLogs();
      setTimeout(() => setMessage(null), 5000);
    } catch (error) {
      console.error("Failed to save settings:", error);
      setMessage({ type: "error", text: "Đã xảy ra lỗi khi lưu cấu hình." });
    } finally {
      setSaving(false);
    }
  };

  const handleToggleHour = (hour: string) => {
    if (fixedHours.includes(hour)) {
      setFixedHours(fixedHours.filter((h) => h !== hour));
    } else {
      setFixedHours([...fixedHours, hour].sort());
    }
  };

  const handleManualTrigger = async () => {
    setTriggering(true);
    setTriggerMsg(null);
    try {
      // Parse local ISO date string
      const payload: { trigger_type: string; date_from?: string; date_to?: string } = {
        trigger_type: "advanced",
      };
      if (dateFrom) {
        payload.date_from = new Date(dateFrom).toISOString();
      }
      if (dateTo) {
        payload.date_to = new Date(dateTo).toISOString();
      }

      const res = await crawlerApi.trigger(payload);
      setTriggerMsg({
        type: "success",
        text: `Đã kích hoạt quét tin thủ công nâng cao thành công! Tiến trình đang chạy ngầm.`,
      });
      setTimeout(() => {
        setTriggerMsg(null);
        fetchLogs();
      }, 5000);
    } catch (error: any) {
      console.error("Failed manual trigger:", error);
      setTriggerMsg({
        type: "error",
        text: error.message || "Đã xảy ra lỗi khi gửi yêu cầu quét tin.",
      });
    } finally {
      setTriggering(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Đang tải cấu hình...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-[hsl(var(--foreground))] flex items-center gap-2">
          <Settings className="h-6 w-6 text-cyan-500" />
          Thiết lập Crawler
        </h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Quản lý tần suất quét tự động và kích hoạt tiến trình cào tin tức thủ công nâng cao.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Left column: Form settings */}
        <div className="md:col-span-2 space-y-6">
          <form onSubmit={handleSaveSettings} className="glass-card rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-6 space-y-6">
            <div className="border-b border-[hsl(var(--border))] pb-4">
              <h2 className="text-lg font-semibold text-[hsl(var(--foreground))]">Tần suất quét tự động</h2>
              <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">Cấu hình thời gian và chế độ chạy tự động của robot thu thập thông tin.</p>
            </div>

            {/* Toggle Enable */}
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-[hsl(var(--foreground))] block">Kích hoạt quét tự động</label>
                <span className="text-xs text-[hsl(var(--muted-foreground))]">Cho phép robot tự động chạy theo lịch trình đã cấu hình.</span>
              </div>
              <button
                type="button"
                onClick={() => setIsEnabled(!isEnabled)}
                className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  isEnabled ? "bg-cyan-500" : "bg-[hsl(var(--muted))]"
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                    isEnabled ? "translate-x-5" : "translate-x-0"
                  }`}
                />
              </button>
            </div>

            {isEnabled && (
              <>
                {/* Frequency Type */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[hsl(var(--foreground))]">Chế độ quét tin</label>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {[
                      { id: "interval", label: "Khoảng thời gian" },
                      { id: "daily", label: "Hàng ngày" },
                      { id: "fixed_hours", label: "Khung giờ cố định" },
                      { id: "hourly_range", label: "Theo ca làm việc" },
                    ].map((mode) => (
                      <button
                        key={mode.id}
                        type="button"
                        onClick={() => setFrequencyType(mode.id as any)}
                        className={`px-3 py-2.5 rounded-xl border text-xs font-medium transition-all ${
                          frequencyType === mode.id
                            ? "bg-cyan-500/10 border-cyan-500 text-cyan-600 dark:text-cyan-400 font-semibold"
                            : "border-[hsl(var(--border))] hover:bg-[hsl(var(--secondary))] text-[hsl(var(--muted-foreground))]"
                        }`}
                      >
                        {mode.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Conditional Fields based on Mode */}
                <div className="bg-[hsl(var(--secondary))]/30 rounded-xl p-4 border border-[hsl(var(--border))]/50 space-y-4">
                  {frequencyType === "interval" && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-xs font-semibold text-[hsl(var(--foreground))] flex items-center gap-1.5 uppercase tracking-wide">
                          <Clock className="h-3.5 w-3.5 text-cyan-500" />
                          Quét mỗi N phút
                        </label>
                      </div>
                      <div className="flex items-center gap-3">
                        <input
                          type="number"
                          min="5"
                          max="1440"
                          value={intervalMinutes}
                          onChange={(e) => setIntervalMinutes(Math.max(5, Number(e.target.value)))}
                          className="w-24 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-3 py-1.5 text-sm text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none"
                        />
                        <span className="text-xs text-[hsl(var(--muted-foreground))]">Phút (Tối thiểu 5 phút, tối đa 1440 phút / 1 ngày)</span>
                      </div>
                    </div>
                  )}

                  {frequencyType === "daily" && (
                    <div className="text-xs text-[hsl(var(--muted-foreground))] flex items-start gap-2 py-2">
                      <CheckCircle2 className="h-4 w-4 text-cyan-500 flex-shrink-0 mt-0.5" />
                      <p>Hệ thống sẽ chạy cào tin tự động mỗi ngày một lần vào lúc **00h00** đêm. Thích hợp cho các báo cáo tổng hợp cuối ngày.</p>
                    </div>
                  )}

                  {frequencyType === "fixed_hours" && (
                    <div className="space-y-3">
                      <label className="text-xs font-semibold text-[hsl(var(--foreground))] uppercase tracking-wide flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5 text-cyan-500" />
                        Chọn các khung giờ trong ngày
                      </label>
                      <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
                        {availableHours.map((hour) => {
                          const isSelected = fixedHours.includes(hour);
                          return (
                            <button
                              key={hour}
                              type="button"
                              onClick={() => handleToggleHour(hour)}
                              className={`py-1.5 rounded-lg border text-xs transition-all ${
                                isSelected
                                  ? "bg-cyan-500/20 border-cyan-500 text-cyan-600 dark:text-cyan-400 font-semibold"
                                  : "border-[hsl(var(--border))] hover:bg-[hsl(var(--secondary))] text-[hsl(var(--muted-foreground))]"
                              }`}
                            >
                              {hour}
                            </button>
                          );
                        })}
                      </div>
                      <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Bạn có thể chọn nhiều khung giờ khác nhau. Robot sẽ chạy tại thời điểm chính xác bắt đầu mỗi giờ được lựa chọn.</p>
                    </div>
                  )}

                  {frequencyType === "hourly_range" && (
                    <div className="space-y-4">
                      <label className="text-xs font-semibold text-[hsl(var(--foreground))] uppercase tracking-wide flex items-center gap-1.5">
                        <Layers className="h-3.5 w-3.5 text-cyan-500" />
                        Quét hàng giờ trong khoảng thời gian làm việc
                      </label>
                      <div className="grid grid-cols-3 gap-3">
                        <div className="space-y-1.5">
                          <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-semibold uppercase">Giờ bắt đầu</span>
                          <select
                            value={startHour}
                            onChange={(e) => setStartHour(Number(e.target.value))}
                            className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-2.5 py-1.5 text-xs text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none"
                          >
                            {Array.from({ length: 24 }, (_, i) => (
                              <option key={i} value={i}>{i}h00</option>
                            ))}
                          </select>
                        </div>
                        <div className="space-y-1.5">
                          <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-semibold uppercase">Giờ kết thúc</span>
                          <select
                            value={endHour}
                            onChange={(e) => setEndHour(Number(e.target.value))}
                            className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-2.5 py-1.5 text-xs text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none"
                          >
                            {Array.from({ length: 24 }, (_, i) => (
                              <option key={i} value={i}>{i}h00</option>
                            ))}
                          </select>
                        </div>
                        <div className="space-y-1.5">
                          <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-semibold uppercase">Bước nhảy (tần suất)</span>
                          <select
                            value={stepHours}
                            onChange={(e) => setStepHours(Number(e.target.value))}
                            className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-2.5 py-1.5 text-xs text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none"
                          >
                            <option value={1}>Mỗi 1 giờ</option>
                            <option value={2}>Mỗi 2 giờ</option>
                            <option value={3}>Mỗi 3 giờ</option>
                            <option value={4}>Mỗi 4 giờ</option>
                          </select>
                        </div>
                      </div>
                      <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Ví dụ: Từ 7h00 đến 19h00, thực hiện hàng giờ (bước nhảy = 1 giờ) sẽ chạy vào 7h00, 8h00, ..., 19h00.</p>
                    </div>
                  )}
                </div>
              </>
            )}

            {message && (
              <div className={`flex items-start gap-2.5 rounded-lg border p-3.5 text-xs ${
                message.type === "success"
                  ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                  : "bg-rose-500/10 border-rose-500/30 text-rose-400"
              }`}>
                {message.type === "success" ? (
                  <CheckCircle2 className="h-4 w-4 mt-0.5 flex-shrink-0" />
                ) : (
                  <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                )}
                <span>{message.text}</span>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={saving}
                className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cyan-500/25 hover:brightness-110 hover:shadow-cyan-500/35 transition-all disabled:opacity-50"
              >
                {saving ? (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Lưu cấu hình
              </button>
            </div>
          </form>
        </div>

        {/* Right column: Advanced Manual Trigger */}
        <div className="space-y-6">
          <div className="glass-card rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-6 space-y-5">
            <div className="border-b border-[hsl(var(--border))] pb-3">
              <h2 className="text-base font-semibold text-[hsl(var(--foreground))] flex items-center gap-1.5">
                <Activity className="h-4 w-4 text-cyan-500" />
                Quét thủ công nâng cao
              </h2>
              <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">Kích hoạt cào tin tức tức thì với mốc thời gian lọc tùy chỉnh.</p>
            </div>

            <div className="space-y-3.5 text-xs">
              <div className="space-y-1.5">
                <label className="text-[10px] text-[hsl(var(--muted-foreground))] font-semibold uppercase flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5 text-cyan-500" />
                  Từ ngày (đăng tải)
                </label>
                <input
                  type="datetime-local"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-3 py-2 text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] text-[hsl(var(--muted-foreground))] font-semibold uppercase flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5 text-cyan-500" />
                  Đến ngày (đăng tải)
                </label>
                <input
                  type="datetime-local"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-3 py-2 text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none"
                />
              </div>
            </div>

            {triggerMsg && (
              <div className={`flex items-start gap-2 rounded-lg border p-3 text-[11px] ${
                triggerMsg.type === "success"
                  ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                  : "bg-rose-500/10 border-rose-500/30 text-rose-400"
              }`}>
                {triggerMsg.type === "success" ? (
                  <CheckCircle2 className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
                ) : (
                  <AlertCircle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
                )}
                <span>{triggerMsg.text}</span>
              </div>
            )}

            <button
              type="button"
              onClick={handleManualTrigger}
              disabled={triggering}
              className="w-full flex items-center justify-center gap-2 rounded-xl border border-cyan-500/30 bg-cyan-500/10 hover:bg-cyan-500/20 px-4 py-2.5 text-xs font-semibold text-cyan-600 dark:text-cyan-400 shadow-sm transition-all disabled:opacity-50"
            >
              {triggering ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
              ) : (
                <Play className="h-4 w-4 fill-cyan-400/20" />
              )}
              Chạy quét nâng cao
            </button>

            <div className="text-[10px] text-[hsl(var(--muted-foreground))] flex gap-1.5 bg-[hsl(var(--secondary))]/20 p-3 rounded-lg border border-[hsl(var(--border))]/50 leading-relaxed">
              <AlertCircle className="h-4 w-4 text-cyan-500 flex-shrink-0 mt-0.5" />
              <p>
                **Quét nhanh** ở thanh tiêu đề (Header) sẽ quét tự động từ thời điểm bài báo mới nhất được lưu trong hệ thống.
                **Quét nâng cao** ở đây cho phép bạn giới hạn thời điểm xuất bản của các tin bài theo nhu cầu cụ thể.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Nhật ký hoạt động của hệ thống */}
      <div className="glass-card rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-[hsl(var(--border))] pb-4">
          <div>
            <h2 className="text-lg font-semibold text-[hsl(var(--foreground))] flex items-center gap-2">
              <Activity className="h-5 w-5 text-cyan-500" />
              Nhật ký hoạt động của hệ thống
            </h2>
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
              Thống kê tin tức thu thập, trạng thái lập lịch và lịch sử vận hành backend.
            </p>
          </div>
          <button
            type="button"
            onClick={fetchLogs}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] hover:bg-[hsl(var(--secondary))] text-xs text-[hsl(var(--foreground))] transition-all"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Làm mới
          </button>
        </div>

        {/* Tab Selection */}
        <div className="flex gap-2 border-b border-[hsl(var(--border))] pb-3">
          {[
            { id: "news", label: "Tin tức", icon: Database },
            { id: "schedule", label: "Lịch quét tin", icon: Clock },
            { id: "history", label: "Lịch sử chạy", icon: List },
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                  activeTab === tab.id
                    ? "bg-cyan-500/10 border border-cyan-500 text-cyan-600 dark:text-cyan-400"
                    : "text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab Contents */}
        {logs ? (
          <div className="space-y-4 pt-2">
            {activeTab === "news" && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-[hsl(var(--secondary))]/25 rounded-xl p-4 border border-[hsl(var(--border))]/50 space-y-1">
                  <span className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase font-bold tracking-wider">Tổng tin đã crawl</span>
                  <p className="text-2xl font-bold text-[hsl(var(--foreground))]">{logs.news_stats.total_crawled}</p>
                  <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Tổng số tin tức thô thu thập được từ nguồn.</p>
                </div>
                <div className="bg-cyan-500/5 rounded-xl p-4 border border-cyan-500/20 space-y-1">
                  <span className="text-[10px] text-cyan-600 dark:text-cyan-400 uppercase font-bold tracking-wider">Tin tức liên quan</span>
                  <p className="text-2xl font-bold text-cyan-600 dark:text-cyan-400">{logs.news_stats.total_relevant}</p>
                  <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Tin tức có giá trị, liên quan đến các dự án giám sát.</p>
                </div>
                <div className="bg-[hsl(var(--secondary))]/25 rounded-xl p-4 border border-[hsl(var(--border))]/50 space-y-1">
                  <span className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase font-bold tracking-wider">Tin không liên quan</span>
                  <p className="text-2xl font-bold text-[hsl(var(--foreground))]">{logs.news_stats.total_irrelevant}</p>
                  <p className="text-[10px] text-[hsl(var(--muted-foreground))]">Tin tức bị lọc bỏ do không khớp từ khóa giám sát.</p>
                </div>
              </div>
            )}

            {activeTab === "schedule" && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-[hsl(var(--secondary))]/25 rounded-xl p-4 border border-[hsl(var(--border))]/50 space-y-3.5 text-xs">
                  <div className="flex justify-between items-center border-b border-[hsl(var(--border))]/50 pb-2">
                    <span className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase font-bold">Lập lịch tự động</span>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      logs.schedule_stats.is_enabled ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"
                    }`}>
                      {logs.schedule_stats.is_enabled ? "BẬT" : "TẮT"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[hsl(var(--muted-foreground))]">Tần suất thiết lập:</span>
                    <span className="font-semibold text-[hsl(var(--foreground))]">{logs.schedule_stats.frequency_description}</span>
                  </div>
                  {logs.schedule_stats.active_llm && (
                    <div className="flex justify-between items-center pt-2 border-t border-[hsl(var(--border))]/40">
                      <span className="text-[hsl(var(--muted-foreground))]">Mô hình AI:</span>
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono font-bold text-cyan-600 dark:text-cyan-400 bg-cyan-500/10 border border-cyan-500/20 px-2 py-0.5 rounded">
                          {logs.schedule_stats.active_llm.model_name}
                        </span>
                        <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[hsl(var(--secondary))] text-[hsl(var(--muted-foreground))] border border-[hsl(var(--border))]">
                          Key: {logs.schedule_stats.active_llm.key_suffix}
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                <div className="bg-[hsl(var(--secondary))]/25 rounded-xl p-4 border border-[hsl(var(--border))]/50 space-y-3.5 text-xs">
                  <div className="flex justify-between items-center border-b border-[hsl(var(--border))]/50 pb-2">
                    <span className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase font-bold">Thời gian vận hành</span>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20">
                      Giờ Việt Nam (UTC+7)
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[hsl(var(--muted-foreground))]">Lần quét gần nhất:</span>
                    <span className="font-semibold text-[hsl(var(--foreground))]">
                      {logs.schedule_stats.last_run ? formatVietnamDateTime(logs.schedule_stats.last_run) : "Chưa có"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[hsl(var(--muted-foreground))]">Lần quét dự kiến tiếp:</span>
                    <span className="font-semibold text-cyan-600 dark:text-cyan-400">
                      {logs.schedule_stats.next_run ? formatVietnamDateTime(logs.schedule_stats.next_run) : "Không lập lịch"}
                    </span>
                  </div>
                  {logs.schedule_stats.active_llm?.prompt_name && (
                    <div className="flex justify-between items-center pt-2 border-t border-[hsl(var(--border))]/40">
                      <span className="text-[hsl(var(--muted-foreground))]">Prompt kích hoạt:</span>
                      <span className="text-[11px] font-medium text-[hsl(var(--foreground))] truncate max-w-[200px]" title={logs.schedule_stats.active_llm.prompt_name}>
                        {logs.schedule_stats.active_llm.prompt_name}
                      </span>
                    </div>
                  )}
                </div>

                {/* Live Free Tier Quota Monitor Card */}
                {logs.live_quota && Object.keys(logs.live_quota).length > 0 && (
                  <div className="col-span-1 sm:col-span-2 rounded-xl bg-[hsl(var(--secondary))]/20 border border-[hsl(var(--border))]/60 p-4 space-y-3">
                    <div className="flex items-center justify-between border-b border-[hsl(var(--border))]/40 pb-2">
                      <div className="flex items-center gap-2">
                        <Cpu className="h-4 w-4 text-cyan-500" />
                        <h4 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))]">
                          Tình trạng Google AI Studio Free Tier (Thời gian thực)
                        </h4>
                      </div>
                      <span className="text-[10px] text-[hsl(var(--muted-foreground))]">
                        Giới hạn Free: 20 RPD / 200k TPM / 5 RPM per key
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                      {Object.entries(logs.live_quota).map(([label, q]) => (
                        <div key={label} className="p-3 rounded-lg bg-[hsl(var(--card))] border border-[hsl(var(--border))]/60 space-y-2 text-xs">
                          <div className="flex items-center justify-between">
                            <span className="font-mono font-bold text-cyan-600 dark:text-cyan-400">{q.model}</span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              q.status === "ready"
                                ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                                : q.status === "cooling_down"
                                ? "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                                : "bg-rose-500/10 text-rose-500 border border-rose-500/20"
                            }`}>
                              {q.status === "ready" ? "Sẵn sàng" : q.status === "cooling_down" ? `Cooldown ${q.cooldown_s}s` : "Hết quota ngày"}
                            </span>
                          </div>

                          <div className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono">
                            API Key: <span className="text-[hsl(var(--foreground))] font-semibold">{q.masked_key}</span> (Đuôi: {q.key_suffix})
                          </div>

                          {/* Progress: RPD (Daily requests) */}
                          <div className="space-y-1">
                            <div className="flex justify-between text-[10px]">
                              <span className="text-[hsl(var(--muted-foreground))]">Requests ngày (RPD):</span>
                              <span className="font-mono font-semibold">{q.rpd_used} / {q.rpd_limit}</span>
                            </div>
                            <div className="w-full bg-[hsl(var(--secondary))] h-1.5 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all ${
                                  q.rpd_used >= q.rpd_limit ? "bg-rose-500" : q.rpd_used >= q.rpd_limit * 0.75 ? "bg-amber-500" : "bg-cyan-500"
                                }`}
                                style={{ width: `${Math.min(100, (q.rpd_used / q.rpd_limit) * 100)}%` }}
                              />
                            </div>
                          </div>

                          {/* Stats Grid: TPM, 429, 503 */}
                          <div className="grid grid-cols-3 gap-1.5 pt-1 text-center text-[10px]">
                            <div className="p-1 rounded bg-[hsl(var(--secondary))]/40">
                              <span className="text-[hsl(var(--muted-foreground))] block">TPM đang dùng</span>
                              <span className="font-mono font-bold">{q.tpm_used.toLocaleString()} / {(q.tpm_limit / 1000).toFixed(0)}k</span>
                            </div>
                            <div className="p-1 rounded bg-[hsl(var(--secondary))]/40">
                              <span className="text-[hsl(var(--muted-foreground))] block">Lỗi 429</span>
                              <span className={`font-mono font-bold ${q.errors_429 > 0 ? "text-amber-500" : "text-[hsl(var(--muted-foreground))]"}`}>
                                {q.errors_429}
                              </span>
                            </div>
                            <div className="p-1 rounded bg-[hsl(var(--secondary))]/40">
                              <span className="text-[hsl(var(--muted-foreground))] block">Lỗi 503</span>
                              <span className={`font-mono font-bold ${q.errors_503 > 0 ? "text-rose-500" : "text-[hsl(var(--muted-foreground))]"}`}>
                                {q.errors_503}
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "history" && (
              <div className="space-y-4">
                {/* Desktop View: Bảng 4 cụm thông tin tinh gọn, không cuộn ngang */}
                <div className="hidden md:block rounded-xl border border-[hsl(var(--border))] overflow-hidden bg-[hsl(var(--card))]">
                  <table className="w-full text-left text-xs divide-y divide-[hsl(var(--border))]">
                    <thead className="bg-[hsl(var(--secondary))]/40 font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wider">
                      <tr>
                        <th className="px-4 py-3 w-[26%]">Thời gian & Trạng thái</th>
                        <th className="px-4 py-3 w-[34%]">Mô hình AI & Quota LLM</th>
                        <th className="px-4 py-3 w-[28%]">Xử lý Tin & Cảnh báo</th>
                        <th className="px-4 py-3 w-[12%] text-right">Chi tiết</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[hsl(var(--border))]/60">
                      {logs.recent_runs.length > 0 ? (
                        logs.recent_runs.map((run) => (
                          <tr key={run._id} className="hover:bg-[hsl(var(--secondary))]/20 transition-colors">
                            {/* Cột 1: Thời gian & Trạng thái */}
                            <td className="px-4 py-3 align-top">
                              <div className="font-medium text-[hsl(var(--foreground))] text-xs">
                                {formatVietnamDateTime(run.timestamp)}
                              </div>
                              <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                  run.status === "success"
                                    ? "bg-emerald-500/10 text-emerald-500"
                                    : run.status === "failed"
                                    ? "bg-rose-500/10 text-rose-500"
                                    : "bg-amber-500/10 text-amber-500"
                                }`}>
                                  {run.status === "success" ? "Thành công" : run.status === "failed" ? "Thất bại" : "Lỗi một phần"}
                                </span>
                                <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono">
                                  ⏱ {run.elapsed_seconds.toFixed(1)}s
                                </span>
                              </div>
                            </td>

                            {/* Cột 2: Mô hình AI & Quota LLM */}
                            <td className="px-4 py-3 align-top">
                              <div className="flex items-center gap-1.5 flex-wrap">
                                <span className="px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20">
                                  {run.llm_model || "gemini-2.0-flash"}
                                </span>
                                <span className="px-1.5 py-0.5 rounded font-mono text-[10px] bg-[hsl(var(--secondary))] text-[hsl(var(--muted-foreground))] border border-[hsl(var(--border))]">
                                  Key: {run.llm_key_suffix || "N/A"}
                                </span>
                              </div>
                              <div className="flex items-center gap-2 mt-1.5 text-[11px] flex-wrap">
                                <span className="font-mono font-semibold text-cyan-600 dark:text-cyan-400">
                                  {(run.llm_tokens_used || 0).toLocaleString()} tok
                                </span>
                                <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono">
                                  / {(run.llm_free_tpm_limit ? (run.llm_free_tpm_limit / 1000).toFixed(0) : 200)}k TPM
                                </span>
                                {(run.llm_errors_429 || 0) + (run.llm_errors_503 || 0) === 0 ? (
                                  <span className="text-[10px] text-emerald-500 font-medium ml-1">✓ 0 lỗi API</span>
                                ) : (
                                  <div className="flex items-center gap-1 ml-1 text-[10px] font-mono">
                                    {run.llm_errors_429 ? (
                                      <span className="px-1.5 py-0.2 rounded bg-amber-500/15 text-amber-500 border border-amber-500/30 font-bold" title="Lỗi 429">
                                        429:{run.llm_errors_429}
                                      </span>
                                    ) : null}
                                    {run.llm_errors_503 ? (
                                      <span className="px-1.5 py-0.2 rounded bg-rose-500/15 text-rose-500 border border-rose-500/30 font-bold" title="Lỗi 503">
                                        503:{run.llm_errors_503}
                                      </span>
                                    ) : null}
                                  </div>
                                )}
                              </div>
                            </td>

                            {/* Cột 3: Xử lý Tin & Cảnh báo */}
                            <td className="px-4 py-3 align-top">
                              <div className="flex items-center gap-1.5 text-xs flex-wrap font-mono">
                                <span className="text-[hsl(var(--foreground))]">{run.crawled_count} thô</span>
                                <span className="text-[hsl(var(--muted-foreground))]">→</span>
                                <span className="font-bold text-amber-500">{run.new_articles} mới</span>
                                <span className="text-[hsl(var(--muted-foreground))]">→</span>
                                <span className="font-bold text-cyan-600 dark:text-cyan-400">{run.processed_count} cụm</span>
                              </div>
                              <div className="text-[10px] text-[hsl(var(--muted-foreground))] mt-1.5">
                                🔔 {run.alerts_sent} cảnh báo gửi qua Telegram
                              </div>
                            </td>

                            {/* Cột 4: Thao tác Chi tiết */}
                            <td className="px-4 py-3 align-top text-right">
                              <button
                                type="button"
                                onClick={() => setSelectedRun(run)}
                                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] hover:bg-cyan-500/10 hover:border-cyan-500/30 text-[hsl(var(--foreground))] hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors text-xs font-medium"
                                title="Xem chi tiết hoạt động LLM"
                              >
                                <Info className="h-3.5 w-3.5 text-cyan-500" />
                                <span>Chi tiết</span>
                              </button>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={4} className="px-4 py-8 text-center text-[hsl(var(--muted-foreground))]">
                            Chưa có lịch sử chạy crawl tin tức.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                {/* Mobile / Tablet View: Thẻ danh sách dọc (Card Stack), chống tràn màn hình */}
                <div className="block md:hidden space-y-3">
                  {logs.recent_runs.length > 0 ? (
                    logs.recent_runs.map((run) => (
                      <div
                        key={run._id}
                        className="glass-card rounded-xl border border-[hsl(var(--border))] p-4 space-y-3 bg-[hsl(var(--card))]"
                      >
                        {/* Header: Thời gian & Trạng thái */}
                        <div className="flex items-start justify-between gap-2 border-b border-[hsl(var(--border))]/60 pb-2.5">
                          <div>
                            <div className="font-bold text-xs text-[hsl(var(--foreground))]">
                              {formatVietnamDateTime(run.timestamp)}
                            </div>
                            <div className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono mt-0.5">
                              Thời lượng: {run.elapsed_seconds.toFixed(1)}s • 🔔 {run.alerts_sent} alerts
                            </div>
                          </div>
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            run.status === "success"
                              ? "bg-emerald-500/10 text-emerald-500"
                              : run.status === "failed"
                              ? "bg-rose-500/10 text-rose-500"
                              : "bg-amber-500/10 text-amber-500"
                          }`}>
                            {run.status === "success" ? "Thành công" : run.status === "failed" ? "Thất bại" : "Lỗi"}
                          </span>
                        </div>

                        {/* LLM & Tokens */}
                        <div className="space-y-1.5 text-xs">
                          <div className="flex items-center justify-between gap-2 flex-wrap">
                            <div className="flex items-center gap-1.5">
                              <span className="px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20">
                                {run.llm_model || "gemini-2.0-flash"}
                              </span>
                              <span className="px-1.5 py-0.5 rounded font-mono text-[10px] bg-[hsl(var(--secondary))] text-[hsl(var(--muted-foreground))] border border-[hsl(var(--border))]">
                                {run.llm_key_suffix || "N/A"}
                              </span>
                            </div>
                            <div className="font-mono text-[11px] font-semibold text-cyan-600 dark:text-cyan-400">
                              {(run.llm_tokens_used || 0).toLocaleString()} tok
                            </div>
                          </div>

                          <div className="flex items-center justify-between text-[11px] text-[hsl(var(--muted-foreground))]">
                            <span>Lỗi 429/503:</span>
                            {(run.llm_errors_429 || 0) + (run.llm_errors_503 || 0) === 0 ? (
                              <span className="text-emerald-500 font-medium">0 lỗi</span>
                            ) : (
                              <span className="font-mono font-bold text-rose-500">
                                {run.llm_errors_429 ? `429: ${run.llm_errors_429} ` : ""}
                                {run.llm_errors_503 ? `503: ${run.llm_errors_503}` : ""}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Pipeline Tin tức */}
                        <div className="p-2.5 rounded-lg bg-[hsl(var(--secondary))]/40 flex items-center justify-between text-xs font-mono">
                          <span className="text-[hsl(var(--foreground))]">{run.crawled_count} thô</span>
                          <span>→</span>
                          <span className="text-amber-500 font-bold">{run.new_articles} mới</span>
                          <span>→</span>
                          <span className="text-cyan-600 dark:text-cyan-400 font-bold">{run.processed_count} cụm lưu</span>
                        </div>

                        {/* Action button */}
                        <button
                          type="button"
                          onClick={() => setSelectedRun(run)}
                          className="w-full py-2 rounded-lg border border-cyan-500/30 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
                        >
                          <Info className="h-3.5 w-3.5" />
                          Xem chi tiết thông số LLM & Quota
                        </button>
                      </div>
                    ))
                  ) : (
                    <div className="glass-card rounded-xl p-8 text-center text-xs text-[hsl(var(--muted-foreground))]">
                      Chưa có lịch sử chạy crawl tin tức.
                    </div>
                  )}
                </div>

                {/* Modal Chi tiết hoạt động LLM */}
                {selectedRun && (
                  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                    <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-2xl max-w-xl w-full p-6 space-y-5 shadow-2xl relative">
                      <div className="flex items-center justify-between border-b border-[hsl(var(--border))] pb-3">
                        <div className="flex items-center gap-2">
                          <Cpu className="h-5 w-5 text-cyan-500" />
                          <div>
                            <h3 className="text-base font-bold text-[hsl(var(--foreground))]">
                              Chi tiết Hoạt động LLM & Quota Free Tier
                            </h3>
                            <p className="text-[11px] text-[hsl(var(--muted-foreground))]">
                              Thời gian: {formatVietnamDateTime(selectedRun.timestamp)} (Giờ Việt Nam UTC+7)
                            </p>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => setSelectedRun(null)}
                          className="p-1.5 rounded-lg border border-[hsl(var(--border))] hover:bg-[hsl(var(--secondary))] text-[hsl(var(--muted-foreground))]"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>

                      <div className="space-y-4 text-xs">
                        {/* Section 1: LLM Engine Details */}
                        <div className="p-3.5 rounded-xl bg-[hsl(var(--secondary))]/30 border border-[hsl(var(--border))]/60 space-y-2.5">
                          <h4 className="text-[11px] font-bold uppercase tracking-wider text-cyan-600 dark:text-cyan-400 flex items-center gap-1.5">
                            <Cpu className="h-3.5 w-3.5" />
                            Thông số Mô hình AI
                          </h4>
                          <div className="grid grid-cols-2 gap-3 pt-1">
                            <div>
                              <span className="text-[10px] text-[hsl(var(--muted-foreground))] block">Mô hình (Model):</span>
                              <span className="font-mono font-bold text-sm text-[hsl(var(--foreground))]">
                                {selectedRun.llm_model || "gemini-3.8-flash"}
                              </span>
                            </div>
                            <div>
                              <span className="text-[10px] text-[hsl(var(--muted-foreground))] block">Đuôi API Key sử dụng:</span>
                              <span className="font-mono font-bold text-sm text-cyan-600 dark:text-cyan-400">
                                {selectedRun.llm_key_suffix || "N/A"}
                              </span>
                            </div>
                            <div>
                              <span className="text-[10px] text-[hsl(var(--muted-foreground))] block">Nhà cung cấp:</span>
                              <span className="font-medium text-[hsl(var(--foreground))]">
                                {selectedRun.llm_provider || "Google Gemini"}
                              </span>
                            </div>
                            <div>
                              <span className="text-[10px] text-[hsl(var(--muted-foreground))] block">Trạng thái LLM:</span>
                              <span className="font-semibold text-emerald-500">
                                {selectedRun.llm_status === "idle"
                                  ? "Nghỉ (không có tin mới)"
                                  : selectedRun.llm_status === "success"
                                  ? "Hoàn thành phân tích"
                                  : selectedRun.llm_status || "Sẵn sàng"}
                              </span>
                            </div>
                          </div>
                          {selectedRun.llm_prompt_name && (
                            <div className="pt-2 border-t border-[hsl(var(--border))]/40">
                              <span className="text-[10px] text-[hsl(var(--muted-foreground))] block">Prompt áp dụng:</span>
                              <span className="font-medium text-[hsl(var(--foreground))]">
                                {selectedRun.llm_prompt_name}
                              </span>
                            </div>
                          )}
                        </div>

                        {/* Section 2: Consumption & Free Tier Limits */}
                        <div className="p-3.5 rounded-xl bg-[hsl(var(--secondary))]/30 border border-[hsl(var(--border))]/60 space-y-2.5">
                          <h4 className="text-[11px] font-bold uppercase tracking-wider text-[hsl(var(--foreground))] flex items-center gap-1.5">
                            <Activity className="h-3.5 w-3.5 text-cyan-500" />
                            Google AI Studio Free Tier & Quota
                          </h4>
                          <div className="grid grid-cols-3 gap-2 pt-1 text-center">
                            <div className="p-2 rounded-lg bg-[hsl(var(--card))] border border-[hsl(var(--border))]/50">
                              <span className="text-[10px] text-[hsl(var(--muted-foreground))] block">Tokens tiêu thụ / Free TPM</span>
                              <span className="font-mono font-bold text-sm text-cyan-600 dark:text-cyan-400">
                                {selectedRun.llm_tokens_used ? selectedRun.llm_tokens_used.toLocaleString() : "0"}
                              </span>
                              <span className="text-[9px] text-[hsl(var(--muted-foreground))] block">
                                / {(selectedRun.llm_free_tpm_limit || 200000).toLocaleString()} TPM
                              </span>
                            </div>
                            <div className="p-2 rounded-lg bg-[hsl(var(--card))] border border-[hsl(var(--border))]/50">
                              <span className="text-[10px] text-[hsl(var(--muted-foreground))] block">Lỗi 429 (Rate Limit)</span>
                              <span className={`font-mono font-bold text-sm ${selectedRun.llm_errors_429 > 0 ? "text-amber-500" : "text-emerald-500"}`}>
                                {selectedRun.llm_errors_429 || 0} lần
                              </span>
                              <span className="text-[9px] text-[hsl(var(--muted-foreground))] block">Giới hạn: 20 RPD</span>
                            </div>
                            <div className="p-2 rounded-lg bg-[hsl(var(--card))] border border-[hsl(var(--border))]/50">
                              <span className="text-[10px] text-[hsl(var(--muted-foreground))] block">Lỗi 503 (Overload)</span>
                              <span className={`font-mono font-bold text-sm ${selectedRun.llm_errors_503 > 0 ? "text-rose-500" : "text-emerald-500"}`}>
                                {selectedRun.llm_errors_503 || 0} lần
                              </span>
                              <span className="text-[9px] text-[hsl(var(--muted-foreground))] block">Google Server High Demand</span>
                            </div>
                          </div>
                        </div>

                        {/* Section 3: Crawl Counts */}
                        <div className="p-3.5 rounded-xl bg-[hsl(var(--secondary))]/30 border border-[hsl(var(--border))]/60 space-y-2.5">
                          <h4 className="text-[11px] font-bold uppercase tracking-wider text-[hsl(var(--foreground))] flex items-center gap-1.5">
                            <Database className="h-3.5 w-3.5 text-cyan-500" />
                            Kết quả Thu thập & Cảnh báo
                          </h4>
                          <div className="grid grid-cols-4 gap-2 pt-1 text-center">
                            <div className="p-2 rounded-lg bg-[hsl(var(--card))] border border-[hsl(var(--border))]/50">
                              <span className="text-[10px] text-[hsl(var(--muted-foreground))] block">Tin thô</span>
                              <span className="font-mono font-bold text-sm">{selectedRun.crawled_count}</span>
                            </div>
                            <div className="p-2 rounded-lg bg-[hsl(var(--card))] border border-[hsl(var(--border))]/50">
                              <span className="text-[10px] text-amber-500 block">Tin mới</span>
                              <span className="font-mono font-bold text-sm text-amber-500">{selectedRun.new_articles}</span>
                            </div>
                            <div className="p-2 rounded-lg bg-[hsl(var(--card))] border border-[hsl(var(--border))]/50">
                              <span className="text-[10px] text-cyan-500 block">Cụm tin</span>
                              <span className="font-mono font-bold text-sm text-cyan-600 dark:text-cyan-400">{selectedRun.processed_count}</span>
                            </div>
                            <div className="p-2 rounded-lg bg-[hsl(var(--card))] border border-[hsl(var(--border))]/50">
                              <span className="text-[10px] text-[hsl(var(--muted-foreground))] block">Cảnh báo</span>
                              <span className="font-mono font-bold text-sm">{selectedRun.alerts_sent}</span>
                            </div>
                          </div>
                          <div className="flex justify-between items-center text-[10px] text-[hsl(var(--muted-foreground))] pt-1">
                            <span>Kiểu kích hoạt: {selectedRun.trigger_type === "scheduled" ? "Tự động theo lịch" : "Thủ công"}</span>
                            <span>ID: {selectedRun._id}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex justify-end pt-2">
                        <button
                          type="button"
                          onClick={() => setSelectedRun(null)}
                          className="px-4 py-2 rounded-xl border border-[hsl(var(--border))] hover:bg-[hsl(var(--secondary))] text-xs font-semibold"
                        >
                          Đóng
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 py-8 text-center">
            <RefreshCw className="h-6 w-6 animate-spin text-cyan-500" />
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Đang tải nhật ký hoạt động hệ thống...</p>
          </div>
        )}
      </div>
    </div>
  );
}
