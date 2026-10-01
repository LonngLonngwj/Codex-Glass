"""Installation-scoped shutdown; a portable copy must not be closed by uninstall."""
import json
import ntpath


def quit_message(executable):
    return json.dumps({"action": "quit", "executable": executable}).encode("utf-8") + b"\n"


def owns_quit(message, executable):
    try:
        data = json.loads(message)
        requested = data.get("executable")
        return (data.get("action") == "quit" and isinstance(requested, str)
                and ntpath.isabs(requested)
                and ntpath.normcase(ntpath.normpath(requested)) ==
                ntpath.normcase(ntpath.normpath(executable)))
    except (ValueError, TypeError, AttributeError):
        return False
