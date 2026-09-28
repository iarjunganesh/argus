import type { Metadata } from "next";

import { Assessment } from "@/components/assessment";

export const metadata: Metadata = { title: "Assessment" };

export default async function AssessmentPage({ params }: PageProps<"/assessments/[id]">) {
  const { id } = await params;
  return <Assessment reportId={decodeURIComponent(id)} />;
}
