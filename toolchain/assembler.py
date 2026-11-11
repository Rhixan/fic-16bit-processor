"""
Tiny two-pass assembler for the FIC 16-bit ISA.

Line syntax (case-insensitive mnemonics):
  label:                      define label
  MNEMONIC [operand]          instruction
Operands:
  ALU ops (ADD..MOV, CMP, TST): register operand  X | Y
      -> encodes regbit; imm field unused (0)
  LDI reg, imm                 reg in {X,Y}, imm signed 9-bit
  LOAD reg, addr               reg = MEM[addr]
  STORE reg, addr              MEM[addr] = reg
  PUSH reg / POP reg
  BRZ/BRN/BRC/BRO/BRA/JMP label   10-bit address
  RET / HLT / NOP

Encoding:
  ALU/mem format: opcode(6)|reg(1)|imm(9)
  branch format : opcode(6)|addr(10)
"""
import re
import isa

REG = {"X": 0, "Y": 1}
ALU_MNEMS = {"ADD", "SUB", "AND", "OR", "XOR", "NOT", "LSL", "LSR", "RSL",
             "RSR", "MUL", "DIV", "MOD", "INC", "DEC", "MOV", "CMP", "TST"}
BRANCH_MNEMS = {"BRZ", "BRN", "BRC", "BRO", "BRA", "JMP"}
NOARG = {"RET", "HLT", "NOP"}
MEM2 = {"LDI", "LOAD", "STORE"}
MEM1 = {"PUSH", "POP"}


def _imm9(v):
    v &= 0x1FF
    return v


def assemble(src):
    lines = []
    for raw in src.splitlines():
        line = raw.split(";")[0].strip()
        if line:
            lines.append(line)
    # pass 1: labels
    labels = {}
    pc = 0
    cleaned = []
    for line in lines:
        m = re.match(r"^([A-Za-z_]\w*):\s*(.*)$", line)
        if m:
            labels[m.group(1).upper()] = pc
            rest = m.group(2).strip()
            if not rest:
                continue
            line = rest
        cleaned.append((pc, line))
        pc += 1
    # pass 2: encode
    words = []
    for pc, line in cleaned:
        parts = re.split(r"[ ,\t]+", line)
        mnem = parts[0].upper()
        args = [p for p in parts[1:] if p]
        if mnem == "NOP":
            words.append(0x0000)  # ADD X (harmless) -> actually use MOV? keep 0
            continue
        if mnem in NOARG:
            op = isa.MNEMONICS[mnem]
            words.append((op << 10) & 0xFFFF)
            continue
        if mnem in ALU_MNEMS:
            op = isa.MNEMONICS[mnem]
            reg = REG[args[0].upper()] if args else 0
            words.append(((op << 10) | (reg << 9)) & 0xFFFF)
            continue
        if mnem == "LDI":
            reg = REG[args[0].upper()]
            imm = _parse_int(args[1])
            words.append(((isa.OP_LDI << 10) | (reg << 9) | _imm9(imm)) & 0xFFFF)
            continue
        if mnem in ("LOAD", "STORE"):
            reg = REG[args[0].upper()]
            addr = _resolve(args[1], labels)
            op = isa.MNEMONICS[mnem]
            words.append(((op << 10) | (reg << 9) | _imm9(addr)) & 0xFFFF)
            continue
        if mnem in MEM1:
            reg = REG[args[0].upper()]
            op = isa.MNEMONICS[mnem]
            words.append(((op << 10) | (reg << 9)) & 0xFFFF)
            continue
        if mnem in BRANCH_MNEMS:
            op = isa.MNEMONICS[mnem]
            addr = _resolve(args[0], labels) & 0x3FF
            words.append(((op << 10) | addr) & 0xFFFF)
            continue
        raise ValueError(f"Unknown instruction: {line}")
    return words


def _parse_int(s):
    s = s.strip()
    if s.lower().startswith("0x"):
        return int(s, 16)
    return int(s, 10)


def _resolve(tok, labels):
    t = tok.strip().upper()
    if t in labels:
        return labels[t]
    return _parse_int(tok)


def rom_contents(words, addr_bits=8, data_bits=16):
    body = " ".join(f"{w:x}" for w in words) if words else "0"
    return f"addr/data: {addr_bits} {data_bits}\n{body}"


if __name__ == "__main__":
    prog = """
        LDI X, 5
        LDI Y, 3
        MOV X        ; A = X = 5
        ADD Y        ; A = A + Y = 8
        STORE X, 100 ; placeholder
        HLT
    """
    ws = assemble(prog)
    print([f"{w:04X}" for w in ws])
    print(rom_contents(ws))
