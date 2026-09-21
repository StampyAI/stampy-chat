"""Rewrite citations of the preloaded system-prompt documents ([TP], [TB], [LL]) into
markdown links. The UIs only resolve numeric [N] refs from tool results, so these
codes otherwise render as dead text. Works on a token stream: a pending "[" is held
back until its "]" arrives (or it stops looking like a citation)."""
import re

CORE_DOCS = {
    "TP": ("The Problem (MIRI)", "https://intelligence.org/the-problem/"),
    "TB": ("The Briefing (MIRI)", "https://intelligence.org/briefing/"),
    "LL": ("AGI Ruin: A List of Lethalities (Yudkowsky)",
           "https://www.lesswrong.com/posts/uMQ3cqWDPHhjtiesc/agi-ruin-a-list-of-lethalities"),
}
_GROUP = re.compile(r"\[([^\[\]\n]{1,40})\](?!\()")
_HOLD = 45  # longest bracket group worth waiting for


def _fix_group(m):
    items = [x.strip() for x in m.group(1).split(",")]
    if not any(i in CORE_DOCS for i in items): return m.group(0)
    return " ".join(f"[{i}]({CORE_DOCS[i][1]})" if i in CORE_DOCS else f"[{i}]" for i in items)


def rewrite(text: str) -> str:
    return _GROUP.sub(_fix_group, text)


class Rewriter:
    def __init__(self): self.buf = ""

    def feed(self, chunk: str) -> str:
        self.buf += chunk
        i = self.buf.rfind("[")
        pending = self.buf[i:] if i >= 0 else ""
        if i < 0 or "]" in pending or "\n" in pending or len(pending) > _HOLD:
            out, self.buf = rewrite(self.buf), ""
        else:
            out, self.buf = rewrite(self.buf[:i]), pending
        return out

    def flush(self) -> str:
        out, self.buf = rewrite(self.buf), ""
        return out
