"use client";

import { Search } from "lucide-react";
import { useState } from "react";

interface SearchBarProps {
  initialQuery?: string;
  onSearch?: (query: string) => void;
  action?: string;
  placeholder?: string;
}

export default function SearchBar({
  initialQuery = "",
  onSearch,
  action,
  placeholder = "搜索报告、主题、实体...",
}: SearchBarProps) {
  const [query, setQuery] = useState(initialQuery);

  const handleSubmit = (e: React.FormEvent) => {
    if (onSearch) {
      e.preventDefault();
      onSearch(query.trim());
    }
    // 如果没有 onSearch，使用 form action 默认提交
  };

  return (
    <form
      action={action}
      onSubmit={handleSubmit}
      className="relative max-w-2xl"
    >
      <input
        type="text"
        name="q"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={placeholder}
        className="w-full pl-10 pr-20 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-neutral-900 dark:border-neutral-700"
      />
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
      <button
        type="submit"
        className="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700"
      >
        搜索
      </button>
    </form>
  );
}
