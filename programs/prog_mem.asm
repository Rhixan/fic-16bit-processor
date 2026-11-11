; Memory test: store X to addr 20, load it back into Y, MOV to A.
        LDI  X, 42       ; X = 42
        STORE X, 20      ; MEM[20] = 42
        LDI  X, 0        ; clobber X
        LOAD Y, 20       ; Y = MEM[20] = 42
        MOV  Y           ; A = Y = 42
        HLT
