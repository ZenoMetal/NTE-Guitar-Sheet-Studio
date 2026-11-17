from dataclasses import dataclass, field


class SheetError(ValueError):
    """An input or conversion error that can be shown directly to the user."""


@dataclass(frozen=True)
class Note:
    start: float
    end: float
    pitch: int
    velocity: int = 100
    source: str = ''
    priority: int = 0


@dataclass
class Part:
    key: str
    name: str
    channel: int
    program: int
    notes: list[Note] = field(default_factory=list)

    @property
    def percussion(self):
        return self.channel == 9


@dataclass
class MidiSong:
    parts: list[Part]
    duration: float
    tempos: list[tuple[float, float]]
    warnings: list[str] = field(default_factory=list)


@dataclass
class Options:
    tone: str = 'Clean'
    transpose: int = 0
    speed: float = 1.0
    max_voices: int = 5
    range_mode: str = 'Octave fold'
    trim_lead: bool = True
    lead_ms: int = 800
    tail_ms: int = 1500


def pitch_name(pitch):
    return ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')[pitch % 12] + str(pitch // 12 - 1)
