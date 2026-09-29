"""Helpers shared by assemble.sh's Python blocks.

One definition of re-rooting, so the kit manifest, skill bodies and the family
kit's server line cannot drift apart (the family builder once carried a retyped
copy — essayeur, 29 Sep 2026, bds-jasuha).
"""
import re

ROOT = "${CLAUDE_PLUGIN_ROOT}"


def reroot(s, comp):
    """Point every braced ${CLAUDE_PLUGIN_ROOT} not already under <comp> at <comp>."""
    return re.sub(r"\$\{CLAUDE_PLUGIN_ROOT\}(?!/" + re.escape(comp) + r"(?![\w-]))",
                  ROOT + "/" + comp, s)


def reroot_tree(v, comp):
    """reroot() through every string of a JSON-shaped value."""
    if isinstance(v, str):
        return reroot(v, comp)
    if isinstance(v, list):
        return [reroot_tree(x, comp) for x in v]
    if isinstance(v, dict):
        return {k: reroot_tree(x, comp) for k, x in v.items()}
    return v
