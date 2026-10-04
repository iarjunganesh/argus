"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, normaliseRequest, submitAssessment, type AssessmentRequest } from "@/lib/api";
import { DEMO_ONLY, RETENTION_NOTICE, offeredDemoCases } from "@/lib/demo";
import { rememberEntityName } from "@/lib/session";

export function AssessmentForm() {
  const router = useRouter();
  const [error, setError] = useState<string>();
  const [pending, setPending] = useState<string>();

  async function run(request: AssessmentRequest) {
    setError(undefined);
    setPending(request.entity_name);
    try {
      const reportId = await submitAssessment(request);
      rememberEntityName(reportId, request.entity_name);
      router.push(`/assessments/${encodeURIComponent(reportId)}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The assessment could not start.");
      setPending(undefined);
    }
  }

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
            {pending ? `Starting the assessment of ${pending}…` : ""}
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
                {pending ? `Starting the assessment of ${pending}…` : ""}
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
          {DEMO_ONLY
            ? "Invented entities, each with recorded agent results."
            : "Synthetic entities, and a payment firm and two banks with published enforcement records."}
        </p>
        <ul className="mt-6 divide-y rounded-lg border bg-card">
          {offeredDemoCases().map((demo) => (
            <li key={demo.entity_name} className="flex items-center gap-4 px-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="font-medium">{demo.entity_name}</p>
                <p className="text-sm text-muted-foreground">
                  {`${demo.entity_type === "corporate" ? "Company" : "Individual"}, ${demo.jurisdiction}, ${demo.origin.toLowerCase()}`}
                </p>
              </div>
              <Button
                variant="outline"
                disabled={Boolean(pending)}
                onClick={() => void run(demo)}
                aria-label={`Run the assessment of ${demo.entity_name}`}
              >
                Run
              </Button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
