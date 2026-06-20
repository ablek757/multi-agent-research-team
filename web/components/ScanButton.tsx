"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Radio } from "lucide-react";
import { runIntelligenceScan } from "@/lib/api";

export default function ScanButton() {
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleScan = async () => {
    setLoading(true);
    try {
      await runIntelligenceScan();
      router.refresh();
    } catch {
      alert("扫描失败，请检查后端服务是否运行。");
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleScan}
      disabled={loading}
      className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed text-sm font-medium"
    >
      <Radio className={`w-4 h-4 ${loading ? "animate-pulse" : ""}`} />
      {loading ? "扫描中..." : "立即扫描"}
    </button>
  );
}
