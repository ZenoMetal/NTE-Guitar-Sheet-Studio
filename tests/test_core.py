import json
import os
from pathlib import Path
import struct
import tempfile
import unittest

from nte_studio.convert import convert, validate
from nte_studio.midi import parse_midi
from nte_studio.model import Note, Options, SheetError
from nte_studio.storage import detect_destinations, install_sheet, write_new
from nte_studio.text_sheet import PRESETS, load_mapping, parse_text, tempo_for_duration


def vlq(n):
    values = [n & 127]
    while n >> 7:
        n >>= 7
        values.append((n & 127) | 128)
    return bytes(reversed(values))


def smf(*tracks, division=480, fmt=None):
    header = b'MThd' + struct.pack('>IHHH', 6, (0 if len(tracks) == 1 else 1) if fmt is None else fmt, len(tracks), division)
    return header + b''.join(b'MTrk' + struct.pack('>I', len(t)) + t for t in tracks)


def track(events):
    return b''.join(vlq(dt) + data for dt, data in events) + b'\x00\xff\x2f\x00'


def sample_midi():
    conductor = track([(0, b'\xff\x51\x03\x07\xa1\x20')])
    melody = track([(0, b'\xff\x03\x04Lead'), (0, b'\xc0\x00'),
                   (0, b'\x90\x3c\x64'), (480, b'\x80\x3c\x00'),
                   (0, b'\x90\x40\x64'), (480, b'\x80\x40\x00'),
                   (0, b'\x90\x43\x64'), (480, b'\x80\x43\x00')])
    drums = track([(0, b'\x99\x24\x64'), (240, b'\x89\x24\x00')])
    return smf(conductor, melody, drums)


class MidiTests(unittest.TestCase):
    def test_format_one_and_percussion(self):
        song = parse_midi(sample_midi())
        self.assertEqual([p.name for p in song.parts], ['Lead', 'Track 3'])
        self.assertEqual([n.pitch for n in song.parts[0].notes], [60, 64, 67])
        self.assertTrue(song.parts[1].percussion)
        self.assertAlmostEqual(song.duration, 1.5)

    def test_tempo_change_inside_a_note(self):
        song = parse_midi(smf(track([(0, b'\x90\x3c\x64'), (480, b'\xff\x51\x03\x0f\x42\x40'),
                                    (480, b'\x80\x3c\x00')])))
        self.assertAlmostEqual(song.parts[0].notes[0].end, 1.5)
        self.assertEqual(song.tempos, [(0.0, 120.0), (.5, 60.0)])

    def test_running_status_and_velocity_zero_off(self):
        song = parse_midi(smf(track([(0, b'\x90\x3c\x64'), (240, b'\x40\x64'),
                                    (240, b'\x3c\x00'), (240, b'\x40\x00')])))
        self.assertEqual(len(song.parts[0].notes), 2)
        self.assertAlmostEqual(song.parts[0].notes[1].start, .25)

    def test_sustain_and_disable_sustain(self):
        data = smf(track([(0, b'\xb0\x40\x7f'), (0, b'\x90\x3c\x64'),
                          (480, b'\x80\x3c\x00'), (480, b'\xb0\x40\x00')]))
        self.assertEqual(parse_midi(data).parts[0].notes[0].end, 1)
        self.assertEqual(parse_midi(data, sustain=False).parts[0].notes[0].end, .5)

    def test_channel_split_in_type_zero(self):
        song = parse_midi(smf(track([(0, b'\x90\x3c\x64'), (0, b'\x91\x40\x64'),
                                    (480, b'\x80\x3c\x00'), (0, b'\x81\x40\x00')])))
        self.assertEqual([p.channel for p in song.parts], [0, 1])

    def test_pedal_control_on_separate_track(self):
        controls = track([(0, b'\xb0\x40\x7f'), (960, b'\xb0\x40\x00')])
        notes = track([(0, b'\x90\x3c\x64'), (480, b'\x80\x3c\x00')])
        song = parse_midi(smf(controls, notes))
        self.assertEqual(song.parts[0].notes[0].end, 1)

    def test_missing_off_is_repaired_and_reported(self):
        song = parse_midi(smf(track([(0, b'\x90\x3c\x64'), (480, b'\xb0\x01\x20')])))
        self.assertEqual(song.parts[0].notes[0].end, .5)
        self.assertTrue(song.warnings)

    def test_all_notes_off_respects_pedal(self):
        data = smf(track([(0, b'\xb0\x40\x7f'), (0, b'\x90\x3c\x64'),
                          (240, b'\xb0\x7b\x00'), (240, b'\xb0\x40\x00')]))
        self.assertEqual(parse_midi(data).parts[0].notes[0].end, .5)

    def test_bad_files_have_clear_errors(self):
        for data in [b'bad', sample_midi()[:-4], smf(b'\x00\x3c\x64'),
                     smf(track([(0, b'\x90\xff\x64')]))]:
            with self.subTest(data=data[:12]), self.assertRaises(SheetError):
                parse_midi(data)

    def test_unsupported_formats(self):
        for data in [smf(b'', division=0xE728), smf(b'', division=0), smf(b'', fmt=2)]:
            with self.assertRaises(SheetError):
                parse_midi(data)

    def test_invalid_tempo(self):
        with self.assertRaisesRegex(SheetError, 'tempo'):
            parse_midi(smf(track([(0, b'\xff\x51\x03\x00\x00\x00')])))


class TextTests(unittest.TestCase):
    def setUp(self):
        self.mapping = PRESETS['Virtual Piano / Roblox (C2–C7)']

    def test_virtual_piano_pitch_anchors(self):
        self.assertEqual(len(self.mapping), 61)
        for key, pitch in [('1', 36), ('8', 48), ('q', 53), ('t', 60), ('s', 72), ('m', 96), ('T', 61), ('(', 51)]:
            self.assertEqual(self.mapping[key], pitch)

    def test_chords_rolls_and_rests(self):
        notes, duration = parse_text('[tuo] - (ty) {tu}', self.mapping, 120, 2)
        self.assertEqual([n.start for n in notes], [0, 0, 0, .5, .625, .75, .75])
        self.assertEqual(duration, 1)

    def test_nested_fast_roll(self):
        notes, duration = parse_text('([tu]o)', self.mapping)
        self.assertEqual([n.start for n in notes], [0, 0, .125])
        self.assertEqual(duration, .25)

    def test_whitespace_and_comments(self):
        a, _ = parse_text('t y\nu', self.mapping)
        b, _ = parse_text('t // comment\ny u', self.mapping)
        self.assertEqual(a, b)

    def test_escaped_reserved_keyboard_keys(self):
        notes, _ = parse_text(r'\(', self.mapping)
        self.assertEqual(notes[0].pitch, 51)
        notes, _ = parse_text(r'\[ \] \-', PRESETS['NTE keyboard (E3–D#6)'])
        self.assertEqual([n.pitch for n in notes], [74, 75, 86])

    def test_screenshot_style_sample(self):
        notes, _ = parse_text('[vaqg] --- t - [bagw] -- [cage] --- t - {vasgq}', self.mapping)
        self.assertEqual(len(notes), 19)

    def test_trailing_rests(self):
        _, duration = parse_text('t --_', self.mapping)
        self.assertEqual(duration, 1.25)

    def test_target_duration_preserves_steps_and_pitches(self):
        text = '[tuo] - (ty) {tu} --'
        for steps in (1, 2, 4, 8):
            _, original_duration = parse_text(text, self.mapping, 120, steps)
            target = original_duration * 1.37
            bpm = tempo_for_duration(text, self.mapping, target, steps)
            self.assertAlmostEqual(bpm, 120 / 1.37)
            original, _ = parse_text(text, self.mapping, 120, steps)
            fitted, duration = parse_text(text, self.mapping, steps_per_beat=steps, target_duration=target)
            self.assertAlmostEqual(duration, target)
            self.assertEqual([n.pitch for n in original], [n.pitch for n in fitted])
            for a, b in zip(original, fitted):
                self.assertAlmostEqual(b.start, a.start * 1.37)

    def test_target_duration_handles_deep_roll_minimum_gate(self):
        text = '(t(y(u(o(p(s(d(f))))))))'
        for bpm in (20, 85.7, 400):
            _, target = parse_text(text, self.mapping, bpm, 8, .1)
            fitted = tempo_for_duration(text, self.mapping, target, 8, .1)
            _, duration = parse_text(text, self.mapping, fitted, 8, .1, target_duration=target)
            self.assertAlmostEqual(duration, target)

    def test_impossible_target_is_rejected_without_changing_steps(self):
        for target in (0, -1, float('nan'), float('inf'), .001, 10000):
            with self.subTest(target=target), self.assertRaises(SheetError):
                tempo_for_duration('t y u', self.mapping, target, 2)

    def test_clear_errors_for_unknown_or_broken_syntax(self):
        for text in ['[tu', 'tu]', '[]', 't\n?', '\\', '', '[t(]']:
            with self.subTest(text=text), self.assertRaises(SheetError):
                parse_text(text, self.mapping)
        with self.assertRaisesRegex(SheetError, 'Line 2, column 1'):
            parse_text('t\n?', self.mapping)

    def test_mapping_validation(self):
        self.assertEqual(load_mapping('{"q":60}'), {'q': 60})
        for mapping in ['[]', '{}', '{"ab":60}', '{"a":true}', '{"a":128}', 'x']:
            with self.assertRaises(SheetError):
                load_mapping(mapping)

    def test_genshin_and_nte_anchors(self):
        self.assertEqual(PRESETS['Genshin lyre (C3–B5)']['z'], 48)
        self.assertEqual(PRESETS['Genshin lyre (C3–B5)']['q'], 72)
        self.assertEqual(PRESETS['NTE keyboard (E3–D#6)']['a'], 52)
        self.assertEqual(PRESETS['NTE keyboard (E3–D#6)']['='], 87)


class ConversionTests(unittest.TestCase):
    def test_schema_tone_and_note_pairs(self):
        doc, report = convert([Note(2, 3, 60), Note(3, 4, 64)], Options(tone='Distortion'))
        self.assertTrue(all(o['audioType'] == 'Distortion' for o in doc['operations']))
        self.assertEqual(doc['operations'][3]['timeMs'], 800)
        self.assertEqual(report['validation']['notes'], 2)
        self.assertEqual(doc['operations'][3]['chordId'], 'Piano_9')
        self.assertEqual(doc['version'], 6)

    def test_duplicate_and_overlapping_repeated_pitch(self):
        doc, report = convert([Note(0, 2, 60), Note(0, 1, 60), Note(.5, 1, 60)])
        self.assertEqual(report['statistics']['duplicate_notes_merged'], 1)
        self.assertEqual(validate(doc)['notes'], 2)

    def test_folding_preserves_pitch_class(self):
        doc, report = convert([Note(0, 1, 27), Note(0, 1, 96)])
        pitches = [int(o['chordId'][6:]) + 51 for o in doc['operations'] if o['type'] == 'String' and o['bPressed']]
        self.assertEqual(sorted(p % 12 for p in pitches), [0, 3])
        self.assertEqual(report['statistics']['folded_notes'], 2)

    def test_polyphony_prioritizes_lead(self):
        notes = [Note(0, 2, p) for p in range(70, 78)] + [Note(0, 2, 55, priority=100)]
        doc, report = convert(notes, Options(max_voices=3))
        self.assertEqual(report['validation']['peak_polyphony'], 3)
        self.assertIn('Piano_4', [o['chordId'] for o in doc['operations'] if o['type'] == 'String'])

    def test_range_rejection_and_drop(self):
        with self.assertRaisesRegex(SheetError, 'outside'):
            convert([Note(0, 1, 20)], Options(range_mode='Reject outside range'))
        doc, report = convert([Note(0, 1, 20), Note(0, 1, 60)], Options(range_mode='Drop outside range'))
        self.assertEqual(report['validation']['notes'], 1)

    def test_speed_transposition_and_keep_lead(self):
        doc, _ = convert([Note(1, 3, 60)], Options(speed=2, transpose=2, trim_lead=False))
        self.assertEqual(doc['operations'][3]['timeMs'], 1300)
        self.assertEqual(doc['operations'][3]['chordId'], 'Piano_11')

    def test_empty_tiny_or_invalid_input(self):
        for notes in [[], [Note(0, .001, 60)], [Note(float('nan'), 1, 60)], [Note(0, 1, 200)]]:
            with self.assertRaises(SheetError):
                convert(notes)

    def test_validator_catches_hanging_notes(self):
        doc, _ = convert([Note(0, 1, 60)])
        doc['operations'].pop()
        with self.assertRaises(SheetError):
            validate(doc)

    def test_text_trailing_rest_survives_conversion(self):
        ns, duration = parse_text('t ----', PRESETS['Virtual Piano / Roblox (C2–C7)'])
        doc, _ = convert(ns, source_duration=duration)
        self.assertEqual(doc['durationMs'], 3550)


class StorageTests(unittest.TestCase):
    def test_install_backup_and_existing_recording_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dest = root / 'GuitarNotes'
            dest.mkdir()
            existing = dest / 'existing.json'
            existing.write_bytes(b'original')
            doc, report = convert([Note(0, 1, 60)])
            result = install_sheet(doc, report, 'Test / song', dest, root / 'exports')
            self.assertEqual(Path(result['target']).read_bytes(), Path(result['backup']).read_bytes())
            self.assertEqual(existing.read_bytes(), b'original')
            self.assertEqual(json.loads(Path(result['target']).read_text()), doc)

    def test_never_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'sheet.json'
            write_new(target, b'original')
            with self.assertRaises(FileExistsError):
                write_new(target, b'new')
            self.assertEqual(target.read_bytes(), b'original')

    def test_windows_both_installations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['Saved_Global', 'Saved_GlobalSteam']:
                (root / 'HT' / name / 'GuitarNotes').mkdir(parents=True)
            targets = detect_destinations(root, {'LOCALAPPDATA': str(root)}, 'nt')
            self.assertEqual(len(targets), 2)
            self.assertTrue(any('Standalone' in name for name, _ in targets))

    def test_proton_external_library(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = root / 'external/SteamLibrary'
            steam = root / '.local/share/Steam/steamapps'
            steam.mkdir(parents=True)
            (steam / 'libraryfolders.vdf').write_text(f'"path" "{library}"')
            expected = library / 'steamapps/compatdata/4508340/pfx/drive_c/users/steamuser/AppData/Local/HT/Saved_GlobalSteam/GuitarNotes'
            expected.mkdir(parents=True)
            result = detect_destinations(root, {}, 'posix')
            self.assertEqual([path for _, path in result], [expected])

    def test_user_mounted_library_without_vdf_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'diskmounts/drive/SteamLibrary/steamapps/compatdata/4508340/pfx/drive_c/users/steamuser/AppData/Local/HT/Saved_GlobalSteam/GuitarNotes'
            target.mkdir(parents=True)
            result = detect_destinations(root, {}, 'posix')
            self.assertIn(target, [p for _, p in result])

    def test_relative_or_empty_destination_rejected(self):
        doc, report = convert([Note(0, 1, 60)])
        for value in ['', 'relative/folder']:
            with self.assertRaises(SheetError):
                install_sheet(doc, report, 'Test', value)


if __name__ == '__main__':
    unittest.main()
