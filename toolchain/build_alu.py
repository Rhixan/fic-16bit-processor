"""
ALU subcircuit (16-bit) for the FIC processor - clean, well-spaced layout.

Pins:  in: A[16], B[16], OP[4]   out: R[16], Z, N, Cf, V
OP: 0 ADD 1 SUB 2 AND 3 OR 4 XOR 5 NOT 6 LSL 7 LSR 8 RSL 9 RSR
    A MUL B DIV C MOD D INC E DEC F MOV
"""
from circ_builder import Circuit, Comp, render_project
import components as C

W = 16


def build_alu(skip_overflow=False, skip_mux=False) -> Circuit:
    circ = Circuit("ALU")

    def add(c):
        circ.comps.append(c); return c

    def wire(a, b):
        circ.wire(a, b)

    def tun(loc, label, bits=1, facing="west"):
        a = {"facing": facing, "label": label}
        if bits != 1:
            a["width"] = str(bits)
        add(Comp("0", "Tunnel", loc, a))

    def const(loc, val, bits=1, facing="east"):
        add(Comp("0", "Constant", loc,
                 {"facing": facing, "width": str(bits), "value": val}))

    def feed(dst, label, bits=W):
        # tunnel 20px west then wire to dst (longer stub avoids pin overlap)
        tun((dst[0] - 20, dst[1]), label, bits, facing="east")
        wire((dst[0] - 20, dst[1]), dst)

    def feed_const(dst, val, bits=W):
        const((dst[0] - 20, dst[1]), val, bits, facing="east")
        wire((dst[0] - 20, dst[1]), dst)

    def emit(src, label, bits=W):
        tun(src, label, bits, facing="west")

    def cin0(p):  # tie an arithmetic unit's aux_in (carry/borrow in) to 0
        const((p["aux_in"][0], p["aux_in"][1] - 20), "0x0", 1, "south")
        wire((p["aux_in"][0], p["aux_in"][1] - 20), p["aux_in"])

    # ---- inputs ----
    add(Comp("0", "Pin", (100, 100), {"appearance": "classic", "label": "A", "width": str(W)}))
    add(Comp("0", "Pin", (100, 140), {"appearance": "classic", "label": "B", "width": str(W)}))
    add(Comp("0", "Pin", (100, 180), {"appearance": "classic", "label": "OP", "width": "4"}))
    tun((160, 100), "A", W); wire((100, 100), (160, 100))
    tun((160, 140), "B", W); wire((100, 140), (160, 140))
    tun((160, 180), "OP", 4); wire((100, 180), (160, 180))

    RX = 450       # unit output loc x
    STEP = 120     # vertical spacing between units (generous)
    y0 = 100

    units = []  # (net, kind) in OP order

    def arith_AB(y, maker, net, aux_out_net=None):
        cc, p = maker((RX, y), W); add(cc)
        feed(p["in0"], "A"); feed(p["in1"], "B"); cin0(p)
        emit(p["out"], net)
        if aux_out_net:
            emit((p["aux_out"][0], p["aux_out"][1] + 10), aux_out_net, 1)
            wire(p["aux_out"], (p["aux_out"][0], p["aux_out"][1] + 10))

    # 0 ADD
    arith_AB(y0 + 0 * STEP, C.adder, "R_ADD", "C_ADD")
    # 1 SUB
    arith_AB(y0 + 1 * STEP, C.subtractor, "R_SUB", "B_SUB")

    # 2 AND / 3 OR / 4 XOR
    for idx, (fn, net) in enumerate([(C.and_gate, "R_AND"),
                                     (C.or_gate, "R_OR"),
                                     (C.xor_gate, "R_XOR")]):
        y = y0 + (2 + idx) * STEP
        cc, p = fn((RX, y), inputs=2, width=W, size=50); add(cc)
        feed(p["in0"], "A"); feed(p["in1"], "B"); emit(p["out"], net)

    # 5 NOT
    y = y0 + 5 * STEP
    cc, p = C.not_gate((RX, y), width=W); add(cc)
    feed(p["in"], "A"); emit(p["out"], "R_NOT")

    # Shift amount = low 4 bits of B (shifter shift-input is 4-bit for 16-bit data)
    # Produce net "SHAMT" (4-bit) once via a Bit Extender truncating B 16->4.
    bex = Comp("0", "Bit Extender", (300, y0 + 6 * STEP - 60),
               {"in_width": str(W), "out_width": "4", "type": "zero"})
    add(bex)
    # input at loc-40
    tun((300 - 40 - 20, y0 + 6 * STEP - 60), "B", W, facing="east")
    wire((300 - 40 - 20, y0 + 6 * STEP - 60), (300 - 40, y0 + 6 * STEP - 60))
    tun((300, y0 + 6 * STEP - 60), "SHAMT", 4, facing="west")  # output

    # 6 LSL 7 LSR 8 RSL 9 RSR
    for idx, (st, net) in enumerate([("ll", "R_LSL"), ("lr", "R_LSR"),
                                     ("rl", "R_RSL"), ("rr", "R_RSR")]):
        y = y0 + (6 + idx) * STEP
        cc, p = C.shifter((RX, y), W, st); add(cc)
        feed(p["in0"], "A"); feed(p["in1"], "SHAMT", 4); emit(p["out"], net)

    # A MUL
    y = y0 + 10 * STEP
    cc, p = C.multiplier((RX, y), W); add(cc)
    feed(p["in0"], "A"); feed(p["in1"], "B")
    const((p["aux_in"][0], p["aux_in"][1] - 20), "0x0", W, "south")
    wire((p["aux_in"][0], p["aux_in"][1] - 20), p["aux_in"])
    emit(p["out"], "R_MUL")

    # B DIV  C MOD
    y = y0 + 11 * STEP
    cc, p = C.divider((RX, y), W); add(cc)
    feed(p["in0"], "A"); feed(p["in1"], "B")
    const((p["aux_in"][0], p["aux_in"][1] - 20), "0x0", W, "south")
    wire((p["aux_in"][0], p["aux_in"][1] - 20), p["aux_in"])
    emit(p["out"], "R_DIV")
    emit((p["aux_out"][0], p["aux_out"][1] + 10), "R_MOD", W)
    wire(p["aux_out"], (p["aux_out"][0], p["aux_out"][1] + 10))

    # D INC = A+1
    y = y0 + 12 * STEP
    cc, p = C.adder((RX, y), W); add(cc)
    feed(p["in0"], "A"); feed_const(p["in1"], "0x1"); cin0(p)
    emit(p["out"], "R_INC")

    # E DEC = A-1
    y = y0 + 13 * STEP
    cc, p = C.subtractor((RX, y), W); add(cc)
    feed(p["in0"], "A"); feed_const(p["in1"], "0x1"); cin0(p)
    emit(p["out"], "R_DEC")

    if skip_mux:
        return circ
    # ---- result mux 16:1 (placed far right, well below inputs) ----
    MX = 1000
    MY = 900
    cc, mp = C.multiplexer((MX, MY), select_bits=4, width=W); add(cc)
    order = ["R_ADD", "R_SUB", "R_AND", "R_OR", "R_XOR", "R_NOT",
             "R_LSL", "R_LSR", "R_RSL", "R_RSR", "R_MUL", "R_DIV",
             "R_MOD", "R_INC", "R_DEC", "B"]
    for i, label in enumerate(order):
        feed(mp[f"in{i}"], label)
    sx, sy = mp["sel"]
    tun((sx, sy + 40), "OP", 4, facing="east"); wire((sx, sy + 40), (sx, sy))
    emit(mp["out"], "R")
    add(Comp("0", "Pin", (MX + 160, MY), {"appearance": "classic", "facing": "west", "output": "true", "label": "R", "width": str(W)}))
    tun((MX + 100, MY), "R", W, facing="east"); wire((MX + 100, MY), (MX + 160, MY))

    # ---- flags ----
    FX = 1500
    # Z = (R == 0)
    cc, p = C.comparator((FX, 1400), W); add(cc)
    feed(p["in0"], "R"); feed_const(p["in1"], "0x0")
    emit(p["eq"], "Z", 1)
    add(Comp("0", "Pin", (FX + 160, 1400), {"appearance": "classic", "facing": "west", "output": "true", "label": "Z"}))
    tun((FX + 100, 1400), "Z", 1, facing="east"); wire((FX + 100, 1400), (FX + 160, 1400))

    # N = (R < 0 signed)
    cc, p = C.comparator((FX, 1500), W); add(cc)
    cc.attrs["mode"] = "twosComplement"
    feed(p["in0"], "R"); feed_const(p["in1"], "0x0")
    emit(p["lt"], "N", 1)
    add(Comp("0", "Pin", (FX + 160, 1500), {"appearance": "classic", "facing": "west", "output": "true", "label": "N"}))
    tun((FX + 100, 1500), "N", 1, facing="east"); wire((FX + 100, 1500), (FX + 160, 1500))

    # Cf = carry of ADD (CPU may also use B_SUB).  Expose C_ADD.
    add(Comp("0", "Pin", (FX + 160, 1600), {"appearance": "classic", "facing": "west", "output": "true", "label": "Cf"}))
    tun((FX + 100, 1600), "C_ADD", 1, facing="east"); wire((FX + 100, 1600), (FX + 160, 1600))

    # V = signed overflow of ADD (computed below).
    add(Comp("0", "Pin", (FX + 160, 1700), {"appearance": "classic", "facing": "west", "output": "true", "label": "V"}))
    tun((FX + 100, 1700), "V", 1, facing="east"); wire((FX + 100, 1700), (FX + 160, 1700))
    if not skip_overflow:
        _overflow_add(circ, add, wire, tun, const)

    return circ


def _overflow_add(circ, add, wire, tun, const):
    """V = (A15 == B15) AND (R_ADD15 != A15).  Uses splitters to grab bit 15."""
    W = 16
    # We grab sign bits via Bit Extender (shift) is messy; use Splitter bit 15.
    # Splitter: combined input, fanout=16; bit i output. We route A,B,R_ADD.
    def sign_bit(src_label, out_label, x, y):
        # Splitter facing east: combined on west (loc), bit outputs on east.
        # Place splitter, feed combined from tunnel, take bit15.
        sp = Comp("0", "Splitter", (x, y),
                  {"facing": "east", "fanout": str(W), "incoming": str(W), "appear": "left"})
        add(sp)
        # combined end is at loc (west). Feed it.
        tun((x - 20, y), src_label, W, facing="east"); wire((x - 20, y), (x, y))
        # bit outputs: for appear=left, bit i at (x+20, y + i*10)? We only need bit15.
        # Rather than guess, use a 1-bit Bit Extender by right-shifting: skip.
        # Instead route all 16 to a known pattern is overkill. Use arithmetic:
        # sign = (val >> 15) & 1 via Shifter then splitter bit0. Too much.
        # Simplest robust: compare val < 0 signed => sign bit. Use comparator.
        return
    # Robust path: N-style comparators for sign bits.
    FX = 2000
    def signflag(src, net, y):
        cc, p = C.comparator((FX, y), W); add(cc)
        cc.attrs["mode"] = "twosComplement"
        tun((p["in0"][0]-20, p["in0"][1]), src, W, "east"); wire((p["in0"][0]-20,p["in0"][1]), p["in0"])
        const((p["in1"][0]-20, p["in1"][1]), "0x0", W); wire((p["in1"][0]-20,p["in1"][1]), p["in1"])
        tun(p["lt"], net, 1, "west")
    signflag("A", "SA", 200)
    signflag("B", "SB", 300)
    signflag("R_ADD", "SR", 400)
    # V = (SA XNOR SB) AND (SA XOR SR)
    # XNOR(SA,SB):
    cc, p = C.xor_gate((FX+200, 200), inputs=2, width=1, size=50, negates=None); add(cc)
    tun((p["in0"][0]-20, p["in0"][1]), "SA", 1, "east"); wire((p["in0"][0]-20,p["in0"][1]), p["in0"])
    tun((p["in1"][0]-20, p["in1"][1]), "SB", 1, "east"); wire((p["in1"][0]-20,p["in1"][1]), p["in1"])
    tun(p["out"], "SAxSB", 1, "west")
    # not of that -> XNOR
    ncc, npp = C.not_gate((FX+300, 200), width=1); add(ncc)
    tun((npp["in"][0]-20, npp["in"][1]), "SAxSB", 1, "east"); wire((npp["in"][0]-20,npp["in"][1]), npp["in"])
    tun(npp["out"], "EQAB", 1, "west")
    # XOR(SA,SR)
    cc, p = C.xor_gate((FX+200, 400), inputs=2, width=1, size=50); add(cc)
    tun((p["in0"][0]-20, p["in0"][1]), "SA", 1, "east"); wire((p["in0"][0]-20,p["in0"][1]), p["in0"])
    tun((p["in1"][0]-20, p["in1"][1]), "SR", 1, "east"); wire((p["in1"][0]-20,p["in1"][1]), p["in1"])
    tun(p["out"], "DIFFAR", 1, "west")
    # AND -> V
    cc, p = C.and_gate((FX+400, 300), inputs=2, width=1, size=50); add(cc)
    tun((p["in0"][0]-20, p["in0"][1]), "EQAB", 1, "east"); wire((p["in0"][0]-20,p["in0"][1]), p["in0"])
    tun((p["in1"][0]-20, p["in1"][1]), "DIFFAR", 1, "east"); wire((p["in1"][0]-20,p["in1"][1]), p["in1"])
    tun(p["out"], "V", 1, "west")


if __name__ == "__main__":
    print(render_project([build_alu()]), end="")
