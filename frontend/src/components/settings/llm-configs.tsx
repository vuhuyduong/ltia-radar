"use client";

import { useEffect, useState } from "react";
import {
  Plus,
  Trash2,
  ToggleLeft,
  ToggleRight,
  Brain,
  Key,
  Star,
  Activity,
  CheckCircle,
  XCircle,
  Edit,
  Eye,
  EyeOff,
  Copy,
  BookOpen,
  Sparkles,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { llmConfigsApi, llmPromptsApi } from "@/lib/api";

interface LLMConfig {
  _id: string;
  provider: string;
  model_name: string;
  api_key: string;
  is_active: boolean;
  is_default: boolean;
  description: string;
  created_at: string;
}

interface LLMPrompt {
  _id: string;
  name: string;
  system_prompt: string;
  batch_system_prompt: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

const POPULAR_MODELS = [
  { provider: "Google Gemini", model: "gemini-3.5-flash", label: "Gemini 3.5 Flash (Mặc định)" },
  { provider: "Google Gemini", model: "gemini-3-flash-preview", label: "Gemini 3 Flash" },
  { provider: "Google Gemini", model: "gemini-2.5-flash", label: "Gemini 2.5 Flash" },
  { provider: "Google Gemini", model: "gemini-2.5-pro", label: "Gemini 2.5 Pro" },
  { provider: "Groq", model: "llama-3.3-70b-versatile", label: "Llama 3.3 70B (Groq)" },
  { provider: "Groq", model: "llama-3.1-8b-instant", label: "Llama 3.1 8B (Groq)" },
  { provider: "OpenAI", model: "gpt-4o", label: "GPT-4o" },
  { provider: "OpenAI", model: "gpt-4o-mini", label: "GPT-4o Mini" },
  { provider: "Anthropic", model: "claude-3-5-sonnet", label: "Claude 3.5 Sonnet" },
];

const DEFAULT_SYSTEM_PROMPT = `Bạn là một chuyên gia phân tích rủi ro truyền thông và cảnh báo sớm cho Dự án Cảng Hàng không Quốc tế Long Thành (LTIA).

Nhiệm vụ: Phân tích bài viết báo chí/mạng xã hội và trích xuất thông tin có cấu trúc.

BỐI CẢNH DỰ ÁN:
- Dự án sân bay Long Thành là siêu dự án trọng điểm quốc gia, mốc khánh thành 01/12/2026
- Các gói thầu quan trọng: Gói 5.10 (Nhà ga, Vietur, 35.000 tỷ), Gói 4.6 (Đường cất hạ cánh)
- Chủ đầu tư: Tổng Công ty Cảng hàng không Việt Nam (ACV)
- Các vấn đề nhạy cảm: tiến độ, bụi/ô nhiễm, giải phóng mặt bằng, thiếu vật liệu, an toàn lao động
- Diện tích thu hồi đất: 2.465 ha tại Long Thành, Nhơn Trạch

QUY TẮC PHÂN TÍCH:
1. CRITICAL: Sự cố nghiêm trọng (tai nạn chết người, đình chỉ dự án, xử phạt pháp lý nặng, đình công quy mô lớn), bài viết phản ánh sai phạm lớn của lãnh đạo ACV hoặc nhà thầu.
2. HIGH: Vấn đề ảnh hưởng tiến độ thi công (thiếu cát san lấp, chậm giải ngân vốn đầu tư công trực tiếp cho dự án, chậm bàn giao mặt bằng thi công, thay đổi nhà thầu gói thầu chính).
3. MEDIUM: Thông tin dự án cần theo dõi (cập nhật tiến độ hàng tuần, hội nghị điều phối dự án, điều chỉnh thông số kỹ thuật phụ).
4. LOW: Tin tức thông thường hoặc quảng bá tích cực (hình ảnh tiến độ đẹp, khen thưởng, ký kết hợp tác thương mại thông thường).
5. is_rumor=true: Khi bài viết chứa thông tin chưa xác minh, nguồn ẩn danh, mạng xã hội đồn đoán chưa được báo chí chính thống đăng tải.
6. is_relevant=true/false (QUY TẮC RẤT NGHIÊM NGẶT - TRÁNH TIN RÁC):
   - Đặt là true NẾU VÀ CHỈ NẾU bài viết trực tiếp nhắc đến Dự án Cảng Hàng không Quốc tế Long Thành (sân bay Long Thành), Tổng Công ty Cảng hàng không Việt Nam (ACV), hoặc các gói thầu, nhân sự lãnh đạo, dự án/hoạt động hàng không trực thuộc ACV.
   - BẮT BUỘC đặt là false nếu bài viết chỉ trùng từ khóa chung nhưng nói về địa phương khác hoặc dự án khác không liên quan đến sân bay Long Thành (Ví dụ: bồi thường giải phóng mặt bằng ở Hà Nội, Hải Dương, Lạng Sơn; tin thời sự chung quốc tế, quốc phòng; tình hình giải ngân đầu tư công của các bộ ngành khác).
   - Nếu bài viết KHÔNG nhắc đến "Long Thành", "sân bay Long Thành" hoặc "ACV" trong tiêu đề hay nội dung cốt lõi, hãy đặt is_relevant = false.

Trả về JSON thuần túy (không markdown, không code block) với cấu trúc sau:
{
  "category": ["<danh mục>"],
  "sentiment": "<POSITIVE|NEGATIVE|NEUTRAL>",
  "target_scope": ["<phạm vi ảnh hưởng>"],
  "impact_level": "<CRITICAL|HIGH|MEDIUM|LOW>",
  "key_entities": [{"name": "<tên>", "type": "<organization|person|agency|contractor>"}],
  "executive_summary": "<tóm tắt 1-2 câu cốt lõi sự việc>",
  "is_rumor": <true|false>,
  "is_relevant": <true|false>
}

Danh mục hợp lệ: Tiến độ, Kỹ thuật, Môi trường, Đấu thầu, Dư luận, An toàn lao động, Giải phóng mặt bằng, Tài chính, Pháp lý
Phạm vi: "Toàn dự án", "Gói thầu 5.10", "Gói thầu 4.6", hoặc hạng mục cụ thể`;

const DEFAULT_BATCH_SYSTEM_PROMPT = `Bạn là một chuyên gia phân tích rủi ro truyền thông và cảnh báo sớm cho Dự án Cảng Hàng không Quốc tế Long Thành (LTIA).

Nhiệm vụ: Phân tích danh sách các bài viết báo chí/mạng xã hội và trích xuất thông tin có cấu trúc cho từng bài viết.

BỐI CẢNH DỰ ÁN:
- Dự án sân bay Long Thành là siêu dự án trọng điểm quốc gia, mốc khánh thành 01/12/2026
- Các gói thầu quan trọng: Gói 5.10 (Nhà ga, Vietur, 35.000 tỷ), Gói 4.6 (Đường cất hạ cánh)
- Chủ đầu tư: Tổng Công ty Cảng hàng không Việt Nam (ACV)
- Các vấn đề nhạy cảm: tiến độ, bụi/ô nhiễm, giải phóng mặt bằng, thiếu vật liệu, an toàn lao động
- Diện tích thu hồi đất: 2.465 ha tại Long Thành, Nhơn Trạch

QUY TẮC PHÂN TÍCH:
1. CRITICAL: Sự cố nghiêm trọng (tai nạn chết người, đình chỉ dự án, xử phạt pháp lý nặng, đình công quy mô lớn), bài viết phản ánh sai phạm lớn của lãnh đạo ACV hoặc nhà thầu.
2. HIGH: Vấn đề ảnh hưởng tiến độ thi công (thiếu cát san lấp, chậm giải ngân vốn đầu tư công trực tiếp cho dự án, chậm bàn giao mặt bằng thi công, thay đổi nhà thầu gói thầu chính).
3. MEDIUM: Thông tin dự án cần theo dõi (cập nhật tiến độ hàng tuần, hội nghị điều phối dự án, điều chỉnh thông số kỹ thuật phụ).
4. LOW: Tin tức thông thường hoặc quảng bá tích cực (hình ảnh tiến độ đẹp, khen thưởng, ký kết hợp tác thương mại thông thường).
5. is_rumor=true: Khi bài viết chứa thông tin chưa xác minh, nguồn ẩn danh, mạng xã hội đồn đoán chưa được báo chí chính thống đăng tải.
6. is_relevant=true/false (QUY TẮC RẤT NGHIÊM NGẶT - TRÁNH TIN RÁC):
   - Đặt là true NẾU VÀ CHỈ NẾU bài viết trực tiếp nhắc đến Dự án Cảng Hàng không Quốc tế Long Thành (sân bay Long Thành), Tổng Công ty Cảng hàng không Việt Nam (ACV), hoặc các gói thầu, nhân sự lãnh đạo, dự án/hoạt động hàng không trực thuộc ACV.
   - BẮT BUỘC đặt là false nếu bài viết chỉ trùng từ khóa chung nhưng nói về địa phương khác hoặc dự án khác không liên quan đến sân bay Long Thành (Ví dụ: bồi thường giải phóng mặt bằng ở Hà Nội, Hải Dương, Lạng Sơn; tin thời sự chung quốc tế, quốc phòng; tình hình giải ngân đầu tư công của các bộ ngành khác).
   - Nếu bài viết KHÔNG nhắc đến "Long Thành", "sân bay Long Thành" hoặc "ACV" trong tiêu đề hay nội dung cốt lõi, hãy đặt is_relevant = false.

Trả về mảng JSON thuần túy (không markdown, không code block) đại diện cho kết quả phân tích tương ứng của từng bài viết trong mảng đầu vào, theo đúng thứ tự:
[
  {
    "index": <số thứ tự tương ứng, từ 0>,
    "category": ["<danh mục>"],
    "sentiment": "<POSITIVE|NEGATIVE|NEUTRAL>",
    "target_scope": ["<phạm vi ảnh hưởng>"],
    "impact_level": "<CRITICAL|HIGH|MEDIUM|LOW>",
    "key_entities": [{"name": "<tên>", "type": "<organization|person|agency|contractor>"}],
    "executive_summary": "<tóm tắt 1-2 câu cốt lõi sự việc>",
    "is_rumor": <true|false>,
    "is_relevant": <true|false>
  },
  ...
]

Danh mục hợp lệ: Tiến độ, Kỹ thuật, Môi trường, Đấu thầu, Dư luận, An toàn lao động, Giải phóng mặt bằng, Tài chính, Pháp lý
Phạm vi: "Toàn dự án", "Gói thầu 5.10", "Gói thầu 4.6", hoặc hạng mục cụ thể`;

export default function LLMConfigsPage() {
  const [activeTab, setActiveTab] = useState<"configs" | "prompts">("configs");
  const [configs, setConfigs] = useState<LLMConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [showInput, setShowInput] = useState(false);

  // Form states (LLM configs)
  const [provider, setProvider] = useState("Google Gemini");
  const [modelName, setModelName] = useState("gemini-3.5-flash");
  const [apiKey, setApiKey] = useState("");
  const [description, setDescription] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [isDefault, setIsDefault] = useState(false);

  // Test states
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ [id: string]: { status: "success" | "failed"; message: string } }>({});

  // ── LLM Prompts states ──
  const [prompts, setPrompts] = useState<LLMPrompt[]>([]);
  const [loadingPrompts, setLoadingPrompts] = useState(false);
  const [showPromptForm, setShowPromptForm] = useState(false);
  const [editPromptId, setEditPromptId] = useState<string | null>(null);
  
  // Prompt form inputs
  const [promptName, setPromptName] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [batchSystemPrompt, setBatchSystemPrompt] = useState("");
  const [activatePromptImmediately, setActivatePromptImmediately] = useState(false);

  // Expanded prompt previews
  const [expandedPromptIds, setExpandedPromptIds] = useState<{ [id: string]: boolean }>({});

  // Guide accordions
  const [openGuideSection, setOpenGuideSection] = useState<string | null>("structure");

  const fetchConfigs = async () => {
    try {
      const res = await llmConfigsApi.list();
      setConfigs((res.data as LLMConfig[]) || []);
    } catch (err) {
      console.error("Failed to load LLM configurations:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchPrompts = async () => {
    setLoadingPrompts(true);
    try {
      const res = await llmPromptsApi.list();
      setPrompts((res.data as LLMPrompt[]) || []);
    } catch (err) {
      console.error("Failed to load LLM prompts:", err);
    } finally {
      setLoadingPrompts(false);
    }
  };

  useEffect(() => {
    fetchConfigs();
    fetchPrompts();
  }, []);

  const handleModelSelect = (selectedModel: string) => {
    setModelName(selectedModel);
    const popular = POPULAR_MODELS.find((m) => m.model === selectedModel);
    if (popular) {
      setProvider(popular.provider);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim() || !modelName.trim()) return;

    try {
      await llmConfigsApi.create({
        provider,
        model_name: modelName.trim(),
        api_key: apiKey.trim(),
        is_active: isActive,
        is_default: isDefault,
        description: description.trim(),
      });
      setApiKey("");
      setDescription("");
      setIsDefault(false);
      setShowInput(false);
      fetchConfigs();
    } catch (err) {
      console.error("Failed to create LLM configuration:", err);
      alert("Lỗi khi thêm cấu hình: " + (err as Error).message);
    }
  };

  const handleToggle = async (config: LLMConfig) => {
    try {
      await llmConfigsApi.update(config._id, {
        is_active: !config.is_active,
      });
      fetchConfigs();
    } catch (err) {
      console.error("Failed to toggle configuration:", err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Bạn có chắc muốn xóa cấu hình API key này?")) return;
    try {
      await llmConfigsApi.delete(id);
      fetchConfigs();
    } catch (err) {
      console.error("Failed to delete configuration:", err);
    }
  };

  const handleSetDefault = async (id: string) => {
    try {
      await llmConfigsApi.setDefault(id);
      fetchConfigs();
    } catch (err) {
      console.error("Failed to set default model:", err);
    }
  };

  const handleTestKey = async (id: string) => {
    setTestingId(id);
    setTestResult((prev) => {
      const copy = { ...prev };
      delete copy[id];
      return copy;
    });

    try {
      const res = await llmConfigsApi.test(id);
      setTestResult((prev) => ({
        ...prev,
        [id]: {
          status: res.status as "success" | "failed",
          message: res.message,
        },
      }));
    } catch (err) {
      setTestResult((prev) => ({
        ...prev,
        [id]: {
          status: "failed",
          message: (err as Error).message,
        },
      }));
    } finally {
      setTestingId(null);
    }
  };

  // ── Prompt CRUD Handlers ──
  const handleLoadSamplePrompt = () => {
    setPromptName("Prompt phân tích rủi ro LTIA nâng cao");
    setSystemPrompt(DEFAULT_SYSTEM_PROMPT);
    setBatchSystemPrompt(DEFAULT_BATCH_SYSTEM_PROMPT);
  };

  const handleOpenNewPromptForm = () => {
    setEditPromptId(null);
    setPromptName("");
    setSystemPrompt("");
    setBatchSystemPrompt("");
    setActivatePromptImmediately(false);
    setShowPromptForm(true);
  };

  const handleOpenEditPromptForm = (prompt: LLMPrompt) => {
    setEditPromptId(prompt._id);
    setPromptName(prompt.name);
    setSystemPrompt(prompt.system_prompt);
    setBatchSystemPrompt(prompt.batch_system_prompt);
    setActivatePromptImmediately(prompt.is_active);
    setShowPromptForm(true);
  };

  const handleSavePrompt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!promptName.trim() || !systemPrompt.trim() || !batchSystemPrompt.trim()) {
      alert("Vui lòng nhập đầy đủ thông tin của Prompt.");
      return;
    }

    try {
      if (editPromptId) {
        // Update existing prompt
        await llmPromptsApi.update(editPromptId, {
          name: promptName.trim(),
          system_prompt: systemPrompt.trim(),
          batch_system_prompt: batchSystemPrompt.trim(),
          is_active: activatePromptImmediately,
        });
      } else {
        // Create new prompt
        await llmPromptsApi.create({
          name: promptName.trim(),
          system_prompt: systemPrompt.trim(),
          batch_system_prompt: batchSystemPrompt.trim(),
          is_active: activatePromptImmediately,
        });
      }
      setShowPromptForm(false);
      setEditPromptId(null);
      fetchPrompts();
    } catch (err) {
      console.error("Failed to save LLM prompt:", err);
      alert("Lỗi khi lưu prompt: " + (err as Error).message);
    }
  };

  const handleSetActivePrompt = async (id: string) => {
    try {
      await llmPromptsApi.setActive(id);
      fetchPrompts();
    } catch (err) {
      console.error("Failed to activate prompt:", err);
      alert("Lỗi khi kích hoạt prompt: " + (err as Error).message);
    }
  };

  const handleDeletePrompt = async (prompt: LLMPrompt) => {
    if (prompt.is_active) {
      alert("Không thể xóa Prompt đang hoạt động. Hãy kích hoạt Prompt khác trước khi xóa.");
      return;
    }
    if (!confirm(`Bạn có chắc muốn xóa cấu hình prompt "${prompt.name}"?`)) return;
    try {
      await llmPromptsApi.delete(prompt._id);
      fetchPrompts();
    } catch (err) {
      console.error("Failed to delete prompt:", err);
      alert("Lỗi khi xóa prompt: " + (err as Error).message);
    }
  };

  const toggleExpandPrompt = (id: string) => {
    setExpandedPromptIds((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const handleCopyText = (text: string) => {
    navigator.clipboard.writeText(text);
    alert("Đã sao chép prompt vào Clipboard!");
  };

  const toggleGuideSection = (section: string) => {
    setOpenGuideSection(openGuideSection === section ? null : section);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-[hsl(var(--foreground))] flex items-center gap-2">
            <Brain className="h-5 w-5 text-cyan-500 dark:text-cyan-400" />
            Cấu hình AI & Prompt
          </h2>
          <p className="mt-0.5 text-xs text-[hsl(var(--muted-foreground))]">
            Quản lý API Key, mô hình ngôn ngữ và tùy chỉnh các prompt hướng dẫn phân tích cho Gemini.
          </p>
        </div>

        {activeTab === "configs" ? (
          <button
            onClick={() => setShowInput(!showInput)}
            className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-3.5 py-2 text-xs font-semibold text-white shadow-lg shadow-cyan-500/20 transition-all hover:shadow-cyan-500/30 hover:brightness-110"
          >
            <Plus className="h-3.5 w-3.5" />
            Thêm API Key
          </button>
        ) : (
          !showPromptForm && (
            <button
              onClick={handleOpenNewPromptForm}
              className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-3.5 py-2 text-xs font-semibold text-white shadow-lg shadow-cyan-500/20 transition-all hover:shadow-cyan-500/30 hover:brightness-110"
            >
              <Plus className="h-3.5 w-3.5" />
              Thêm Prompt Mới
            </button>
          )
        )}
      </div>

      {/* Tab Selector */}
      <div className="flex border-b border-[hsl(var(--border))]">
        <button
          onClick={() => setActiveTab("configs")}
          className={`flex items-center gap-2 border-b-2 px-5 py-2.5 text-xs font-semibold transition-all duration-200 ${
            activeTab === "configs"
              ? "border-cyan-500 text-cyan-600 dark:text-cyan-400 font-bold"
              : "border-transparent text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
          }`}
        >
          <Key className="h-3.5 w-3.5" />
          Cấu hình API Key & Model
        </button>
        <button
          onClick={() => setActiveTab("prompts")}
          className={`flex items-center gap-2 border-b-2 px-5 py-2.5 text-xs font-semibold transition-all duration-200 ${
            activeTab === "prompts"
              ? "border-cyan-500 text-cyan-600 dark:text-cyan-400 font-bold"
              : "border-transparent text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
          }`}
        >
          <Brain className="h-3.5 w-3.5" />
          Cấu hình Prompt Phân Tích
        </button>
      </div>

      {/* ── TAB 1: API CONFIGS & MODEL ── */}
      {activeTab === "configs" && (
        <div className="space-y-6">
          {/* Info Warning/Tips */}
          <div className="rounded-xl border border-cyan-500/20 bg-cyan-50 dark:bg-cyan-950/20 p-4">
            <h3 className="text-sm font-semibold text-cyan-800 dark:text-cyan-300">💡 Cơ chế Xoay vòng & Tránh Rate Limit</h3>
            <p className="mt-1 text-xs text-cyan-700 dark:text-cyan-200/70 leading-relaxed">
              - <strong>Xoay vòng Key (Rotation)</strong>: Nếu bạn thêm nhiều API key cho cùng một mô hình, hệ thống sẽ tự động phân phối các yêu cầu ngẫu nhiên/xoay vòng giữa các key hoạt động để tăng giới hạn số lượng cuộc gọi (RPM).
              <br />
              - <strong>Tự động khôi phục (Fallback)</strong>: Khi một API key gặp lỗi (như hết hạn, sai cấu hình, hoặc bị rate limit), hệ thống sẽ thử lại bằng key hoạt động tiếp theo trong pool.
              <br />
              - <strong>Gom lô (Batching)</strong>: Hệ thống sẽ tự động gộp nhiều bài báo vào trong một submit duy nhất để gửi đến mô hình, giúp tiết kiệm số lượng request đáng kể (stay within 5 RPM).
            </p>
          </div>

          {/* Add LLM Configuration Form */}
          {showInput && (
            <form
              onSubmit={handleCreate}
              className="glass-card space-y-4 rounded-xl p-5"
            >
              <h3 className="text-sm font-semibold text-[hsl(var(--foreground))]">Thêm API Key & Mô hình mới</h3>
              
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <label className="block text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5">
                    Chọn mô hình phổ biến
                  </label>
                  <select
                    value={modelName}
                    onChange={(e) => handleModelSelect(e.target.value)}
                    className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                  >
                    {POPULAR_MODELS.map((m) => (
                      <option key={m.model} value={m.model}>
                        {m.label} ({m.provider})
                      </option>
                    ))}
                    <option value="custom">-- Tự nhập mô hình khác --</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5">
                    Nhà cung cấp (Provider)
                  </label>
                  <input
                    type="text"
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    placeholder="VD: Google Gemini, OpenAI..."
                    className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                  />
                </div>

                {modelName === "custom" && (
                  <div className="md:col-span-2">
                    <label className="block text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5">
                      Tên Mô hình (Model Name) định danh API
                    </label>
                    <input
                      type="text"
                      placeholder="VD: gemini-3.1-flash-lite, gpt-4o-mini..."
                      onChange={(e) => setModelName(e.target.value)}
                      className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                    />
                  </div>
                )}

                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5">
                    API Key
                  </label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="Nhập API Key ở đây"
                    className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))]/50 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                    required
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5">
                    Mô tả (Tùy chọn)
                  </label>
                  <input
                    type="text"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="VD: Key phụ (5 RPM) hoặc Key dự phòng"
                    className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                  />
                </div>

                <div className="flex items-center gap-6 py-2 col-span-2">
                  <label className="flex items-center gap-2 text-sm text-[hsl(var(--foreground))] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isActive}
                      onChange={(e) => setIsActive(e.target.checked)}
                      className="rounded border-[hsl(var(--border))] bg-[hsl(var(--secondary))] text-cyan-600 focus:ring-cyan-500"
                    />
                    Kích hoạt key này
                  </label>
                  <label className="flex items-center gap-2 text-sm text-[hsl(var(--foreground))] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isDefault}
                      onChange={(e) => setIsDefault(e.target.checked)}
                      className="rounded border-[hsl(var(--border))] bg-[hsl(var(--secondary))] text-cyan-600 focus:ring-cyan-500"
                    />
                    Đặt mô hình này làm mặc định
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="submit"
                  className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500"
                >
                  Lưu cấu hình
                </button>
                <button
                  type="button"
                  onClick={() => setShowInput(false)}
                  className="rounded-lg bg-[hsl(var(--secondary))] px-4 py-2 text-sm font-medium text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                >
                  Hủy
                </button>
              </div>
            </form>
          )}

          {/* Configs Table / List */}
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
            </div>
          ) : configs.length === 0 ? (
            <div className="glass-card rounded-xl py-16 text-center">
              <Key className="mx-auto h-10 w-10 text-[hsl(var(--muted-foreground))]" />
              <p className="mt-3 text-sm text-[hsl(var(--muted-foreground))]">
                Chưa có cấu hình API Key nào được cài đặt.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {configs.map((config) => {
                const hasTestResult = !!testResult[config._id];
                const result = testResult[config._id];

                return (
                  <div
                    key={config._id}
                    className="glass-card flex flex-col md:flex-row md:items-center justify-between gap-4 rounded-xl p-5 transition-all duration-200 hover:border-cyan-500/20"
                  >
                    <div className="space-y-1.5 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="rounded-md bg-cyan-500/10 px-2 py-0.5 text-xs font-semibold text-cyan-600 dark:text-cyan-400">
                          {config.provider}
                        </span>
                        <span className="text-sm font-bold text-[hsl(var(--foreground))]">
                          {config.model_name}
                        </span>
                        {config.is_default && (
                          <span className="flex items-center gap-1 rounded-md bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold text-amber-400 border border-amber-500/20">
                            <Star className="h-3 w-3 fill-amber-400" />
                            Mặc định
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-[hsl(var(--muted-foreground))] font-mono flex items-center gap-1.5">
                        <Key className="h-3 w-3" />
                        ••••••••••••••••{config.api_key.substring(config.api_key.length - 8)}
                      </p>
                      {config.description && (
                        <p className="text-xs text-[hsl(var(--muted-foreground))] italic">
                          Mô tả: {config.description}
                        </p>
                      )}
                    </div>

                    <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                      {/* Test Connection Display */}
                      {hasTestResult && (
                        <div
                          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium ${
                            result.status === "success"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : "bg-red-500/10 text-red-400 border border-red-500/20"
                          }`}
                        >
                          {result.status === "success" ? (
                            <CheckCircle className="h-3.5 w-3.5" />
                          ) : (
                            <XCircle className="h-3.5 w-3.5" />
                          )}
                          <span className="truncate max-w-[150px]" title={result.message}>
                            {result.message}
                          </span>
                        </div>
                      )}

                      {/* Actions */}
                      <div className="flex items-center gap-2">
                        {/* Test Button */}
                        <button
                          onClick={() => handleTestKey(config._id)}
                          disabled={testingId === config._id}
                          className="flex items-center gap-1 rounded-lg bg-[hsl(var(--secondary))] px-3 py-1.5 text-xs font-medium text-[hsl(var(--foreground))] hover:bg-[hsl(var(--border))] disabled:opacity-50"
                        >
                          <Activity className={`h-3.5 w-3.5 ${testingId === config._id ? "animate-pulse text-cyan-500 dark:text-cyan-400" : ""}`} />
                          {testingId === config._id ? "Đang thử..." : "Thử kết nối"}
                        </button>

                        {/* Set Default Button */}
                        {!config.is_default && config.is_active && (
                          <button
                            onClick={() => handleSetDefault(config._id)}
                            className="rounded-lg p-1.5 text-[hsl(var(--muted-foreground))] hover:bg-amber-500/10 hover:text-amber-500 dark:hover:text-amber-400 transition-colors"
                            title="Đặt làm mặc định"
                          >
                            <Star className="h-4.5 w-4.5" />
                          </button>
                        )}

                        {/* Active/Inactive Toggle */}
                        <button
                          onClick={() => handleToggle(config)}
                          className="rounded-lg p-1 transition-colors hover:bg-[hsl(var(--secondary))]"
                        >
                          {config.is_active ? (
                            <ToggleRight className="h-6 w-6 text-emerald-400" />
                          ) : (
                            <ToggleLeft className="h-6 w-6 text-[hsl(var(--muted-foreground))]" />
                          )}
                        </button>

                        {/* Delete Button */}
                        <button
                          onClick={() => handleDelete(config._id)}
                          className="rounded-lg p-1.5 text-[hsl(var(--muted-foreground))] transition-colors hover:bg-red-500/10 hover:text-red-500 dark:hover:text-red-400"
                        >
                          <Trash2 className="h-4.5 w-4.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── TAB 2: ANALYSIS PROMPTS CUSTOMIZATION ── */}
      {activeTab === "prompts" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start animate-fadeIn">
          {/* Main prompt management area (Left column: 7/12) */}
          <div className="lg:col-span-7 space-y-6">
            
            {/* Prompt Editor Form */}
            {showPromptForm && (
              <form onSubmit={handleSavePrompt} className="glass-card p-5 rounded-xl space-y-4 border border-cyan-500/30">
                <div className="flex items-center justify-between border-b border-[hsl(var(--border))] pb-2.5">
                  <h3 className="text-sm font-bold text-[hsl(var(--foreground))] flex items-center gap-1.5">
                    <Sparkles className="h-4 w-4 text-cyan-500 dark:text-cyan-400" />
                    {editPromptId ? "Chỉnh sửa Prompt" : "Tạo Prompt Phân Tích Mới"}
                  </h3>
                  <button
                    type="button"
                    onClick={handleLoadSamplePrompt}
                    className="text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-cyan-500/20 bg-cyan-500/10 dark:bg-cyan-950/20 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500 hover:text-white transition-all flex items-center gap-1"
                    title="Nạp cấu trúc & nội dung prompt mẫu chuẩn"
                  >
                    <BookOpen className="h-3 w-3" />
                    Nạp prompt mẫu
                  </button>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1.5">
                      Tên cấu hình Prompt
                    </label>
                    <input
                      type="text"
                      value={promptName}
                      onChange={(e) => setPromptName(e.target.value)}
                      placeholder="VD: Cấu hình phân tích rủi ro LTIA chuẩn"
                      className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-sm text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none"
                      required
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="block text-xs font-medium text-[hsl(var(--muted-foreground))]">
                        System Instruction (Bài viết đơn lẻ - Single Article)
                      </label>
                      <span className="text-[10px] text-[hsl(var(--muted-foreground))] italic">Dùng để phân tích một bài báo cụ thể</span>
                    </div>
                    <textarea
                      value={systemPrompt}
                      onChange={(e) => setSystemPrompt(e.target.value)}
                      placeholder="Nhập hướng dẫn phân tích bài báo đơn lẻ ở đây..."
                      className="w-full h-48 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-xs font-mono text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none resize-y"
                      required
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="block text-xs font-medium text-[hsl(var(--muted-foreground))]">
                        System Instruction (Gom lô nhiều bài viết - Batch Articles)
                      </label>
                      <span className="text-[10px] text-[hsl(var(--muted-foreground))] italic">Dùng để phân tích đồng thời nhiều bài viết (tiết kiệm RPM)</span>
                    </div>
                    <textarea
                      value={batchSystemPrompt}
                      onChange={(e) => setBatchSystemPrompt(e.target.value)}
                      placeholder="Nhập hướng dẫn phân tích lô nhiều bài viết ở đây..."
                      className="w-full h-48 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--secondary))] px-3 py-2 text-xs font-mono text-[hsl(var(--foreground))] focus:border-cyan-500 focus:outline-none resize-y"
                      required
                    />
                  </div>

                  <div className="flex items-center py-2">
                    <label className="flex items-center gap-2 text-xs text-[hsl(var(--foreground))] cursor-pointer">
                      <input
                        type="checkbox"
                        checked={activatePromptImmediately}
                        onChange={(e) => setActivatePromptImmediately(e.target.checked)}
                        className="rounded border-[hsl(var(--border))] bg-[hsl(var(--secondary))] text-cyan-600 focus:ring-cyan-500"
                      />
                      Kích hoạt làm Prompt hoạt động chính thức ngay sau khi lưu
                    </label>
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-3 border-t border-[hsl(var(--border))]">
                  <button
                    type="submit"
                    className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500 transition-colors"
                  >
                    Lưu cấu hình
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowPromptForm(false);
                      setEditPromptId(null);
                    }}
                    className="rounded-lg bg-[hsl(var(--secondary))] px-4 py-2 text-sm font-medium text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-colors"
                  >
                    Hủy
                  </button>
                </div>
              </form>
            )}

            {/* Prompt List */}
            {loadingPrompts ? (
              <div className="flex justify-center py-12">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
              </div>
            ) : prompts.length === 0 ? (
              <div className="glass-card rounded-xl py-16 text-center">
                <Brain className="mx-auto h-10 w-10 text-[hsl(var(--muted-foreground))]" />
                <p className="mt-3 text-sm text-[hsl(var(--muted-foreground))]">
                  Chưa có prompt cấu hình tùy chỉnh nào trong database.
                </p>
                <button
                  onClick={handleOpenNewPromptForm}
                  className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-cyan-500/10 dark:bg-cyan-600/20 border border-cyan-500/30 hover:bg-cyan-600 hover:text-white dark:hover:bg-cyan-600/30 text-cyan-600 dark:text-cyan-400 px-3.5 py-2 text-xs font-semibold"
                >
                  <Plus className="h-3.5 w-3.5" /> Tạo prompt đầu tiên
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {prompts.map((prompt) => {
                  const isExpanded = !!expandedPromptIds[prompt._id];
                  
                  return (
                    <div
                      key={prompt._id}
                      className={`glass-card rounded-xl p-5 border transition-all duration-200 ${
                        prompt.is_active ? "border-cyan-500/40 bg-cyan-500/5" : "hover:border-cyan-500/20"
                      }`}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[hsl(var(--border))]/50">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-[hsl(var(--foreground))]">
                              {prompt.name}
                            </span>
                            {prompt.is_active && (
                              <span className="flex items-center gap-1 rounded-md bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                                <CheckCircle className="h-3 w-3" />
                                Đang hoạt động
                              </span>
                            )}
                          </div>
                          <span className="block text-[10px] text-[hsl(var(--muted-foreground))]">
                            Cập nhật: {new Date(prompt.updated_at).toLocaleString("vi-VN")}
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          {/* Toggle expand preview */}
                          <button
                            onClick={() => toggleExpandPrompt(prompt._id)}
                            className="flex items-center gap-1 rounded-lg bg-[hsl(var(--secondary))] px-2.5 py-1.5 text-xs font-medium text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                            title="Xem chi tiết nội dung prompt"
                          >
                            {isExpanded ? (
                              <>
                                <EyeOff className="h-3.5 w-3.5" />
                                Ẩn bớt
                              </>
                            ) : (
                              <>
                                <Eye className="h-3.5 w-3.5" />
                                Chi tiết
                              </>
                            )}
                          </button>

                          {/* Set Active Button */}
                          {!prompt.is_active && (
                            <button
                              onClick={() => handleSetActivePrompt(prompt._id)}
                              className="rounded-lg bg-cyan-500/10 dark:bg-cyan-900/40 border border-cyan-500/30 hover:bg-cyan-500 hover:text-white px-2.5 py-1.5 text-xs font-semibold text-cyan-600 dark:text-cyan-400 transition-colors"
                            >
                              Kích hoạt
                            </button>
                          )}

                          {/* Edit Button */}
                          <button
                            onClick={() => handleOpenEditPromptForm(prompt)}
                            className="rounded-lg p-1.5 text-[hsl(var(--muted-foreground))] hover:bg-cyan-500/10 hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors"
                            title="Sửa prompt"
                          >
                            <Edit className="h-4.5 w-4.5" />
                          </button>

                          {/* Delete Button */}
                          <button
                            onClick={() => handleDeletePrompt(prompt)}
                            disabled={prompt.is_active}
                            className={`rounded-lg p-1.5 transition-colors ${
                              prompt.is_active 
                                ? "text-[hsl(var(--muted-foreground))] cursor-not-allowed opacity-40" 
                                : "text-[hsl(var(--muted-foreground))] hover:bg-red-500/10 hover:text-red-500 dark:hover:text-red-400"
                            }`}
                            title="Xóa prompt (chỉ xóa được khi không hoạt động)"
                          >
                            <Trash2 className="h-4.5 w-4.5" />
                          </button>
                        </div>
                      </div>

                      {/* Expanded View for Prompt Body */}
                      {isExpanded && (
                        <div className="mt-4 space-y-4 animate-fadeIn">
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between">
                              <h4 className="text-xs font-semibold text-cyan-700 dark:text-cyan-300">Single Article System Instruction:</h4>
                              <button
                                type="button"
                                onClick={() => handleCopyText(prompt.system_prompt)}
                                className="text-[10px] text-[hsl(var(--muted-foreground))] hover:text-cyan-600 dark:hover:text-cyan-400 flex items-center gap-1"
                              >
                                <Copy className="h-3 w-3" /> Sao chép
                              </button>
                            </div>
                            <pre className="max-h-40 overflow-y-auto rounded-lg bg-[hsl(var(--secondary))] p-3 text-[10px] font-mono text-[hsl(var(--foreground))] whitespace-pre-wrap border border-[hsl(var(--border))]">
                              {prompt.system_prompt}
                            </pre>
                          </div>

                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between">
                              <h4 className="text-xs font-semibold text-cyan-700 dark:text-cyan-300">Batch Articles System Instruction:</h4>
                              <button
                                type="button"
                                onClick={() => handleCopyText(prompt.batch_system_prompt)}
                                className="text-[10px] text-[hsl(var(--muted-foreground))] hover:text-cyan-600 dark:hover:text-cyan-400 flex items-center gap-1"
                              >
                                <Copy className="h-3 w-3" /> Sao chép
                              </button>
                            </div>
                            <pre className="max-h-40 overflow-y-auto rounded-lg bg-[hsl(var(--secondary))] p-3 text-[10px] font-mono text-[hsl(var(--foreground))] whitespace-pre-wrap border border-[hsl(var(--border))]">
                              {prompt.batch_system_prompt}
                            </pre>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Interactive Prompt Guidelines & Guidebook Sidebar (Right column: 5/12) */}
          <div className="lg:col-span-5 space-y-4">
            <div className="glass-card p-5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))]/50">
              <div className="flex items-center gap-2 mb-3">
                <BookOpen className="h-5 w-5 text-cyan-500 dark:text-cyan-400" />
                <h3 className="text-sm font-bold text-[hsl(var(--foreground))]">Cẩm Nang Thiết Kế Prompt</h3>
              </div>
              <p className="text-xs text-[hsl(var(--muted-foreground))] leading-relaxed mb-4">
                Mô hình Gemini sử dụng prompt cấu hình này để phân loại thông tin thu thập được từ báo chí. Hãy tuân thủ hướng dẫn để đảm bảo chất lượng phân tích cao nhất và tránh tin rác.
              </p>

              {/* Guide Accordions */}
              <div className="space-y-2 text-xs">
                
                {/* 1. Cấu trúc Prompt */}
                <div className="border border-[hsl(var(--border))] rounded-lg overflow-hidden">
                  <button
                    type="button"
                    onClick={() => toggleGuideSection("structure")}
                    className="w-full flex items-center justify-between p-3 bg-[hsl(var(--secondary))]/40 hover:bg-[hsl(var(--secondary))] font-semibold text-[hsl(var(--foreground))] transition-colors text-left"
                  >
                    <span>1. Cấu trúc Prompt chuẩn cần có</span>
                    {openGuideSection === "structure" ? (
                      <ChevronUp className="h-4 w-4 text-cyan-500 dark:text-cyan-400" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </button>
                  {openGuideSection === "structure" && (
                    <div className="p-3 bg-[hsl(var(--secondary))]/20 border-t border-[hsl(var(--border))] space-y-2 leading-relaxed text-[hsl(var(--foreground))]">
                      <p>Một prompt chất lượng cho hệ thống cảnh báo sớm cần cấu trúc 4 phần chính:</p>
                      <ul className="list-disc pl-5 space-y-1.5">
                        <li><strong>Vai trò / Bối cảnh</strong>: Định danh LLM là chuyên gia rủi ro truyền thông của dự án Sân bay Long Thành.</li>
                        <li><strong>Dữ liệu đầu vào</strong>: Quy định cấu trúc đầu vào gồm tiêu đề, nội dung bài báo.</li>
                        <li><strong>Quy tắc phân tích cụ thể</strong>: Chi tiết về các mức độ rủi ro và các tiêu chuẩn đặc trưng.</li>
                        <li><strong>Định dạng đầu ra bắt buộc</strong>: Định nghĩa rõ ràng JSON schema và các giá trị enum được phép.</li>
                      </ul>
                    </div>
                  )}
                </div>

                {/* 2. Quy tắc is_relevant */}
                <div className="border border-[hsl(var(--border))] rounded-lg overflow-hidden">
                  <button
                    type="button"
                    onClick={() => toggleGuideSection("relevance")}
                    className="w-full flex items-center justify-between p-3 bg-[hsl(var(--secondary))]/40 hover:bg-[hsl(var(--secondary))] font-semibold text-[hsl(var(--foreground))] transition-colors text-left"
                  >
                    <span>2. Cách lọc tin rác (is_relevant = false)</span>
                    {openGuideSection === "relevance" ? (
                      <ChevronUp className="h-4 w-4 text-cyan-500 dark:text-cyan-400" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </button>
                  {openGuideSection === "relevance" && (
                    <div className="p-3 bg-[hsl(var(--secondary))]/20 border-t border-[hsl(var(--border))] space-y-2 leading-relaxed text-[hsl(var(--foreground))]">
                      <p className="text-amber-700 dark:text-amber-400 font-semibold flex items-center gap-1">🚨 Quy tắc cốt lõi tránh tràn ngập tin tức không liên quan:</p>
                      <p>
                        Hệ thống thu thập dữ liệu tự động theo từ khóa nên rất dễ bị trùng khóa chung ở các lĩnh vực khác. Cần ghi rõ ràng quy tắc lọc:
                      </p>
                      <ul className="list-disc pl-5 space-y-2">
                        <li>Chỉ đặt <code className="px-1.5 py-0.5 rounded font-mono text-[10px] bg-[hsl(var(--secondary))] text-cyan-800 dark:text-cyan-300 border border-[hsl(var(--border))]">is_relevant: true</code> khi bài viết trực tiếp nhắc đến Sân bay Long Thành, Tổng Công ty Cảng hàng không Việt Nam (ACV), gói thầu 5.10, gói thầu 4.6 hoặc ban lãnh đạo ACV.</li>
                        <li>Đặt <code className="px-1.5 py-0.5 rounded font-mono text-[10px] bg-[hsl(var(--secondary))] text-cyan-800 dark:text-cyan-300 border border-[hsl(var(--border))]">is_relevant: false</code> nếu bài viết chỉ nói về giải phóng mặt bằng chung ở các tỉnh khác, hoặc các dự án cơ sở hạ tầng giao thông vĩ mô khác không thuộc LTIA.</li>
                      </ul>
                    </div>
                  )}
                </div>

                {/* 3. Định dạng JSON */}
                <div className="border border-[hsl(var(--border))] rounded-lg overflow-hidden">
                  <button
                    type="button"
                    onClick={() => toggleGuideSection("json")}
                    className="w-full flex items-center justify-between p-3 bg-[hsl(var(--secondary))]/40 hover:bg-[hsl(var(--secondary))] font-semibold text-[hsl(var(--foreground))] transition-colors text-left"
                  >
                    <span>3. Định dạng đầu ra mong muốn (JSON Schema)</span>
                    {openGuideSection === "json" ? (
                      <ChevronUp className="h-4 w-4 text-cyan-500 dark:text-cyan-400" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </button>
                  {openGuideSection === "json" && (
                    <div className="p-3 bg-[hsl(var(--secondary))]/20 border-t border-[hsl(var(--border))] space-y-2 text-[hsl(var(--foreground))]">
                      <p className="mb-2">LLM bắt buộc trả về một JSON Object (đơn lẻ) hoặc một JSON Array (đối với batch) với định dạng chính xác:</p>
                      <pre className="rounded bg-[hsl(var(--secondary))] p-2 font-mono text-[10px] text-cyan-800 dark:text-cyan-300 overflow-x-auto border border-[hsl(var(--border))]">
{`{
  "category": ["Tiến độ", "Đấu thầu"...],
  "sentiment": "POSITIVE | NEGATIVE | NEUTRAL",
  "target_scope": ["Toàn dự án" | "Gói thầu 5.10"...],
  "impact_level": "CRITICAL | HIGH | MEDIUM | LOW",
  "key_entities": [{"name": "ACV", "type": "organization"}],
  "executive_summary": "Tóm tắt sự việc bằng tiếng Việt...",
  "is_rumor": false,
  "is_relevant": true
}`}
                      </pre>
                    </div>
                  )}
                </div>

                {/* 4. Định nghĩa Mức độ ảnh hưởng */}
                <div className="border border-[hsl(var(--border))] rounded-lg overflow-hidden">
                  <button
                    type="button"
                    onClick={() => toggleGuideSection("impact")}
                    className="w-full flex items-center justify-between p-3 bg-[hsl(var(--secondary))]/40 hover:bg-[hsl(var(--secondary))] font-semibold text-[hsl(var(--foreground))] transition-colors text-left"
                  >
                    <span>4. Phân chia rủi ro (Impact Levels)</span>
                    {openGuideSection === "impact" ? (
                      <ChevronUp className="h-4 w-4 text-cyan-500 dark:text-cyan-400" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </button>
                  {openGuideSection === "impact" && (
                    <div className="p-3 bg-[hsl(var(--secondary))]/20 border-t border-[hsl(var(--border))] space-y-2 leading-relaxed text-[hsl(var(--foreground))]">
                      <ul className="list-disc pl-5 space-y-2">
                        <li><strong className="text-red-700 dark:text-red-400">CRITICAL</strong>: Tai nạn chết người, thanh tra sai phạm pháp lý lớn, đình chỉ thi công, biểu tình hay đình công quy mô lớn.</li>
                        <li><strong className="text-amber-600 dark:text-amber-400">HIGH</strong>: Trực tiếp đe dọa đến tiến độ về đích của dự án (ví dụ: thiếu đất/cát san lấp nghiêm trọng, chậm giải ngân vốn đầu tư công, chậm trễ bàn giao mặt bằng).</li>
                        <li><strong className="text-yellow-600 dark:text-yellow-400">MEDIUM</strong>: Các thông tin cập nhật thi công kỹ thuật định kỳ, điều chỉnh thông số kỹ thuật phụ cần theo dõi.</li>
                        <li><strong className="text-emerald-600 dark:text-emerald-400">LOW</strong>: Tin tức hình ảnh đẹp, khen thưởng, kỷ niệm, hợp tác thương mại mang tính quảng bá tích cực.</li>
                      </ul>
                    </div>
                  )}
                </div>

              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
