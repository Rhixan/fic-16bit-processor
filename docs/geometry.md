# Verified Logisim-Evolution v5 component geometry (loc = anchor)

All verified empirically via headless simulation in this project.

## Arithmetic (lib 3) — loc = OUTPUT (east tip), bounds (-40,-20,40,40)
Adder/Subtractor/Multiplier/Divider/Comparator/Shifter/Negator:
  in0=(x-40,y-10)  in1=(x-40,y+10)  out=(x,y)
  aux_in=(x-20,y-20)   aux_out=(x-20,y+20)   [Cin/Cout, borrow, upper/rem, Chi]
  Comparator: gt=(x,y-10) eq=(x,y) lt=(x,y+10); attr mode=twosComplement for signed
  Shifter shift-input (in1) width = ceil(log2(data)) = 4 for 16-bit!  (truncate B with Bit Extender)
  **MUST set width attr explicitly (default is 8, not 16).**

## Gates (lib 1) — loc = OUTPUT. size=50, 2-input, width 16: inputs (x-50,y-20)/(x-50,y+20)
NOT gate: in=(x-30,y), out=(x,y)

## Multiplexer (lib 2) facing=east, NOT narrow, botLeft:
  out=(x,y); inputs i at (x-40, y-(inputs/2)*10 + 10*i); sel=(x-20, y+(inputs/2)*10)
  select_bits attr; width attr (default 1).

## Register (lib 4, appearance=classic) — loc=OUTPUT
  out=(x,y) in=(x-30,y) ck=(x-20,y+20) clr=(x-10,y+20) en=(x-30,y+10)
  **set width explicitly (default 8).**

## Counter (lib 4, appearance=classic)
  out=(x,y) in=(x-30,y) ck=(x-20,y+20) clr=(x-10,y+20) ld=(x-30,y-10) ud=(x-20,y-20)
  en=(x-30,y+10) carry=(x,y+10). max attr for wrap value.

## Bit Extender (lib 0) — loc=OUTPUT. in=(x-40,y). Supports TRUNCATION (out<in).
  attrs: in_width, out_width, type=zero|sign.

## RAM (lib 4, appearance=classic, asyncread=true, databus=bibus) — loc=TOP-LEFT
  addr   = (x,   y+10)  [addrWidth]
  dataOut= (x+240,y+90) [dataWidth]  -- requires OE=1 to drive!
  dataIn = (x,   y+90)  [dataWidth]
  OE     = (x,   y+60)
  WE     = (x,   y+50)
  CLK    = (x,   y+70)
  RAM is VOLATILE: inline contents are NOT restored in headless run; starts empty.
  Program therefore lives in ROM; RAM used for data + stack.

## ROM (lib 4, appearance=classic) — loc=TOP-LEFT. Inline contents DO load.
  addr   = (x,   y+10)  [addrWidth]
  dataOut= (x+240,y+60) [dataWidth]  (always drives, async)
  contents format (element text): "addr/data: <addrbits> <databits>\n<hex words...>"

## Pin: loc = connection point. Tunnel: connects by label regardless of facing.
## Constant: loc = output point.
## Project header must NOT contain a DOCTYPE line (v5 rejects it).
## -t table with a `halt` output pin => sequential simulation (ticks clocks),
   prints outputs each time they change. Without halt => combinational enum.
## --load/--save and TTY require -t tty (needs a TTY component).
