#!/usr/bin/env python3
"""Every text file the repository tracks is free of characters a reader cannot see: format characters (zero-width spaces
and joiners, bidirectional controls, byte-order marks), control characters other than tab and newline (a carriage return
among them), spaces other than the plain one, line and paragraph separators, private-use characters, variation
selectors, and the letters and marks Unicode lets a reader ignore (Hangul fillers among them). Code writes such a
character as an escape (`\\u200B`). A tracked file that is not UTF-8 must be a PNG. Skipped outside a git checkout.

    python3 -m unittest discover -s scripts -p 'test_*.py'
"""
import pathlib
import subprocess
import unicodedata
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
BINARY = {".png"}
# Letters and marks Unicode lets a reader ignore: the grapheme joiner, Khmer's inherent vowels, Mongolian's
# variation selectors and the Hangul fillers.
IGNORABLE = {0x034F, 0x115F, 0x1160, 0x17B4, 0x17B5, 0x180B, 0x180C, 0x180D, 0x180F, 0x3164, 0xFFA0}


def tracked():
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return [ROOT / name for name in out.decode().split("\0") if name]


def invisible(ch):
    o = ord(ch)
    if ch in "\t\n":
        return False
    category = unicodedata.category(ch)
    return (category in ("Cf", "Cc", "Co", "Zl", "Zp") or (category == "Zs" and ch != " ")
            or 0xFE00 <= o <= 0xFE0F or 0xE0100 <= o <= 0xE01EF or o in IGNORABLE)


def found(text):
    for number, line in enumerate(text.split("\n"), 1):
        for ch in line:
            if invisible(ch):
                yield number, f"U+{ord(ch):04X} {unicodedata.name(ch, 'unnamed')}"


class InvisibleCharacters(unittest.TestCase):
    def test_finds_them(self):
        self.assertEqual(list(found("a\u200bb\n\tc d\n")), [(1, "U+200B ZERO WIDTH SPACE")])
        self.assertEqual([n for n, _ in found("x\u2699\ufe0e\n\u00a0\n\u202e\n\r\n\u2028\n")], [1, 2, 3, 4, 5])
        self.assertEqual([n for n, _ in found("a\u180bb\u3164\u034f\n")], [1, 1, 1])
        self.assertEqual(list(found("\u00b7 \u2026 \u2192 \u00d7 \u2713\n")), [])

    def test_tracked_text_has_none(self):
        files = tracked()
        if files is None:
            self.skipTest("not a git checkout")
        hits = []
        for path in files:
            if path.is_symlink() or not path.is_file():
                continue  # a link, a submodule, or a file deleted and not yet staged
            try:
                text = path.read_bytes().decode("utf-8")  # read_text would turn a carriage return into a newline
            except UnicodeDecodeError:
                if path.suffix not in BINARY:
                    hits.append(f"{path.relative_to(ROOT)}: not UTF-8")
                continue
            hits += [f"{path.relative_to(ROOT)}:{number}: {name}" for number, name in found(text)]
        self.assertEqual(hits, [], "write each as an escape in code (\\u200B), or drop it from text")


if __name__ == "__main__":
    unittest.main()
