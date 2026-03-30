# MIPS Assignment 2

This repository contains a complete submission-ready solution for a MIPS assembly assignment with three goals:

1. Translate the provided C loop into two different MIPS32 programs.
2. Analyze instruction distribution and average CPI for both versions.
3. Compare execution time on single-cycle and multi-cycle processors.

## Repository Layout

- `src/version_a.asm`: Logic-based parity detection with `andi` and `BEQ`-style loop control.
- `src/version_b.asm`: Arithmetic parity detection with `sra` + `sll` + `sub` and `BNE`-style loop control.
- `tools/check_submission.py`: Static checker plus a lightweight executor for the subset of MIPS used in this assignment.
- `docs/analysis.md`: Part 2 and Part 3 write-up with formulas, counts, CPI, execution time, and trade-off discussion.

## Design Summary

### Version A

- Uses `andi` to test the least significant bit.
- Uses `slt` followed by `beq` to exit the loop when `i < n` becomes false.
- Keeps the positive and negative branches close to the original C logic.

### Version B

- Does not use `andi`.
- Computes parity with:

```text
q = val >> 1
q2 = q << 1
remainder = val - q2
```

- Uses `slt` followed by `bne` to enter the loop body when `i < n` is true.

## Expected Results

For the array `{12, -5, 8, -3, 14, -7, 6, -9, 10, -11}`:

- `sum_even_pos = 50`
- `count_neg_odd = 5`

The assignment handout lists `count_neg_odd = 4` in one place, but the data itself clearly contains five negative odd numbers. The code and analysis in this repository follow the actual array contents.

## Static Check

Run:

```bash
python3 tools/check_submission.py
```

The checker verifies:

- forbidden pseudoinstructions are absent
- forbidden multiply and divide instructions are absent
- Version A uses `andi`
- Version B avoids `andi` and uses `sra`, `sll`, and `sub`
- both versions produce the same final stored results

## Analysis Snapshot

- Version A total instructions: `144`
- Version A average CPI: `3.6181`
- Version A multi-cycle time: `130250 ps`
- Version B total instructions: `165`
- Version B average CPI: `3.6545`
- Version B multi-cycle time: `150750 ps`

Version A is faster because logical parity detection needs fewer arithmetic instructions than the shift-and-subtract method in Version B.

Detailed calculations are in [docs/analysis.md](docs/analysis.md).
