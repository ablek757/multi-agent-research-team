"use client";

import { useEffect, useState } from "react";
import { Sparkles, Save, User } from "lucide-react";
import { getStyleProfile, learnStyle, StyleProfile } from "@/lib/api";

export default function StylePage() {
  const [profile, setProfile] = useState<StyleProfile | null>(null);
  const [original, setOriginal] = useState("");
  const [revised, setRevised] = useState("");
  const [feedback, setFeedback] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    getStyleProfile().then(setProfile).catch(() => setProfile(null));
  }, []);

  const handleLearn = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      const payload: { original?: string; revised?: string; feedback?: string } = {};
      if (revised.trim()) {
        payload.original = original;
        payload.revised = revised;
      } else if (feedback.trim()) {
        payload.original = original;
        payload.feedback = feedback;
      }
      const updated = await learnStyle(payload);
      setProfile(updated);
      setMessage("风格画像已更新");
    } catch (err: any) {
      setMessage(err.message || "学习失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="flex items-center gap-3">
        <User className="w-8 h-8 text-green-600" />
        <div>
          <h1 className="text-2xl font-bold">用户研究风格</h1>
          <p className="text-neutral-600 dark:text-neutral-400">
            提交修订样本或审稿反馈，让系统学习你的写作偏好。
          </p>
        </div>
      </div>

      {profile && (
        <div className="bg-white dark:bg-neutral-900 border rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5" />
            当前风格画像
          </h2>
          <div className="grid md:grid-cols-2 gap-4 text-sm">
            <div className="flex justify-between border-b py-2">
              <span className="text-neutral-500">语言</span>
              <span className="font-medium">{profile.language}</span>
            </div>
            <div className="flex justify-between border-b py-2">
              <span className="text-neutral-500">段落长度</span>
              <span className="font-medium">{profile.paragraph_length}</span>
            </div>
            <div className="flex justify-between border-b py-2">
              <span className="text-neutral-500">引用密度</span>
              <span className="font-medium">{profile.citation_density}</span>
            </div>
            <div className="flex justify-between border-b py-2">
              <span className="text-neutral-500">论述结构</span>
              <span className="font-medium">{profile.structure_preference}</span>
            </div>
            <div className="flex justify-between border-b py-2">
              <span className="text-neutral-500">语气</span>
              <span className="font-medium">{profile.tone}</span>
            </div>
            <div className="flex justify-between border-b py-2">
              <span className="text-neutral-500">批判性强度</span>
              <span className="font-medium">{profile.critical_intensity}/10</span>
            </div>
            <div className="flex justify-between border-b py-2">
              <span className="text-neutral-500">过渡词</span>
              <span className="font-medium">
                {profile.transition_words.length > 0
                  ? profile.transition_words.join("、")
                  : "未学习"}
              </span>
            </div>
            <div className="flex justify-between border-b py-2">
              <span className="text-neutral-500">样本数</span>
              <span className="font-medium">{profile.sample_count}</span>
            </div>
          </div>
        </div>
      )}

      <form onSubmit={handleLearn} className="bg-white dark:bg-neutral-900 border rounded-xl p-6 space-y-6">
        <h2 className="text-lg font-semibold">提交学习样本</h2>

        <div>
          <label className="block text-sm font-medium mb-2">原文 / 当前报告</label>
          <textarea
            value={original}
            onChange={(e) => setOriginal(e.target.value)}
            rows={4}
            className="w-full px-4 py-2 rounded-lg border bg-white dark:bg-neutral-800 focus:ring-2 focus:ring-green-500 outline-none"
            placeholder="粘贴原始文本或报告段落"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">修订文（可选）</label>
          <textarea
            value={revised}
            onChange={(e) => setRevised(e.target.value)}
            rows={4}
            className="w-full px-4 py-2 rounded-lg border bg-white dark:bg-neutral-800 focus:ring-2 focus:ring-green-500 outline-none"
            placeholder="粘贴你修改后的版本，系统将学习两者差异"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">审稿反馈（可选）</label>
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            rows={3}
            className="w-full px-4 py-2 rounded-lg border bg-white dark:bg-neutral-800 focus:ring-2 focus:ring-green-500 outline-none"
            placeholder="例如：请使用更简洁的段落、增加批判性分析"
          />
        </div>

        <button
          type="submit"
          disabled={loading || !original.trim() || (!revised.trim() && !feedback.trim())}
          className="flex items-center gap-2 px-6 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          {loading ? "学习中..." : "更新风格画像"}
        </button>

        {message && (
          <div className="p-3 rounded-lg bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300">
            {message}
          </div>
        )}
      </form>
    </div>
  );
}
