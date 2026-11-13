# Roadmap: Multi-Modal Evidence

**Status:** idea, not scheduled. "Current state" corrected on 2026-11-11.
**Goal:** Extend ARGUS identity verification beyond static documents to voice, video, and liveness signals.

---

## Current state

ARGUS reads static, synthetic identity documents only, and not yet through the API:

- The API has no documents field. OCR runs only when the Identity agent is called directly,
  as the tests do.
- Locally, Tesseract reads the `Label: value` lines of the synthetic documents (PNG and PDF).
- The Azure implementation (Document Intelligence) is tested against stand-ins and has not run
  against the live service.
- `identity_validator` cross-checks extracted fields against the entity store.

Everything below would process biometric data of real people. That is outside the
synthetic-data rule in [`AGENTS.md`](../../AGENTS.md) and would need its own decision, a
privacy review and a lawful basis before any of it is built.

## What multi-modal adds

### Liveness detection

Prevents spoofing with a printed photo or screen replay. The identity agent gains a `liveness_check` tool that:

- Requests a brief selfie video (3-second blink or head-turn prompt)
- Scores passive liveness (texture analysis) + active liveness (motion prompt compliance)
- Returns a liveness confidence score (0–1) fed into the Identity dimension score

### Voice identity

For accessibility and low-literacy contexts where document upload is a barrier:

- The applicant reads a random 6-word phrase
- Voice biometric embedding compared against a previously enrolled sample (enrollment optional)
- Voice + document together raise identity confidence; voice alone is supplementary

### Document + face matching

- Extract face from ID photo using Azure Face API
- Compare against selfie captured at submission time
- Match confidence fed into Identity dimension

---

## Accessibility considerations

Multi-modal cannot become an exclusion mechanism. Every evidence type is supplementary, not required:

- Liveness check must have a fallback (human agent video call)
- Voice check must have a fallback (document-only path)
- All video/audio UI must have captions and keyboard-navigable controls
- No biometric data stored longer than the assessment session without explicit consent

---

## Tech stack additions

| Component | Service | Community Edition alternative |
| --- | --- | --- |
| Liveness detection | Azure AI Vision / Face API | OpenCV passive liveness (less accurate) |
| Voice biometrics | Azure Speaker Recognition | Resemblyzer (open source) |
| Face matching | Azure Face API | DeepFace (open source) |

---

## Rollout plan

- [ ] Privacy policy update (biometric data handling)
- [ ] Liveness check tool in Identity Agent
- [ ] Face match tool in Identity Agent
- [ ] Web UI: webcam capture component (ARIA-labelled, keyboard accessible)
- [ ] Community Edition: OpenCV + Resemblyzer path
- [ ] Tests: stand-in liveness/face API responses, accessibility test for capture UI
