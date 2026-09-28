import type { Metadata } from "next";

import { Assessment } from "@/components/assessment";

export const metadata: Metadata = { title: "Assessment" };

export default async function AssessmentPage({
  params,
  searchParams,
}: PageProps<"/assessments/[id]">) {
  const { id } = await params;
  const { entity } = await searchParams;
  return (
    <Assessment
      reportId={decodeURIComponent(id)}
      entityName={typeof entity === "string" ? entity : undefined}
    />
  );
}
