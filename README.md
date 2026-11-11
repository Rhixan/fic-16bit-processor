# FIC 16-bit General Purpose Processor (Logisim Evolution)

A complete, working single-cycle 16-bit CPU for **Logisim Evolution**, built to
the FIC project specification. The processor is fully simulated and verified:
ALU operations, conditional/unconditional branches, memory load/store, and a
hardware stack with `JMP`/`RET` subroutine calls all execute correctly.

Open **`fic_processor.circ`** in Logisim Evolution to use it.

## What's in the box

```
fic_processor.circ     The Logisim Evolution circuit (open this).
                       Contains two circuits:
                         - main : the full CPU datapath
                         - ALU  : the 16-bit ALU as a standalone subcircuit
toolchain/             Python tools that generate & test the circuit
  isa.py               Opcode definitions
  assembler.py         Two-pass assembler (asm -> machine code)
  control.py           Control-unit microcode (opcode -> control word)
  build_cpu.py         Generates the .circ (CPU + ALU)
  build_alu.py         Generates the ALU circuit
  components.py        Logisim component geometry library
  circ_builder.py      .circ XML emitter
  run_prog.py          Assemble + simulate a program headlessly
programs/              Example assembly programs (all verified)
docs/DESIGN.md         ISA + datapath design document
docs/geometry.md       Verified Logisim component pin geometry notes
```

## Architecture (single-cycle)

| Unit | Implementation |
|------|----------------|
| Accumulator **A**, registers **X**, **Y** | 16-bit `Register` |
| **PC**, **SP** | 16-bit `Counter` (SP grows downward) |
| **Flag** register | 4-bit `Register` {V,C,N,Z} |
| **ALU** | all 19 operations (ADD…MOV, CMP, TST) + Z/N/C/V flags |
| **Control Unit** | microcode `ROM` indexed by the 6-bit opcode |
| **Program memory** | `ROM` (async read) — holds the assembled program |
| **Data + stack memory** | `RAM` (async read, byte-addressed low 8 bits) |
| **Sign-extend** | `Bit Extender` (imm9 → 16 signed; addr10 → 16 zero) |
| **Clock** | one `Clock`; one instruction per rising edge |

> **Memory note.** The spec asks for unified memory. Logisim's RAM is volatile
> (its contents reset at simulation start), so the *program* lives in a ROM and
> *data + the stack* live in a RAM. This is a standard Harvard-style split that
> supports every required instruction (LOAD/STORE/PUSH/POP/JMP/RET all use the
> RAM). See `docs/DESIGN.md` for how to make it a single unified RAM if your
> course requires it.

## Instruction set

16-bit instructions. Two formats:

```
ALU / memory :  opcode[15:10] | reg[9] | imm[8:0]
branch       :  opcode[15:10] | addr[9:0]
```
`reg` selects X (0) or Y (1); `imm` is sign-extended.

| Mnemonic | Opcode | Effect | Flags |
|----------|:------:|--------|:-----:|
| ADD/SUB/AND/OR/XOR | 00–04 | A = A op reg | ✔ |
| NOT | 05 | A = ~A | ✔ |
| LSL/LSR | 06–07 | A = A shift reg | ✔ |
| RSL/RSR | 08–09 | A = A rotate reg | ✔ |
| MUL/DIV/MOD | 0A–0C | A = A op reg | ✔ |
| INC/DEC | 0D–0E | A = A ± 1 | ✔ |
| MOV | 0F | A = reg | ✔ |
| CMP | 10 | flags = A − reg (A kept) | ✔ |
| TST | 11 | flags = A & reg (A kept) | ✔ |
| LOAD reg,addr | 18 | reg = MEM[addr] | |
| STORE reg,addr | 19 | MEM[addr] = reg | |
| LDI reg,imm | 1A | reg = imm | |
| PUSH reg | 1B | SP--; MEM[SP] = reg | |
| POP reg | 1C | reg = MEM[SP]; SP++ | |
| BRZ/BRN/BRC/BRO addr | 20–23 | branch if Z/N/C/V | |
| BRA addr | 24 | branch always | |
| JMP addr | 25 | call: push PC+1, PC = addr | |
| RET | 26 | pop PC | |
| HLT | 3F | halt | |

## Running a program

Assemble and simulate headlessly (requires Java 17+ and the Logisim Evolution
JAR). Download the JAR once from the
[Logisim Evolution releases](https://github.com/logisim-evolution/logisim-evolution/releases)
(the `*-all.jar`) and either place it next to `run_prog.py` as `logisim.jar`
or set `LOGISIM_JAR=/path/to/logisim-evolution-all.jar`:

```bash
cd toolchain
LOGISIM_JAR=/path/to/logisim-evolution-all.jar python3 run_prog.py ../programs/prog_add.asm
```

Regenerate the circuit with a program baked into the ROM:

```bash
python3 build_cpu.py ../programs/prog_add.asm > ../fic_processor.circ
```

In the **Logisim GUI**: open `fic_processor.circ`, enable
*Simulate → Ticks Enabled*, and watch `A`, `X`, `Y`, `PC`, `SP`, `FLAG` on the
output pins. The `halt` pin goes high when `HLT` executes.

## Verified example programs

| Program | What it proves | Result |
|---------|----------------|--------|
| `prog_add`   | ALU + LDI + MOV | A = 5+3 = **8** |
| `prog_loop`  | DEC, Z flag, BRZ, BRA | A counts down to **0** |
| `prog_mem`   | STORE then LOAD | value **42** survives a round-trip through RAM |
| `prog_stack` | PUSH/POP LIFO | registers swapped (X=9, Y=7) |
| `prog_call`  | JMP + RET subroutine | returns correctly, A = **11** |

All five halt cleanly with the expected register state.
