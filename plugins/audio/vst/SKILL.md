---
name: vst
description: >-
  Know the audio plugins installed on this Mac — VST3 instruments and effects
  and Audio Units — which of them actually work, every parameter each one has,
  its presets, and roughly what it sounds like, from a cached catalog, short
  test renders measured into plain words, spectrograms, and the user's own
  notes. Use whenever a task involves choosing, setting up or swapping a
  software synth, sampler or effect: "which synths do I have", "pick a reverb",
  "what's a good bass plugin here", "what parameters does Serum have", "what's
  the cutoff parameter called", "what does this plugin sound like", "use one of
  my plugins", or writing code or a project for a host that loads plugins
  (SuperCollider's VSTPlugin, Echoder's server.plugin, a DAW session, a
  pedalboard script). macOS only.
---

# vst

## Why this exists

An agent picking a plugin is guessing. It does not know what is installed,
which plugins open outside a DAW, what a parameter is called (`CutOff`?
`Filter Cutoff`? `flt_cutoff`?), or what anything sounds like. This skill
answers the first three exactly and the fourth as well as measurement can:

- **`vst scan`** opens every installed plugin in a throwaway process, records
  what it reports, and checks that it makes sound.
- **`vst list` / `vst inspect`** read that catalog: kinds, vendors,
  categories, status, every parameter with its range, every preset file.
- **`vst audition`** renders a fixed test through one plugin and writes a WAV,
  a spectrogram PNG, measurements, and a one-line summary in plain words.
- **`notes.md`** holds the user's own words for each plugin. It outranks
  everything you can measure.

**You cannot hear.** The summary, the numbers and the spectrogram are
stand-ins. Say what you based a choice on ("Serum: bright, sharp attack,
follows the note"), and when the sound matters, give the user the WAV path to
listen to rather than claiming it sounds a particular way.

## Running it

macOS with [`uv`](https://docs.astral.sh/uv/) installed. The launcher fetches
pedalboard and numpy into uv's cache on first use:

```bash
VST="${CLAUDE_PLUGIN_ROOT}/vst/scripts/vst"
"$VST" list --kind instrument --status works
```

Everything lives in `~/Library/Application Support/vst-catalog/` (`"$VST"
where` prints it; `VST_CATALOG_DIR` overrides it): `catalog.json`,
`plugins/<id>.json` with each plugin's parameters, `auditions/`, and
`notes.md`.

## The loop

1. **Make sure the catalog exists and is current.** `"$VST" list`. Empty, or
   missing a plugin the user mentions → `"$VST" scan`. A scan re-probes only
   new or changed bundles, so it is cheap after the first one; the first takes
   10–20 minutes for ~120 plugins (run it in the background). Never re-probe
   everything (`--force`) unasked.
2. **Shortlist from the catalog and the notes.** `"$VST" list --kind effect
   --status works --search reverb` searches name, vendor, category and notes.
   Categories are coarse and often just `Fx` or `Synth`, so also scan the
   names. Read `notes.md` for every candidate; a note settles it.
3. **Read the parameters you need.** `"$VST" inspect "Mini V3" --filter
   "cutoff|emphasis|attack"`. Synths have hundreds or thousands of parameters,
   so always filter. The preset list doubles as a description of what the
   plugin is for: Serum's `Bass/BA Deep Womp` says more than any measurement.
4. **Audition what you are unsure of.** `"$VST" audition serum`, or with
   settings: `"$VST" audition "Mini V3" --set CutOff=0.1 --set Emphasis=0.85`.
   Compare candidates on the same numbers. Look at `spectrogram.png` when the
   shape over time matters.
5. **Use it in the host,** with the names `inspect` printed. How a host loads
   a plugin is the host's business: read its own docs or skill (for
   SuperCollider, the `supercollider-vst` skill). Hosts differ in units: many,
   VSTPlugin among them, take every parameter as 0..1 rather than the units
   `inspect` shows.
6. **Keep what the user tells you.** When the user says what a plugin sounds
   like or is good for, offer to add it to `notes.md` in their words, under
   `## <name as vst list spells it>`.

## Commands

| Command | What it does |
| --- | --- |
| `scan [name] [--force] [--jobs 4] [--timeout 90]` | Probe new or changed plugins (all matching `name`, if given), each in its own process; prints the table after. |
| `list [--kind instrument\|effect] [--status works\|…] [--search words] [--json]` | The catalog. `works` = `ok` or `needs-lead-in`. |
| `inspect <name> [--filter regex] [--limit 80] [--json]` | Formats and paths, status, notes, preset files, parameters. |
| `audition <name> [--preset f.vstpreset] [--set Param=value …] [--json]` | Render and measure; results in `auditions/<id>/<variant>/`. |
| `where` | The data folder and the notes file. |

A name matches by id, then by exact name ignoring case and punctuation, then
by a unique part ("valhallaroom", "mini v3", "pro-q").

## Reading the results

**Status** (from `scan`):

| Status | Meaning |
| --- | --- |
| `ok` | Opens and makes sound. |
| `needs-lead-in` | Silent at first, sounds after `lead_in_s` seconds of real time: it loads samples in the background. Hosts must wait or play something first; `audition` does this itself. |
| `silent` | Opens, never sounds within 24 s. Usually unlicensed or not activated, a sampler with nothing loaded (Kontakt), a drum or sample instrument that only finishes loading inside a real-time host, or hardware companion software with no hardware. Not a choice without the user. |
| `crashed`, `timeout`, `error` | Fails outside a DAW: companion plugins for absent hardware crash, a licence or login dialog times out, and pedalboard refuses some channel layouts (a mono-in, stereo-out plugin). `inspect` shows the error and, when both formats were tried, each one's outcome. Avoid. |
| `shell` | One bundle holding several plugins (Waves' WaveShell); listed, not probed. |

**Parameters**: `name` is the plugin's own name for it, which is what most
hosts (VSTPlugin, DAWs, automation lanes) use. `[key]` is pedalboard's
snake_case spelling, only for pedalboard code. Ranges and the current value
are in the parameter's own units; many plugins report a normalised 0..1
range instead.

**Audition material** is fixed so numbers compare across plugins:

- *Instrument*: C1, C2, C3, C4 for 0.8 s each at velocity 100, then C2 at
  velocity 40. Per note: `level_db`, `centroid_hz` (brightness), `flatness`
  (0 tonal … 1 noise), `pitch_hz` against `expected_hz`, `attack_ms` (to 90%
  of peak), `release_ms` (note-off until 40 dB down; `null` = still ringing at
  the next note), `width` (0 mono … ~1 very wide).
- *Effect*: four plucks and a noise burst, then silence (`audition.wav`, with
  the input as `dry.wav`), and a single impulse (`impulse.wav`). `gain_db`,
  dry and wet brightness and width, `tail_after_input_ms`, `impulse_tail_ms`
  (60 dB decay; `null` = longer than 5 s).
- **Summary words** are coarse bands over those numbers: brightness under
  700 Hz is dark, under 2 kHz mellow, under 4.5 kHz bright; attack under 15 ms
  is sharp, under 80 ms quick, under 300 ms soft. "Follows the note, 2 octaves
  down" means the pitch moves with the keys at a fixed interval (Mini V3's
  default patch has a low oscillator).

**Spectrogram**: time left to right, 30 Hz to 16 kHz bottom to top on a log
scale, 90 dB from black to pale yellow. Dim dotted lines mark 100 Hz, 1 kHz
and 10 kHz; white ticks along the top mark each note or input event. Even
horizontal lines are harmonics (tonal); a smear is noise; how far colour
runs past an event is its tail.

## Limits

- **Default patches only, mostly.** `--preset` loads `.vstpreset` files
  alone. Most vendors save presets in their own format (Serum `.fxp`, u-he
  `.h2p`, Valhalla `.vpreset`), which only the plugin's UI opens, and
  Arturia and Native Instruments keep theirs in a database. `inspect` still
  lists the files it finds, by name. What you audition is the plugin's init
  sound, which for a synth is often a plain saw.
- **pedalboard is not every host.** A plugin that fails here may work in a
  DAW or in VSTPlugin's sandbox, and the reverse. `crashed` means "avoid
  unless the user's host has been seen to load it", not "broken".
- **VST2-only (`.vst`) plugins are not catalogued**: pedalboard cannot load
  them. Most vendors also ship VST3 or AU.
- **Intel-only plugins run under Rosetta.** On Apple Silicon a plugin with no
  arm64 binary is probed and auditioned from an x86_64 Python that uv fetches
  (`arch` in the catalog says which binaries a plugin has). It is slower to
  start, and needs Rosetta installed. A host that cannot bridge architectures
  will not load these plugins at all, whatever the catalog says.
- **Rendering is offline, at 48 kHz, in blocks of 512 samples.** pedalboard's
  default of 8192 makes some instruments (Arturia's) render silence; a host
  that uses big blocks may see the same.
