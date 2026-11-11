"""
Control unit as a ROM indexed by the 6-bit opcode.
Outputs a 16-bit control word with the following bit layout:

 bit 0      writeA      : commit ALU result to A
 bit 1      writeReg    : commit value to selected register (X/Y)
 bits 3:2   regSrc      : 0=mem data, 1=immediate (LDI), 2=A, 3=ALURES
 bit 4      memWrite    : RAM write enable
 bits 6:5   memAddrSel  : 0=imm(ext), 1=SP, 2=SP-1(push addr)
 bit 7      updFlags    : commit ALU flags
 bits 10:8  pcSel       : 0=PC+1, 1=branch-if-cond, 2=branch-always,
                          3=call(jmp), 4=ret(from mem)
 bit 11     spDec       : SP = SP - 1 (push/call)
 bit 12     spInc       : SP = SP + 1 (pop/ret)
 bit 13     halt
 bits .. aluOp is taken directly from opcode[3:0] in datapath (not in ctrl word)

pcSel semantics for conditional: the datapath ANDs with the proper flag
according to a separate 3-bit "branchCond" field:
 bits 15:14 (plus reuse) -> we encode branchCond in bits 15:13? limited.
To keep it simple we use a SECOND control nibble via a separate ctrl ROM word
is overkill; instead encode condition in pcSel values:
 pcSel: 0=+1, 1=BRZ,2=BRN,3=BRC,4=BRO,5=BRA,6=JMP(call),7=RET
"""
import isa

# Control word is 20-bit. Bit positions:
WRITE_A = 0
WRITE_REG = 1
REGSRC0 = 2   # 2 bits  [3:2]
MEMWRITE = 4
MEMADDR0 = 5  # 2 bits  [6:5]
UPDFLAGS = 7
PCSEL0 = 8    # 3 bits  [10:8]
SPDEC = 11
SPINC = 12
HALT = 13
ALUOP0 = 14   # 4 bits  [17:14]
ALUOPSEL = 18 # 1 = use control aluOp override, 0 = use opcode[3:0]
CW_BITS = 20

REGSRC_MEM = 0
REGSRC_IMM = 1
REGSRC_A = 2

MEMADDR_IMM = 0
MEMADDR_SP = 1
MEMADDR_SPDEC = 2

PCSEL_INC = 0
PCSEL_BRZ = 1
PCSEL_BRN = 2
PCSEL_BRC = 3
PCSEL_BRO = 4
PCSEL_BRA = 5
PCSEL_JMP = 6
PCSEL_RET = 7


def cw(writeA=0, writeReg=0, regSrc=0, memWrite=0, memAddr=0, updFlags=0,
       pcSel=0, spDec=0, spInc=0, halt=0, aluOp=None):
    w = 0
    w |= (writeA & 1) << WRITE_A
    w |= (writeReg & 1) << WRITE_REG
    w |= (regSrc & 3) << REGSRC0
    w |= (memWrite & 1) << MEMWRITE
    w |= (memAddr & 3) << MEMADDR0
    w |= (updFlags & 1) << UPDFLAGS
    w |= (pcSel & 7) << PCSEL0
    w |= (spDec & 1) << SPDEC
    w |= (spInc & 1) << SPINC
    w |= (halt & 1) << HALT
    if aluOp is not None:
        w |= (aluOp & 0xF) << ALUOP0
        w |= 1 << ALUOPSEL
    return w


def control_word(opcode):
    o = opcode
    # ALU ops 0x00..0x0F : writeA, updateFlags
    if 0x00 <= o <= 0x0F:
        return cw(writeA=1, updFlags=1)
    if o == isa.OP_CMP:   # 0x10 : flags only (uses SUB)
        return cw(updFlags=1, aluOp=isa.ALU_SUB)
    if o == isa.OP_TST:   # 0x11 : flags only (uses AND)
        return cw(updFlags=1, aluOp=isa.ALU_AND)
    if o == isa.OP_LOAD:  # 0x18 reg = MEM[imm]
        return cw(writeReg=1, regSrc=REGSRC_MEM, memAddr=MEMADDR_IMM)
    if o == isa.OP_STORE: # 0x19 MEM[imm] = reg
        return cw(memWrite=1, memAddr=MEMADDR_IMM)
    if o == isa.OP_LDI:   # 0x1A reg = imm
        return cw(writeReg=1, regSrc=REGSRC_IMM)
    if o == isa.OP_PUSH:  # 0x1B SP--; MEM[SP]=reg
        return cw(memWrite=1, memAddr=MEMADDR_SPDEC, spDec=1)
    if o == isa.OP_POP:   # 0x1C reg = MEM[SP]; SP++
        return cw(writeReg=1, regSrc=REGSRC_MEM, memAddr=MEMADDR_SP, spInc=1)
    if o == isa.OP_BRZ:
        return cw(pcSel=PCSEL_BRZ)
    if o == isa.OP_BRN:
        return cw(pcSel=PCSEL_BRN)
    if o == isa.OP_BRC:
        return cw(pcSel=PCSEL_BRC)
    if o == isa.OP_BRO:
        return cw(pcSel=PCSEL_BRO)
    if o == isa.OP_BRA:
        return cw(pcSel=PCSEL_BRA)
    if o == isa.OP_JMP:   # call
        return cw(pcSel=PCSEL_JMP, memWrite=1, memAddr=MEMADDR_SPDEC, spDec=1)
    if o == isa.OP_RET:
        return cw(pcSel=PCSEL_RET, spInc=1, memAddr=MEMADDR_SP)
    if o == isa.OP_HLT:
        return cw(halt=1)
    return cw()  # NOP default


def control_rom_words():
    """Return list of 64 control words indexed by opcode."""
    return [control_word(o) for o in range(64)]


if __name__ == "__main__":
    for o in range(64):
        w = control_word(o)
        if w:
            print(f"opcode 0x{o:02X} -> ctrl 0x{w:04X}")
