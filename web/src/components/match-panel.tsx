import type { ReactNode } from "react";

import { Facts } from "@/components/facts";
import { sanctionsListing } from "@/lib/case";
import { NOT_REPORTED, type Report } from "@/lib/report";

const yesNo = (value?: boolean) => (value === undefined ? NOT_REPORTED : value ? "Yes" : "No");

/** A potential sanctions match: the listing beside the customer, where a person resolves it. */
export function MatchPanel({ report, children }: { report: Report; children?: ReactNode }) {
  const listing = sanctionsListing(report);
  if (!listing) return null;
  const entity = report.entity ?? {};
  return (
    <section
      id="match"
      aria-labelledby="match-heading"
      className="mt-6 scroll-mt-6 rounded-xl border bg-card p-6"
    >
      <h2 id="match-heading" className="text-xl font-semibold">
        Potential sanctions match
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        A person must confirm or clear it before anything else happens.
      </p>
      <div className="mt-4 grid gap-6 md:grid-cols-2">
        <div>
          <h3 className="mb-2 font-semibold">Listing</h3>
          <Facts
            items={[
              ["Programme", listing.programme ?? NOT_REPORTED],
              ["Entry", listing.entryId ?? NOT_REPORTED],
              ["Active", yesNo(listing.active)],
              ["List", listing.document ?? NOT_REPORTED],
              ["Match", listing.match ?? NOT_REPORTED],
              ["Match score reported by the screening source", listing.sourceScore ?? NOT_REPORTED],
            ]}
          />
        </div>
        <div>
          <h3 className="mb-2 font-semibold">Customer</h3>
          <Facts
            items={[
              ["Name", entity.name ?? NOT_REPORTED],
              [
                "Type",
                entity.type
                  ? entity.type === "individual"
                    ? "Individual"
                    : "Company"
                  : NOT_REPORTED,
              ],
              ["Jurisdiction", entity.jurisdiction ?? NOT_REPORTED],
            ]}
          />
        </div>
      </div>
      <p className="mt-4 max-w-3xl text-sm text-muted-foreground">
        Comparing identifiers (date of birth, nationality, registration number) needs data the
        synthetic records do not hold yet.
      </p>
      {children}
    </section>
  );
}
