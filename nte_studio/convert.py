"""Arrange notes and serialize the user-provided NTE version-6 schema."""
from collections import defaultdict
from dataclasses import asdict, replace
import math
import re
import uuid

from .model import Note, Options, SheetError

BASE = {
    'timeMs': 0, 'order': 0, 'type': 'AudioType',
    'stringId': 'Guitar_String_1', 'chordId': 'None',
    'playMode': 'ChordMode', 'audioType': 'Clean',
    'bPressed': False, 'bFromTouch': False,
    'pageIndex': 0, 'chordIndex': 0, 'pianoScaleType': 'Natural',
    'pianoGamepadLine': 2,
}


def convert(notes, options=None, sheet_id=None, source_duration=None):
    options = options or Options()
    if options.tone not in ('Clean', 'Distortion'):
        raise SheetError('Choose Clean or Distortion tone.')
    if options.range_mode not in ('Octave fold', 'Drop outside range', 'Reject outside range'):
        raise SheetError('Choose a valid pitch-range mode.')
    if not .25 <= options.speed <= 4 or not 1 <= options.max_voices <= 5 or not -48 <= options.transpose <= 48:
        raise SheetError('Speed, voice limit or transposition is outside the supported range.')
    if not 0 <= options.lead_ms <= 10000 or not 0 <= options.tail_ms <= 10000:
        raise SheetError('Lead-in and tail must be between 0 and 10 seconds.')
    notes = list(notes)
    if not notes:
        raise SheetError('Select at least one track containing playable notes.')
    if len(notes) > 200_000:
        raise SheetError('Choose fewer notes (maximum 200,000).')
    for n in notes:
        if not all(math.isfinite(x) for x in (n.start, n.end)) or n.start < 0 or n.end < n.start or type(n.pitch) is not int or not 0 <= n.pitch <= 127:
            raise SheetError('A source note has an invalid pitch or timestamp.')
    first = min(n.start for n in notes) if options.trim_lead else 0
    stats = dict(input_notes=len(notes), folded_notes=0, out_of_range_dropped=0, short_notes_dropped=0,
                 duplicate_notes_merged=0, polyphony_dropped=0, notes_shortened=0)
    groups = defaultdict(dict)
    for n in notes:
        pitch = n.pitch + options.transpose
        if not 52 <= pitch <= 87:
            if options.range_mode == 'Reject outside range':
                raise SheetError(f'Pitch MIDI {pitch} is outside E3–D#6. Change transposition or choose Octave fold.')
            if options.range_mode == 'Drop outside range':
                stats['out_of_range_dropped'] += 1
                continue
            while pitch < 52:
                pitch += 12
            while pitch > 87:
                pitch -= 12
            stats['folded_notes'] += 1
        start = round((n.start - first) * 1000 / options.speed) + options.lead_ms
        end = round((n.end - first) * 1000 / options.speed) + options.lead_ms
        if end - start < 25:
            stats['short_notes_dropped'] += 1
            continue
        item = {'start': start, 'end': end, 'pitch': pitch,
                'rank': (n.priority, pitch, n.velocity)}
        old = groups[start].get(pitch)
        if old:
            stats['duplicate_notes_merged'] += 1
            old['end'] = max(old['end'], end)
            old['rank'] = max(old['rank'], item['rank'])
        else:
            groups[start][pitch] = item
    active, chosen = {}, []
    for start, incoming in sorted(groups.items()):
        active = {p: n for p, n in active.items() if n['end'] > start}
        for pitch in incoming:
            if pitch in active:
                active.pop(pitch)['end'] = start - 6
                stats['notes_shortened'] += 1
        candidates = list(active.values()) + list(incoming.values())
        keep = sorted(candidates, key=lambda n: n['rank'], reverse=True)[:options.max_voices]
        ids = {id(n) for n in keep}
        for n in active.values():
            if id(n) not in ids:
                n['end'] = start - 6
                stats['notes_shortened'] += 1
        for n in incoming.values():
            if id(n) in ids:
                chosen.append(n)
            else:
                stats['polyphony_dropped'] += 1
        active = {n['pitch']: n for n in keep}
    played = []
    for n in chosen:
        if n['end'] - n['start'] < 25:
            stats['short_notes_dropped'] += 1
            continue
        played.append({**n, 'end': n['end'] - min(8, (n['end'] - n['start']) // 10)})
    if not played:
        raise SheetError('No notes remain after range and duration filtering. Adjust the conversion settings.')
    note_id = sheet_id.upper() if sheet_id else uuid.uuid4().hex.upper()
    if not re.fullmatch('[0-9A-F]{32}', note_id):
        raise SheetError('A local sheet ID must contain exactly 32 hexadecimal characters.')
    operations = []
    for kind in ('AudioType', 'Sustain', 'PianoLayout'):
        operations.append({**BASE, 'type': kind, 'audioType': options.tone})
    for n in played:
        for pressed, time in ((True, n['start']), (False, n['end'])):
            operations.append({**BASE, 'timeMs': time, 'type': 'String',
                               'chordId': f"Piano_{n['pitch'] - 51}", 'playMode': 'PianoMode',
                               'audioType': options.tone, 'bPressed': pressed, 'bFromTouch': True})
    operations.sort(key=lambda o: (o['timeMs'], 0 if o['type'] != 'String' else (2 if o['bPressed'] else 1)))
    for i, op in enumerate(operations):
        op['order'] = i
    last_ms = max(o['timeMs'] for o in operations)
    if source_duration is not None:
        if not math.isfinite(source_duration) or source_duration < max(n.end for n in notes):
            raise SheetError('The source duration ends before its last note.')
        # Text sheets can intentionally end with rests. MIDI trailing silence
        # is omitted unless the user explicitly supplies a source duration.
        last_ms = max(last_ms, round((source_duration - first) * 1000 / options.speed) + options.lead_ms)
    doc = {'version': 6, 'noteId': note_id, 'playUIType': 'PianoKey',
           'durationMs': last_ms + max(1, options.tail_ms), 'operations': operations}
    validation = validate(doc)
    report = {'statistics': stats, 'validation': validation, 'options': asdict(options),
              'trimmed_lead_seconds': first, 'in_game_tested': False,
              'code_type': 'Local sheet ID; not a registered online share code'}
    return doc, report


def validate(doc):
    def require(condition, message):
        if not condition:
            raise SheetError('Invalid generated sheet: ' + message)
    require(set(doc) == {'version', 'noteId', 'playUIType', 'durationMs', 'operations'}, 'top-level fields')
    require(type(doc['version']) is int and doc['version'] == 6, 'version')
    require(isinstance(doc['noteId'], str) and re.fullmatch('[0-9A-F]{32}', doc['noteId']), 'ID')
    require(doc['playUIType'] == 'PianoKey', 'keyboard mode')
    require(type(doc['durationMs']) is int and doc['durationMs'] > 0, 'duration')
    require(isinstance(doc['operations'], list) and len(doc['operations']) >= 5, 'operations')
    active, peak, count, last = set(), 0, 0, -1
    for index, op in enumerate(doc['operations']):
        require(isinstance(op, dict) and {k: type(v) for k, v in op.items()} == {k: type(v) for k, v in BASE.items()}, 'operation fields/types')
        require(op['order'] == index and op['timeMs'] >= last, 'event ordering')
        require(op['timeMs'] >= 0 and op['audioType'] in ('Clean', 'Distortion'), 'timestamp/tone')
        require(op['stringId'] == 'Guitar_String_1' and op['pianoScaleType'] == 'Natural', 'guitar layout')
        last = op['timeMs']
        require(op['type'] in ('AudioType', 'Sustain', 'PianoLayout', 'String'), 'operation kind')
        if op['type'] != 'String':
            require(op['playMode'] == 'ChordMode' and op['chordId'] == 'None' and not op['bFromTouch'], 'settings operation')
            continue
        require(op['playMode'] == 'PianoMode' and op['bFromTouch'], 'note operation')
        require(re.fullmatch(r'Piano_([1-9]|[12][0-9]|3[0-6])', op['chordId']), 'pitch range')
        pitch = op['chordId']
        if op['bPressed']:
            require(pitch not in active, 'duplicate note-on')
            active.add(pitch)
            count += 1
        else:
            require(pitch in active, 'unmatched note-off')
            active.remove(pitch)
        peak = max(peak, len(active))
    require(not active and peak <= 5 and count > 0, 'hanging notes or too many voices')
    require(doc['durationMs'] > last, 'end timestamp')
    return {'notes': count, 'peak_polyphony': peak, 'duration_seconds': doc['durationMs'] / 1000,
            'operations': len(doc['operations'])}
