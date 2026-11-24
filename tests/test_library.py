import json
from pathlib import Path
import tempfile
import unittest
from nte_studio.library import midi_files, read_collection
from nte_studio.convert import convert
from nte_studio.model import Note
from nte_studio.storage import install_sheet
from nte_studio.i18n import CATALOGS, LANGUAGES, translate

class LibraryTests(unittest.TestCase):
    def test_library_only_midi_files_and_stable_sort(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            for name in ('z.MID','alpha.midi','skip.mp3','beta.mid'): (p/name).write_bytes(b'x')
            (p/'folder.mid').mkdir()
            self.assertEqual([f.name for f in midi_files(str(p))],['alpha.midi','beta.mid','z.MID'])
            self.assertEqual(midi_files(''),[])

    def test_titles_recovered_from_old_export_reports_without_editing_game_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); doc,report=convert([Note(0,1,60)])
            result=install_sheet(doc,report,'My original song',root/'GuitarNotes',root/'old-exports')
            before=Path(result['target']).read_bytes()
            entries,warnings=read_collection(root/'GuitarNotes',[root/'old-exports'])
            self.assertFalse(warnings); self.assertEqual(entries[0].title,'My original song')
            self.assertEqual(entries[0].code,doc['noteId']); self.assertEqual(before,Path(result['target']).read_bytes())

    def test_unknown_and_broken_recordings_do_not_hide_other_sheets(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); (p/'guitar_note_A.json').write_text('{"noteId":"A","durationMs":500}')
            (p/'guitar_note_B.json').write_text('bad json')
            entries,warnings=read_collection(p,[])
            self.assertEqual(len(entries),1); self.assertEqual(len(warnings),1); self.assertEqual(entries[0].title,'')

    def test_all_languages_have_complete_key_sets_and_placeholders(self):
        import string
        keys=set(CATALOGS['en'])
        self.assertEqual(set(CATALOGS),set(LANGUAGES))
        def fields(value): return {f for _,f,_,_ in string.Formatter().parse(value) if f}
        for code,catalog in CATALOGS.items():
            self.assertEqual(set(catalog),keys,code)
            for key,value in catalog.items():
                self.assertEqual(fields(value),fields(CATALOGS['en'][key]),(code,key))
        self.assertEqual(translate('de','settings'),'Einstellungen')
