"use client";

import { useEffect, useState } from "react";
import { crawlerApi } from "@/lib/api";
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
                </div>

                <div className="bg-[hsl(var(--secondary))]/25 rounded-xl p-4 border border-[hsl(var(--border))]/50 space-y-3.5 text-xs">
                  <div className="flex justify-between items-center border-b border-[hsl(var(--border))]/50 pb-2">
                    <span className="text-[10px] text-[hsl(var(--muted-foreground))] uppercase font-bold">Thời gian vận hành</span>
                    <span className="text-[10px] text-[hsl(var(--muted-foreground))]">GMT+7</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[hsl(var(--muted-foreground))]">Lần quét gần nhất:</span>
                    <span className="font-semibold text-[hsl(var(--foreground))]">
                      {logs.schedule_stats.last_run ? new Date(logs.schedule_stats.last_run).toLocaleString("vi-VN") : "Chưa có"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[hsl(var(--muted-foreground))]">Lần quét dự kiến tiếp:</span>
                    <span className="font-semibold text-cyan-600 dark:text-cyan-400">
                      {logs.schedule_stats.next_run ? new Date(logs.schedule_stats.next_run).toLocaleString("vi-VN") : "Không lập lịch"}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "history" && (
              <div className="overflow-x-auto rounded-xl border border-[hsl(var(--border))]">
                <table className="min-w-full divide-y divide-[hsl(var(--border))] text-left text-xs">
                  <thead className="bg-[hsl(var(--secondary))]/35 font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wider">
                    <tr>
                      <th className="px-4 py-3">Thời gian</th>
                      <th className="px-4 py-3">Trạng thái</th>
                      <th className="px-4 py-3">Kiểu kích hoạt</th>
                      <th className="px-4 py-3 text-center">Tin thô</th>
                      <th className="px-4 py-3 text-center">Tin mới</th>
                      <th className="px-4 py-3 text-center">Liên quan</th>
                      <th className="px-4 py-3 text-center">Cảnh báo</th>
                      <th className="px-4 py-3 text-right">Thời gian chạy</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[hsl(var(--border))]/60">
                    {logs.recent_runs.length > 0 ? (
                      logs.recent_runs.map((run) => (
                        <tr key={run._id} className="hover:bg-[hsl(var(--secondary))]/10 transition-colors">
                          <td className="px-4 py-3 font-medium whitespace-nowrap text-[hsl(var(--foreground))]">
                            {new Date(run.timestamp).toLocaleString("vi-VN")}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              run.status === "success"
                                ? "bg-emerald-500/10 text-emerald-500"
                                : run.status === "failed"
                                ? "bg-rose-500/10 text-rose-500"
                                : "bg-amber-500/10 text-amber-500"
                            }`}>
                              {run.status === "success" ? "Thành công" : run.status === "failed" ? "Thất bại" : "Lỗi một phần"}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-medium text-[hsl(var(--muted-foreground))]">
                            {run.trigger_type === "scheduled"
                              ? "Tự động theo lịch"
                              : run.trigger_type === "manual_fast"
                              ? "Quét nhanh thủ công"
                              : "Quét nâng cao thủ công"}
                          </td>
                          <td className="px-4 py-3 text-center text-[hsl(var(--foreground))]">{run.crawled_count}</td>
                          <td className="px-4 py-3 text-center text-[hsl(var(--foreground))]">{run.new_articles}</td>
                          <td className="px-4 py-3 text-center text-cyan-600 dark:text-cyan-400 font-semibold">{run.processed_count}</td>
                          <td className="px-4 py-3 text-center text-[hsl(var(--foreground))]">{run.alerts_sent}</td>
                          <td className="px-4 py-3 text-right text-[hsl(var(--muted-foreground))] font-mono">
                            {run.elapsed_seconds.toFixed(1)}s
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={8} className="px-4 py-8 text-center text-[hsl(var(--muted-foreground))]">
                          Chưa có lịch sử chạy crawl tin tức.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
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
