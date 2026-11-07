"""Colour a file's first lines for Qt's StyledText: python3 highlight.py <path> <lines>"""
from fnmatch import fnmatchcase
import os
import re
import sys

from pygments import format
from pygments.formatters import HtmlFormatter
from pygments.lexers import find_lexer_class, get_lexer_for_filename
from pygments.lexers._mapping import LEXERS
from pygments.lexers.special import TextLexer

# Lines split as Qt splits them, at \n alone; Pygments reads a lone \r as a line end itself.
path, lines = sys.argv[1], int(sys.argv[2])
src = open(path, errors="replace", newline="").read()


# Pygments' own choice by file name, without compiling all of its ~900 name patterns: a plain
# *.ext is a suffix test. An exact name beats a pattern, then the higher priority.
def lexer_for(name):
    found = [(cls.priority + ("*" not in glob) * 0.5, cls.__name__, cls)
             for _, lexer, _, globs, _ in LEXERS.values() for glob in globs
             if (name.endswith(glob[1:]) if glob.startswith("*.") and not any(c in glob[2:] for c in "*?[")
                 else fnmatchcase(name, glob))
             for cls in [find_lexer_class(lexer)]]
    return max(found)[2](stripnl=False) if found else TextLexer(stripnl=False)


def first_tokens(lexer):
    # Keep lookahead past the cut for comments and heredocs; stop consuming tokens at the cut.
    # Match Pygments' CR/BOM normalization without treating lone CRs as Qt line boundaries.
    # The cut keeps the break after its last line, for the strip below to take rather than a blank
    # line, and a line more when that strip takes a blank first one.
    body = src.removeprefix("\ufeff")
    n = lines + body.startswith(("\n", "\r\n"))
    parts = body.split("\n", n)
    prefix = "\n".join(parts[:n]) + "\n" * (len(parts) > n)
    left = len(prefix.replace("\r\n", "\n").replace("\r", "\n"))
    for token, text in lexer.get_tokens(src):
        yield token, text[:left]
        left -= len(text)
        if left <= 0:
            break


try:
    lexer = lexer_for(os.path.basename(path))
except Exception:
    # pygments' table changed shape: its own, slower lookup. Failing that, the preview stays plain.
    lexer = get_lexer_for_filename(path, stripnl=False)
html = format(first_tokens(lexer), HtmlFormatter(nowrap=True, noclasses=True, style="one-dark"))

# The same rules as FilesIndex.styledCode(), which shows the file until this answers.
if html.startswith("\n"):
    html = html[1:]
if html.endswith("\n"):
    html = html[:-1]
space = re.compile("[\t\x0b\x0c \xa0\u1680\u2000-\u200a\u202f\u205f\u3000]")
closers = []


def styled(piece):
    if piece == "</span>":
        return closers.pop()
    if piece.startswith("<span"):
        color = re.search(r"color: (#\w+)", piece)
        opened, closer = ('<font color="%s">' % color.group(1), "</font>") if color else ("", "")
        for word, tag in (("bold", "b"), ("italic", "i")):
            if word in piece:
                opened, closer = opened + "<%s>" % tag, "</%s>" % tag + closer
        closers.append(closer)
        return opened
    piece = re.sub("[\n\u2028\u2029]", "<br>", piece)
    # Qt reads &#133; as an ellipsis; another glyphless control keeps NEL's box.
    piece = piece.replace("\x85", "\x80")
    return space.sub(lambda m: "&#%d;" % ord(m.group()), piece)


sys.stdout.write("".join(map(styled, re.split("(<[^>]*>)", html))))
