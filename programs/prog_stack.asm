; Stack test: push X and Y, pop them back swapped.
; SP starts at 0; push decrements SP first (stack grows down).
        LDI  X, 7
        LDI  Y, 9
        PUSH X           ; MEM[SP-1]=7, SP--
        PUSH Y           ; MEM[SP-1]=9, SP--
        POP  X           ; X = MEM[SP]=9, SP++
        POP  Y           ; Y = MEM[SP]=7, SP++
        MOV  X           ; A = X = 9
        HLT
