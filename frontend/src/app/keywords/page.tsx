"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, ToggleLeft, ToggleRight, Hash } from "lucide-react";
import { keywordsApi } from "@/lib/api";

interface Keyword {
  _id: string;
  value: string;
  is_active: boolean;
  created_at: string;
}

export default function KeywordsPage() {
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [loading, setLoading] = useState(true);
  const [newKeyword, setNewKeyword] = useState("");
  const [showInput, setShowInput] = useState(false);

  const fetchKeywords = async () => {
    try {
      const res = await keywordsApi.list();
      setKeywords((res.data as Keyword[]) || []);
    } catch (err) {
      console.error("Failed to load keywords:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeywords();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyword.trim()) return;

    try {
      await keywordsApi.create({ value: newKeyword.trim() });
      setNewKeyword("");
      setShowInput(false);
      fetchKeywords();
    } catch (err) {
      console.error("Failed to create keyword:", err);
    }
  };

  const handleToggle = async (keyword: Keyword) => {
    try {
      await keywordsApi.update(keyword._id, {
        is_active: !keyword.is_active,
      });
      fetchKeywords();
    } catch (err) {
      console.error("Failed to toggle keyword:", err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Bạn có chắc muốn xóa từ khóa này?")) return;
    try {
      await keywordsApi.delete(id);
      fetchKeywords();
    } catch (err) {
      console.error("Failed to delete keyword:", err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Từ khóa</h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Quản lý danh sách từ khóa mục tiêu để lọc tin tức liên quan
          </p>
        </div>
        <button
          onClick={() => setShowInput(!showInput)}
          className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2.5 text-sm font-medium text-white shadow-lg shadow-cyan-500/20 transition-all hover:shadow-cyan-500/30 hover:brightness-110"
        >
          <Plus className="h-4 w-4" />
          Thêm từ khóa
        </button>
      </div>

      {/* Add Keyword Input */}
      {showInput && (
        <form
          onSubmit={handleCreate}
          className="glass-card flex gap-3 rounded-xl p-4"
        >
          <input
            type="text"
            value={newKeyword}
            onChange={(e) => setNewKeyword(e.target.value)}
            placeholder='VD: "sân bay Long Thành", "Vietur", "bụi đỏ"...'
            className="flex-1 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-white placeholder:text-[hsl(var(--muted-foreground))] focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
            autoFocus
          />
          <button
            type="submit"
            className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500"
          >
            Lưu
          </button>
          <button
            type="button"
            onClick={() => setShowInput(false)}
            className="rounded-lg bg-[hsl(var(--secondary))] px-4 py-2 text-sm font-medium text-[hsl(var(--muted-foreground))] hover:text-white"
          >
            Hủy
          </button>
        </form>
      )}

      {/* Keywords Grid */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
        </div>
      ) : keywords.length === 0 ? (
        <div className="glass-card rounded-xl py-16 text-center">
          <Hash className="mx-auto h-10 w-10 text-[hsl(var(--muted-foreground))]" />
          <p className="mt-3 text-sm text-[hsl(var(--muted-foreground))]">
            Chưa có từ khóa. Thêm từ khóa để bắt đầu lọc tin tức.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {keywords.map((keyword) => (
            <div
              key={keyword._id}
              className="glass-card flex items-center justify-between rounded-xl px-4 py-3"
            >
              <div className="flex items-center gap-3">
                <Hash className="h-4 w-4 text-cyan-400" />
                <span
                  className={`text-sm font-medium ${
                    keyword.is_active
                      ? "text-white"
                      : "text-[hsl(var(--muted-foreground))] line-through"
                  }`}
                >
                  {keyword.value}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => handleToggle(keyword)}
                  className="rounded-lg p-1.5 transition-colors hover:bg-[hsl(var(--secondary))]"
                >
                  {keyword.is_active ? (
                    <ToggleRight className="h-5 w-5 text-emerald-400" />
                  ) : (
                    <ToggleLeft className="h-5 w-5 text-gray-500" />
                  )}
                </button>
                <button
                  onClick={() => handleDelete(keyword._id)}
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
