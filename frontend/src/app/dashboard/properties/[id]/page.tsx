"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { formatKES } from "@/lib/format";
import { PageHeader } from "@/components/dashboard/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/toast";

interface PropertyOut {
  id: string;
  name: string;
  address: string;
  photo_url: string | null;
}
interface UnitOut {
  id: string;
  property_id: string;
  label: string;
  rent_amount: string | number;
  due_day_of_month: number;
  status: "vacant" | "occupied";
}

export default function PropertyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const { push } = useToast();

  const property = useQuery({
    queryKey: ["property", id],
    queryFn: () => api<PropertyOut>(`/properties/${id}`),
  });
  const units = useQuery({
    queryKey: ["units", id],
    queryFn: () => api<UnitOut[]>(`/properties/${id}/units`),
  });

  const [showNew, setShowNew] = useState(false);
  const [label, setLabel] = useState("");
  const [rent, setRent] = useState("0");
  const [dueDay, setDueDay] = useState(1);

  const createUnit = useMutation({
    mutationFn: () =>
      api<UnitOut>(`/properties/${id}/units`, {
        method: "POST",
        body: {
          label,
          rent_amount: rent,
          due_day_of_month: dueDay,
        },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["units", id] });
      setShowNew(false);
      setLabel("");
      setRent("0");
      setDueDay(1);
      push({ kind: "success", message: "Unit created" });
    },
    onError: (e: unknown) =>
      push({
        kind: "error",
        message: e instanceof ApiError ? e.message : "Could not create",
      }),
  });

  return (
    <>
      <PageHeader
        title={property.data?.name ?? "Property"}
        description={property.data?.address}
        actions={
          <Button onClick={() => setShowNew((v) => !v)}>
            {showNew ? "Cancel" : "Add unit"}
          </Button>
        }
      />

      {showNew && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">New unit</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              aria-label="unit-form"
              className="grid gap-3 md:grid-cols-3"
              onSubmit={(e) => {
                e.preventDefault();
                if (!label.trim()) return;
                createUnit.mutate();
              }}
            >
              <div className="space-y-1">
                <Label htmlFor="label">Label</Label>
                <Input
                  id="label"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="rent">Rent (KES)</Label>
                <Input
                  id="rent"
                  type="number"
                  min="0"
                  value={rent}
                  onChange={(e) => setRent(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="dueDay">Due day (1–28)</Label>
                <Input
                  id="dueDay"
                  type="number"
                  min={1}
                  max={28}
                  value={dueDay}
                  onChange={(e) => setDueDay(Number(e.target.value))}
                />
              </div>
              <div className="md:col-span-3">
                <Button type="submit" disabled={createUnit.isPending}>
                  {createUnit.isPending ? "Saving…" : "Save"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Units</CardTitle>
        </CardHeader>
        <CardContent>
          {units.isLoading ? (
            <Skeleton className="h-20" />
          ) : (units.data?.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground">No units yet.</p>
          ) : (
            <ul className="divide-y">
              {units.data!.map((u) => (
                <li
                  key={u.id}
                  className="flex items-center justify-between py-3"
                >
                  <Link
                    href={`/dashboard/units/${u.id}`}
                    className="hover:underline"
                  >
                    <span className="font-medium">{u.label}</span>
                  </Link>
                  <span className="flex items-center gap-3 text-sm">
                    <Badge variant={u.status === "occupied" ? "default" : "secondary"}>
                      {u.status}
                    </Badge>
                    <span className="tabular-nums">{formatKES(u.rent_amount)}</span>
                    <span className="text-muted-foreground">
                      due day {u.due_day_of_month}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </>
  );
}
