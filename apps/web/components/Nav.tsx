"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileText, LayoutDashboard, Upload, BookOpen } from "lucide-react";
import clsx from "clsx";

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/process", label: "Process Invoice", icon: Upload },
  { href: "/reference/vendors", label: "Vendors", icon: BookOpen },
  { href: "/reference/pos", label: "Purchase Orders", icon: FileText },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <header className="border-b border-surface-border bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-900 text-white">
            <FileText className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">AP Control Room</p>
            <p className="text-xs text-muted">Invoice Processing</p>
          </div>
        </div>
        <nav className="flex items-center gap-1">
          {links.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={clsx(
                "inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                pathname === href || (href !== "/" && pathname.startsWith(href))
                  ? "bg-slate-100 text-slate-900"
                  : "text-muted hover:bg-slate-50 hover:text-slate-900"
              )}
            >
              <Icon className="h-4 w-4" />
              <span className="hidden sm:inline">{label}</span>
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
