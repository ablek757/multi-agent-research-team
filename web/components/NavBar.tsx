"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, FileText, GitGraph, Home, Clock } from "lucide-react";

const navItems = [
  { href: "/", label: "仪表盘", icon: Home },
  { href: "/reports", label: "报告库", icon: FileText },
  { href: "/graph", label: "主题关联", icon: GitGraph },
  { href: "/timeline", label: "时间线", icon: Clock },
];

export default function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="border-b bg-white dark:bg-neutral-900 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-14 items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-semibold text-lg">
            <BarChart3 className="w-6 h-6 text-blue-600" />
            <span>研究知识库</span>
          </Link>
          <div className="flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    active
                      ? "bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300"
                      : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}
