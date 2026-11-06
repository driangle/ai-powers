// Live: a VST instrument played from sclang, then a VST reverb on a bus.
// Run the whole block. Paths are this Mac's; swap in your own plugins.
(
s = Server.default;
s.options.numOutputBusChannels = 2;
s.waitForBoot {
	var synth, ctl, fx, fxctl, cond = Condition.new;

	// One VSTPlugin per synth; `id` names it so the controller can find it.
	SynthDef(\vsti, { |out = 0, amp = 0.5|
		Out.ar(out, VSTPlugin.ar(nil, 2, id: \vsti) * amp);
	}).add;
	// An effect reads a bus and replaces what is on the output.
	SynthDef(\vstfx, { |in = 16, out = 0|
		ReplaceOut.ar(out, VSTPlugin.ar(In.ar(in, 2), 2, id: \fx));
	}).add;
	SynthDef(\pluck, { |out = 16, freq = 220|
		var sig = Pluck.ar(WhiteNoise.ar(0.3) ! 2, Impulse.kr(0), 0.01, freq.reciprocal, 3);
		Out.ar(out, sig * Line.kr(1, 1, 3, doneAction: 2));
	}).add;
	s.sync;

	synth = Synth(\vsti);
	ctl = VSTPluginController(synth, \vsti);
	// Sandbox mode: a crashing plugin takes its own process down, not scsynth.
	ctl.open("/Library/Audio/Plug-Ins/VST3/Mini V3.vst3", editor: false, mode: \sandbox,
		action: { |c, ok| ("opened: " ++ ok).postln; cond.unhang });
	cond.hang;  // never send notes before the plugin is open

	ctl.midi.noteOn(0, 48, 100); 1.wait; ctl.midi.noteOff(0, 48); 1.wait;
	ctl.set('CutOff', 0.1);  // the plugin's own name, normalised 0..1
	ctl.midi.noteOn(0, 48, 100); 1.wait; ctl.midi.noteOff(0, 48); 1.wait;

	// A pattern plays the plugin through the \vst_midi event type.
	Pbind(\type, \vst_midi, \vst, ctl, \midinote, Pseq([48, 55, 60, 67]),
		\dur, 0.25, \legato, 0.8, \amp, 0.8).play;
	1.5.wait;
	synth.free;  // freeing the synth closes the plugin

	fx = Synth(\vstfx, [\in, 16, \out, 0], addAction: \addToTail);
	fxctl = VSTPluginController(fx, \fx);
	fxctl.open("/Library/Audio/Plug-Ins/VST3/ValhallaVintageVerb.vst3", editor: false, mode: \sandbox,
		action: { |c, ok| ("fx opened: " ++ ok).postln; cond.unhang });
	cond.hang;
	fxctl.set('Mix', 1.0);
	Synth(\pluck, [\out, 16, \freq, 220], addAction: \addToHead);
};
)
