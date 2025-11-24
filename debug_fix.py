"""Quick check to ensure SpellBook accepts the legacy `talents` argument."""

import random
import sys
import types

# Provide a lightweight numpy stub so the package import works in minimal environments.
if 'numpy' not in sys.modules:
    numpy_stub = types.SimpleNamespace()
    numpy_stub.float32 = float
    numpy_stub.zeros = lambda *args, **kwargs: [0] * args[0]
    numpy_stub.random = types.SimpleNamespace(rand=lambda: random.random())
    sys.modules['numpy'] = numpy_stub

from ppmonk.core.spell_book import SpellBook


def main():
    book = SpellBook(talents=['WDP'])
    assert 'WDP' in book.active_talents, "SpellBook should accept `talents` as an alias for `active_talents`"
    print("SpellBook initialized with talents:", book.active_talents)


if __name__ == "__main__":
    main()
