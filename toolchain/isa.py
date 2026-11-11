"""
ISA definition for the FIC 16-bit General Purpose Processor.

Instruction formats (16-bit):
  ALU / Memory format:
     [15:10] opcode (6)  | [9] reg (1) | [8:0] immediate (9)
  Branch format:
     [15:10] opcode (6)  | [9:0] address (10)

Register bit:  0 -> X,  1 -> Y   (A is the implicit accumulator)

The ALU opcode low 4 bits are chosen so that bits [13:10] of the
instruction directly select the ALU operation for arithmetic/logic
instructions. Opcode bits [15:14] form a "class":
    00 = ALU      (uses ALU op = opcode[3:0])
    01 = memory   (LOAD / STORE)
    10 = branch / control
"""

# ---- ALU operation codes (4-bit) used internally by the ALU subcircuit ----
ALU_ADD = 0x0
ALU_SUB = 0x1
ALU_AND = 0x2
ALU_OR  = 0x3
ALU_XOR = 0x4
ALU_NOT = 0x5
ALU_LSL = 0x6   # logical shift left
ALU_LSR = 0x7   # logical shift right
ALU_RSL = 0x8   # rotate left
ALU_RSR = 0x9   # rotate right
ALU_MUL = 0xA
ALU_DIV = 0xB
ALU_MOD = 0xC
ALU_INC = 0xD
ALU_DEC = 0xE
ALU_MOV = 0xF   # pass operand B through (used for MOV / CMP/TST reuse SUB/AND)

# ---- Full 6-bit opcodes ----
# Class 00 -> ALU.  opcode = 0b00_xxxx where xxxx = ALU op.
def alu_op(op4):
    return 0b000000 | (op4 & 0xF)

OP_ADD = alu_op(ALU_ADD)   # 0x00
OP_SUB = alu_op(ALU_SUB)   # 0x01
OP_AND = alu_op(ALU_AND)   # 0x02
OP_OR  = alu_op(ALU_OR)    # 0x03
OP_XOR = alu_op(ALU_XOR)   # 0x04
OP_NOT = alu_op(ALU_NOT)   # 0x05
OP_LSL = alu_op(ALU_LSL)   # 0x06
OP_LSR = alu_op(ALU_LSR)   # 0x07
OP_RSL = alu_op(ALU_RSL)   # 0x08
OP_RSR = alu_op(ALU_RSR)   # 0x09
OP_MUL = alu_op(ALU_MUL)   # 0x0A
OP_DIV = alu_op(ALU_DIV)   # 0x0B
OP_MOD = alu_op(ALU_MOD)   # 0x0C
OP_INC = alu_op(ALU_INC)   # 0x0D
OP_DEC = alu_op(ALU_DEC)   # 0x0E
OP_MOV = alu_op(ALU_MOV)   # 0x0F

# CMP = SUB but discards result (only flags).  TST = AND but discards result.
OP_CMP = 0b010000          # 0x10
OP_TST = 0b010001          # 0x11

# Class 01 (0x1x) memory
OP_LOAD  = 0b011000        # 0x18 : A = MEM[imm] (reg bit chooses X/Y as base? -> here A<-MEM)
OP_STORE = 0b011001        # 0x19 : MEM[imm] = reg (X or Y)
OP_LDI   = 0b011010        # 0x1A : reg = sign_ext(imm)  (load immediate)
OP_PUSH  = 0b011011        # 0x1B : push reg
OP_POP   = 0b011100        # 0x1C : pop reg

# Class 10 (0x2x) branch / control
OP_BRZ = 0b100000          # 0x20
OP_BRN = 0b100001          # 0x21
OP_BRC = 0b100010          # 0x22
OP_BRO = 0b100011          # 0x23
OP_BRA = 0b100100          # 0x24
OP_JMP = 0b100101          # 0x25 call procedure (push PC)
OP_RET = 0b100110          # 0x26 return (pop PC)
OP_HLT = 0b111111          # 0x3F halt

MNEMONICS = {
    "ADD": OP_ADD, "SUB": OP_SUB, "AND": OP_AND, "OR": OP_OR, "XOR": OP_XOR,
    "NOT": OP_NOT, "LSL": OP_LSL, "LSR": OP_LSR, "RSL": OP_RSL, "RSR": OP_RSR,
    "MUL": OP_MUL, "DIV": OP_DIV, "MOD": OP_MOD, "INC": OP_INC, "DEC": OP_DEC,
    "MOV": OP_MOV, "CMP": OP_CMP, "TST": OP_TST,
    "LOAD": OP_LOAD, "STORE": OP_STORE, "LDI": OP_LDI, "PUSH": OP_PUSH, "POP": OP_POP,
    "BRZ": OP_BRZ, "BRN": OP_BRN, "BRC": OP_BRC, "BRO": OP_BRO, "BRA": OP_BRA,
    "JMP": OP_JMP, "RET": OP_RET, "HLT": OP_HLT,
}
