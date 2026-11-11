; Subroutine call/return test.
; main: X=10, call 'inc_a' which sets A=X+1, then after return A stays, HLT.
        LDI  X, 10
        MOV  X          ; A = 10
        JMP  sub        ; call subroutine (push return addr)
        HLT             ; <- return comes back here; A should be 11

sub:    INC             ; A = A + 1 = 11
        RET             ; pop return address -> back to HLT
