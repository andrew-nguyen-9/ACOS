# Phase 11.9 — Frontend Showcase Capstones + Phase 11 Close-out

**Track:** Frontend · **Depends on:** 11.5–11.8 (and all of 11.0–11.4 for the close-out audit) · **Status:** Planned

> Read the roadmap index first. Heaviest visual tier + the final hardening sign-off for the whole
> phase. Everything here is opt-in/degradable and gated by the 11.0 FPS budget.

---

## 1. Context

This segment lands the emotional-payoff features and then **closes Phase 11**: a full perf audit,
accessibility/reduced-motion pass, documentation, and a release-safety review across both tracks.

Reuses: 11.5 tokens/motion, 11.6 kinematics, 11.7 WebGL canvas + throttled clock + capability tier,
11.8 haptics. New WebGL here renders into the **same single canvas/clock** from 11.7 — no second context.

## 2. Guidelines implemented (IDs)

- **HVP-001** "Hired" success choreography (WebGL particle dispersion from resume words)
- **HVP-002** sub-pixel tactile feedback (haptic + sound on score milestones) — reuse 11.8 haptics
- **IIS-001** spatial-audio mock interview panel (Web Audio API positional voices)
- **IIS-002** real-time cadence/pace map (lightweight waveform) — *if cheap*
- **RCL-003** quantum cover-letter morphing (tone dial morphs typography/structure)
- Catalog: #83 particle celebration, #98 milestone constellations, #44 filler-word vaporize (IIS)

## 3. Goals

- **Success choreography (HVP-001/HVP-002)**: on finalize/export or a score milestone, a GPU
  particle effect (in the 11.7 canvas) that pulls the document's actual words into a constellation,
  paired with a haptic tick + subtle sound. Skippable, reduced-motion → a tasteful static flourish.
- **Quantum cover-letter morphing (RCL-003)**: a slider on the cover-letter editor between
  "Traditional ↔ Bold" that morphs tone *and* typography (variable-font axes from 11.5) with a
  fluid transition; calls the existing cover-letter generation with a tone parameter.
- **Immersive interview sim (IIS-001)**: Web Audio API positions AI interviewer voices in stereo
  space (panner nodes) for a panel feel; an abstract WebGL interlocutor (reuse canvas) pulses with
  speech. Cadence waveform (IIS-002) only if it stays cheap.
- **Phase 11 close-out**: final perf audit (re-run all 11.0 benches + FE traces), a11y pass
  (reduced-motion everywhere, focus states, keyboard nav), docs update, release-safety review.

## 4. Non-goals (YAGNI)

- No video avatars / no real-time face tracking / no posture analysis.
- No speech-to-text engine build — if cadence needs audio analysis, use existing Web Audio
  `AnalyserNode` only (volume/timing), not transcription. Filler-word detection only if a cheap
  heuristic exists; otherwise drop.
- No second WebGL context — extend the 11.7 canvas.
- No new backend features; reuse cover-letter/interview endpoints (add a tone param at most).

## 5. Design

- `frontend/src/webgl/SuccessParticles.tsx`: a particle system rendered into the existing canvas;
  takes the document's words, disperses/reassembles into a constellation. Triggered by an event bus
  (`emitCelebrate(words)`); auto-cleans; respects the throttled clock + capability tier.
- `frontend/src/components/cover_letter/ToneDial.tsx` + `useToneMorph.ts`: a slider mapping 0..1 to
  (a) a backend `tone` param for regeneration and (b) live `font-variation-settings`/spacing morph
  via framer-motion `useTransform`. Debounce backend calls; morph typography instantly client-side.
- `frontend/src/audio/spatialPanel.ts`: Web Audio graph with `PannerNode`/`StereoPannerNode` per
  virtual interviewer; plays existing TTS/audio (or beeps as placeholder) from positioned sources.
- `frontend/src/components/interview/Interlocutor.tsx`: abstract WebGL shape (canvas) reacting to an
  `AnalyserNode` amplitude. Cadence waveform `CadenceMeter.tsx` from the same analyser (optional).
- Wire celebrate triggers into resume/cover-letter finalize + score-milestone points.

### Close-out tasks (do these last, as their own commits)
- Re-run `scripts/perf/*` + 11.0 FE traces; update `docs/PERFORMANCE_LOG.md` with final numbers vs
  the Phase 11 start baseline. Confirm **no metric regressed** beyond budget.
- a11y sweep: every animation honors `prefersReducedMotion`; visible focus rings; tab order; the
  visual-effects "Off" tier produces a fully usable, calm app.
- Update `docs/08_ROADMAP.md` (mark Phase 11 done + criteria), `docs/USER_GUIDE.md` (effects/backup/
  recovery/maintenance), `README.md`, and `MEMORY.md` pointer.
- `claude-md-management` + `pr-review-toolkit` release-safety review across 11.0–11.9.

## 6. File-level plan

```
NEW  frontend/src/webgl/SuccessParticles.tsx
NEW  frontend/src/lib/celebrate.ts                (event bus: emitCelebrate/onCelebrate)
NEW  frontend/src/components/cover_letter/ToneDial.tsx
NEW  frontend/src/components/cover_letter/useToneMorph.ts
NEW  frontend/src/audio/spatialPanel.ts
NEW  frontend/src/components/interview/Interlocutor.tsx
NEW  frontend/src/components/interview/CadenceMeter.tsx   (optional/if cheap)
EDIT frontend/src/pages/CoverLetterPage.tsx       (ToneDial + morph)
EDIT frontend/src/pages/InterviewPrepPage.tsx     (spatial panel + interlocutor)
EDIT frontend/src/pages/ResumePage.tsx            (celebrate on finalize/export)
EDIT frontend/src/webgl/MaterialCanvas.tsx        (host particle layer)
EDIT docs/PERFORMANCE_LOG.md, docs/08_ROADMAP.md, docs/USER_GUIDE.md, README.md
EDIT MEMORY.md pointer (+ memory file for Phase 11)
```

## 7. Test plan

- Unit: `celebrate` bus subscribe/emit; `useToneMorph` maps slider→axes + debounces backend; spatial
  panel builds the audio graph without throwing (mock AudioContext); reduced-motion → static paths.
- Playwright e2e: finalize resume → celebrate runs (canvas active) and is skippable; tone dial morphs
  cover letter without console errors; interview page builds audio graph (no error) and renders interlocutor.
- **Manual perf gate (BLOCKING):** particle burst holds ≥60fps; interview page (audio + WebGL)
  holds ≥60fps; with effects Off, all features still work (static fallbacks). Attach traces.
- **Close-out gate:** all 11.0 benches within budget vs phase-start baseline; a11y checklist passed.

## 8. Plugin orchestration checklist

- [ ] `context7` — Web Audio PannerNode/AnalyserNode, R3F particles (instanced meshes), framer-motion variable-font morph.
- [ ] `chrome-devtools` skill — FPS/GPU + audio perf for the gates.
- [ ] `frontend-design` — celebration must be tasteful (no generic confetti), interview UI premium.
- [ ] `claude-md-management` — finalize docs.
- [ ] `pr-review-toolkit` + `security-guidance` — **phase-wide release-safety review** (both tracks).
- [ ] `superpowers:verification-before-completion`.

## 9. Perf budget impact

Highest-cost segment. Mitigations: particles are instanced + transient (auto-dispose); reuse the one
canvas + throttled clock (App-Nap pauses everything when hidden); audio nodes torn down on unmount;
all gated by capability tier. BLOCKING 60fps gates above. Initial bundle unaffected (lazy).

## 10. Risks & mitigations

- *Particle GC/leak on repeat* → dispose geometries/materials on cleanup; cap particle count; test repeat triggers.
- *AudioContext autoplay policy* → create/resume on user gesture (start-interview button).
- *Feature creep (full interview AI)* → strictly visual/audio shell over existing endpoints; no new ML.
- *Close-out finds a regression* → fix or default-off the offending effect; stability > show.

## 11. Definition of Done

Success choreography, quantum tone dial, spatial interview panel + interlocutor implemented and
degradable; BLOCKING FPS gates passed; **Phase 11 close-out complete** — all benches within budget,
a11y pass, docs (`08_ROADMAP`, `USER_GUIDE`, `PERFORMANCE_LOG`, `README`, memory) updated, phase-wide
release-safety review run. **Phase 11 ends here.**
