import unittest
from instance import owns_quit, quit_message


class InstanceTests(unittest.TestCase):
    def test_only_same_installation_can_be_closed(self):
        current = r'C:\Apps\Codex-Glass\Codex-Glass.exe'
        self.assertTrue(owns_quit(quit_message(current.lower()), current))
        self.assertTrue(owns_quit(quit_message(current.replace('\\', '/')), current))
        self.assertFalse(owns_quit(quit_message(r'C:\Portable\Codex-Glass.exe'), current))

    def test_invalid_commands_do_not_close(self):
        for message in (b'quit', b'{}', b'[]', b'null', b'{"action":"quit","executable":17}',
                        quit_message('Codex-Glass.exe'), b'{"action":"show","executable":"x"}'):
            self.assertFalse(owns_quit(message, r'C:\Apps\Codex-Glass.exe'))


if __name__ == '__main__':
    unittest.main()
