# Security policy

## Reporting a vulnerability

Please report vulnerabilities privately, through GitHub:
**[Report a vulnerability](https://github.com/iarjunganesh/argus/security/advisories/new)**
(the repository's **Security** tab → **Report a vulnerability**). Don't open a public issue.

Include what you found, how to reproduce it, and what an attacker could do with it. You should
get an acknowledgement within a week.

## Scope

ARGUS is a research and demonstration system. It works on synthetic data and makes
recommendations for a human reviewer; it is not a production KYC service. Reports are still
welcome, especially about:

- secrets or credentials that could leak through logs, reports or the UI;
- ways to make an explanation hide or contradict the underlying findings;
- dependency vulnerabilities that CI's `pip-audit` step has not caught.

**Never include real personal data** in a report, a reproduction or a test case.

## Supported versions

Only the latest release and the `main` branch receive fixes.
