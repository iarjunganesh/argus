import { AssessmentForm } from "@/components/assessment-form";

export default function Home() {
  return (
    <>
      <h1 className="text-3xl font-semibold tracking-tight">New assessment</h1>
      <p className="mt-2 max-w-2xl text-muted-foreground">
        Fixed rules set the risk score and tier. A language model only writes the explanation, and
        every finding points to its evidence.
      </p>
      <div className="mt-10">
        <AssessmentForm />
      </div>
    </>
  );
}
