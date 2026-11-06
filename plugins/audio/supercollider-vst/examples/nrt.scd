// Offline: render a VST instrument into a VST reverb with Score.recordNRT.
// No running server needed. Writes ~/vst-nrt.wav and exits.
(
var server = Server(\nrt, options: ServerOptions.new.numOutputBusChannels_(2));
var defs, synth, ctl, fx, fxctl, score;
defs = [
	// The instrument writes to bus 16; its filter sweeps, driven by parameter index 23 (CutOff).
	SynthDef(\vsti, { |out = 0, amp = 0.5|
		var cutoff = Line.kr(0.05, 0.6, 6);
		Out.ar(out, VSTPlugin.ar(nil, 2, params: [23, cutoff], id: \vsti) * amp);
	}),
	SynthDef(\vstfx, { |in = 16, out = 0|
		Out.ar(out, VSTPlugin.ar(In.ar(in, 2), 2, id: \fx));
	})
];
defs.do(_.add);  // the language needs each SynthDesc to find the VSTPlugin by id
synth = Synth.basicNew(\vsti, server);
fx = Synth.basicNew(\vstfx, server);
ctl = VSTPluginController(synth, \vsti);
fxctl = VSTPluginController(fx, \fx);

score = Score([
	[0.0] ++ defs.collect { |d| [\d_recv, d.asBytes] },
	[0.0, fx.newMsg(nil, [\in, 16, \out, 0], \addToTail)],
	[0.0, synth.newMsg(nil, [\out, 16], \addToHead)],
	[0.0, ctl.openMsg("/Library/Audio/Plug-Ins/VST3/Mini V3.vst3", editor: false, mode: \sandbox)],
	[0.0, fxctl.openMsg("/Library/Audio/Plug-Ins/VST3/ValhallaVintageVerb.vst3", editor: false, mode: \sandbox)],
	[0.0, fxctl.setMsg('Mix', 0.5)]
]);
// A preset can replace the whole patch mid-score:
// score.add([3.0, ctl.readProgramMsg("~/presets/dark.vstpreset".standardizePath)]);
8.do { |i|
	var t = 0.5 + (i * 0.5), note = [48, 55, 60, 67].wrapAt(i);
	score.add([t, ctl.midi.noteOnMsg(0, note, 100)]);
	score.add([t + 0.4, ctl.midi.noteOffMsg(0, note)]);
};
score.add([9.0, [\c_set, 0, 0]]);  // a last event sets the length
score.sort;
score.recordNRT("~/vst-nrt.osc".standardizePath, "~/vst-nrt.wav".standardizePath,
	headerFormat: "WAV", sampleFormat: "int16", options: server.options, duration: 9,
	action: { "rendered ~/vst-nrt.wav".postln; server.remove; 0.exit });
)
