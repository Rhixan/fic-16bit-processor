# FIC 16-bit General Purpose Processor — Design

Single-cycle implementation for Logisim-Evolution. One instruction executes
per clock cycle (combinational RAM read, synchronous writes on the rising edge).

## Registers
- `A`  — 16-bit accumulator (implicit destination/source of ALU ops)
- `X`, `Y` — 16-bit general purpose registers
- `PC` — 16-bit program counter
- `SP` — 16-bit stack pointer (stack grows **downward**: push = SP-1 then store)
- `Flag` — 4-bit {V,C,N,Z} (updated only by arithmetic/logic instructions)

## Memory
Single unified `RAM` (16-bit address, 16-bit word). Holds program, data and
stack. Asynchronous (combinational) read port for instruction/data fetch;
synchronous write port for stores/pushes.

## Instruction formats (16-bit)
```
ALU / Memory :  [15:10] opcode(6) | [9] reg(1) | [8:0] imm(9)
Branch       :  [15:10] opcode(6) | [9:0] addr(10)
```
`reg` selects X (0) or Y (1). `imm` is sign-extended to 16 bits.

## Opcode map (6-bit)
ALU class (opcode[5:4]=00): opcode[3:0] = ALU operation, operate on A and the
operand. Operand source for ALU ops = selected register (X if reg=0, Y if reg=1).
(Immediate ALU variants can be added later; core uses register operand.)

| mnem | opcode | effect                               | flags |
|------|--------|--------------------------------------|-------|
| ADD  | 0x00   | A = A + R                            | yes   |
| SUB  | 0x01   | A = A - R                            | yes   |
| AND  | 0x02   | A = A & R                            | yes   |
| OR   | 0x03   | A = A | R                            | yes   |
| XOR  | 0x04   | A = A ^ R                            | yes   |
| NOT  | 0x05   | A = ~A                               | yes   |
| LSL  | 0x06   | A = A << R                           | yes   |
| LSR  | 0x07   | A = A >> R                           | yes   |
| RSL  | 0x08   | A = rotl(A,R)                        | yes   |
| RSR  | 0x09   | A = rotr(A,R)                        | yes   |
| MUL  | 0x0A   | A = A * R                            | yes   |
| DIV  | 0x0B   | A = A / R                            | yes   |
| MOD  | 0x0C   | A = A % R                            | yes   |
| INC  | 0x0D   | A = A + 1                            | yes   |
| DEC  | 0x0E   | A = A - 1                            | yes   |
| MOV  | 0x0F   | A = R                                | yes   |
| CMP  | 0x10   | flags = A - R (A unchanged)         | yes   |
| TST  | 0x11   | flags = A & R (A unchanged)         | yes   |

Memory class (opcode[5:4]=01):
| LOAD  | 0x18 | reg = MEM[imm]         | no |
| STORE | 0x19 | MEM[imm] = reg         | no |
| LDI   | 0x1A | reg = signext(imm)     | no |
| PUSH  | 0x1B | SP--; MEM[SP] = reg    | no |
| POP   | 0x1C | reg = MEM[SP]; SP++    | no |

Branch class (opcode[5:4]=10): target = addr(10-bit, zero-extended)
| BRZ | 0x20 | if Z  PC=addr            |
| BRN | 0x21 | if N  PC=addr            |
| BRC | 0x22 | if C  PC=addr            |
| BRO | 0x23 | if V  PC=addr            |
| BRA | 0x24 | PC=addr                  |
| JMP | 0x25 | SP--; MEM[SP]=PC+1; PC=addr (call) |
| RET | 0x26 | PC=MEM[SP]; SP++         |
| HLT | 0x3F | halt (PC holds)          |

Default (no branch taken / non-branch): PC = PC + 1.

## Flag computation
Flags come from the ALU for arithmetic/logic ops and CMP/TST. CMP uses SUB,
TST uses AND; both assert the "update flags" control but suppress the A write.

## Datapath control signals (from Control Unit, by opcode)
- `aluOp[4]`        : ALU operation selector
- `writeA`          : commit ALU result to A
- `writeReg`        : commit value to selected reg (X/Y)
- `regData sel`     : what goes to reg write (memdata / imm / A)
- `memWrite`        : RAM write enable
- `memAddr sel`     : imm vs SP
- `updateFlags`     : commit ALU flags
- `pcSel[.]`        : PC+1 / branch addr / mem(ret) / call
- `spOp`            : none / dec / inc
```
