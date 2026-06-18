"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Newspaper,
  Globe,
  Hash,
  Bell,
  Radar,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    label: "Tin tức",
    href: "/articles",
    icon: Newspaper,
  },
  {
    label: "Nguồn tin",
    href: "/sources",
    icon: Globe,
  },
  {
    label: "Từ khóa",
    href: "/keywords",
    icon: Hash,
  },
  {
    label: "Cảnh báo",
    href: "/settings",
    icon: Bell,
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-[hsl(var(--sidebar-border))] bg-[hsl(var(--sidebar))]">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-[hsl(var(--sidebar-border))] px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/20">
          <Radar className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="text-sm font-bold tracking-wide text-white">
            LTIA RADAR
          </h1>
          <p className="text-[10px] text-[hsl(var(--muted-foreground))]">
            Early Warning System
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="mt-6 px-3">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                    isActive
                      ? "bg-gradient-to-r from-cyan-500/15 to-blue-500/10 text-cyan-400 shadow-sm"
                      : "text-[hsl(var(--sidebar-foreground))] hover:bg-[hsl(var(--secondary))] hover:text-white"
                  )}
                >
                  <item.icon
                    className={cn(
                      "h-4.5 w-4.5",
                      isActive ? "text-cyan-400" : "text-[hsl(var(--muted-foreground))]"
                    )}
                  />
                  {item.label}
                  {isActive && (
                    <div className="ml-auto h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-sm shadow-cyan-400/50" />
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="absolute bottom-0 left-0 right-0 border-t border-[hsl(var(--sidebar-border))] p-4">
        <div className="flex items-center gap-2 rounded-lg bg-[hsl(var(--secondary))] px-3 py-2">
          <div className="h-2 w-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50" />
          <span className="text-xs text-[hsl(var(--muted-foreground))]">
            Hệ thống hoạt động
          </span>
        </div>
      </div>
    </aside>
  );
}
