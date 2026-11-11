"""
Component factory with EXACT Logisim-Evolution v5 port geometry.

Each factory returns (Comp, ports_dict) where ports_dict maps logical
port names to absolute (x,y) coordinates, computed from the component's
loc using the offsets taken directly from Logisim-evolution source.

loc convention: for east-facing components, loc is the primary OUTPUT (east tip).
"""
from __future__ import annotations
from circ_builder import Comp
from typing import Dict, Tuple

Point = Tuple[int, int]


# ---------------- Wiring ----------------
def pin_in(loc, label, bits=1, facing="east"):
    a = {"appearance": "classic", "facing": facing, "label": label}
    if bits != 1:
        a["width"] = str(bits)
    return Comp("0", "Pin", loc, a), {"p": loc}


def pin_out(loc, label, bits=1, facing="west"):
    a = {"appearance": "classic", "facing": facing, "label": label, "output": "true"}
    if bits != 1:
        a["width"] = str(bits)
    return Comp("0", "Pin", loc, a), {"p": loc}


def tunnel(loc, label, bits=1, facing="west"):
    """A tunnel. facing=west means the stub connects on the EAST side (loc)."""
    a = {"facing": facing, "label": label}
    if bits != 1:
        a["width"] = str(bits)
    return Comp("0", "Tunnel", loc, a), {"p": loc}


def constant(loc, value, bits=1, facing="east"):
    a = {"facing": facing, "width": str(bits), "value": value}
    return Comp("0", "Constant", loc, a), {"p": loc}


def splitter(loc, fanout, incoming, bitmap=None, appear="left", facing="east"):
    """Splitter facing east. loc = combined end (west).
    bitmap: dict {input_bit_index -> group_index}. Group outputs on east.
    Ports: 'combined' and 'g0','g1',... at (x+20, y-10*fanout+10*i).
    """
    a = {"fanout": str(fanout), "incoming": str(incoming), "appear": appear,
         "facing": facing}
    if bitmap:
        for bit_idx, grp in bitmap.items():
            a[f"bit{bit_idx}"] = str(grp)
    x, y = loc
    ports = {"combined": loc}
    for i in range(fanout):
        ports[f"g{i}"] = (x + 20, y - 10 * fanout + 10 * i)
    return Comp("0", "Splitter", loc, a), ports


def bit_extender(loc, in_width, out_width, typ="sign"):
    # loc is OUTPUT (east). input at (-40,0) per convention? Bit Extender bounds:
    # input west at loc-(40,0), output east at loc.  (verified: 40 wide)
    a = {"in_width": str(in_width), "out_width": str(out_width), "type": typ}
    x, y = loc
    return Comp("0", "Bit Extender", loc, a), {"out": loc, "in": (x - 40, y)}


# ---------------- Gates ---------------- (loc = output, east)
def _gate_input_offsets(inputs, size, negates):
    """Return list of (dx,dy) input offsets for an east-facing shaped gate.
    Mirrors Logisim AbstractGate.getInputOffset (bonusWidth=0)."""
    axis = size + (0)  # bonusWidth is 0 for our widths/sizes (verified)
    if inputs <= 3:
        if size < 40:
            skipStart, skipDist, skipLowerEven = -5, 10, 10
        elif size < 60 or inputs <= 2:
            skipStart, skipDist, skipLowerEven = -10, 20, 20
        else:
            skipStart, skipDist, skipLowerEven = -15, 30, 30
    elif inputs == 4 and size >= 60:
        skipStart, skipDist, skipLowerEven = -5, 20, 0
    else:
        skipStart, skipDist, skipLowerEven = -5, 10, 10
    offs = []
    for index in range(inputs):
        if inputs & 1:
            dy = skipStart * (inputs - 1) + skipDist * index
        else:
            dy = skipStart * inputs + skipDist * index
            if index >= inputs // 2:
                dy += skipLowerEven
            if inputs == 4 and size >= 60:
                dy -= 10
        dx = axis + (10 if (negates and (index + 1) in negates) else 0)
        offs.append((-dx, dy))
    return offs


def _gate(kind, loc, inputs=2, width=1, size=50, negates=None, facing="east"):
    a = {"facing": facing}
    if width != 1:
        a["width"] = str(width)
    if inputs != 2:
        a["inputs"] = str(inputs)
    if size != 50:
        a["size"] = str(size)
    if negates:
        for i in negates:
            a[f"negate{i}"] = "true"
    x, y = loc
    ports = {"out": loc}
    for i, (dx, dy) in enumerate(_gate_input_offsets(inputs, size, negates)):
        ports[f"in{i}"] = (x + dx, y + dy)
    return Comp("1", kind, loc, a), ports


def and_gate(loc, inputs=2, width=1, size=50, negates=None):
    return _gate("AND Gate", loc, inputs, width, size, negates)


def or_gate(loc, inputs=2, width=1, size=50, negates=None):
    return _gate("OR Gate", loc, inputs, width, size, negates)


def xor_gate(loc, inputs=2, width=1, size=50, negates=None):
    return _gate("XOR Gate", loc, inputs, width, size, negates)


def not_gate(loc, width=1, facing="east"):
    a = {"facing": facing}
    if width != 1:
        a["width"] = str(width)
    x, y = loc
    return Comp("1", "NOT Gate", loc, a), {"out": loc, "in": (x - 30, y)}


# ---------------- Arithmetic (lib 3) ----------------
# All share: bounds (-40,-20,40,40); IN0=(-40,-10) IN1=(-40,10) OUT=(0,0)
#            aux_in=(-20,-20) aux_out=(-20,20)
def _arith(name, loc, width=16):
    a = {"width": str(width)}
    x, y = loc
    ports = {
        "in0": (x - 40, y - 10),
        "in1": (x - 40, y + 10),
        "out": (x, y),
        "aux_in": (x - 20, y - 20),
        "aux_out": (x - 20, y + 20),
    }
    return Comp("3", name, loc, a), ports


def adder(loc, width=16):      # aux_in=Cin, aux_out=Cout
    return _arith("Adder", loc, width)

def subtractor(loc, width=16): # aux_in=Bin(borrow in), aux_out=Bout
    return _arith("Subtractor", loc, width)

def multiplier(loc, width=16): # aux_out = high bits
    return _arith("Multiplier", loc, width)

def divider(loc, width=16):    # aux_in=upper, aux_out=remainder
    return _arith("Divider", loc, width)

def comparator(loc, width=16):
    # GT=(0,-10) EQ=(0,0) LT=(0,10), inputs at (-40,-10)/(-40,10)
    x, y = loc
    a = {"width": str(width)}
    ports = {
        "in0": (x - 40, y - 10),
        "in1": (x - 40, y + 10),
        "gt": (x, y - 10),
        "eq": (x, y),
        "lt": (x, y + 10),
    }
    return Comp("3", "Comparator", loc, a), ports

def shifter(loc, width=16, shift_type="ll"):
    # IN0 data (-40,-10), IN1 shift amount (-40,10), OUT (0,0)
    a = {"shift": shift_type, "width": str(width)}
    x, y = loc
    ports = {"in0": (x - 40, y - 10), "in1": (x - 40, y + 10), "out": (x, y)}
    return Comp("3", "Shifter", loc, a), ports

def negator(loc, width=16):
    a = {"width": str(width)}
    x, y = loc
    return Comp("3", "Negator", loc, a), {"in": (x - 40, y), "out": (x, y)}


# ---------------- Memory (lib 4) ----------------
# Register classic: bounds(-30,-20,30,40) OUT(0,0) IN(-30,0) CK(-20,20) CLR(-10,20) EN(-30,10)
def register(loc, width=16, label=None, trigger="rising"):
    a = {"appearance": "classic", "width": str(width)}
    if label:
        a["label"] = label
    if trigger != "rising":
        a["trigger"] = trigger
    x, y = loc
    ports = {
        "out": (x, y),
        "in": (x - 30, y),
        "ck": (x - 20, y + 20),
        "clr": (x - 10, y + 20),
        "en": (x - 30, y + 10),
    }
    return Comp("4", "Register", loc, a), ports


# Counter classic: bounds(-30,-20,30,40) OUT(0,0) IN(-30,0) CK(-20,20) CLR(-10,20)
# LD(-30,-10) UD(-20,-20) EN(-30,10) CARRY(0,10)
def counter(loc, width=16, label=None, max_val=None):
    a = {"appearance": "classic", "width": str(width)}
    if label:
        a["label"] = label
    if max_val is not None:
        a["max"] = f"0x{max_val:x}"
    x, y = loc
    ports = {
        "out": (x, y),
        "in": (x - 30, y),
        "ck": (x - 20, y + 20),
        "clr": (x - 10, y + 20),
        "ld": (x - 30, y - 10),
        "ud": (x - 20, y - 20),
        "en": (x - 30, y + 10),
        "carry": (x, y + 10),
    }
    return Comp("4", "Counter", loc, a), ports


# RAM: use classic appearance.  We'll fetch exact offsets separately.
def ram(loc, addr_bits=16, data_bits=16, label=None, extra=None):
    a = {"addrWidth": str(addr_bits), "dataWidth": str(data_bits),
         "appearance": "classic"}
    if label:
        a["label"] = label
    if extra:
        a.update(extra)
    return Comp("4", "RAM", loc, a), {"loc": loc}


# ---------------- Plexers (lib 2) ----------------
# Multiplexer facing=east, NOT narrow (w=40,s=20), botLeft (selMult=1):
#   output (0,0); inputs i at (-40, -10*inputs/... )
#   for inputs=2**sel: dx=-40 (fixed), dy0=-(inputs/2)*10, ddy=10
#   sel at (-20, +(dy0+10*inputs)) = (-20, +(inputs/2)*10)
def multiplexer(loc, select_bits, width=16, enable=False):
    inputs = 1 << select_bits
    a = {"select": str(select_bits)}
    if width != 1:
        a["width"] = str(width)
    a["enable"] = "true" if enable else "false"
    x, y = loc
    ports = {"out": (x, y)}
    if inputs == 2:
        # Logisim 2:1 mux (wide): w=30, s=20
        ports["in0"] = (x - 30, y - 10)
        ports["in1"] = (x - 30, y + 10)
        sel = (x - 20, y + 20)
    else:
        w = 40
        dy0 = -(inputs // 2) * 10
        for i in range(inputs):
            ports[f"in{i}"] = (x - w, y + dy0 + 10 * i)
        sel = (x - 20, y + (dy0 + 10 * inputs))
    ports["sel"] = sel
    if enable:
        ports["en"] = (sel[0] + 10, sel[1])
    return Comp("2", "Multiplexer", loc, a), ports


# Demultiplexer: mirror of mux. output(s) east, single input west.
def demultiplexer(loc, select_bits, width=16, enable=False):
    outputs = 1 << select_bits
    a = {"select": str(select_bits)}
    if width != 1:
        a["width"] = str(width)
    a["enable"] = "true" if enable else "false"
    x, y = loc
    dy0 = -(outputs // 2) * 10
    ports = {"in": (x - 40, y)}
    # Demux: the data input is on west at (-40,0)? Actually demux input is single.
    # We'll compute precisely later if used.
    for i in range(outputs):
        ports[f"out{i}"] = (x, y + dy0 + 10 * i)
    sel_y = y + (dy0 + 10 * outputs)
    ports["sel"] = (x - 20, sel_y)
    return Comp("2", "Demultiplexer", loc, a), ports
