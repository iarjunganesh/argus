"use client";

import type { FormEvent } from "react";

import { CaseQueue } from "@/components/case-queue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useStartAssessment } from "@/components/use-start-assessment";
import { normaliseRequest } from "@/lib/api";
import { DEMO_ONLY, RETENTION_NOTICE } from "@/lib/demo";

export function AssessmentForm() {
  const { run, pending, error, setError, status } = useStartAssessment();

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const request = normaliseRequest(
      String(data.get("entity_name") ?? ""),
      String(data.get("entity_type") ?? ""),
      String(data.get("jurisdiction") ?? ""),
    );
    if ("error" in request) {
      setError(request.error);
      return;
    }
    void run(request);
  }

  return (
    <div className="grid gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      {DEMO_ONLY ? (
        <section aria-labelledby="about-heading">
          <h2 id="about-heading" className="text-xl font-semibold">
            About this demo
          </h2>
          <p className="mt-1 text-muted-foreground">
            This public demo runs only the synthetic cases listed here. Their entities are invented,
            so no real person&apos;s or company&apos;s details are entered. {RETENTION_NOTICE}
          </p>
          <p role="status" className="mt-4 text-sm text-muted-foreground">
            {status}
          </p>
          <p role="alert" className="text-sm font-medium text-destructive">
            {error}
          </p>
        </section>
      ) : (
        <section aria-labelledby="new-heading">
          <h2 id="new-heading" className="text-xl font-semibold">
            Screen an entity
          </h2>
          <p className="mt-1 text-muted-foreground">
            Five agents check identity, screening, ownership and transactions, then score the case.
          </p>
          <form
            onSubmit={onSubmit}
            noValidate
            className="mt-6 grid gap-5"
            aria-describedby="form-error"
          >
            <div className="grid gap-2">
              <Label htmlFor="entity_name">Entity name</Label>
              <Input
                id="entity_name"
                name="entity_name"
                autoComplete="off"
                placeholder="Synthetic Holdings B.V."
                className="h-10"
              />
            </div>
            <fieldset className="grid gap-2">
              <legend className="mb-2 text-sm font-medium">Entity type</legend>
              <div className="flex gap-6">
                {(["corporate", "individual"] as const).map((type) => (
                  <label key={type} className="flex items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name="entity_type"
                      value={type}
                      defaultChecked={type === "corporate"}
                      className="size-4 accent-primary"
                    />
                    {type === "corporate" ? "Company" : "Individual"}
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="grid gap-2">
              <Label htmlFor="jurisdiction">Jurisdiction</Label>
              <Input
                id="jurisdiction"
                name="jurisdiction"
                autoComplete="off"
                maxLength={2}
                placeholder="NL"
                aria-describedby="jurisdiction-hint"
                className="h-10 w-24 uppercase"
              />
              <p id="jurisdiction-hint" className="text-sm text-muted-foreground">
                Two-letter country code, such as DE or GB.
              </p>
            </div>
            <div className="flex items-center gap-4">
              <Button type="submit" size="lg" disabled={Boolean(pending)} className="h-10 px-4">
                Run assessment
              </Button>
              <p role="status" className="text-sm text-muted-foreground">
                {status}
              </p>
            </div>
            <p id="form-error" role="alert" className="text-sm font-medium text-destructive">
              {error}
            </p>
            <p className="text-sm text-muted-foreground">
              Enter synthetic entities only. {RETENTION_NOTICE}
            </p>
          </form>
        </section>
      )}

      <section aria-labelledby="demo-heading">
        <h2 id="demo-heading" className="text-xl font-semibold">
          Demo cases
        </h2>
        <p className="mt-1 text-muted-foreground">
          Invented entities, each with recorded agent results. Your runs appear here, riskiest
          first, for 24 hours in this browser.
        </p>
        <CaseQueue onRun={(request) => void run(request)} disabled={Boolean(pending)} />
      </section>
    </div>
  );
}
