# Analysis

## Part 1 Summary

### Version A: Logic-Based with BEQ

- Parity detection uses `andi $t4, $t0, 1`
- Loop control uses:

```text
slt $t1, $s2, $s1
beq $t1, $zero, loop_end
```

- If `val > 0` and even, add it to `$s3`
- If `val < 0` and odd, increment `$s4`

### Version B: Arithmetic-Based with BNE

- Parity detection uses:

```text
sra $t4, $t0, 1
sll $t5, $t4, 1
sub $t6, $t0, $t5
```

- Loop control uses:

```text
slt $t1, $s2, $s1
bne $t1, $zero, loop_body
j loop_end
```

- If the computed remainder is `0`, the number is even
- If the computed remainder is non-zero for a negative value, it is treated as odd

## Part 2: Instruction Distribution and CPI

The checker executes each version over the fixed 10-element array and classifies instructions according to the assignment table.

### Instruction Counts

| Version | Arithmetic/Logic | LW | SW | BEQ/BNE | J | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 80 | 11 | 2 | 36 | 15 | 144 |
| B | 100 | 11 | 2 | 36 | 16 | 165 |

### Average CPI

Assignment CPI values:

- Arithmetic/Logic = 4
- `lw` = 5
- `sw` = 4
- `beq`/`bne` = 3
- `j` = 2

Version A weighted cycle count:

```text
(80 x 4) + (11 x 5) + (2 x 4) + (36 x 3) + (15 x 2)
= 320 + 55 + 8 + 108 + 30
= 521 cycles
```

Version A average CPI:

```text
521 / 144 = 3.6181
```

Version B weighted cycle count:

```text
(100 x 4) + (11 x 5) + (2 x 4) + (36 x 3) + (16 x 2)
= 400 + 55 + 8 + 108 + 32
= 603 cycles
```

Version B average CPI:

```text
603 / 165 = 3.6545
```

### Performance Comparison

Version A is faster than Version B.

Reason:

- Both versions execute the same number of loads, stores, and conditional branches for this dataset.
- Version B needs extra `sra`, `sll`, and `sub` instructions every time it checks parity.
- Those extra arithmetic instructions increase both the total instruction count and the weighted cycle count.

## Part 3: Single-Cycle vs Multi-Cycle Performance

Processor settings from the assignment:

- Single-cycle clock = `1000 ps`, `CPI = 1` for every instruction
- Multi-cycle clock = `250 ps`, CPI depends on instruction type

### Execution Time

Formula:

```text
Execution Time = Instruction Count x CPI x Clock Cycle Time
```

| Version | Single-Cycle Time | Multi-Cycle Time |
| --- | ---: | ---: |
| A | 144000 ps | 130250 ps |
| B | 165000 ps | 150750 ps |

### Speedup of Multi-Cycle Relative to Single-Cycle

Using:

```text
Speedup = Single-Cycle Time / Multi-Cycle Time
```

| Version | Speedup |
| --- | ---: |
| A | 1.1056x |
| B | 1.0945x |

### Why the Multi-Cycle Processor Is Faster Here

- The multi-cycle processor has a much shorter clock period: `250 ps` instead of `1000 ps`.
- Even though many instructions require more than one cycle, the shorter clock still wins overall for both programs.
- The benefit is slightly larger for Version A because it uses fewer arithmetic instructions.

## Trade-Off Discussion

The assignment asks for a modified multi-cycle design:

- clock cycle improves from `250 ps` to `200 ps`
- `lw` CPI increases from `5` to `6`

For Version A:

```text
New weighted cycles
= (80 x 4) + (11 x 6) + (2 x 4) + (36 x 3) + (15 x 2)
= 320 + 66 + 8 + 108 + 30
= 532 cycles

New execution time
= 532 x 200 ps
= 106400 ps
```

Conclusion:

- The new design is still better than the original multi-cycle result of `130250 ps`
- Improvement = `23850 ps`, about `18.31%`
- This trade-off is reasonable for Version A because only `11` load instructions are executed, while the faster clock benefits all `144` instructions
- If the workload were much more load-heavy, the higher `lw` CPI would become a larger concern

## Verification Command

```bash
python3 tools/check_submission.py
```
