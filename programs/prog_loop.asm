; Count A down from 5 to 0 using DEC + BRZ branch.
; Verifies DEC, flag Z, and conditional branch BRZ, and BRA loop.
        LDI  X, 5
        MOV  X          ; A = 5
loop:   DEC             ; A = A - 1   (updates Z flag)
        BRZ  done       ; if A==0 goto done
        BRA  loop       ; else repeat
done:   HLT             ; A should be 0 here
