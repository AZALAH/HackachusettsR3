# DataMon: 3-minute demo video script

**One speaker (Ahmed). Target length 2:55.** Judges stop at 3:00.
About 380 spoken words (~2:30 at 150 words per minute), which leaves ~25 s of
breathing room for clicks, streaming and the tour clip.

Order: intro → what it is and the problem → Kiro (quick) → live demo of the
whole UI → close.

`[SLIDE n]` = show that slide from `DataMon.pptx`. `[SCREEN]` = screen recording
of the app. Each slide's lines are also in its speaker notes.

---

## Before you record (5 minutes)

1. **Run the app locally**, not on Streamlit Cloud, so the "Manage app" badge
   (a third-party trademark) stays out of the video:
   `.venv\Scripts\python.exe -m streamlit run dashboard.py`
2. Open **Dataset quality** and note one **reject** episode and one **review**
   episode.
3. Set **Playback speed** to **8.0**. Stream the **review** episode once, so the
   review queue has something in it.
4. **Sign out**, so the recording starts on the login page.
5. Browser zoom 80–90%. No background music.

---

## Script

### 0:00–0:10 · Intro  `[SLIDE 1]`
> Hi, I'm Ahmed Salah. My teammate Jesse Silva and I built DataMon for the
> Robotics and Hardware track.

### 0:10–0:30 · What it is and the problem  `[SLIDE 2]` → `[SLIDE 3]`
> Robots learn by copying recorded demonstrations. But a frozen sensor, a
> timing glitch, or a recording nobody labelled teaches the robot the wrong
> thing, and nobody notices until after an expensive training run.
> *(switch to slide 3)* DataMon is a quality gate. Every recording gets a score
> from zero to a hundred, with reasons, and is accepted, held for a human, or
> quarantined.

### 0:30–0:52 · How we used Kiro  `[SLIDE 4]`
> We built it entirely with Kiro. Kiro Crew on my laptop set up the project,
> ran the tests, and shipped every feature as its own pull request. Kiro Web,
> in the cloud, couldn't install Streamlit, so it read Streamlit's source on
> GitHub and used the Playwright power to screenshot the UI before shipping.
> Specs and steering docs kept it consistent: twenty-one pull requests, a
> hundred and twenty-nine passing tests.

### 0:52–1:05 · Sign in  `[SCREEN]` login page → sign in as `judge`
> Here it is live, on real public robot data from DROID and BridgeData. The
> loading screen is actually scoring every recording, and telling robot jokes
> while it works.

*(In editing, cut the loader to ~4 s, then let the pop-in animation play.)*

### 1:05–1:20 · Sidebar setup  `[SCREEN]` point at the clock, Data source, Robot profile, Quality bands
> On the left you set the rules: the data source, a saved profile for your
> robot, and the pass marks. Below the first line is rejected, above the
> second is accepted, and in between, a human decides.

### 1:20–1:35 · The gate  `[SCREEN]` Ingest gate → reject episode → **Stream and gate**
> I'll replay a recording frame by frame, as if it's coming off a robot right
> now… and it's rejected. You see the verdict, and you hear it.

### 1:35–1:52 · Review queue  `[SCREEN]` Review queue → **Audit history** → **Promote to clean**
> When the gate isn't sure, it asks. I can promote this one, reject it, or
> send it back to be recorded again. Every decision goes into an audit trail
> that's never overwritten.

### 1:52–2:05 · Playback  `[SCREEN]` Episode playback → **Play**
> Playback shows any recording's sensor traces and timing, so you can see
> exactly where it went wrong.

### 2:05–2:20 · Report card and labels  `[SCREEN]` Dataset quality, then Label / coverage
> The report card scores every recording in the dataset. And here are
> recordings with missing or nonsense labels: the robot was never told what
> it was doing.

### 2:20–2:42 · Accessibility  `[SCREEN]` **Start guided tour** (let step 1 play ~5 s), then open **Ask about the interface**
> And nobody gets left out. There's a narrated tour, voiced with ElevenLabs,
> with captions and a pointing arrow, a help assistant that only answers from
> our own docs, and every animation turns off for anyone who prefers reduced
> motion.

*(While step 1 plays, add an on-screen caption in editing: "Narration voice:
ElevenLabs".)*

### 2:42–2:55 · Close  `[SLIDE 5]`
> It reads the open LeRobot format, so it works with any dataset published
> that way. Good data in, bad data out. That's DataMon. Thanks for watching.

---

## Timing check

| Section | Ends | Seconds |
|---|---|---|
| Intro + problem + solution | 0:30 | 30 |
| Kiro | 0:52 | 22 |
| Live demo (whole UI) | 2:42 | 110 |
| Close | 2:55 | 13 |

About two-thirds of the video shows the app working.
**If you run long:** cut the Playback beat (1:52–2:05) first, then the sidebar
beat.

**Backup slides** 6–9 (how scoring works, accessibility, who benefits, the
demo divider) are at the end of the deck. They're not in the video, but they're
there for questions or a live presentation.

---

## Video description (paste into YouTube / Vimeo)

> DataMon: a quality gate for robot training data. Built for Hackachusetts
> (Robotics & Hardware) by Ahmed Salah and Jesse Silva, using Kiro.
> Guided-tour narration voice generated with ElevenLabs.
> Code: https://github.com/AZALAH/HackachusettsR3

## Don't use tour step 11

Step 11 says the project was built with "agent hooks and property-based
tests". The repo has neither. Only show step 1. See `SUBMISSION.md` for a
corrected line.
