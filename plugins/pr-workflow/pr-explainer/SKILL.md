---
name: pr-explainer
description: >
  Help a reviewer understand a pull request before they review it. Reads the PR description,
  linked tickets, the full diff and the surrounding code at the PR's head commit, forms its own
  model of the change, then publishes an interactive explainer page as an Artifact (what changed
  and why, where it hooks into the existing flow, flag or mode behaviour, a playground for any
  pure heuristic, a short animation (an SVG scene on a GSAP timeline, Three.js or a Remotion
  video) when a concept is clearer in motion, a suggested review order, the places worth a
  careful read and questions for the author) and gives a short guide in chat. Use this whenever the user shares a PR link or number
  and asks to understand it, get walked through it, get a guide or explainer for it, know how or
  in which order to review it, or what to focus on, even if they don't say "explainer". It
  explains rather than reviews: use pr-review when the user wants review comments or a verdict.
---

# PR Explainer

Turns "help me understand this PR" into an interactive page a reviewer reads before opening the
diff, plus a short guide in chat. The goal is understanding: what the change does, why, where it
plugs in, and where its subtleties are. It is not a review. It gives no approve or reject verdict
and writes no review comments. Points of concern are framed as "confirm this is intended".

## 1. Read the PR

Get the metadata and description:

```bash
gh pr view <n> --repo <owner/repo> --json title,body,author,state,baseRefName,headRefName,headRefOid,additions,deletions,changedFiles,files,commits,labels,reviews,comments
```

- Read the description and every linked ticket. Ticket bots often paste the ticket text into a PR
  comment. Otherwise fetch it through the ticket tracker's MCP server or CLI when one is
  available, and ask the user for the text when none is. The parent ticket usually holds
  the "why", the product decisions and what is out of scope.
- Save the diff to the scratchpad (`gh pr diff <n> --repo <owner/repo> > diff.patch`). Read the
  non-test files first, then list the test names, which show the intended behaviour:

  ```bash
  awk '/^diff --git/{p = ($0 !~ /__tests__|\.spec\.|\.test\.|int-spec|_test\./)} p' diff.patch
  grep -nE "^\+\s*(it|describe|test)(\.each)?\(" diff.patch
  ```

  Adjust both patterns to the repo's language and test layout (for example `def test_` in
  Python or `func Test` in Go).

## 2. Read the code around the change

The diff alone hides what the change relies on. Read the touched functions in full, their callers
and the helpers they call, **at the PR's head commit**:

```bash
git fetch -q origin +pull/<n>/head:refs/remotes/origin/pr-<n>
git rev-parse --short origin/pr-<n>   # must equal headRefOid
git show origin/pr-<n>:<path>
```

Always fetch with the leading `+` into `refs/remotes/...`. A plain `git fetch origin
pull/<n>/head:pr-<n>` silently keeps an older local branch when the PR was force-pushed, and you
end up explaining code that no longer exists. Check the short SHA against `headRefOid` before
reading. Run these from a local clone of the PR's repository. If you can't find one, ask the user
where it is, or read the files through `gh api repos/<owner/repo>/contents/<path>?ref=<headRefOid>`.

For a large PR, an Explore subagent can map callers and helpers. Read the core logic yourself.

## 3. Form your own model

Before writing anything, settle on these points in your own words. Each one becomes a section of
the page:

- **The gist.** Two to four separate ideas the PR introduces, and the single most important
  fact a reviewer could miss (for example "the new heuristic is computed but never applied in
  this PR").
- **Concrete cases.** The real examples the PR or ticket is built around: input, behaviour
  before, behaviour after. Tests named after tickets or customers are the best source.
- **Where it hooks in.** The existing flow as a sequence of steps, each marked unchanged,
  changed, new or refactor-only, with what changed in each.
- **Modes.** If the change sits behind a flag or mode: what runs, what is applied and what is
  only logged, in each mode. Check that `off` really keeps today's behaviour.
- **Pure logic worth trying.** A parser, matcher, scoring rule or heuristic whose behaviour
  depends on input. Note its exact rules so you can port it.
- **A concept that moves.** Something easier to see in motion than to read. Note it only if the
  PR has one; most PRs don't. Section 4 lists the kinds that qualify.
- **Review order.** The files in the order that builds understanding fastest. Usually: contract
  (description, docs, types), then pure helpers with their tests, then the wiring, then mechanical
  refactors to skim, then one-liners, then integration tests.
- **Things to look at closely.** Verify each against the code before listing it. Good sources:
  behaviour that differs from what a name or comment promises, fallbacks that disappear, paths
  that only work under some configuration, shadow or logging paths that diverge from the real
  path, heuristics broader than they look, log fields whose meaning shifts with a flag, scope the
  description does not mention, and test runs that only passed locally.
- **Questions for the author.** The open points that only the author can settle.

Do not invent problems to fill the list. If something is fine, leave it out.

## 4. Build the explainer page

Call `Artifact` with `action: "quickstart"`, `intent: "other"` and `design_systems: false`, and
follow its page guidance for a plain page. Write the HTML in the scratchpad. Sections, in this
order, each skipped when it has nothing real to show:

1. **Header.** Repo, PR number, title, a one-paragraph summary, and chips for size
   (`+add / −del`, files), risk labels, the flag key, author, and a link to the PR's files tab.
2. **The gist.** Short cards for the main ideas, then the most important fact in one sentence.
3. **Concrete cases.** A table with one row per case: input, before, after, and what is
   actually applied.
4. **Where it hooks in.** Clickable pipeline steps tagged changed, new or unchanged, with a
   detail panel for the selected step that names functions and files.
5. **See it move** (optional). A short animation of the concept that moves. See "Animations"
   below.
6. **Modes.** A segmented control per mode showing what runs, what is applied and what is only
   logged.
7. **Playground.** A form with presets taken from the concrete cases, plus a step-by-step trace
   of which branch fired and the result. Port the logic line for line from the PR (regexes,
   constants, thresholds) and say on the page that it is a port. Add one or two presets that
   probe a concern from the "look closely" list.
8. **Review order.** A numbered list of collapsible steps, each with files, approximate size,
   why it sits at that point and what to check. Open the first few.
9. **Look closely at.** Cards with a severity label (high, med or low) plus a short category, a
   one-line heading and a short explanation that names the code.
10. **Questions for the author.**
11. **Footer.** Sources (description, diff at `<short sha>`, surrounding code) and what is out
    of scope.

Keep the copy plain and specific: name functions, files, flags and real values. Build the
interactive parts with a small inline script and no libraries, except GSAP or Three.js for an animation.

### Animations

An animation is one explaining tool among several. Use it when it shows something the
diagram, table or playground can't, and skip it otherwise. Most PRs need none. It fits:

- **Data moving through stages.** Items passing through a pipeline, a queue, retries or a
  fan-out and fan-in, where order or timing is the point.
- **State over time.** A cache filling and evicting, a state machine stepping through its
  states, a lock or lease being taken and released, or a race between two actors.
- **Before and after.** The same input travelling the old path and the new path side by side,
  ending in different results.
- **Shape and space.** Geometry, layout, transforms, spatial indexes, or a graph being walked.

It does not fit renames, refactors, config changes, or anything a table already makes clear.

Pick the tool:

- **An SVG scene driven by a GSAP timeline, inline in the page.** This is the default, because
  most PR concepts are 2D: boxes, arrows, tokens moving along a flow, values changing. Draw the
  scene as inline SVG (crisp at any size, text stays selectable, colors come from CSS tokens).
  Load GSAP's UMD build from cdnjs, pinned to an exact version
  (`https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js`, which defines `gsap`),
  before the inline script that uses it. Build one `gsap.timeline({ paused: true })` and give each
  step a label (`tl.addLabel('cleaned')`). The labels become chapter buttons (`tl.play(label)`).
  An `<input type="range">` bound to `tl.progress()` gives a scrub bar, and an `onUpdate`
  callback changes the caption as the timeline passes each label. Animate `transform`,
  `opacity` and `attr` values, and keep the scene's numbers and text in data, not hard-coded in
  the tweens, so a case from the playground can rebuild the timeline.
- **Three.js, inline in the page.** Use it for real 3D, or for many moving objects and camera
  moves that SVG would struggle with. Load the UMD build from cdnjs, pinned to an exact version
  (`https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js`, which defines `THREE`),
  before the inline script that uses it. It needs no build and can react to the page's controls.
  Labels are harder in a WebGL canvas, so put them in HTML overlays or CSS2D-style elements
  positioned over it.
- **Remotion, rendered to a video.** Use it for a narrated sequence: scenes with captions, a
  clear start and end, and timing that matters more than interaction. It needs Node and network
  access to install. Scaffold a small project in the scratchpad (`npx create-video@latest`, or
  add `remotion` and `@remotion/cli` to an empty project), write one composition of about 10 to
  30 seconds, and render it with `npx remotion render <entry> <CompositionId> out.mp4`. Publish
  the MP4 with the page through the Artifact `files` map (15MB limit per binary file) and embed
  it with `<video controls muted playsinline>`. If the Artifact tool lists a Motion type, you
  can use it to make a standalone animated explainer and link to it from the page.

Rules for any animation:

- Animate the real thing. Use the PR's own names, values and cases, and label every moving part.
  A generic spinning shape explains nothing.
- Keep it short, about 5 to 30 seconds per loop or scene, with play, pause and replay controls,
  and a caption that says what is happening at each step.
- Show a meaningful still frame before playback starts, and respect `prefers-reduced-motion`:
  show the still frame and a step button instead of autoplay. With a GSAP timeline, the step
  button can jump from label to label with `tl.seek(label)`.
- Take colors from the page's theme tokens so the animation reads in light and dark. Size the
  canvas to its container and keep it at `max-width: 100%`.
- One animation per page is usually enough. If you can't say what the reader learns from it in
  one sentence, leave it out.

## 5. Check and publish

- Syntax-check the script before publishing:

  ```bash
  sed -n '/<script>/,/<\/script>/p' page.html | sed '1d;$d' > page.js && node --check page.js
  ```

- That extraction takes inline scripts only, because a `<script src=…>` line does not match
  `<script>`. For a Remotion video, play the rendered MP4 once, or extract a frame
  (`npx remotion still`) and look at it, before publishing.
- Previewing a scratchpad `file://` page in the browser pane shows a static snapshot without
  running scripts, so it can't check the interactive parts. Don't spend turns on it.
- Publish with `Artifact` (`icon: "code"`, a one-sentence `description`). Title the page after
  the change, such as `<TICKET-ID> <short change name>`, not "PR explainer".
- For later fixes, use `Edit` on the file and republish the same path in the same message. Avoid
  regex rewrites through scripts: when the pattern misses, half an edit lands and the page breaks.

## 6. Guide the user in chat

Give the link first and say the page is private until shared. Then write a short guide that can
be read without the page:

- What the PR does, in three or four numbered points, plus the single most important fact.
- The review order as a numbered list, one line each.
- The three to five most important things to look at closely, one or two sentences each.
- Say what you could not verify (for example that the page's script was not run in a browser).
