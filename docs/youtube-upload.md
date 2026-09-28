# FieldReady Local — YouTube upload package

Use this after recording the final demo from `docs/demo-script.md`.

## Recommended title

**FieldReady Local | Local Survey Quality Review with MCP + Bounded AI | Amazon Developer Hackathon**

Alternative shorter title:

**FieldReady Local — MCP-Powered Survey Quality Review | Amazon Developer Hackathon**

Prefer the first title unless it is visually truncated in an unhelpful way.

## Recommended YouTube description

FieldReady Local is a local-first survey-quality review assistant built for the Alexa+ track
of the Build, Ship, Shape: Amazon Developer Hackathon.

Instead of letting AI become the source of truth, FieldReady Local uses a stricter authority
boundary:

Deterministic rules own the facts -> MCP exposes bounded evidence operations -> local AI
helps interpret review focus -> the supervisor explicitly owns the decision -> local export
preserves the audit trail.

In this demo:

- a versioned synthetic field-survey batch is validated locally;
- 14 fictional records produce 17 evidence-backed findings across 13 affected records;
- the browser shows a real self-hosted MCP connection over Streamable HTTP;
- deterministic Python explains why each finding was raised and what should be verified;
- optional local qwen2.5:1.5b AI only classifies the review focus;
- a supervisor explicitly confirms the review decision;
- the reviewed run exports a Markdown summary, findings CSV, review-history CSV and
  integrity manifest;
- the raw source CSV is deliberately excluded from the export.

Verified project evidence includes real MCP/web/SQLite integration, restart persistence,
local report export, a network-disabled full-stack test and a public Apache-2.0 repository.

This is a simulated Alexa+ experience backed by a real local MCP server. It does not claim a
live Alexa+ connection or Amazon certification.

GitHub:
https://github.com/buriro-ezekia/fieldready-local

Primary track:
Alexa+

Mini challenge:
None

#AmazonDeveloperHackathon #AlexaPlus #MCP #LocalAI #SurveyData #DataQuality

## Short description for sharing

**FieldReady Local turns survey-quality problems into an evidence-backed supervisor review:
real MCP, deterministic validation, bounded local AI and explicit human approval — all in a
local-first workflow.**

## Recommended thumbnail text

Use very little text:

**FIELDREADY LOCAL**

Smaller secondary line:

**Evidence. AI. Human Control.**

Optional small badge:

**MCP • LOCAL-FIRST**

Avoid placing all 14/17/13 metrics on the thumbnail. Those belong inside the video.

## Thumbnail composition

Recommended layout:

- left: FieldReady Local name + one-line hook;
- right: clean crop of the supervisor dashboard;
- visible metrics: 14 Records / 17 Findings / 13 Affected;
- keep the MCP live badge visible if the crop remains readable;
- no personal browser chrome, private token or Windows path.

Do not use generated people, stock survey workers or unrelated Amazon/Alexa imagery. The
product UI itself is stronger and avoids misleading viewers about the actual demo.

## Upload settings checklist

- Visibility: **Public**
- Language: **English**
- Video duration: **under 3:00**
- Use an audience setting that accurately reflects the developer/product-demo content.
- Add the repository URL in the description.
- Do not use copyrighted background music or footage unless you have permission.
- Keep comments/settings at your normal preference; they are not part of the product proof.

## Suggested video filename before upload

`fieldready-local-amazon-developer-hackathon-demo.mp4`

## Optional chapter-style timestamps for the description

For a video this short, chapters are optional. If you include them, use:

00:00 Field data quality problem
00:16 Real MCP-backed simulated Alexa+ experience
00:30 Versioned field-survey validation
00:52 Evidence and priority review
01:17 Bounded local AI
01:47 Explicit human decision
02:10 Local audit export
02:27 Final architecture

Adjust these timestamps to the actual recording. Do not publish inaccurate timestamps merely
to match the script.

## Final upload sequence

1. Record using `docs/demo-script.md`.
2. Watch the entire exported MP4 once before uploading.
3. Confirm:
   - no token;
   - no personal path;
   - no real respondent data;
   - audio is clear;
   - UI text is readable;
   - final duration is below three minutes.
4. Upload the MP4 to YouTube.
5. Set it to Public.
6. Paste the recommended title and description.
7. Add the chosen thumbnail.
8. Open the public video in a private/incognito browser to verify it is actually viewable.
9. Copy the final public YouTube URL.
10. Replace `REQUIRES_CONFIRMATION_VIDEO_URL` in `docs/devpost-submission.md`.
11. Run:

       .\.venv\Scripts\python.exe scripts/check_submission.py

12. Do not submit to Devpost until the command ends with:

       SUBMISSION AUDIT: PASS

## Final verbal closing line

Use this exactly if it sounds natural in your delivery:

> **Evidence stays authoritative, AI stays bounded, and the human stays in control.**
