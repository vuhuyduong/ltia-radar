"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Newspaper,
  Globe,
  Hash,
  Bell,
  Radar,
  Brain,
  X,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";


export function Sidebar() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);

  const isAdminRoute = pathname?.startsWith("/admin");
  const items = isAdminRoute
    ? [
        {
          label: "Dashboard",
          href: "/admin/dashboard",
          icon: LayoutDashboard,
        },
        {
          label: "Tin tức",
          href: "/admin/articles",
          icon: Newspaper,
        },
        {
          label: "Cài đặt",
          href: "/admin/settings",
          icon: Settings,
        },
      ]
    : [
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
      ];

  useEffect(() => {
    const handleToggle = () => setIsOpen((prev) => !prev);
    const handleClose = () => setIsOpen(false);

    window.addEventListener("toggle-sidebar", handleToggle);
    window.addEventListener("close-sidebar", handleClose);

    return () => {
      window.removeEventListener("toggle-sidebar", handleToggle);
      window.removeEventListener("close-sidebar", handleClose);
    };
  }, []);

  const closeSidebar = () => {
    setIsOpen(false);
  };

  return (
    <>
      {/* Tap-to-close Backdrop for Mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden transition-opacity duration-300"
          onClick={closeSidebar}
        />
      )}

      <aside
        className={cn(
          "fixed left-0 top-0 z-50 h-screen w-64 border-r border-[hsl(var(--sidebar-border))] bg-[hsl(var(--sidebar))] transition-transform duration-300 ease-in-out lg:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center justify-between border-b border-[hsl(var(--sidebar-border))] px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/20">
              <Radar className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-wide text-[hsl(var(--sidebar-foreground))]">
                LTIA RADAR
              </h1>
              <p className="text-[10px] text-[hsl(var(--muted-foreground))]">
                Early Warning System
              </p>
            </div>
          </div>
          {/* Close button for mobile */}
          <button
            onClick={closeSidebar}
            className="rounded-lg p-1.5 text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--secondary))] hover:text-[hsl(var(--sidebar-foreground))] lg:hidden"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="mt-6 px-3">
          <ul className="space-y-1">
            {items.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={closeSidebar}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                      isActive
                        ? "bg-gradient-to-r from-cyan-500/15 to-blue-500/10 text-cyan-400 shadow-sm"
                        : "text-[hsl(var(--sidebar-foreground))] hover:bg-[hsl(var(--secondary))] hover:text-[hsl(var(--sidebar-foreground))]"
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
    </>
  );
}
