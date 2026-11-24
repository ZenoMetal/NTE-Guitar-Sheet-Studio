"""Explicit, configurable keyboard-sheet syntax with nested chords and rolls."""
import json
import math
from dataclasses import dataclass

from .model import Note, SheetError


def white_pitches(start, count):
    result, pitch = [], start
    while len(result) < count:
        if pitch % 12 in (0, 2, 4, 5, 7, 9, 11):
            result.append(pitch)
        pitch += 1
    return result


def virtual_piano():
    keys = '1234567890qwertyuiopasdfghjklzxcvbnm'
    result = dict(zip(keys, white_pitches(36, len(keys))))
    shifted = dict(zip('1234567890', '!@#$%^&*()'))
    for key, pitch in list(result.items()):
        if pitch % 12 not in (4, 11) and pitch < 96:
            result[shifted.get(key, key.upper())] = pitch + 1
    return result


def genshin():
    result = {}
    for keys, start in [('zxcvbnm', 48), ('asdfghj', 60), ('qwertyu', 72)]:
        for key, pitch in zip(keys, white_pitches(start, 7)):
            result[key] = result[key.upper()] = pitch
    return result


def nte():
    result = {}
    for keys, start in [("asdfghjkl;'~", 52), ('qwertyuiop[]', 64), ('1234567890-=', 76)]:
        for i, key in enumerate(keys):
            result[key] = start + i
            if key.isalpha():
                result[key.upper()] = start + i
    return result


PRESETS = {
    'Virtual Piano / Roblox (C2–C7)': virtual_piano(),
    'Genshin lyre (C3–B5)': genshin(),
    'NTE keyboard (E3–D#6)': nte(),
}


def load_mapping(text):
    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SheetError(f'Invalid custom mapping JSON: line {exc.lineno}, column {exc.colno}.') from exc
    if not isinstance(result, dict) or not result:
        raise SheetError('The key mapping must be a non-empty JSON object, such as {"q": 60}.')
    for key, pitch in result.items():
        if not isinstance(key, str) or len(key) != 1 or key.isspace():
            raise SheetError('Each custom key must be exactly one non-whitespace character.')
        if type(pitch) is not int or not 0 <= pitch <= 127:
            raise SheetError(f'The MIDI pitch for {key!r} must be an integer from 0 to 127.')
    return result


@dataclass
class Node:
    kind: str
    value: object


class Parser:
    def __init__(self, text, mapping):
        if len(text) > 200_000:
            raise SheetError('Text sheets are limited to 200,000 characters.')
        self.text = text.replace('\r\n', '\n').replace('–', '-').replace('—', '-').replace('−', '-')
        self.mapping, self.pos = mapping, 0

    def error(self, message):
        line = self.text.count('\n', 0, self.pos) + 1
        last = self.text.rfind('\n', 0, self.pos)
        raise SheetError(f'Line {line}, column {self.pos - last}: {message}')

    def sequence(self, closing=None, depth=0):
        if depth > 16:
            self.error('Too many nested groups (maximum 16).')
        result = []
        pairs = {'[': ']', '{': '}', '(': ')'}
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch.isspace():
                self.pos += 1
                continue
            if self.text.startswith('//', self.pos):
                end = self.text.find('\n', self.pos)
                self.pos = len(self.text) if end < 0 else end
                continue
            if ch == closing:
                self.pos += 1
                if not result:
                    self.error('Empty groups are not playable.')
                return result
            if ch in ']})':
                self.error(f'Unexpected {ch!r}. Escape a literal keyboard key with a backslash.')
            if ch in pairs:
                self.pos += 1
                children = self.sequence(pairs[ch], depth + 1)
                result.append(Node('roll' if ch == '(' else 'chord', children))
            elif ch in '-_|':
                result.append(Node('rest', 2 if ch == '_' else 1))
                self.pos += 1
            else:
                if ch == '\\':
                    self.pos += 1
                    if self.pos >= len(self.text):
                        self.error('A backslash must be followed by a literal keyboard key.')
                    ch = self.text[self.pos]
                if ch not in self.mapping:
                    self.error(f'Unknown key {ch!r} for this layout. Choose another layout or edit the key mapping.')
                result.append(Node('note', self.mapping[ch]))
                self.pos += 1
        if closing:
            self.error(f'Missing closing {closing!r}.')
        return result


def validate_timing(bpm, steps_per_beat, gate):
    if not 20 <= bpm <= 400:
        raise SheetError('Tempo must be between 20 and 400 BPM.')
    if steps_per_beat not in (1, 2, 4, 8):
        raise SheetError('Choose 1, 2, 4 or 8 steps per beat.')
    if not .1 <= gate <= 1:
        raise SheetError('Note length must be between 10% and 100%.')


def compile_steps(text, mapping):
    """Compile notation once in step units, independent of the chosen tempo."""
    nodes = Parser(text, mapping).sequence()
    events = []

    def emit(node, start, unit):
        if node.kind == 'note':
            events.append((start, unit, node.value))
            return unit
        if node.kind == 'rest':
            return unit * node.value
        if node.kind == 'chord':
            return max(emit(child, start, unit) for child in node.value)
        duration = 0
        for child in node.value:
            duration += emit(child, start + duration, unit / 2)
        return duration

    cursor = 0
    for node in nodes:
        cursor += emit(node, cursor, 1)
    if not events:
        raise SheetError('Paste at least one playable note or chord.')
    return events, cursor


def fitted_tempo(events, cursor, seconds, steps_per_beat, gate):
    if not math.isfinite(seconds) or seconds <= 0:
        raise SheetError('Target length must be greater than zero.')
    # Duration is the maximum of two linear functions of the step length:
    # the timeline/gated ends, and the final onset plus the 25 ms minimum gate.
    linear_end = max(cursor, max(start + unit * gate for start, unit, _ in events))
    last_onset = max(start for start, _, _ in events)
    def duration(bpm):
        step = 60 / bpm / steps_per_beat
        return max(linear_end * step, last_onset * step + .025)
    shortest, longest = duration(400), duration(20)
    if seconds < shortest - 1e-9 or seconds > longest + 1e-9:
        raise SheetError(f'Target length must be between {shortest:.3f} and {longest:.3f} seconds '
                         'for this sheet at the current steps per beat (20–400 BPM).')
    step = seconds / linear_end
    if last_onset:
        step = min(step, (seconds - .025) / last_onset)
    return max(20.0, min(400.0, 60 / step / steps_per_beat))


def tempo_for_duration(text, mapping, seconds, steps_per_beat=2, gate=.85):
    validate_timing(120, steps_per_beat, gate)
    events, cursor = compile_steps(text, mapping)
    return fitted_tempo(events, cursor, seconds, steps_per_beat, gate)


def parse_text(text, mapping, bpm=120, steps_per_beat=2, gate=.85, target_duration=None):
    validate_timing(bpm, steps_per_beat, gate)
    events, cursor = compile_steps(text, mapping)
    if target_duration is not None:
        bpm = fitted_tempo(events, cursor, target_duration, steps_per_beat, gate)
    step = 60 / bpm / steps_per_beat
    notes = [Note(start * step, start * step + max(.025, unit * step * gate), pitch, source='text')
             for start, unit, pitch in events]
    cursor *= step
    return notes, max(cursor, max(n.end for n in notes))
