"use client";

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { cn } from "@/lib/utils";

export type ToastKind = "success" | "error" | "info";

export interface Toast {
  id: string;
  kind: ToastKind;
  title?: string;
  message: string;
}

interface ToastContextValue {
  toasts: Toast[];
  push: (t: Omit<Toast, "id"> & { ttlMs?: number }) => void;
  dismiss: (id: string) => void;
}

const ToastContext = React.createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = React.useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const dismiss = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = React.useCallback<ToastContextValue["push"]>(
    ({ ttlMs = 4_000, ...t }) => {
      const id = crypto.randomUUID();
      setToasts((prev) => [...prev, { id, ...t }]);
      window.setTimeout(() => dismiss(id), ttlMs);
    },
    [dismiss]
  );

  const value = React.useMemo(
    () => ({ toasts, push, dismiss }),
    [toasts, push, dismiss]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2"
      >
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 16 }}
              transition={{ duration: 0.18 }}
              role="status"
              className={cn(
                "pointer-events-auto rounded-md border bg-card p-3 text-card-foreground shadow",
                t.kind === "success" && "border-paid-500",
                t.kind === "error" && "border-overdue-500",
                t.kind === "info" && "border-input"
              )}
            >
              {t.title && <div className="text-sm font-semibold">{t.title}</div>}
              <div className="text-sm">{t.message}</div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
