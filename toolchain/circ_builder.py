"""
Helper library for generating Logisim-Evolution .circ XML files.

Everything is placed on a grid (default 10px). Points are (x, y) tuples.
A Circuit accumulates components (comp) and wires, then renders to XML.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from xml.sax.saxutils import escape

Point = Tuple[int, int]


def attr(name: str, val: str) -> str:
    return f'      <a name="{escape(name)}" val="{escape(str(val))}"/>'


@dataclass
class Comp:
    lib: Optional[str]
    name: str
    loc: Point
    attrs: Dict[str, str] = field(default_factory=dict)

    def render(self) -> str:
        libpart = f' lib="{self.lib}"' if self.lib is not None else ""
        head = f'    <comp{libpart} loc="({self.loc[0]},{self.loc[1]})" name="{escape(self.name)}">'
        if not self.attrs:
            return f'    <comp{libpart} loc="({self.loc[0]},{self.loc[1]})" name="{escape(self.name)}"/>'
        lines = [head]
        for k, v in self.attrs.items():
            if k == "contents":
                # memory contents are stored as element text, not a val attribute
                lines.append(f'      <a name="contents">{escape(str(v))}</a>')
            else:
                lines.append(attr(k, v))
        lines.append("    </comp>")
        return "\n".join(lines)


@dataclass
class Wire:
    a: Point
    b: Point

    def render(self) -> str:
        return (f'    <wire from="({self.a[0]},{self.a[1]})" '
                f'to="({self.b[0]},{self.b[1]})"/>')


@dataclass
class Circuit:
    name: str
    comps: List[Comp] = field(default_factory=list)
    wires: List[Wire] = field(default_factory=list)
    appearance: Optional[str] = None
    circ_attrs: Dict[str, str] = field(default_factory=dict)

    def add(self, c: Comp) -> Comp:
        self.comps.append(c)
        return c

    def wire(self, a: Point, b: Point):
        if a == b:
            return
        self.wires.append(Wire(a, b))

    # draw an orthogonal L-shaped connection (horizontal first then vertical)
    def wire_hv(self, a: Point, b: Point):
        corner = (b[0], a[1])
        self.wire(a, corner)
        self.wire(corner, b)

    # vertical first then horizontal
    def wire_vh(self, a: Point, b: Point):
        corner = (a[0], b[1])
        self.wire(a, corner)
        self.wire(corner, b)

    def render(self) -> str:
        lines = [f'  <circuit name="{escape(self.name)}">']
        lines.append(attr("circuit", self.name))
        lines.append('      <a name="simulationFrequency" val="1.0"/>')
        if self.circ_attrs:
            for k, v in self.circ_attrs.items():
                lines.append(attr(k, v))
        if self.appearance:
            lines.append(self.appearance)
        for w in self.wires:
            lines.append(w.render())
        for c in self.comps:
            lines.append(c.render())
        lines.append('  </circuit>')
        return "\n".join(lines)


PROJECT_HEADER = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<project source="3.8.0" version="1.0">
  This file is intended to be loaded by Logisim-evolution (https://github.com/logisim-evolution/).

  <lib desc="#Wiring" name="0">
    <tool name="Pin">
      <a name="appearance" val="classic"/>
    </tool>
  </lib>
  <lib desc="#Gates" name="1"/>
  <lib desc="#Plexers" name="2"/>
  <lib desc="#Arithmetic" name="3"/>
  <lib desc="#Memory" name="4">
    <tool name="ROM">
      <a name="contents">addr/data: 8 8
0
</a>
    </tool>
  </lib>
  <lib desc="#I/O" name="5"/>
  <lib desc="#TTL" name="6"/>
  <lib desc="#TCL" name="7"/>
  <lib desc="#Base" name="8"/>
  <lib desc="#BFH-Praktika" name="9"/>
  <lib desc="#Input/Output-Extra" name="10"/>
  <lib desc="#Soc" name="11"/>
  <main name="main"/>
  <options>
    <a name="gateUndefined" val="ignore"/>
    <a name="simlimit" val="1000"/>
    <a name="simrand" val="0"/>
  </options>
  <mappings>
    <tool lib="8" map="Button2" name="Menu Tool"/>
    <tool lib="8" map="Button3" name="Menu Tool"/>
    <tool lib="8" map="Ctrl Button1" name="Menu Tool"/>
  </mappings>
  <toolbar>
    <tool lib="8" name="Poke Tool"/>
    <tool lib="8" name="Edit Tool"/>
    <tool lib="8" name="Wiring Tool"/>
    <tool lib="8" name="Text Tool"/>
    <sep/>
    <tool lib="0" name="Pin"/>
    <tool lib="0" name="Pin">
      <a name="facing" val="west"/>
      <a name="output" val="true"/>
    </tool>
    <sep/>
    <tool lib="1" name="NOT Gate"/>
    <tool lib="1" name="AND Gate"/>
    <tool lib="1" name="OR Gate"/>
  </toolbar>'''

PROJECT_FOOTER = '</project>'


def render_project(circuits: List[Circuit]) -> str:
    parts = [PROJECT_HEADER]
    for c in circuits:
        parts.append(c.render())
    parts.append(PROJECT_FOOTER)
    return "\n".join(parts) + "\n"
