# Day 22 Meeting Rescheduling Infographic Prompt

Generate a polished 16:9 technical infographic for an open-source engineering report.

Exact title text:
"Safe Rescheduling: What the June 16 Meeting Established"

Exact subtitle text:
"Karmada #7621 -> PR #7662 | Official video ASR evidence"

Use an off-white or very light neutral background with crisp dark text. Use a restrained multi-color engineering palette: Karmada-like blue for existing components, teal/green for the target-first safety invariant, amber for open design questions, and red only for the service-loss risk. Do not use gradients, decorative blobs, glassmorphism, excessive rounded cards, mascots, or unrelated logos. Keep corners at 6px or less. The visual should feel like a serious architecture review artifact, not a marketing poster.

Create a left-to-right five-stage flow with clear arrows and compact technical illustrations:

1. "Resource pressure"
   Supporting text: "Set target watermarks | Rank workloads by balancing benefit | Stop when pools recover"
   Visual: two member-cluster resource pools with unequal utilization bars becoming balanced.

2. "Explicit intent"
   Supporting text: "WorkloadRebalancer is the user-facing rescheduling command | Automation may trigger it"
   Visual: a small CR/API document flowing into a scheduler.

3. "Current safety gap"
   Supporting text: "Delete source + create target happen together | Deletion is faster | Service is impaired"
   Visual: cluster A disappearing before cluster B is ready, with a concise red risk marker.

4. "Target-first invariant"
   Supporting text: "Create B -> wait until B is Ready and stable -> delete A"
   Visual: cluster A remains active while B warms up, then a controlled handoff. Make this the main visual focus.

5. "Workload-aware units"
   Supporting text: "CPU/GPU: Pod units | Sharded workloads: data-shard units"
   Visual: one Pod icon and one partitioned data-shard icon.

Add a bottom evidence boundary band with exact text:
"Supports: WR strategy direction, target-first behavior, Pod/shard granularity"
"Does not approve: API shape, ownership, persistence, rollback, or implementation"
"ASR evidence - not official minutes - no named-speaker attribution"

Add a small impact meter at bottom right with exact labels:
"Component replacement: MEDIUM"
"Runtime contract risk: HIGH to VERY HIGH"

All visible text must be English only, correctly spelled, sharp, and readable at report width. Preserve the exact spellings `Karmada`, `WorkloadRebalancer`, `Ready`, `Pod`, `data shard`, `ASR`, `API`, and `PR #7662`. Avoid tiny paragraphs; use strong hierarchy and concise labels. No Chinese characters. No watermark.
