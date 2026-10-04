# Deploying ARGUS to Azure

How to put the API on Azure the way decision D1 describes it ("Hosting" in
[ARCHITECTURE.md](ARCHITECTURE.md)), fill its data plane, check it, and remove it again. Nothing here is needed to run ARGUS locally:
the local data plane, the default, uses no cloud service at all.

Every command runs the same in PowerShell and bash. None of them prints a key.

## What gets created

[`infra/main.bicep`](../infra/main.bicep) creates everything in one resource group:

| Resource | Tier | Cost when idle |
| --- | --- | --- |
| Container Apps environment and the API app | Consumption profile, 0 to 1 replicas, 0.5 vCPU and 1 GiB | $0 (within the monthly free grant) |
| Log Analytics workspace | Pay as you go, 30-day retention, 0.1 GB daily ingestion cap | About $0 |
| Azure AI Search | Free: 50 MB, 3 indexes, one per subscription | $0 |
| Cosmos DB | Free tier: one database of 1000 RU/s shared by five containers, one per subscription | $0 |
| Foundry (AI Services) account with a `gpt-5.4-mini` deployment | S0, Data Zone Standard (EU), 10k tokens a minute | $0; pay per token |
| Document Intelligence | F0: 500 pages a month, one per subscription | $0 |

No keys are stored. The API's managed identity signs in to Cosmos DB, the model and Document
Intelligence, and their local (key) authentication is turned off. The one key is AI Search's
query key (read only), because the Free tier has no keyless access: the template reads it from
the service and hands it to the API as a Container Apps secret. The image comes from GitHub
Container Registry, so there is no container registry to pay for, and there is no virtual network.

The API does not accept identity documents yet, so Document Intelligence is deployed but not
called, and its public network access is off until it is (see "Known issues" in
[`CHANGELOG.md`](../CHANGELOG.md)). The Foundry account stays reachable over the internet, as
there is no virtual network; only Entra ID sign-in, with the API's role, is accepted there.

## Before the first deployment

1. **Approval.** Each deployment creates resources in an Azure subscription; get the
   maintainer's approval first ([`AGENTS.md`](../AGENTS.md)). Keep a budget alert on the
   subscription.
2. **Free-tier slots.** AI Search Free, the Cosmos DB free tier and Document Intelligence F0 each
   allow one per subscription. If one is already taken, the deployment fails; for Cosmos DB,
   `cosmosFreeTier=false` deploys a billed account instead.
3. **Model quota.** `gpt-5.4-mini` Data Zone Standard needs 10k tokens a minute of quota in the
   region (`chatCapacity` sets it). The API is public, so this rate is also the most that a flood
   of requests can spend on the model.
4. **Tools.** The Azure CLI, signed in (`az login`), with Owner (or Contributor and Role Based
   Access Control Administrator) on the resource group. `uv` for the data scripts.
5. **The image.** A public image of the API on GitHub Container Registry, built from the root
   `Dockerfile`. Container Apps pulls it anonymously, so the package must be public (package
   settings on GitHub, once).

## Deploy

Create the resource group once, then deploy the template. The deployment must be named `argus`:
the scripts below read its outputs by that name.

```sh
az group create --name rg-argus --location swedencentral
az deployment group create --resource-group rg-argus --name argus \
  --template-file infra/main.bicep \
  --parameters image=ghcr.io/iarjunganesh/argus@sha256:<digest> \
               operatorPrincipalId=$(az ad signed-in-user show --query id --output tsv) \
  --query properties.outputs.apiUrl.value --output tsv
```

In PowerShell, continue the lines with a backtick instead of a backslash. The command prints the
API's address. `operatorPrincipalId` gives you the Cosmos DB data role that filling the data
plane needs; leave it out on later deployments if you like, the role stays. Other parameters
(region, model, capacity, the web UI's origin in `corsOrigins`) are described in the template.

Redeploying the same template with a new `image` replaces the API's revision and leaves the data
alone.

## Fill the data plane

Generate the synthetic data, then upload it and build the three knowledge bases:

```sh
uv run python data/synthetic/generate_entities.py
uv run python data/synthetic/generate_corporate_graph.py
uv run python data/synthetic/generate_transactions.py
uv run python data/synthetic/generate_sanctions.py
uv run python data/synthetic/generate_adverse_media.py
uv run python infra/populate.py --resource-group rg-argus
```

[`infra/populate.py`](../infra/populate.py) creates the search indexes, knowledge sources and
knowledge bases, indexes the regulation texts, sanctions and adverse media, and uploads the
entities, ownership graph and transactions to Cosmos DB. It reads the search admin key with your
Azure access and passes it to those steps only. Every step overwrites what is there, so it can
run again after the data is regenerated.

## Check it

```sh
uv run python scripts/ci/smoke_api.py https://<the API's address>
```

This runs the synthetic Cayman Synth Capital demo through the deployed API: the progress stream,
the report, its CRITICAL tier (a potential sanctions match), where each result came from, and
cited regulations (which need the filled knowledge bases).
It prints how long `/health` took to answer, which is the cold start when the API was scaled to
zero.

## Deploy from GitHub

[`deploy.yml`](../.github/workflows/deploy.yml) does the same from GitHub Actions: it builds the
image, pushes it to GitHub Container Registry as `sha-<commit>`, deploys the template with the
image's digest, and runs the smoke test against the result. It runs when started by hand (Actions
→ Deploy → Run workflow) and after every published release (`release.yml`). It signs in to Azure
with OpenID Connect, so no client secret exists anywhere. Setting it up, once:

1. **An identity for the workflow.** Create an app registration (Microsoft Entra ID → App
   registrations → New), and on it a federated credential for GitHub Actions: organization
   `iarjunganesh`, repository `argus`, entity **Environment**, name `azure`.
2. **Its access, on the resource group only.** Contributor, plus Role Based Access Control
   Administrator constrained to assigning the two roles the template grants the API (Cognitive
   Services OpenAI User and Cognitive Services User; the portal's "Allow user to only assign
   selected roles" condition does this).
3. **The GitHub environment.** Settings → Environments → `azure`: allow deployments from `main`
   and `v*` tags only (optionally require a reviewer), and add the environment secrets
   `AZURE_CLIENT_ID` (the app's client ID), `AZURE_TENANT_ID` and `AZURE_SUBSCRIPTION_ID`. They
   are identifiers, not credentials; as secrets they are masked in the public logs.
4. **The target.** The repository variable `AZURE_RESOURCE_GROUP` (for example `rg-argus`).
   `release.yml` deploys only when it is set.
5. **The package.** After the first run, make the `argus` package public (Packages → argus →
   Package settings → Change visibility), then run the workflow again.

The deployed API runs only the synthetic demo cases (`ARGUS_DEMO_ONLY=true` in the template):
anything else gets a 403, so visitors can't enter a real person's details. Reports and their
progress events expire 24 hours after their last change (the `kyc_reports` container's default
time to live), and the logs, kept 30 days, record report IDs but not entity names.

The workflow deploys with the template's defaults; filling the data plane stays a step you run
yourself.

## The web UI

The web UI is deployed separately, on Vercel: a project with root directory `web`, framework
Next.js, and two environment variables: `NEXT_PUBLIC_API_URL`, set to the API's address, and
`NEXT_PUBLIC_ARGUS_DEMO_ONLY=true`, so the site offers only the demo cases the API accepts. The
API must list the site's origin in `corsOrigins`.

## Limits to know

- **Requests end after 240 seconds.** Container Apps' ingress closes any HTTP request after 240
  seconds. An assessment finishes well within that; a progress stream that is cut reconnects and
  resumes from its last event.
- **Cold starts.** At zero replicas, the first request waits for the API to start. The smoke test
  measures it.
- **Reports live in Cosmos DB,** so they survive the API scaling to zero.
- **AI Search Free** may be deleted after a long time without use when the region runs short of
  capacity. Moving to Basic means a new service and a rerun of `infra/populate.py`.

## Remove it

```sh
uv run python infra/teardown.py --resource-group rg-argus
uv run python infra/teardown.py --resource-group rg-argus --yes
```

The first command only lists what would be deleted. The second deletes the Log Analytics
workspace for good, then the resource group with everything in it, then purges the two AI
accounts, which Azure otherwise keeps soft-deleted for 48 hours with their names and model quota.
Use a resource group that holds nothing but ARGUS.
