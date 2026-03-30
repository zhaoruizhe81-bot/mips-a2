.data
arr:            .word 12, -5, 8, -3, 14, -7, 6, -9, 10, -11
n:              .word 10
sum_even_pos:   .word 0
count_neg_odd:  .word 0

.text
main:
    lui   $s0, 0x1001         # Base address of arr in the default data segment.
    lw    $s1, 40($s0)        # n
    addi  $s2, $zero, 0       # i
    addi  $s3, $zero, 0       # sum_even_pos
    addi  $s4, $zero, 0       # count_neg_odd

loop_check:
    slt   $t1, $s2, $s1
    bne   $t1, $zero, loop_body
    j     loop_end

loop_body:
    sll   $t2, $s2, 2
    addu  $t3, $s0, $t2
    lw    $t0, 0($t3)

    slt   $t1, $zero, $t0
    bne   $t1, $zero, positive_branch

    slt   $t1, $t0, $zero
    bne   $t1, $zero, negative_branch
    j     increment_i

positive_branch:
    sra   $t4, $t0, 1
    sll   $t5, $t4, 1
    sub   $t6, $t0, $t5
    bne   $t6, $zero, increment_i
    add   $s3, $s3, $t0
    j     increment_i

negative_branch:
    sra   $t4, $t0, 1
    sll   $t5, $t4, 1
    sub   $t6, $t0, $t5
    beq   $t6, $zero, increment_i
    addi  $s4, $s4, 1

increment_i:
    addi  $s2, $s2, 1
    j     loop_check

loop_end:
    sw    $s3, 44($s0)
    sw    $s4, 48($s0)
