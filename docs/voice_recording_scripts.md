# Voice clip recording guide — 3 clips, ~90 seconds each

These recordings are the raw material for the Voice Capture agent (spec §6.9) and
**Pattern 4 (divergence)** — the winning demo finding. Record them early; the whole
Day-1 voice module depends on having them.

## Ground rules

- **~90 seconds per clip**, one language per clip: **Tamil** (clip 1), **Hindi** (clip 2),
  and one more of your choice — Telugu / Malayalam / Kannada (clip 3).
- **Speak naturally, don't read.** Ramble, hesitate, self-correct — the LLM structuring
  pass is supposed to handle real speech. Reading a script aloud defeats the demo.
- Persona: a **senior operator / fitter with ~30 years at the plant, about to retire**,
  passing on what the manuals don't say.
- Phone voice-memo quality is fine (quiet room, phone ~20 cm from mouth).
  Save/convert to WAV or just drop the files in as-is:
  `corpus/audio/clip_01.wav`, `clip_02.wav`, `clip_03.wav`
  (m4a/mp3 also fine — faster-whisper reads them; we'll keep the names `clip_01..03`).

## The one thing every clip MUST contain (Pattern 4)

Each clip must independently make this claim, in your own words, in that clip's language:

> During the monsoon (June–September), the suction strainers on the P-101 pumps have to
> be cleaned **every two weeks / fortnightly** — the **monthly** schedule in the book is
> not enough, because debris load goes way up in the wet season.

Phrase it differently in each clip (that's what makes "three operators independently
say fortnightly" credible). Say the pump tag casually at least once — e.g. "p one oh
one A" — the pipeline deliberately has to recover `p-101a` from spoken words.

## Talking-point menus (pick a few per clip, any order, your own words)

**Clip 1 — Tamil (P-101 pumps / strainers focus)**
- The fortnightly-in-monsoon strainer claim (mandatory).
- What a plugging strainer sounds like: pump starts "eating gravel", discharge gauge
  needle goes shaky before the trip.
- Trick: check strainer ΔP gauge on Monday rounds; if it moved at all during monsoon,
  don't wait for the schedule.

**Clip 2 — Hindi (seals / bearings focus + the monsoon claim)**
- The fortnightly-in-monsoon strainer claim (mandatory).
- A seal that weeps a little on startup usually settles by lunch; one that drips
  steadily will fail within the month — change it in the next planned window, don't wait.
- Old-timer trick: touch the bearing housing with the back of the hand every round —
  "if you can't hold five seconds, raise a work order."

**Clip 3 — your third language (vibration / general wisdom + the monsoon claim)**
- The fortnightly-in-monsoon strainer claim (mandatory).
- P-102A has "always been a shaky pump" — alignment never holds more than a few months;
  people keep re-aligning instead of fixing the baseplate grout (root cause).
- After any power failure, the dosing pumps don't restart on their own — everyone
  forgets, water chemistry drifts for days.

## After recording

Drop the three files into `corpus/audio/`. Everything downstream (transcription →
translation → claim extraction → divergence detection) is automated from there.
