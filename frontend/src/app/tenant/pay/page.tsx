"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, AlertCircle } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { formatKES } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

interface InvoiceOut {
  id: string;
  status: string;
  amount: string | number;
  late_fee_accrued: string | number;
  period_start: string;
}
interface StkInitiateResponse {
  payment_id: string;
  checkout_request_id: string;
}
interface PaymentOut {
  id: string;
  status: "pending" | "success" | "failed";
  amount: string | number;
  mpesa_receipt?: string | null;
  failure_reason?: string | null;
}

function num(v: string | number): number {
  return typeof v === "number" ? v : Number(v) || 0;
}

export default function TenantPayPage() {
  const { push } = useToast();

  const invoices = useQuery({
    queryKey: ["my-invoices"],
    queryFn: () => api<InvoiceOut[]>("/tenant/invoices"),
  });
  const oldestOpen = (invoices.data ?? []).find((i) =>
    ["open", "partial", "overdue", "on_pay_plan"].includes(i.status)
  );
  const due = oldestOpen
    ? num(oldestOpen.amount) + num(oldestOpen.late_fee_accrued)
    : 0;

  const [phone, setPhone] = useState("");
  const [amount, setAmount] = useState("");
  const [checkoutId, setCheckoutId] = useState<string | null>(null);

  useEffect(() => {
    if (oldestOpen && !amount) setAmount(String(due));
  }, [oldestOpen, amount, due]);

  const initiate = useMutation({
    mutationFn: () =>
      api<StkInitiateResponse>("/payments/stk/initiate", {
        method: "POST",
        body: {
          invoice_id: oldestOpen?.id,
          phone,
          amount,
        },
      }),
    onSuccess: (r) => {
      setCheckoutId(r.checkout_request_id);
      push({ kind: "info", message: "Check your phone for the M-Pesa prompt." });
    },
    onError: (e: unknown) => {
      const msg = e instanceof ApiError ? e.message : "Could not start payment.";
      push({ kind: "error", message: msg });
    },
  });

  const status = useQuery<PaymentOut | null>({
    queryKey: ["stk-status", checkoutId],
    enabled: !!checkoutId,
    refetchInterval: (q) => {
      const data = q.state.data as PaymentOut | null | undefined;
      return data && data.status !== "pending" ? false : 2000;
    },
    queryFn: () =>
      api<PaymentOut>(`/payments/stk/${encodeURIComponent(checkoutId!)}`),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Pay rent</CardTitle>
        </CardHeader>
        <CardContent>
          {invoices.isLoading ? (
            <Skeleton className="h-32" />
          ) : !oldestOpen ? (
            <p className="text-sm text-muted-foreground">
              You have no outstanding invoices. Nice.
            </p>
          ) : (
            <form
              aria-label="stk-form"
              className="space-y-3"
              onSubmit={(e) => {
                e.preventDefault();
                if (!phone || !amount) return;
                initiate.mutate();
              }}
            >
              <p className="rounded-md bg-muted/40 p-3 text-sm">
                Period {oldestOpen.period_start} — total due{" "}
                <span className="font-semibold tabular-nums">{formatKES(due)}</span>
              </p>
              <div className="space-y-1">
                <Label htmlFor="phone">M-Pesa phone (E.164)</Label>
                <Input
                  id="phone"
                  inputMode="tel"
                  placeholder="+2547..."
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="amount">Amount (KES)</Label>
                <Input
                  id="amount"
                  type="number"
                  min="1"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                />
              </div>
              <Button
                size="lg"
                className="w-full"
                disabled={initiate.isPending || !!checkoutId}
              >
                {initiate.isPending
                  ? "Sending prompt…"
                  : checkoutId
                  ? "Awaiting confirmation"
                  : "Pay with M-Pesa"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>

      <AnimatePresence>
        {checkoutId && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <Card>
              <CardContent className="p-6">
                {!status.data || status.data.status === "pending" ? (
                  <div className="flex items-center gap-3" role="status" aria-live="polite">
                    <motion.span
                      animate={{ scale: [1, 1.15, 1] }}
                      transition={{ duration: 1.2, repeat: Infinity }}
                      className="inline-block h-3 w-3 rounded-full bg-primary"
                      aria-hidden
                    />
                    <p className="text-sm">
                      Waiting for you to enter your M-Pesa PIN…
                    </p>
                  </div>
                ) : status.data.status === "success" ? (
                  <motion.div
                    initial={{ scale: 0.96, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="flex items-start gap-3"
                    role="status"
                    aria-live="polite"
                  >
                    <CheckCircle2 className="h-6 w-6 text-paid-500" aria-hidden />
                    <div>
                      <p className="text-sm font-medium">Payment received</p>
                      <p className="text-sm text-muted-foreground">
                        {formatKES(status.data.amount)}
                        {status.data.mpesa_receipt
                          ? ` · receipt ${status.data.mpesa_receipt}`
                          : ""}
                      </p>
                      <a
                        className="mt-2 inline-block text-sm text-primary hover:underline"
                        href={`/api/payments/${status.data.id}/receipt.pdf`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Download receipt
                      </a>
                    </div>
                  </motion.div>
                ) : (
                  <div className="flex items-start gap-3" role="alert">
                    <AlertCircle className="h-6 w-6 text-overdue-500" aria-hidden />
                    <div>
                      <p className="text-sm font-medium">Payment failed</p>
                      <p className="text-sm text-muted-foreground">
                        {status.data.failure_reason ??
                          "M-Pesa returned an error. Try again."}
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
