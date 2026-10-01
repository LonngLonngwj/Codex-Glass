"""Brand migration does not reset preferences or enable previously-off startup."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import settings


class Key:
    def __enter__(self): return self
    def __exit__(self, *args): pass


class BrandTests(unittest.TestCase):
    def registry(self, values):
        def query(key, name):
            if name not in values: raise FileNotFoundError(name)
            return values[name], 1
        return SimpleNamespace(HKEY_CURRENT_USER=0, REG_SZ=1,
            OpenKey=lambda *a:Key(), CreateKey=lambda *a:Key(), QueryValueEx=query,
            SetValueEx=lambda key,name,reserved,kind,value:values.update({name:value}),
            DeleteValue=lambda key,name:values.pop(name))

    def test_enabled_legacy_migrates_once_and_preserves_preferences(self):
        legacy = '"C:\\old\\QuotaGlassQt.exe" --watch'
        values = {'QuotaGlass':legacy}
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with patch.multiple(settings,FOLDER=folder,FILE=folder/'settings-v2.json'), \
                 patch.dict('sys.modules',winreg=self.registry(values)), \
                 patch.object(settings.sys,'frozen',True,create=True), \
                 patch.object(settings.sys,'executable',r'C:\new\Codex-Glass.exe'):
                settings.save({'card_size':220,'target':'codex','position':[120,240]})
                before = settings.FILE.read_bytes()
                self.assertTrue(settings.migrate_startup())
                self.assertNotIn('QuotaGlass',values)
                self.assertEqual(values['Codex-Glass'], '"C:\\new\\Codex-Glass.exe" --watch')
                self.assertTrue(settings.startup_enabled())
                self.assertFalse(settings.migrate_startup())
                self.assertEqual(settings.FILE.read_bytes(),before)
                backup = json.loads((folder/'startup-before-rename.json').read_text(encoding='utf-8'))
                self.assertEqual(backup['QuotaGlass'],legacy)
                settings.set_startup(False)
                self.assertNotIn('Codex-Glass', values)

    def test_missing_or_unrelated_startup_stays_unchanged(self):
        for values in ({}, {'QuotaGlass':'"C:\\other\\SomethingElse.exe" --watch'}):
            before = values.copy()
            with patch.dict('sys.modules',winreg=self.registry(values)), \
                 patch.object(settings.sys,'frozen',True,create=True):
                self.assertFalse(settings.migrate_startup())
                self.assertEqual(values,before)

    def test_source_run_does_not_replace_packaged_startup(self):
        values={'QuotaGlass':'"C:\\old\\QuotaGlassQt.exe" --watch'}
        with patch.dict('sys.modules',winreg=self.registry(values)), \
             patch.object(settings.sys,'frozen',False,create=True):
            self.assertFalse(settings.migrate_startup())
            self.assertIn('QuotaGlass',values)


if __name__ == '__main__':
    unittest.main()
