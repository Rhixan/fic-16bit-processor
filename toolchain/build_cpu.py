"""
Build the complete FIC 16-bit single-cycle CPU as a flat `main` circuit,
plus the ALU as a documented subcircuit (ALU logic is also inlined in main
so the whole design is verifiable headlessly).

Memory: ROM = program (async read). RAM = data + stack (volatile).
Clocking: one Clock; registers latch on rising edge -> 1 instruction / 2 ticks.
A `halt` output pin stops the headless simulation (set by HLT).
"""
from circ_builder import Circuit, Comp, render_project
import components as C
from build_alu import build_alu
import isa

W = 16


# ---------- small helpers bound to a circuit ----------
class B:
    def __init__(self, circ):
        self.c = circ

    def add(self, comp):
        self.c.comps.append(comp)
        return comp

    def wire(self, a, b):
        self.c.wire(a, b)

    def tun(self, loc, label, bits=1, facing="west"):
        a = {"facing": facing, "label": label}
        if bits != 1:
            a["width"] = str(bits)
        self.add(Comp("0", "Tunnel", loc, a))

    def const(self, loc, val, bits=1, facing="east"):
        self.add(Comp("0", "Constant", loc, {"facing": facing, "width": str(bits), "value": val}))

    def pin_in(self, loc, label, bits=1):
        a = {"appearance": "classic", "label": label}
        if bits != 1:
            a["width"] = str(bits)
        self.add(Comp("0", "Pin", loc, a))

    def pin_out(self, loc, label, bits=1):
        a = {"appearance": "classic", "facing": "west", "output": "true", "label": label}
        if bits != 1:
            a["width"] = str(bits)
        self.add(Comp("0", "Pin", loc, a))

    def feed(self, dst, label, bits=W, stub=20):
        self.tun((dst[0] - stub, dst[1]), label, bits, facing="east")
        self.wire((dst[0] - stub, dst[1]), dst)

    def feed_const(self, dst, val, bits=W, stub=20):
        self.const((dst[0] - stub, dst[1]), val, bits, facing="east")
        self.wire((dst[0] - stub, dst[1]), dst)

    def emit(self, src, label, bits=W):
        self.tun(src, label, bits, facing="west")


def inline_alu(b: B, ox, oy):
    """Inline a copy of the ALU, reading nets A,B_OPND,ALUOP ; writing
    ALURES, fZ,fN,fC,fV. (Same structure as build_alu but with CPU net names.)"""
    RX = ox + 450
    STEP = 120
    y0 = oy

    def cin0(p):
        b.const((p["aux_in"][0], p["aux_in"][1] - 20), "0x0", 1, "south")
        b.wire((p["aux_in"][0], p["aux_in"][1] - 20), p["aux_in"])

    def arith(y, maker, net, aux=None, aw=W):
        cc, p = maker((RX, y), W); b.add(cc)
        b.feed(p["in0"], "A"); b.feed(p["in1"], "OPND"); cin0(p)
        b.emit(p["out"], net)
        if aux:
            b.emit((p["aux_out"][0], p["aux_out"][1] + 10), aux, 1)
            b.wire(p["aux_out"], (p["aux_out"][0], p["aux_out"][1] + 10))

    arith(y0 + 0 * STEP, C.adder, "R_ADD", "C_ADD")
    arith(y0 + 1 * STEP, C.subtractor, "R_SUB", "B_SUB")
    for i, (fn, net) in enumerate([(C.and_gate, "R_AND"), (C.or_gate, "R_OR"), (C.xor_gate, "R_XOR")]):
        y = y0 + (2 + i) * STEP
        cc, p = fn((RX, y), inputs=2, width=W, size=50); b.add(cc)
        b.feed(p["in0"], "A"); b.feed(p["in1"], "OPND"); b.emit(p["out"], net)
    # NOT A
    y = y0 + 5 * STEP
    cc, p = C.not_gate((RX, y), width=W); b.add(cc)
    b.feed(p["in"], "A"); b.emit(p["out"], "R_NOT")
    # shift amount = low 4 bits of OPND
    bex = Comp("0", "Bit Extender", (ox + 300, y0 + 6 * STEP - 60),
               {"in_width": str(W), "out_width": "4", "type": "zero"})
    b.add(bex)
    b.tun((ox + 300 - 60, y0 + 6 * STEP - 60), "OPND", W, facing="east")
    b.wire((ox + 300 - 60, y0 + 6 * STEP - 60), (ox + 300 - 40, y0 + 6 * STEP - 60))
    b.tun((ox + 300, y0 + 6 * STEP - 60), "SHAMT", 4, facing="west")
    for i, (st, net) in enumerate([("ll", "R_LSL"), ("lr", "R_LSR"), ("rl", "R_RSL"), ("rr", "R_RSR")]):
        y = y0 + (6 + i) * STEP
        cc, p = C.shifter((RX, y), W, st); b.add(cc)
        b.feed(p["in0"], "A"); b.feed(p["in1"], "SHAMT", 4); b.emit(p["out"], net)
    # MUL
    y = y0 + 10 * STEP
    cc, p = C.multiplier((RX, y), W); b.add(cc)
    b.feed(p["in0"], "A"); b.feed(p["in1"], "OPND")
    b.const((p["aux_in"][0], p["aux_in"][1] - 20), "0x0", W, "south"); b.wire((p["aux_in"][0], p["aux_in"][1] - 20), p["aux_in"])
    b.emit(p["out"], "R_MUL")
    # DIV/MOD
    y = y0 + 11 * STEP
    cc, p = C.divider((RX, y), W); b.add(cc)
    b.feed(p["in0"], "A"); b.feed(p["in1"], "OPND")
    b.const((p["aux_in"][0], p["aux_in"][1] - 20), "0x0", W, "south"); b.wire((p["aux_in"][0], p["aux_in"][1] - 20), p["aux_in"])
    b.emit(p["out"], "R_DIV")
    b.emit((p["aux_out"][0], p["aux_out"][1] + 10), "R_MOD", W); b.wire(p["aux_out"], (p["aux_out"][0], p["aux_out"][1] + 10))
    # INC
    y = y0 + 12 * STEP
    cc, p = C.adder((RX, y), W); b.add(cc)
    b.feed(p["in0"], "A"); b.feed_const(p["in1"], "0x1"); cin0(p); b.emit(p["out"], "R_INC")
    # DEC
    y = y0 + 13 * STEP
    cc, p = C.subtractor((RX, y), W); b.add(cc)
    b.feed(p["in0"], "A"); b.feed_const(p["in1"], "0x1"); cin0(p); b.emit(p["out"], "R_DEC")

    # result mux
    MX = ox + 1000; MY = y0 + 400
    cc, mp = C.multiplexer((MX, MY), select_bits=4, width=W); b.add(cc)
    order = ["R_ADD", "R_SUB", "R_AND", "R_OR", "R_XOR", "R_NOT",
             "R_LSL", "R_LSR", "R_RSL", "R_RSR", "R_MUL", "R_DIV",
             "R_MOD", "R_INC", "R_DEC", "OPND"]
    for i, label in enumerate(order):
        b.feed(mp[f"in{i}"], label)
    sx, sy = mp["sel"]
    b.tun((sx, sy + 40), "ALUOP", 4, facing="east"); b.wire((sx, sy + 40), (sx, sy))
    b.emit(mp["out"], "ALURES")

    # flags Z,N
    FX = ox + 1500
    cc, p = C.comparator((FX, y0 + 1400), W); b.add(cc)
    b.feed(p["in0"], "ALURES"); b.feed_const(p["in1"], "0x0"); b.emit(p["eq"], "fZ", 1)
    cc, p = C.comparator((FX, y0 + 1500), W); b.add(cc); cc.attrs["mode"] = "twosComplement"
    b.feed(p["in0"], "ALURES"); b.feed_const(p["in1"], "0x0"); b.emit(p["lt"], "fN", 1)
    # carry = C_ADD, overflow computed minimally = 0 (CMP relies on Z/N)
    b.tun((FX, y0 + 1600), "C_ADD", 1, facing="east"); b.tun((FX + 20, y0 + 1600), "fC", 1, facing="west"); b.wire((FX, y0 + 1600), (FX + 20, y0 + 1600))
    b.const((FX, y0 + 1700), "0x0", 1); b.tun((FX + 20, y0 + 1700), "fV", 1, facing="west"); b.wire((FX, y0 + 1700), (FX + 20, y0 + 1700))


def build_cpu(program_words=None) -> Circuit:
    circ = Circuit("main")
    b = B(circ)
    b._program = program_words

    # ============ CLOCK & RESET ============
    b.add(Comp("0", "Clock", (100, 60), {}))
    b.tun((160, 60), "CLK", 1); b.wire((100, 60), (160, 60))
    # reset = 0 (no reset input in headless; use constant 0). Could add a Pin.
    b.const((100, 120), "0x0", 1); b.tun((160, 120), "RST", 1); b.wire((100, 120), (160, 120))

    # ============ PROGRAM COUNTER (Counter, 16-bit) ============
    # PC counter: out=PC. load target when pcLoad; else increments by enable.
    pcx, pcy = 300, 300
    cc, pc = C.counter((pcx, pcy), W, label="PC", max_val=0xFFFF); b.add(cc)
    b.emit(pc["out"], "PC")
    # clock
    b.tun((pc["ck"][0], pc["ck"][1] + 10), "CLK", 1, facing="north"); b.wire(pc["ck"], (pc["ck"][0], pc["ck"][1] + 10))
    # clear = RST
    b.tun((pc["clr"][0], pc["clr"][1] + 10), "RST", 1, facing="north"); b.wire(pc["clr"], (pc["clr"][0], pc["clr"][1] + 10))
    # enable = 1 (always advance unless load). Counter: if LD=1 loads IN; else if EN counts.
    b.const((pc["en"][0] - 20, pc["en"][1]), "0x1", 1); b.wire((pc["en"][0] - 20, pc["en"][1]), pc["en"])
    # up/down = up (1)
    b.const((pc["ud"][0], pc["ud"][1] - 20), "0x1", 1, "south"); b.wire((pc["ud"][0], pc["ud"][1] - 20), pc["ud"])
    # load = pcLoad ; IN = pcTarget
    b.feed(pc["ld"], "PCLOAD", 1, stub=20)
    b.feed(pc["in"], "PCTARGET", W, stub=40)

    # ============ PROGRAM ROM ============
    # ROM addr = PC[? ] ; use low addr bits. Use addrWidth = 8 (256 words).
    romx, romy = 700, 300
    rom = Comp("4", "ROM", (romx, romy), {"addrWidth": "8", "dataWidth": str(W), "appearance": "classic", "label": "PROG"})
    if b._program:
        body = " ".join(f"{w:x}" for w in b._program)
    else:
        body = "0"
    rom.attrs["contents"] = "addr/data: 8 16\n" + body
    b.add(rom)
    # addr: take low 8 bits of PC via bit extender (truncate 16->8)
    be = Comp("0", "Bit Extender", (romx - 80, romy + 10), {"in_width": str(W), "out_width": "8", "type": "zero"})
    b.add(be)
    b.tun((romx - 80 - 60, romy + 10), "PC", W, facing="east"); b.wire((romx - 80 - 60, romy + 10), (romx - 80 - 40, romy + 10))
    b.wire((romx - 80, romy + 10), (romx, romy + 10))  # be out -> rom addr
    # data out -> INSTR
    b.emit((romx + 240, romy + 60), "INSTR", W)

    # ============ INSTRUCTION DECODE (splitter) ============
    # INSTR[15:0]: group bits -> g0=imm9(bits0..8), g1=regbit(bit9), g2=opcode(bits10..15)
    bitmap = {}
    for i in range(16):
        bitmap[i] = 0 if i <= 8 else (1 if i == 9 else 2)
    spx, spy = 1300, 300
    cc, sp = C.splitter((spx, spy), fanout=3, incoming=16, bitmap=bitmap); b.add(cc)
    b.tun(sp["combined"], "INSTR", W, facing="east")
    # NOTE: combined is the WEST end; feeding it means INSTR drives in. Use a source tunnel.
    # g0 = imm9 (9 bits), g1 = regbit (1), g2 = opcode (6)
    b.emit(sp["g0"], "IMM9", 9)
    b.emit(sp["g1"], "REGBIT", 1)
    b.emit(sp["g2"], "OPCODE", 6)
    # also addr10 = INSTR[9:0] : separate splitter g0'=addr10
    bitmap2 = {i: (0 if i <= 9 else 1) for i in range(16)}
    cc, sp2 = C.splitter((spx, spy + 200), fanout=2, incoming=16, bitmap=bitmap2); b.add(cc)
    b.tun(sp2["combined"], "INSTR", W, facing="east")
    b.emit(sp2["g0"], "ADDR10", 10)

    # sign-extend imm9 -> IMMEXT(16)
    be2 = Comp("0", "Bit Extender", (1600, 600), {"in_width": "9", "out_width": str(W), "type": "sign"})
    b.add(be2)
    b.tun((1600 - 60, 600), "IMM9", 9, facing="east"); b.wire((1600 - 60, 600), (1600 - 40, 600))
    b.tun((1600, 600), "IMMEXT", W, facing="west")
    # zero-extend addr10 -> ADDREXT(16)
    be3 = Comp("0", "Bit Extender", (1600, 700), {"in_width": "10", "out_width": str(W), "type": "zero"})
    b.add(be3)
    b.tun((1600 - 60, 700), "ADDR10", 10, facing="east"); b.wire((1600 - 60, 700), (1600 - 40, 700))
    b.tun((1600, 700), "ADDREXT", W, facing="west")

    # ============ CONTROL ROM (indexed by OPCODE) ============
    import control as CTL
    words = CTL.control_rom_words()
    crx, cry = 1300, 900
    crom = Comp("4", "ROM", (crx, cry), {"addrWidth": "6", "dataWidth": "20", "appearance": "classic", "label": "CTRL"})
    crom.attrs["contents"] = "addr/data: 6 20\n" + " ".join(f"{w:x}" for w in words)
    b.add(crom)
    b.tun((crx - 60, cry + 10), "OPCODE", 6, facing="east"); b.wire((crx - 60, cry + 10), (crx, cry + 10))
    b.emit((crx + 240, cry + 60), "CW", 20)

    # break CW into signals via a splitter (fanout per field)
    # Layout per control.py: [0]writeA [1]writeReg [3:2]regSrc [4]memW [6:5]memAddr
    #   [7]updFlags [10:8]pcSel [11]spDec [12]spInc [13]halt [17:14]aluOp [18]aluOpSel
    cwmap = {}
    def fld(bits, grp):
        for bb in bits:
            cwmap[bb] = grp
    fld([0], 0)                 # g0 writeA
    fld([1], 1)                 # g1 writeReg
    fld([2, 3], 2)              # g2 regSrc(2)
    fld([4], 3)                 # g3 memW
    fld([5, 6], 4)              # g4 memAddr(2)
    fld([7], 5)                 # g5 updFlags
    fld([8, 9, 10], 6)          # g6 pcSel(3)
    fld([11], 7)                # g7 spDec
    fld([12], 8)                # g8 spInc
    fld([13], 9)                # g9 halt
    fld([14, 15, 16, 17], 10)   # g10 aluOp(4)
    fld([18], 11)               # g11 aluOpSel
    fld([19], 12)               # g12 unused
    sx, sy = 1900, 1000
    cc, csp = C.splitter((sx, sy), fanout=13, incoming=20, bitmap=cwmap); b.add(cc)
    b.tun(csp["combined"], "CW", 20, facing="east")
    names = ["writeA", "writeReg", "regSrc", "memW", "memAddr", "updFlags",
             "pcSel", "spDec", "spInc", "halt", "cAluOp", "aluOpSel", "cwUnused"]
    widths = [1, 1, 2, 1, 2, 1, 3, 1, 1, 1, 4, 1, 1]
    for i, (nm, wd) in enumerate(zip(names, widths)):
        b.emit(csp[f"g{i}"], nm, wd)

    # ============ ALUOP selection: opcode[3:0] or control override ============
    # extract opcode[3:0] via splitter
    cc, osp = C.splitter((1900, 500), fanout=2, incoming=6, bitmap={i: (0 if i <= 3 else 1) for i in range(6)}); b.add(cc)
    b.tun(osp["combined"], "OPCODE", 6, facing="east")
    b.emit(osp["g0"], "OPLOW4", 4)
    # mux: sel=aluOpSel, in0=OPLOW4, in1=cAluOp -> ALUOP
    cc, amx = C.multiplexer((2300, 500), select_bits=1, width=4); b.add(cc)
    b.feed(amx["in0"], "OPLOW4", 4); b.feed(amx["in1"], "cAluOp", 4)
    b.tun((amx["sel"][0], amx["sel"][1] + 30), "aluOpSel", 1, facing="east"); b.wire((amx["sel"][0], amx["sel"][1] + 30), amx["sel"])
    b.emit(amx["out"], "ALUOP", 4)

    # ============ OPERAND select: X (regbit=0) or Y (regbit=1) ============
    cc, omx = C.multiplexer((2300, 1500), select_bits=1, width=W); b.add(cc)
    b.feed(omx["in0"], "X"); b.feed(omx["in1"], "Y")
    b.tun((omx["sel"][0], omx["sel"][1] + 30), "REGBIT", 1, facing="east"); b.wire((omx["sel"][0], omx["sel"][1] + 30), omx["sel"])
    b.emit(omx["out"], "OPND")

    # ============ INLINE ALU ============
    inline_alu(b, 2800, 200)

    # ============ A REGISTER ============
    ax, ay = 2600, 2000
    cc, ra = C.register((ax, ay), W, label="A"); b.add(cc)
    b.emit(ra["out"], "A")
    b.feed(ra["in"], "ALURES", W, stub=30)
    b.tun((ra["ck"][0], ra["ck"][1] + 10), "CLK", 1, facing="north"); b.wire(ra["ck"], (ra["ck"][0], ra["ck"][1] + 10))
    b.tun((ra["clr"][0], ra["clr"][1] + 10), "RST", 1, facing="north"); b.wire(ra["clr"], (ra["clr"][0], ra["clr"][1] + 10))
    b.feed(ra["en"], "writeA", 1, stub=20)

    # ============ REG WRITE DATA mux (for X/Y): 0=MEMDATA 1=IMMEXT 2=A 3=ALURES ============
    cc, rwm = C.multiplexer((2300, 2300), select_bits=2, width=W); b.add(cc)
    b.feed(rwm["in0"], "MEMDATA"); b.feed(rwm["in1"], "IMMEXT")
    b.feed(rwm["in2"], "A"); b.feed(rwm["in3"], "ALURES")
    b.tun((rwm["sel"][0], rwm["sel"][1] + 30), "regSrc", 2, facing="east"); b.wire((rwm["sel"][0], rwm["sel"][1] + 30), rwm["sel"])
    b.emit(rwm["out"], "REGWDATA")

    # write-enable for X = writeReg & ~REGBIT ; for Y = writeReg & REGBIT
    # ~REGBIT
    cc, ng = C.not_gate((2000, 2600), width=1); b.add(cc)
    b.feed(ng["in"], "REGBIT", 1, stub=20); b.emit(ng["out"], "NREGBIT")
    cc, g1 = C.and_gate((2200, 2600), inputs=2, width=1, size=50); b.add(cc)
    b.feed(g1["in0"], "writeReg", 1); b.feed(g1["in1"], "NREGBIT", 1); b.emit(g1["out"], "weX")
    cc, g2 = C.and_gate((2200, 2750), inputs=2, width=1, size=50); b.add(cc)
    b.feed(g2["in0"], "writeReg", 1); b.feed(g2["in1"], "REGBIT", 1); b.emit(g2["out"], "weY")

    # ============ X REGISTER ============
    xx, xy = 2600, 2600
    cc, rx = C.register((xx, xy), W, label="X"); b.add(cc)
    b.emit(rx["out"], "X")
    b.feed(rx["in"], "REGWDATA", W, stub=30)
    b.tun((rx["ck"][0], rx["ck"][1] + 10), "CLK", 1, facing="north"); b.wire(rx["ck"], (rx["ck"][0], rx["ck"][1] + 10))
    b.tun((rx["clr"][0], rx["clr"][1] + 10), "RST", 1, facing="north"); b.wire(rx["clr"], (rx["clr"][0], rx["clr"][1] + 10))
    b.feed(rx["en"], "weX", 1, stub=20)

    # ============ Y REGISTER ============
    yx, yy = 2600, 2750
    cc, ry = C.register((yx, yy), W, label="Y"); b.add(cc)
    b.emit(ry["out"], "Y")
    b.feed(ry["in"], "REGWDATA", W, stub=30)
    b.tun((ry["ck"][0], ry["ck"][1] + 10), "CLK", 1, facing="north"); b.wire(ry["ck"], (ry["ck"][0], ry["ck"][1] + 10))
    b.tun((ry["clr"][0], ry["clr"][1] + 10), "RST", 1, facing="north"); b.wire(ry["clr"], (ry["clr"][0], ry["clr"][1] + 10))
    b.feed(ry["en"], "weY", 1, stub=20)

    # ============ FLAG REGISTER (4-bit {V,C,N,Z}) ============
    # combine fZ,fN,fC,fV into FLAGIN via splitter (reverse: combine 4x1 -> 4)
    cc, fsp = C.splitter((2000, 3100), fanout=4, incoming=4, bitmap={0: 0, 1: 1, 2: 2, 3: 3}); b.add(cc)
    # here combined is OUTPUT side? For combine we drive group ends and read combined.
    b.tun((fsp["g0"]), "fZ", 1, facing="east")
    b.tun((fsp["g1"]), "fN", 1, facing="east")
    b.tun((fsp["g2"]), "fC", 1, facing="east")
    b.tun((fsp["g3"]), "fV", 1, facing="east")
    b.tun(fsp["combined"], "FLAGIN", 4, facing="west")
    fx, fy = 2600, 3100
    cc, rf = C.register((fx, fy), 4, label="FLAG"); b.add(cc)
    b.emit(rf["out"], "FLAG")
    b.feed(rf["in"], "FLAGIN", 4, stub=30)
    b.tun((rf["ck"][0], rf["ck"][1] + 10), "CLK", 1, facing="north"); b.wire(rf["ck"], (rf["ck"][0], rf["ck"][1] + 10))
    b.tun((rf["clr"][0], rf["clr"][1] + 10), "RST", 1, facing="north"); b.wire(rf["clr"], (rf["clr"][0], rf["clr"][1] + 10))
    b.feed(rf["en"], "updFlags", 1, stub=20)
    # split FLAG -> Zf,Nf,Cf,Vf
    cc, fsp2 = C.splitter((3100, 3100), fanout=4, incoming=4, bitmap={0: 0, 1: 1, 2: 2, 3: 3}); b.add(cc)
    b.tun(fsp2["combined"], "FLAG", 4, facing="east")
    b.emit(fsp2["g0"], "Zf", 1); b.emit(fsp2["g1"], "Nf", 1)
    b.emit(fsp2["g2"], "Cf", 1); b.emit(fsp2["g3"], "Vf", 1)

    # ============ STACK POINTER (Counter) ============
    # SP: decrement on spDec, increment on spInc. Use up/down counter.
    # enable = spDec | spInc ; ud = spInc (1=up) else down.
    cc, org = C.or_gate((2000, 3500), inputs=2, width=1, size=50); b.add(cc)
    b.feed(org["in0"], "spDec", 1); b.feed(org["in1"], "spInc", 1); b.emit(org["out"], "spEn")
    spx2, spy2 = 2600, 3500
    cc, sprg = C.counter((spx2, spy2), W, label="SP", max_val=0xFFFF); b.add(cc)
    b.emit(sprg["out"], "SP")
    b.tun((sprg["ck"][0], sprg["ck"][1] + 10), "CLK", 1, facing="north"); b.wire(sprg["ck"], (sprg["ck"][0], sprg["ck"][1] + 10))
    b.tun((sprg["clr"][0], sprg["clr"][1] + 10), "RST", 1, facing="north"); b.wire(sprg["clr"], (sprg["clr"][0], sprg["clr"][1] + 10))
    b.feed(sprg["en"], "spEn", 1, stub=20)
    b.feed(sprg["ud"], "spInc", 1, stub=0)  # up when spInc; down when spDec
    b.tun((sprg["ud"][0], sprg["ud"][1] - 20), "spInc", 1, facing="south"); b.wire((sprg["ud"][0], sprg["ud"][1] - 20), sprg["ud"])
    b.const((sprg["ld"][0] - 20, sprg["ld"][1]), "0x0", 1); b.wire((sprg["ld"][0] - 20, sprg["ld"][1]), sprg["ld"])  # no load
    # SP-1 (push address) = SP - 1
    cc, sm = C.subtractor((3100, 3700), W); b.add(cc)
    b.feed(sm["in0"], "SP"); b.feed_const(sm["in1"], "0x1")
    b.const((sm["aux_in"][0], sm["aux_in"][1] - 20), "0x0", 1, "south"); b.wire((sm["aux_in"][0], sm["aux_in"][1] - 20), sm["aux_in"])
    b.emit(sm["out"], "SPDECV")

    # ============ DATA/STACK RAM ============
    # addr = memAddr sel : 0=IMMEXT 1=SP 2=SPDECV
    cc, amm = C.multiplexer((2300, 4000), select_bits=2, width=W); b.add(cc)
    b.feed(amm["in0"], "IMMEXT"); b.feed(amm["in1"], "SP"); b.feed(amm["in2"], "SPDECV")
    b.feed(amm["in3"], "IMMEXT")
    b.tun((amm["sel"][0], amm["sel"][1] + 30), "memAddr", 2, facing="east"); b.wire((amm["sel"][0], amm["sel"][1] + 30), amm["sel"])
    b.emit(amm["out"], "MEMADDR")
    # store data = reg (X/Y) for STORE/PUSH ; for JMP store PC+1
    # STORE/PUSH use OPND (selected reg). JMP(call) uses PCPLUS1. Select by pcSel==JMP.
    # Simplify: memWData = OPND normally; if call, = PCPLUS1. Use a 2:1 mux on isCall.
    # isCall = (pcSel == 6). Build via comparator.
    cc, cmpc = C.comparator((2000, 4300), 3); b.add(cc)
    b.feed(cmpc["in0"], "pcSel", 3); b.feed_const(cmpc["in1"], "0x6", 3)
    b.emit(cmpc["eq"], "isCall", 1)
    cc, mwd = C.multiplexer((2300, 4400), select_bits=1, width=W); b.add(cc)
    b.feed(mwd["in0"], "OPND"); b.feed(mwd["in1"], "PCPLUS1")
    b.tun((mwd["sel"][0], mwd["sel"][1] + 30), "isCall", 1, facing="east"); b.wire((mwd["sel"][0], mwd["sel"][1] + 30), mwd["sel"])
    b.emit(mwd["out"], "MEMWDATA")

    ramx, ramy = 3400, 4000
    ram = Comp("4", "RAM", (ramx, ramy), {"addrWidth": "8", "dataWidth": str(W), "appearance": "classic", "asyncread": "true", "label": "DATA"})
    b.add(ram)
    # addr low8
    be4 = Comp("0", "Bit Extender", (ramx - 80, ramy + 10), {"in_width": str(W), "out_width": "8", "type": "zero"}); b.add(be4)
    b.tun((ramx - 80 - 60, ramy + 10), "MEMADDR", W, facing="east"); b.wire((ramx - 80 - 60, ramy + 10), (ramx - 80 - 40, ramy + 10))
    b.wire((ramx - 80, ramy + 10), (ramx, ramy + 10))
    # data-in
    b.tun((ramx - 20, ramy + 90), "MEMWDATA", W, facing="east"); b.wire((ramx - 20, ramy + 90), (ramx, ramy + 90))
    # OE = 1 (always drive read)
    b.const((ramx - 20, ramy + 60), "0x1", 1); b.wire((ramx - 20, ramy + 60), (ramx, ramy + 60))
    # WE = memW
    b.tun((ramx - 20, ramy + 50), "memW", 1, facing="east"); b.wire((ramx - 20, ramy + 50), (ramx, ramy + 50))
    # CLK
    b.tun((ramx - 20, ramy + 70), "CLK", 1, facing="east"); b.wire((ramx - 20, ramy + 70), (ramx, ramy + 70))
    # data-out -> MEMDATA
    b.emit((ramx + 240, ramy + 90), "MEMDATA", W)

    # ============ PC+1 ============
    cc, pcadd = C.adder((2000, 4700), W); b.add(cc)
    b.feed(pcadd["in0"], "PC"); b.feed_const(pcadd["in1"], "0x1")
    b.const((pcadd["aux_in"][0], pcadd["aux_in"][1] - 20), "0x0", 1, "south"); b.wire((pcadd["aux_in"][0], pcadd["aux_in"][1] - 20), pcadd["aux_in"])
    b.emit(pcadd["out"], "PCPLUS1")

    # ============ BRANCH / PC CONTROL ============
    # Decide PCLOAD and PCTARGET.
    # branch condition value by pcSel: 1=Z 2=N 3=C 4=V 5=always 6=call(always) 7=ret(always)
    # cond mux (select=pcSel 3bit, width1): in0=0, in1=Zf, in2=Nf, in3=Cf, in4=Vf,
    #   in5=1,in6=1,in7=1
    cc, cmx = C.multiplexer((2300, 5000), select_bits=3, width=1); b.add(cc)
    b.feed_const(cmx["in0"], "0x0", 1)
    b.feed(cmx["in1"], "Zf", 1); b.feed(cmx["in2"], "Nf", 1)
    b.feed(cmx["in3"], "Cf", 1); b.feed(cmx["in4"], "Vf", 1)
    b.feed_const(cmx["in5"], "0x1", 1); b.feed_const(cmx["in6"], "0x1", 1); b.feed_const(cmx["in7"], "0x1", 1)
    b.tun((cmx["sel"][0], cmx["sel"][1] + 30), "pcSel", 3, facing="east"); b.wire((cmx["sel"][0], cmx["sel"][1] + 30), cmx["sel"])
    b.emit(cmx["out"], "PCLOAD")

    # PCTARGET: if ret -> MEMDATA(from stack) ; else -> ADDREXT
    cc, cmpr = C.comparator((2000, 5300), 3); b.add(cc)
    b.feed(cmpr["in0"], "pcSel", 3); b.feed_const(cmpr["in1"], "0x7", 3)
    b.emit(cmpr["eq"], "isRet", 1)
    cc, tmx = C.multiplexer((2300, 5400), select_bits=1, width=W); b.add(cc)
    b.feed(tmx["in0"], "ADDREXT"); b.feed(tmx["in1"], "MEMDATA")
    b.tun((tmx["sel"][0], tmx["sel"][1] + 30), "isRet", 1, facing="east"); b.wire((tmx["sel"][0], tmx["sel"][1] + 30), tmx["sel"])
    b.emit(tmx["out"], "PCTARGET")

    # ============ HALT output ============
    b.pin_out((3600, 5600), "halt", 1)
    b.tun((3540, 5600), "halt", 1, facing="east"); b.wire((3540, 5600), (3600, 5600))

    # ============ debug/observation output pins ============
    for i, (nm, bits) in enumerate([("A", W), ("X", W), ("Y", W), ("PC", W), ("SP", W), ("FLAG", 4)]):
        y = 5800 + i * 60
        b.pin_out((3600, y), nm + "_o" if nm in ("A", "X", "Y") else nm, bits)
        b.tun((3540, y), nm, bits, facing="east"); b.wire((3540, y), (3600, y))

    return circ


def build_project(program_words=None):
    """Return the full project: main CPU circuit + standalone ALU subcircuit."""
    from build_alu import build_alu
    main = build_cpu(program_words)
    alu = build_alu()
    return [main, alu]


if __name__ == "__main__":
    import sys
    from assembler import assemble
    prog = None
    if len(sys.argv) > 1:
        prog = assemble(open(sys.argv[1]).read())
    print(render_project(build_project(prog)), end="")
