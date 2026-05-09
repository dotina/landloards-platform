"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { api, ApiError } from "@/lib/api";
import { formatKES } from "@/lib/format";
import { PageHeader } from "@/components/dashboard/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

interface PropertyOut {
  id: string;
  name: string;
}
interface UnitOut {
  id: string;
  property_id: string;
  label: string;
  rent_amount: string | number;
  status: "vacant" | "occupied";
  due_day_of_month: number;
}
interface AdminTenantOut {
  id: string;
  name: string;
  phone: string;
}
interface LeaseOut {
  id: string;
}

const STEPS = ["Property & Unit", "Tenant", "Terms", "Confirm"] as const;

export default function NewLeasePage() {
  const router = useRouter();
  const { push } = useToast();

  const [step, setStep] = useState(0);
  const [propertyId, setPropertyId] = useState<string | null>(null);
  const [unitId, setUnitId] = useState<string | null>(null);
  const [tenantId, setTenantId] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [deposit, setDeposit] = useState("0");

  const properties = useQuery({
    queryKey: ["properties"],
    queryFn: () => api<PropertyOut[]>("/properties"),
  });
  const units = useQuery({
    queryKey: ["units", propertyId],
    enabled: !!propertyId,
    queryFn: () => api<UnitOut[]>(`/properties/${propertyId}/units`),
  });
  const tenants = useQuery({
    queryKey: ["admin-tenants"],
    queryFn: () => api<AdminTenantOut[]>("/admin/tenants"),
  });

  const selectedUnit = units.data?.find((u) => u.id === unitId);

  const createLease = useMutation({
    mutationFn: () =>
      api<LeaseOut>("/leases", {
        method: "POST",
        body: {
          unit_id: unitId,
          tenant_id: tenantId,
          start_date: startDate,
          end_date: endDate,
          rent_amount: selectedUnit?.rent_amount ?? "0",
          deposit_amount: deposit,
        },
      }),
    onSuccess: () => {
      push({ kind: "success", message: "Lease created" });
      router.push("/dashboard");
    },
    onError: (e: unknown) =>
      push({
        kind: "error",
        message: e instanceof ApiError ? e.message : "Could not create lease",
      }),
  });

  function next() {
    if (step === 0 && unitId) setStep(1);
    else if (step === 1 && tenantId) setStep(2);
    else if (step === 2 && startDate && endDate) setStep(3);
  }
  function prev() {
    setStep((s) => Math.max(0, s - 1));
  }

  return (
    <>
      <PageHeader title="New lease" description={`Step ${step + 1} of ${STEPS.length}: ${STEPS[step]}`} />

      <Card>
        <CardContent className="p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.18 }}
            >
              {step === 0 && (
                <Step1
                  propertyId={propertyId}
                  setPropertyId={setPropertyId}
                  unitId={unitId}
                  setUnitId={setUnitId}
                  properties={properties.data ?? []}
                  units={units.data ?? []}
                  loading={properties.isLoading}
                />
              )}
              {step === 1 && (
                <Step2
                  tenantId={tenantId}
                  setTenantId={setTenantId}
                  tenants={tenants.data ?? []}
                />
              )}
              {step === 2 && (
                <Step3
                  startDate={startDate}
                  endDate={endDate}
                  setStartDate={setStartDate}
                  setEndDate={setEndDate}
                  deposit={deposit}
                  setDeposit={setDeposit}
                />
              )}
              {step === 3 && (
                <Step4
                  unit={selectedUnit}
                  startDate={startDate}
                  endDate={endDate}
                  deposit={deposit}
                />
              )}
            </motion.div>
          </AnimatePresence>

          <div className="mt-6 flex items-center justify-between">
            <Button variant="outline" onClick={prev} disabled={step === 0}>
              Back
            </Button>
            {step < STEPS.length - 1 ? (
              <Button
                onClick={next}
                disabled={
                  (step === 0 && !unitId) ||
                  (step === 1 && !tenantId) ||
                  (step === 2 && (!startDate || !endDate))
                }
              >
                Next
              </Button>
            ) : (
              <Button
                onClick={() => createLease.mutate()}
                disabled={createLease.isPending}
              >
                {createLease.isPending ? "Creating…" : "Create lease"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

function Step1(props: {
  propertyId: string | null;
  setPropertyId: (s: string | null) => void;
  unitId: string | null;
  setUnitId: (s: string | null) => void;
  properties: PropertyOut[];
  units: UnitOut[];
  loading: boolean;
}) {
  if (props.loading) return <Skeleton className="h-24" />;
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Property</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 md:grid-cols-3">
          {props.properties.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => {
                props.setPropertyId(p.id);
                props.setUnitId(null);
              }}
              className={`rounded-md border p-3 text-left text-sm ${
                props.propertyId === p.id ? "border-primary bg-primary/5" : ""
              }`}
            >
              {p.name}
            </button>
          ))}
        </CardContent>
      </Card>
      {props.propertyId && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Unit</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 md:grid-cols-3">
            {props.units
              .filter((u) => u.status === "vacant")
              .map((u) => (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => props.setUnitId(u.id)}
                  className={`rounded-md border p-3 text-left text-sm ${
                    props.unitId === u.id ? "border-primary bg-primary/5" : ""
                  }`}
                >
                  <div className="font-medium">{u.label}</div>
                  <div className="text-muted-foreground">
                    {formatKES(u.rent_amount)} · day {u.due_day_of_month}
                  </div>
                </button>
              ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Step2(props: {
  tenantId: string | null;
  setTenantId: (s: string | null) => void;
  tenants: AdminTenantOut[];
}) {
  return (
    <div className="grid gap-2 md:grid-cols-3">
      {props.tenants.map((t) => (
        <button
          key={t.id}
          type="button"
          onClick={() => props.setTenantId(t.id)}
          className={`rounded-md border p-3 text-left text-sm ${
            props.tenantId === t.id ? "border-primary bg-primary/5" : ""
          }`}
        >
          <div className="font-medium">{t.name}</div>
          <div className="text-muted-foreground">{t.phone}</div>
        </button>
      ))}
    </div>
  );
}

function Step3(props: {
  startDate: string;
  endDate: string;
  setStartDate: (s: string) => void;
  setEndDate: (s: string) => void;
  deposit: string;
  setDeposit: (s: string) => void;
}) {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      <div className="space-y-1">
        <Label htmlFor="start">Start date</Label>
        <Input
          id="start"
          type="date"
          value={props.startDate}
          onChange={(e) => props.setStartDate(e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="end">End date</Label>
        <Input
          id="end"
          type="date"
          value={props.endDate}
          onChange={(e) => props.setEndDate(e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="dep">Deposit (KES)</Label>
        <Input
          id="dep"
          type="number"
          min="0"
          value={props.deposit}
          onChange={(e) => props.setDeposit(e.target.value)}
        />
      </div>
    </div>
  );
}

function Step4(props: {
  unit?: UnitOut;
  startDate: string;
  endDate: string;
  deposit: string;
}) {
  return (
    <div className="space-y-2 text-sm">
      <p>
        Unit: <span className="font-medium">{props.unit?.label ?? "—"}</span>
      </p>
      <p>
        Rent:{" "}
        <span className="font-medium">{formatKES(props.unit?.rent_amount ?? 0)}</span>
      </p>
      <p>
        From <span className="font-medium">{props.startDate}</span> to{" "}
        <span className="font-medium">{props.endDate}</span>
      </p>
      <p>
        Deposit: <span className="font-medium">{formatKES(props.deposit)}</span>
      </p>
      <p className="pt-3 text-muted-foreground">
        By creating this lease you confirm the tenant has read and accepted the
        terms.
      </p>
    </div>
  );
}
