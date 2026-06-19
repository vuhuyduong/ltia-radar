"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, Globe, Rss, ToggleLeft, ToggleRight } from "lucide-react";
import { sourcesApi } from "@/lib/api";

interface Source {
  _id: string;
  url: string;
  name: string;
  source_type: string;
  is_active: boolean;
  created_at: string;
}

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    url: "",
    name: "",
    source_type: "WEB",
  });
  const [error, setError] = useState("");

  const fetchSources = async () => {
    try {
      const res = await sourcesApi.list();
      setSources((res.data as Source[]) || []);
    } catch (err) {
      console.error("Failed to load sources:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSources();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // URL validation (US-1.1 AC#2)
    try {
      new URL(formData.url);
    } catch {
      setError("URL không hợp lệ. Vui lòng nhập đúng định dạng.");
      return;
    }

    try {
      await sourcesApi.create(formData);
      setShowForm(false);
      setFormData({ url: "", name: "", source_type: "WEB" });
      fetchSources();
    } catch {
      setError("Không thể tạo nguồn tin. Vui lòng thử lại.");
    }
  };

  const handleToggle = async (source: Source) => {
    try {
      await sourcesApi.update(source._id, {
        is_active: !source.is_active,
      });
      fetchSources();
    } catch (err) {
      console.error("Failed to toggle source:", err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Bạn có chắc muốn xóa nguồn tin này?")) return;
    try {
      await sourcesApi.delete(id);
      fetchSources();
    } catch (err) {
      console.error("Failed to delete source:", err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[hsl(var(--foreground))]">Nguồn tin</h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Quản lý danh sách URL báo chí và diễn đàn để hệ thống rà quét
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2.5 text-sm font-medium text-white shadow-lg shadow-cyan-500/20 transition-all hover:shadow-cyan-500/30 hover:brightness-110"
        >
          <Plus className="h-4 w-4" />
          Thêm nguồn
        </button>
      </div>

      {/* Add Form */}
      {showForm && (
        <form
          onSubmit={handleCreate}
          className="glass-card space-y-4 rounded-xl p-5"
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-[hsl(var(--muted-foreground))]">
                URL nguồn
              </label>
              <input
                type="text"
                value={formData.url}
                onChange={(e) =>
                  setFormData({ ...formData, url: e.target.value })
                }
                placeholder="https://vnexpress.net/rss/..."
                className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                required
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-[hsl(var(--muted-foreground))]">
                Tên nguồn
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder="VnExpress"
                className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                required
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-[hsl(var(--muted-foreground))]">
                Loại nguồn
              </label>
              <select
                value={formData.source_type}
                onChange={(e) =>
                  setFormData({ ...formData, source_type: e.target.value })
                }
                className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
              >
                <option value="WEB">Website (HTML)</option>
                <option value="RSS">RSS Feed</option>
              </select>
            </div>
          </div>
          {error && (
            <p className="text-sm text-red-400">{error}</p>
          )}
          <div className="flex gap-2">
            <button
              type="submit"
              className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500"
            >
              Lưu
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-lg bg-[hsl(var(--secondary))] px-4 py-2 text-sm font-medium text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
            >
              Hủy
            </button>
          </div>
        </form>
      )}

      {/* Sources Table */}
      <div className="chart-container overflow-hidden">
        <div className="overflow-x-auto">
          <table className="data-table w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                <th className="px-5 py-3 font-medium">Tên</th>
                <th className="px-5 py-3 font-medium">URL</th>
                <th className="px-5 py-3 font-medium">Loại</th>
                <th className="px-5 py-3 font-medium">Trạng thái</th>
                <th className="px-5 py-3 font-medium">Hành động</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[hsl(var(--border))]">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center">
                    <div className="flex justify-center">
                      <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
                    </div>
                  </td>
                </tr>
              ) : sources.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-5 py-12 text-center text-[hsl(var(--muted-foreground))]"
                  >
                    Chưa có nguồn tin nào. Nhấn &quot;Thêm nguồn&quot; để bắt đầu.
                  </td>
                </tr>
              ) : (
                sources.map((source) => (
                  <tr key={source._id}>
                    <td className="px-5 py-3 font-medium text-[hsl(var(--foreground))]">
                      <div className="flex items-center gap-2">
                        {source.source_type === "RSS" ? (
                          <Rss className="h-4 w-4 text-orange-400" />
                        ) : (
                          <Globe className="h-4 w-4 text-cyan-400" />
                        )}
                        {source.name}
                      </div>
                    </td>
                    <td className="max-w-[300px] truncate px-5 py-3 text-[hsl(var(--muted-foreground))]">
                      {source.url}
                    </td>
                    <td className="px-5 py-3">
                      <span className="rounded-md bg-[hsl(var(--secondary))] px-2 py-0.5 text-xs">
                        {source.source_type}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <button
                        onClick={() => handleToggle(source)}
                        className="flex items-center gap-1.5"
                      >
                        {source.is_active ? (
                          <>
                            <ToggleRight className="h-5 w-5 text-emerald-400" />
                            <span className="text-xs text-emerald-400">
                              Hoạt động
                            </span>
                          </>
                        ) : (
                          <>
                            <ToggleLeft className="h-5 w-5 text-gray-500" />
                            <span className="text-xs text-gray-500">
                              Tạm dừng
                            </span>
                          </>
                        )}
                      </button>
                    </td>
                    <td className="px-5 py-3">
                      <button
                        onClick={() => handleDelete(source._id)}
                        className="rounded-lg p-1.5 text-gray-500 transition-colors hover:bg-red-500/10 hover:text-red-400"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
