"use client";

import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { PageHeader } from "@/components/dashboard/page-header";
import { EmptyState } from "@/components/dashboard/empty-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

interface PropertyOut {
  id: string;
  name: string;
  address: string;
  photo_url: string | null;
}

export default function PropertiesPage() {
  const qc = useQueryClient();
  const { push } = useToast();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");

  const list = useQuery({
    queryKey: ["properties"],
    queryFn: () => api<PropertyOut[]>("/properties"),
  });

  const create = useMutation({
    mutationFn: (body: { name: string; address: string }) =>
      api<PropertyOut>("/properties", { method: "POST", body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["properties"] });
      setCreating(false);
      setName("");
      setAddress("");
      push({ kind: "success", message: "Property created" });
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
        title="Properties"
        actions={
          <Button onClick={() => setCreating((v) => !v)}>
            {creating ? "Cancel" : "Add property"}
          </Button>
        }
      />

      {creating && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">New property</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              aria-label="property-form"
              className="space-y-3"
              onSubmit={(e) => {
                e.preventDefault();
                if (!name.trim() || !address.trim()) return;
                create.mutate({ name, address });
              }}
            >
              <div className="space-y-1">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="address">Address</Label>
                <Input
                  id="address"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                />
              </div>
              <Button type="submit" disabled={create.isPending}>
                {create.isPending ? "Saving…" : "Save"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {list.isLoading ? (
        <div className="grid gap-4 md:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      ) : (list.data?.length ?? 0) === 0 ? (
        <EmptyState
          title="No properties yet"
          description="Add your first property to start onboarding tenants."
          action={
            <Button onClick={() => setCreating(true)}>Add property</Button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {list.data!.map((p) => (
            <Link
              key={p.id}
              href={`/dashboard/properties/${p.id}`}
              className="group rounded-lg border bg-card p-4 transition-shadow hover:shadow"
            >
              <div className="aspect-video w-full rounded-md bg-muted" />
              <div className="mt-3">
                <p className="font-medium">{p.name}</p>
                <p className="text-sm text-muted-foreground">{p.address}</p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
