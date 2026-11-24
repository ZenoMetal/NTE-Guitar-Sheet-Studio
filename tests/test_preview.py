from array import array
import unittest

from nte_studio.model import MidiSong, Note, Part
from nte_studio.preview import PreviewSynth


def fixture():
    return MidiSong([
        Part('lead', 'Lead', 0, 0, [Note(0, 1, 69)]),
        Part('bass', 'Bass', 1, 32, [Note(.2, 1.2, 45)]),
        Part('drums', 'Drums', 9, 0, [Note(0, 1.5, 36)]),
    ], 1.5, [(0, 120)])


class PreviewTests(unittest.TestCase):
    def test_unchecked_parts_are_absent_from_audio(self):
        song = fixture()
        selected = PreviewSynth(song, {'lead'}, sample_rate=8000)
        reference = PreviewSynth(MidiSong(song.parts[:1], 1.5, [(0, 120)]), {'lead'}, sample_rate=8000)
        actual = selected.render(12000)
        self.assertEqual(actual, reference.render(12000))
        self.assertTrue(any(actual))

    def test_no_selection_and_percussion_are_silent(self):
        for keys in (set(), {'drums'}):
            synth = PreviewSynth(fixture(), keys, sample_rate=8000)
            self.assertEqual(synth.render(4000), b'\0' * 8000)

    def test_muting_sustained_note_and_reenabling_mid_note(self):
        synth = PreviewSynth(fixture(), {'lead'}, sample_rate=8000)
        self.assertTrue(any(synth.render(2000)))
        synth.select(set())
        self.assertEqual(synth.render(2000), b'\0' * 4000)
        synth.select({'lead'})
        self.assertTrue(any(synth.render(2000)))
        self.assertEqual(synth.frame, 6000)

    def test_speed_seek_and_end(self):
        synth = PreviewSynth(fixture(), {'bass'}, speed=2, sample_rate=8000)
        self.assertEqual(synth.duration, .75)
        self.assertEqual(synth.render(800), b'\0' * 1600)
        self.assertTrue(any(synth.render(800)))
        synth.seek(.65)
        self.assertEqual(synth.render(800), b'\0' * 1600)
        self.assertEqual(synth.render(800), b'')

    def test_stereo_and_float_formats(self):
        for floating, code in ((False, 'h'), (True, 'f')):
            synth = PreviewSynth(fixture(), {'lead'}, sample_rate=8000)
            samples = array(code)
            samples.frombytes(synth.render(800, channels=2, floating=floating))
            self.assertEqual(len(samples), 1600)
            self.assertEqual(samples[::2], samples[1::2])
            self.assertTrue(any(samples))

    def test_tempo_map_times_preserved(self):
        song = MidiSong([Part('a', 'Lead', 0, 0, [Note(.5, 1.5, 60)])], 2,
                        [(0, 120), (.5, 60)])
        synth = PreviewSynth(song, {'a'}, sample_rate=8000)
        self.assertEqual(synth.render(4000), b'\0' * 8000)
        self.assertTrue(any(synth.render(8000)))
        self.assertEqual(synth.render(4000), b'\0' * 8000)
