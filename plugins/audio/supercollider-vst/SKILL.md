---
name: supercollider-vst
description: >-
  Write SuperCollider synths and scores that run VST3 and VST2 plugins
  through the VSTPlugin extension — a VST instrument played from
  sclang, patterns or a Score, a VST effect on a bus, parameters set by name
  or swept from a UGen, presets loaded mid-piece — live on scsynth or rendered
  offline with Score.recordNRT. Use whenever SuperCollider code should use a
  software synth or effect plugin: "use Serum in SuperCollider", "put a
  Valhalla reverb on this SynthDef", "VSTPlugin", "VSTPluginController",
  "render a VST in NRT", "play a plugin from a Pbind". macOS; pairs with the
  `vst` skill for choosing a plugin.
---

# supercollider-vst

## Why this exists

VSTPlugin works, but its traps cost an afternoon each: a plugin that takes
scsynth down with it, notes sent before the plugin finished opening, a
parameter name that resolves in one place and throws in another, a value in
the wrong units, a preset that saves stale. This skill is the working pattern,
checked on this Mac live and offline, and `examples/` holds the two files it
was checked with: `live.scd` and `nrt.scd`. Start from those.

## Before writing code

1. **Check VSTPlugin is installed.** It is an extension, not part of
   SuperCollider: `ls "$HOME/Library/Application Support/SuperCollider/Extensions/VSTPlugin"`
   should show `classes/` and `plugins/` (with `VSTPlugin.scx` and `host`). If
   it is missing, tell the user: download the macOS release from
   <https://git.iem.at/pd/vstplugin/-/releases>, unzip the `VSTPlugin` folder
   into that `Extensions` folder, and recompile the class library. A copy
   downloaded in a browser is quarantined; clear it with
   `xattr -r -d com.apple.quarantine <that folder>`.
2. **Choose the plugin.** If the `vst` skill is available, use it: `vst list
   --kind instrument --status works`, `vst inspect <name>`, `vst audition
   <name>`, and the user's `notes.md`. Skip plugins it marks `crashed`,
   `silent` or `error`, and plugins installed only as an Audio Unit (`inspect`
   lists the formats): VSTPlugin hosts VST3 and VST2, never AU. Otherwise ask
   the user which plugin.
3. **Get the exact parameter names and indices from VSTPlugin itself.** Names
   are the plugin's own spelling (Mini V3: `CutOff`, `Emphasis`; Valhalla:
   `Mix`, `Decay`), and VSTPlugin's index order can differ from other hosts'.
   VSTPlugin's own probe lists them, one per line, in index order:

   ```bash
   H="$HOME/Library/Application Support/SuperCollider/Extensions/VSTPlugin/plugins/host"
   "$H" probe "/Library/Audio/Plug-Ins/VST3/Mini V3.vst3" _ /tmp/mini.txt
   awk '/^\[parameters\]/{f=1;next} /^\[/{f=0} f&&!/^n=/{print i++": "$0}' /tmp/mini.txt | grep -i cutoff
   # 23: CutOff,,17,1
   ```

   Live, `ctl.info.parameters.collect(_.name)` gives the same list once the
   plugin is open.

## The pattern

**One `VSTPlugin.ar` per plugin, inside a SynthDef, named with `id:`.**

```supercollider
SynthDef(\vsti, { |out = 0, amp = 0.5|   // instrument: no input
	Out.ar(out, VSTPlugin.ar(nil, 2, id: \vsti) * amp);
}).add;
SynthDef(\vstfx, { |in = 16, out = 0|    // effect: reads a bus
	ReplaceOut.ar(out, VSTPlugin.ar(In.ar(in, 2), 2, id: \fx));
}).add;
```

- `VSTPlugin.ar(input, numOut, bypass, params, id, info, blockSize)`. An
  instrument takes `nil`; an effect takes its input signal. Chain several in
  one SynthDef by feeding one into the next, each with its own `id`.
- Order matters as for any synth: the effect goes after its source
  (`addAction: \addToTail`, or a later group).
- **A VSTPlugin is silent until a controller opens a plugin in it.**

**Open it through a `VSTPluginController`, in sandbox mode, and wait.**

```supercollider
synth = Synth(\vsti);
ctl = VSTPluginController(synth, \vsti);
ctl.open("/Library/Audio/Plug-Ins/VST3/Mini V3.vst3", editor: false, mode: \sandbox,
	action: { |c, ok| ok.if { /* now play */ } });
```

- **Always `mode: \sandbox`.** It runs the plugin in its own process, so a
  crash costs the plugin, not scsynth. Arturia instruments segfaulted a live
  scsynth in the default in-process mode. Intel-only plugins open the same way
  on Apple Silicon: VSTPlugin bridges them itself.
- Pass the full bundle path. A bare name ("Serum") only resolves after
  `VSTPlugin.search`, which scans every plugin and takes minutes the first time.
- Opening takes seconds (about 3 s for Mini V3 sandboxed). Play nothing until
  `action` reports `true`; in a Routine, a `Condition` does it (see
  `examples/live.scd`).
- `editor: true` opens the plugin's own window (`ctl.editor`) for tweaking by
  hand; leave it off in code that runs unattended.
- Freeing the synth closes the plugin.

**Play it with MIDI.**

```supercollider
ctl.midi.noteOn(0, 48, 100); ctl.midi.noteOff(0, 48);   // channel, note, velocity
Pbind(\type, \vst_midi, \vst, ctl, \midinote, Pseq([48, 55, 60]), \dur, 0.25).play;
```

**Parameters are 0..1, whatever the plugin shows.**

- `ctl.set('CutOff', 0.1)`. Values are VSTPlugin's normalised range, not the
  units a UI or the `vst` skill's `inspect` prints (Valhalla's `Mix` reads
  0–100 % there and is `1.0` here for fully wet).
- **`get` right after `set` returns the old value** in sandbox mode; the set
  still lands. Don't use `get` to confirm a set.
- **Sweeping a parameter from inside the SynthDef** goes through `params:`
  pairs, and there it must be the **index**, not the name:
  `VSTPlugin.ar(nil, 2, params: [23, Line.kr(0.05, 0.6, 6)], id: \vsti)`. A
  name there throws `can't resolve parameter 'CutOff' without info`, because
  the SynthDef is built before any plugin is open. `set`/`setMsg` with a name
  is fine: the server resolves it once the plugin is loaded.

**Presets.** Read: `ctl.readProgram(path)` live, `ctl.readProgramMsg(path)` in
a score (`.vstpreset` for VST3, `.fxp` for VST2; `readBank` for `.fxb`). To
make one, open the plugin live with `editor: true`, set it up by hand or with
`set`, then `ctl.writeProgram(path)` there. Keep presets beside the code that
uses them. Don't write presets from a non-realtime render: a sandboxed plugin
there saved its state from before the changes.

## Offline rendering (NRT)

Every controller method has a `*Msg` twin that returns an OSC message for a
`Score`, so the whole piece renders with `Score.recordNRT` and no running
server. The shape, from `examples/nrt.scd`:

```supercollider
var server = Server(\nrt, options: ServerOptions.new.numOutputBusChannels_(2));
def.add;                                    // the language needs the SynthDesc
synth = Synth.basicNew(\vsti, server);
ctl = VSTPluginController(synth, \vsti);
score = Score([
	[0.0, [\d_recv, def.asBytes]],          // ship the SynthDef inside the score
	[0.0, synth.newMsg],
	[0.0, ctl.openMsg("/Library/Audio/Plug-Ins/VST3/Mini V3.vst3", editor: false, mode: \sandbox)],
	[0.5, ctl.midi.noteOnMsg(0, 48, 100)],
	[0.9, ctl.midi.noteOffMsg(0, 48)],
	[2.0, ctl.setMsg('CutOff', 0.1)],
	[3.0, ctl.readProgramMsg("/path/to/dark.vstpreset")],
	[9.0, [\c_set, 0, 0]]                   // a last event sets the length
]);
score.recordNRT(oscPath, wavPath, headerFormat: "WAV", sampleFormat: "int16",
	options: server.options, duration: 9, action: { server.remove; 0.exit });
```

- `.add` the SynthDef in the language *and* `d_recv` it in the score: the
  controller needs the SynthDesc to find each VSTPlugin by `id`, and the
  render server needs the def. `.store`, as VSTPlugin's own help does, also
  works but leaves a file in the synthdefs folder.
- Plugins open at time 0; the render waits for them, so notes can follow
  straight after.
- A pattern renders into the score with `pbind.asScore(dur, start, (vst: ctl))`
  (see VSTPlugin's help, *Non-Realtime Synthesis*).
- Running `sclang file.scd` renders without the IDE; end with `0.exit`.

## Check that it sounds

Code that runs without errors can still be silent: a plugin unlicensed or
still loading, notes sent before the open finished, an effect placed before
its source. Render or record (`s.record` live) and check the file has sound
where notes are, then tell the user where it is so they can listen. Some
instruments (the `vst` skill marks them `needs-lead-in`) ignore their first
notes while samples load; start their notes later or play throwaway ones first.
