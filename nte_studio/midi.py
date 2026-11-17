"""Bounded SMF 0/1 reader, tempo maps, channels, sustain and note releases.

No playback engine or third-party MIDI dependency is required.
"""
from bisect import bisect_right
from collections import defaultdict, deque
from pathlib import Path
import struct

from .model import MidiSong, Note, Part, SheetError

MAX_BYTES = 16 * 1024 * 1024
MAX_EVENTS = 600_000


class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def read(self, count):
        if count < 0 or self.pos + count > len(self.data):
            raise SheetError('The MIDI file is truncated or contains an invalid chunk length.')
        value = self.data[self.pos:self.pos + count]
        self.pos += count
        return value

    def byte(self):
        return self.read(1)[0]

    def vlq(self):
        result = 0
        for _ in range(4):
            value = self.byte()
            result = (result << 7) | (value & 127)
            if not value & 128:
                return result
        raise SheetError('The MIDI file contains an invalid variable-length value.')


def read_midi(path, sustain=True):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise SheetError('Choose a MIDI file smaller than 16 MB.')
    return parse_midi(path.read_bytes(), sustain=sustain)


def parse_midi(data, sustain=True):
    if len(data) > MAX_BYTES:
        raise SheetError('Choose a MIDI file smaller than 16 MB.')
    r = Reader(data)
    if r.read(4) != b'MThd':
        raise SheetError('This is not a Standard MIDI File (.mid or .midi). Audio files cannot be converted.')
    header_size = int.from_bytes(r.read(4), 'big')
    header = r.read(header_size)
    if len(header) < 6:
        raise SheetError('The MIDI header is incomplete.')
    fmt, track_count, division = struct.unpack('>HHH', header[:6])
    if fmt not in (0, 1):
        raise SheetError('MIDI type 2 is not supported. Export the song as MIDI type 0 or type 1.')
    if not track_count or (fmt == 0 and track_count != 1) or track_count > 2048:
        raise SheetError('The MIDI header declares an invalid number of tracks.')
    if division & 0x8000:
        raise SheetError('SMPTE-timed MIDI is not supported. Export using beats/ticks timing.')
    if division == 0:
        raise SheetError('The MIDI file declares zero ticks per beat.')
    events, names, count, end_tick = [], {}, 0, 0
    for ti in range(track_count):
        if r.read(4) != b'MTrk':
            raise SheetError(f'MIDI track {ti + 1} has an invalid header.')
        chunk = Reader(r.read(int.from_bytes(r.read(4), 'big')))
        tick, running, order = 0, None, 0
        while chunk.pos < len(chunk.data):
            tick += chunk.vlq()
            first = chunk.byte()
            if first & 128:
                status = first
                if status < 0xf0:
                    running = status
                else:
                    running = None
                first_data = None
            else:
                if running is None:
                    raise SheetError('The MIDI file uses running status before defining a channel status.')
                status, first_data = running, first
            count += 1
            if count > MAX_EVENTS:
                raise SheetError('This MIDI contains too many events. Export fewer tracks or a shorter section.')
            if status == 0xff:
                kind = chunk.byte()
                payload = chunk.read(chunk.vlq())
                if kind == 3:
                    names[ti] = payload.decode('utf-8', errors='replace').strip('\x00')
                elif kind == 0x51:
                    if len(payload) != 3 or int.from_bytes(payload, 'big') == 0:
                        raise SheetError('The MIDI file contains an invalid tempo event.')
                    events.append((tick, ti, order, 'tempo', int.from_bytes(payload, 'big')))
                if kind == 0x2f:
                    break
            elif status in (0xf0, 0xf7):
                chunk.read(chunk.vlq())
            elif 0x80 <= status <= 0xef:
                kind, channel = status >> 4, status & 15
                size = 1 if kind in (0xc, 0xd) else 2
                values = bytes([first_data]) + chunk.read(size - 1) if first_data is not None else chunk.read(size)
                if any(v > 127 for v in values):
                    raise SheetError('The MIDI file contains an invalid channel-data byte.')
                events.append((tick, ti, order, kind, channel, *values))
            else:
                raise SheetError(f'Unsupported MIDI status 0x{status:02X}. Export a Standard MIDI File.')
            order += 1
        end_tick = max(end_tick, tick)
    events.sort(key=lambda e: e[:3])
    # At the same tick, the last tempo event in file order wins.
    tempo_map = {0: 500000}
    for e in events:
        if e[3] == 'tempo':
            tempo_map[e[0]] = e[4]
    segments, seconds = [], 0.0
    for tick, usec in sorted(tempo_map.items()):
        if segments:
            pt, ps, pu = segments[-1]
            seconds = ps + (tick - pt) * pu / division / 1_000_000
        segments.append((tick, seconds, usec))
    ticks = [s[0] for s in segments]

    def sec(tick):
        t, s, u = segments[bisect_right(ticks, tick) - 1]
        return s + (tick - t) * u / division / 1_000_000

    active, held = defaultdict(deque), defaultdict(list)
    pedal, programs, parts = defaultdict(bool), defaultdict(int), {}
    unpaired = dangling = 0

    def finish(item, tick):
        ti, ch, pitch, start, velocity, program = item
        if tick <= start:
            return
        key = (ti, ch)
        if key not in parts:
            label = names.get(ti) or f'Track {ti + 1}'
            parts[key] = Part(f'{ti}:{ch}', label, ch, program)
        part = parts[key]
        part.notes.append(Note(sec(start), sec(tick), pitch, velocity, part.key))

    for e in events:
        if e[3] == 'tempo':
            continue
        tick, ti, _, kind, ch, *values = e
        # MIDI channel controllers are shared across type-1 tracks. A pedal
        # message may live on a separate control track from its notes.
        channel_key = ch
        if kind == 12:
            programs[channel_key] = values[0]
        elif kind == 9 and values[1] > 0:
            active[(ti, ch, values[0])].append((ti, ch, values[0], tick, values[1], programs[channel_key]))
        elif kind == 8 or (kind == 9 and values[1] == 0):
            queue = active[(ti, ch, values[0])]
            if not queue:
                unpaired += 1
                continue
            item = queue.popleft()
            if sustain and pedal[channel_key]:
                held[channel_key].append(item)
            else:
                finish(item, tick)
        elif kind == 11:
            controller, value = values
            if controller == 64:
                pedal[channel_key] = value >= 64
                if not pedal[channel_key]:
                    for item in held.pop(channel_key, []):
                        finish(item, tick)
            elif controller in (120, 123):
                for key in list(active):
                    if key[1] == channel_key:
                        while active[key]:
                            item = active[key].popleft()
                            if controller == 123 and sustain and pedal[channel_key]:
                                held[channel_key].append(item)
                            else:
                                finish(item, tick)
                if controller == 120:
                    for item in held.pop(channel_key, []):
                        finish(item, tick)
            elif controller == 121:
                pedal[channel_key] = False
                for item in held.pop(channel_key, []):
                    finish(item, tick)
    for queue in active.values():
        while queue:
            dangling += 1
            finish(queue.popleft(), end_tick)
    for items in held.values():
        for item in items:
            finish(item, end_tick)
    result = sorted(parts.values(), key=lambda p: tuple(map(int, p.key.split(':'))))
    for part in result:
        part.notes.sort(key=lambda n: (n.start, n.pitch, n.end))
    if not any(p.notes for p in result):
        raise SheetError('This MIDI has no playable notes.')
    warnings = []
    if dangling:
        warnings.append(f'{dangling} notes without note-off events were closed at the end of the MIDI.')
    if unpaired:
        warnings.append(f'{unpaired} unmatched note-off events were ignored.')
    return MidiSong(result, sec(end_tick), [(s, 60_000_000 / u) for _, s, u in segments], warnings)
