# DataMon: 3-minute demo video script

Target length: **2:55**. Judges stop at 3:00, so keep 5 seconds spare.
About 385 spoken words (~2:34 at 150 words per minute), which leaves ~20 s for streaming and the tour clip.

`[SLIDE n]` means show that slide from `DataMon.pptx`.
`[SCREEN]` means a screen recording of the running app.
Each slide's lines are also in its speaker notes.

---

## Before you record

1. **Record the app running locally, not on Streamlit Cloud.**
   `.venv\Scripts\python.exe -m streamlit run dashboard.py`
   The local version has no "Manage app" button or Streamlit Cloud badge. The
   rules forbid third-party trademarks without permission, so this keeps them
   out of the video. It still counts as "the project functioning on the device".
2. **Pick your episodes in advance.** Open **Dataset quality** and note:
   - one episode with grade **reject** (for the alert sound), and
   - one episode with grade **review** (so the review queue isn't empty).
   Set **Playback speed** in the sidebar to **8.0** so streaming takes about 1–2 seconds.
3. **Pre-stream the review episode once** before you hit record. It then waits
   in the review queue for the demo.
4. Set the browser zoom so the whole dashboard fits (80–90% usually works).
5. **No background music**, unless it's royalty-free with a licence you can show.
6. Don't play tour step 11 (see the note at the bottom).

---

## Script

### 0:00–0:08 · Hook  `[SLIDE 1]`
> Robots learn by copying recorded demonstrations. And one bad demonstration
> can quietly teach a robot the wrong move. This is DataMon.

### 0:08–0:20 · The problem  `[SLIDE 2]`
> A frozen sensor. A timing glitch. A recording nobody labelled. The robot
> learns from all of it, and nobody notices until after an expensive training
> run. Garbage in, garbage out. Except here, the garbage learns to drive a
> robot arm.

### 0:20–0:30 · The solution  `[SLIDE 3]`
> DataMon is a quality gate for robot training data. Every recording gets a
> score from zero to a hundred, with the reasons, and goes one of three ways:
> clean, held for a human, or quarantined.

### 0:30–0:42 · Sign in  `[SCREEN]` sign in as `judge`, loader plays
> Here it is live, on real public robot data from DROID and BridgeData. The
> loading screen is actually scoring every recording, and telling robot jokes
> while it works.

*(Cut the loader to about 4 seconds in editing. Let the pop-in animation play.)*

### 0:42–0:58 · The gate  `[SCREEN]` Ingest gate → pick the **reject** episode → **Stream and gate**
> I'll replay a recording frame by frame, as if it's coming off a robot right
> now… and it's rejected. You see the verdict, and you hear it.

### 0:58–1:15 · Review queue  `[SCREEN]` Review queue → open **Audit history** → **Promote to clean**
> When the gate isn't sure, it asks. I can promote this one, reject it, or
> send it back to be recorded again. Every decision lands in an audit trail
> that's never overwritten.

### 1:15–1:27 · Report card  `[SCREEN]` Dataset quality
> The report card for the whole dataset: a score, a verdict and the reasons
> for every recording.

### 1:27–1:35 · Labels  `[SCREEN]` Label / coverage
> And here, recordings with missing or nonsense task labels. The robot was
> never told what it was doing.

### 1:35–1:55 · Accessibility  `[SCREEN]` sidebar → **Start guided tour** (let step 1 play ~5 s with its caption), then `[SLIDE 6]`
> We built it so nobody's left out: a narrated tour with captions and a
> pointing arrow, a help assistant that only answers from our own docs, and
> reduced-motion support throughout.

### 1:55–2:30 · How we used Kiro  `[SLIDE 7]`
> We built all of it with Kiro, using two of its tools. Kiro Crew on a laptop
> set up Python, ran the app and tests, and shipped each feature as its own
> pull request. Kiro Web worked in a cloud sandbox that couldn't install
> Streamlit, so it read Streamlit's source on GitHub, let CI run the tests,
> and used the Playwright power to screenshot the interface before shipping.
> Specs defined our core features, and two steering docs kept every session
> honest and tested. Twenty-one pull requests, a hundred and twenty-nine
> passing tests.

### 2:30–2:45 · Who benefits  `[SLIDE 8]`
> DataMon reads the open LeRobot format, so it works on any dataset published
> that way, and live robots can stream straight in. Labs, data-collection
> teams and dataset publishers catch bad data while it's still cheap to fix.

### 2:45–2:55 · Close  `[SLIDE 9]`
> Good data in. Bad data out. That's DataMon.

---

## Timing check

| Section | Ends at | Seconds |
|---|---|---|
| Hook, problem, solution (slides) | 0:30 | 30 |
| Live demo | 1:35 | 65 |
| Accessibility | 1:55 | 20 |
| Kiro | 2:30 | 35 |
| Value + close | 2:55 | 25 |

Over 60% of the video shows the app working, which is what the rules ask for.
If you run long, cut the **Labels** beat (1:27–1:35) first, then shorten the
Kiro section to its first and last sentences.

---

## Note: tour step 11 overclaims

Tour step 11 says DataMon was built with "specs, agent hooks, and
property-based tests". The repo has specs and steering, but **no agent hooks
and no property-based tests**. A judge who checks `/.kiro` would notice. Don't
use step 11 in the video. Before submitting, either re-record that one line or
change the caption (see `SUBMISSION.md`).
