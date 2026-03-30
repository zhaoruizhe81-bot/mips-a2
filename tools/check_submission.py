#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DATA_BASE = 0x10010000
TEXT_BASE = 0x00400000

FORBIDDEN_COMMON = {
    "li",
    "la",
    "move",
    "blt",
    "bgt",
    "ble",
    "bge",
    "bltu",
    "bgtu",
    "bleu",
    "bgeu",
    "mul",
    "mulo",
    "mulou",
    "mult",
    "multu",
    "div",
    "divu",
    "rem",
    "remu",
    "mfhi",
    "mflo",
}

INSTRUCTION_CLASSES = {
    "add": "arithmetic_logic",
    "addi": "arithmetic_logic",
    "addu": "arithmetic_logic",
    "andi": "arithmetic_logic",
    "lui": "arithmetic_logic",
    "ori": "arithmetic_logic",
    "sll": "arithmetic_logic",
    "slt": "arithmetic_logic",
    "sra": "arithmetic_logic",
    "sub": "arithmetic_logic",
    "lw": "lw",
    "sw": "sw",
    "beq": "branch",
    "bne": "branch",
    "j": "jump",
}

CPI = {
    "arithmetic_logic": 4,
    "lw": 5,
    "sw": 4,
    "branch": 3,
    "jump": 2,
}

REGISTER_ALIASES = {
    "zero": 0,
    "0": 0,
    "at": 1,
    "v0": 2,
    "v1": 3,
    "a0": 4,
    "a1": 5,
    "a2": 6,
    "a3": 7,
    "t0": 8,
    "t1": 9,
    "t2": 10,
    "t3": 11,
    "t4": 12,
    "t5": 13,
    "t6": 14,
    "t7": 15,
    "s0": 16,
    "s1": 17,
    "s2": 18,
    "s3": 19,
    "s4": 20,
    "s5": 21,
    "s6": 22,
    "s7": 23,
    "t8": 24,
    "t9": 25,
    "k0": 26,
    "k1": 27,
    "gp": 28,
    "sp": 29,
    "fp": 30,
    "ra": 31,
}


@dataclass
class Instruction:
    op: str
    args: list[str]
    source_line: int
    text_address: int


def parse_int(value: str) -> int:
    value = value.strip()
    if value.startswith("-0x"):
        return -int(value[3:], 16)
    if value.startswith("0x"):
        return int(value, 16)
    return int(value, 10)


def reg_index(token: str) -> int:
    token = token.strip()
    if not token.startswith("$"):
        raise ValueError(f"Expected register, got {token!r}")
    name = token[1:]
    if name not in REGISTER_ALIASES:
        raise ValueError(f"Unknown register {token!r}")
    return REGISTER_ALIASES[name]


def signed32(value: int) -> int:
    value &= 0xFFFFFFFF
    if value & 0x80000000:
        return value - 0x100000000
    return value


def parse_offset_base(token: str) -> tuple[int, int]:
    match = re.fullmatch(r"([+-]?(?:0x[0-9a-fA-F]+|\d+))\((\$[a-z0-9]+)\)", token.strip())
    if not match:
        raise ValueError(f"Invalid memory operand {token!r}")
    offset = parse_int(match.group(1))
    base = reg_index(match.group(2))
    return offset, base


def strip_comment(line: str) -> str:
    if "#" in line:
        return line.split("#", 1)[0]
    return line


def parse_data_words(payload: str) -> list[int]:
    if not payload.startswith(".word"):
        raise ValueError(f"Only .word supported, got {payload!r}")
    body = payload[len(".word") :].strip()
    return [parse_int(part.strip()) for part in body.split(",") if part.strip()]


def parse_asm(path: Path) -> tuple[list[Instruction], dict[str, int], dict[int, int], dict[str, int]]:
    instructions: list[Instruction] = []
    text_labels: dict[str, int] = {}
    data_labels: dict[str, int] = {}
    memory: dict[int, int] = {}
    section: str | None = None
    data_addr = DATA_BASE
    text_addr = TEXT_BASE

    for line_no, raw_line in enumerate(path.read_text().splitlines(), 1):
        line = strip_comment(raw_line).strip()
        if not line:
            continue
        if line == ".data":
            section = "data"
            continue
        if line == ".text":
            section = "text"
            continue

        label = None
        if ":" in line:
            left, right = line.split(":", 1)
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", left.strip()):
                label = left.strip()
                line = right.strip()
                if section == "data":
                    data_labels[label] = data_addr
                elif section == "text":
                    text_labels[label] = text_addr
                else:
                    raise ValueError(f"Label outside section at line {line_no}")

        if not line:
            continue

        if section == "data":
            words = parse_data_words(line)
            for word in words:
                memory[data_addr] = signed32(word)
                data_addr += 4
            continue

        if section != "text":
            raise ValueError(f"Instruction outside .text at line {line_no}")

        tokens = [token.strip() for token in re.split(r"[\s,]+", line) if token.strip()]
        op = tokens[0].lower()
        args = tokens[1:]
        instructions.append(
            Instruction(op=op, args=args, source_line=line_no, text_address=text_addr)
        )
        text_addr += 4

    return instructions, text_labels, memory, data_labels


def classify_instruction(op: str) -> str:
    if op not in INSTRUCTION_CLASSES:
        raise ValueError(f"Unsupported instruction {op!r} in checker")
    return INSTRUCTION_CLASSES[op]


def static_checks(version: str, path: Path, instructions: Iterable[Instruction]) -> list[str]:
    errors: list[str] = []
    ops = [ins.op for ins in instructions]

    for ins in instructions:
        if ins.op in FORBIDDEN_COMMON:
            errors.append(
                f"{path.name}:{ins.source_line} uses forbidden instruction {ins.op}"
            )

    if version == "a":
        if "andi" not in ops:
            errors.append(f"{path.name} must use andi for parity detection")
        if "bne" not in ops:
            errors.append(f"{path.name} should use BNE for internal branching")
        if "beq" not in ops:
            errors.append(f"{path.name} must use BEQ")
    if version == "b":
        if "andi" in ops:
            errors.append(f"{path.name} must not use andi")
        for required in ("sra", "sll", "sub"):
            if required not in ops:
                errors.append(f"{path.name} must use {required} for arithmetic parity detection")
        if "bne" not in ops:
            errors.append(f"{path.name} must use BNE")

    return errors


def run_program(
    instructions: list[Instruction],
    text_labels: dict[str, int],
    memory: dict[int, int],
) -> tuple[dict[int, int], Counter[str]]:
    regs = [0] * 32
    pc_map = {ins.text_address: ins for ins in instructions}
    counts: Counter[str] = Counter()
    pc = TEXT_BASE
    max_steps = 10000

    for _ in range(max_steps):
        ins = pc_map.get(pc)
        if ins is None:
            break
        counts[classify_instruction(ins.op)] += 1
        next_pc = pc + 4
        op = ins.op
        args = ins.args

        if op == "lui":
            rt = reg_index(args[0])
            imm = parse_int(args[1]) & 0xFFFF
            regs[rt] = signed32(imm << 16)
        elif op == "ori":
            rd = reg_index(args[0])
            rs = reg_index(args[1])
            imm = parse_int(args[2]) & 0xFFFF
            regs[rd] = signed32((regs[rs] & 0xFFFFFFFF) | imm)
        elif op == "addi":
            rt = reg_index(args[0])
            rs = reg_index(args[1])
            imm = parse_int(args[2])
            regs[rt] = signed32(regs[rs] + imm)
        elif op == "add":
            rd = reg_index(args[0])
            rs = reg_index(args[1])
            rt = reg_index(args[2])
            regs[rd] = signed32(regs[rs] + regs[rt])
        elif op == "addu":
            rd = reg_index(args[0])
            rs = reg_index(args[1])
            rt = reg_index(args[2])
            regs[rd] = signed32((regs[rs] & 0xFFFFFFFF) + (regs[rt] & 0xFFFFFFFF))
        elif op == "sub":
            rd = reg_index(args[0])
            rs = reg_index(args[1])
            rt = reg_index(args[2])
            regs[rd] = signed32(regs[rs] - regs[rt])
        elif op == "andi":
            rt = reg_index(args[0])
            rs = reg_index(args[1])
            imm = parse_int(args[2]) & 0xFFFF
            regs[rt] = signed32((regs[rs] & 0xFFFFFFFF) & imm)
        elif op == "sll":
            rd = reg_index(args[0])
            rt = reg_index(args[1])
            shamt = parse_int(args[2])
            regs[rd] = signed32((regs[rt] & 0xFFFFFFFF) << shamt)
        elif op == "sra":
            rd = reg_index(args[0])
            rt = reg_index(args[1])
            shamt = parse_int(args[2])
            regs[rd] = signed32(regs[rt] >> shamt)
        elif op == "slt":
            rd = reg_index(args[0])
            rs = reg_index(args[1])
            rt = reg_index(args[2])
            regs[rd] = 1 if regs[rs] < regs[rt] else 0
        elif op == "lw":
            rt = reg_index(args[0])
            offset, base = parse_offset_base(args[1])
            address = signed32(regs[base] + offset)
            regs[rt] = signed32(memory.get(address, 0))
        elif op == "sw":
            rt = reg_index(args[0])
            offset, base = parse_offset_base(args[1])
            address = signed32(regs[base] + offset)
            memory[address] = signed32(regs[rt])
        elif op == "beq":
            rs = reg_index(args[0])
            rt = reg_index(args[1])
            label = args[2]
            if regs[rs] == regs[rt]:
                next_pc = text_labels[label]
        elif op == "bne":
            rs = reg_index(args[0])
            rt = reg_index(args[1])
            label = args[2]
            if regs[rs] != regs[rt]:
                next_pc = text_labels[label]
        elif op == "j":
            next_pc = text_labels[args[0]]
        else:
            raise ValueError(f"Unsupported instruction {op}")

        regs[0] = 0
        pc = next_pc
    else:
        raise RuntimeError("Program did not terminate within the step limit")

    return {
        "sum_even_pos": memory[DATA_BASE + 44],
        "count_neg_odd": memory[DATA_BASE + 48],
    }, counts


def build_metrics(counts: Counter[str]) -> dict[str, object]:
    total_instructions = sum(counts.values())
    weighted_cycles = sum(counts[name] * CPI[name] for name in counts)
    average_cpi = weighted_cycles / total_instructions

    single_cycle_time_ps = total_instructions * 1000
    multi_cycle_time_ps = weighted_cycles * 250
    optimized_va_time_ps = None

    metrics = {
        "instruction_counts": {
            "arithmetic_logic": counts["arithmetic_logic"],
            "lw": counts["lw"],
            "sw": counts["sw"],
            "branch": counts["branch"],
            "jump": counts["jump"],
            "total": total_instructions,
        },
        "weighted_cycles": weighted_cycles,
        "average_cpi": average_cpi,
        "single_cycle_time_ps": single_cycle_time_ps,
        "multi_cycle_time_ps": multi_cycle_time_ps,
    }
    if counts["lw"] is not None:
        optimized_va_time_ps = (
            (counts["arithmetic_logic"] * 4)
            + (counts["lw"] * 6)
            + (counts["sw"] * 4)
            + (counts["branch"] * 3)
            + (counts["jump"] * 2)
        ) * 200
        metrics["optimized_multi_cycle_time_ps"] = optimized_va_time_ps
    return metrics


def analyze_file(version: str, path: Path) -> dict[str, object]:
    instructions, labels, memory, _ = parse_asm(path)
    errors = static_checks(version, path, instructions)
    if errors:
        raise SystemExit("\n".join(errors))
    results, counts = run_program(instructions, labels, memory.copy())
    metrics = build_metrics(counts)
    return {
        "file": str(path),
        "results": results,
        "metrics": metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Static checks and lightweight execution for MIPS A2")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    version_a = analyze_file("a", root / "src" / "version_a.asm")
    version_b = analyze_file("b", root / "src" / "version_b.asm")

    if version_a["results"] != version_b["results"]:
        raise SystemExit("Version A and Version B do not produce the same final results")
    if version_a["results"] != {"sum_even_pos": 50, "count_neg_odd": 5}:
        raise SystemExit(
            "Final results do not match the expected values: sum_even_pos=50, count_neg_odd=5"
        )

    speedups = {
        "version_a": version_a["metrics"]["single_cycle_time_ps"]
        / version_a["metrics"]["multi_cycle_time_ps"],
        "version_b": version_b["metrics"]["single_cycle_time_ps"]
        / version_b["metrics"]["multi_cycle_time_ps"],
    }

    payload = {
        "version_a": version_a,
        "version_b": version_b,
        "speedup_multi_vs_single": speedups,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return

    for label, item in (("Version A", version_a), ("Version B", version_b)):
        metrics = item["metrics"]
        counts = metrics["instruction_counts"]
        print(label)
        print(f"  Results: {item['results']}")
        print(f"  Counts: {counts}")
        print(f"  Average CPI: {metrics['average_cpi']:.4f}")
        print(f"  Single-cycle time: {metrics['single_cycle_time_ps']} ps")
        print(f"  Multi-cycle time: {metrics['multi_cycle_time_ps']} ps")
        if label == "Version A":
            print(
                "  Optimized multi-cycle time (200 ps clock, LW CPI=6): "
                f"{metrics['optimized_multi_cycle_time_ps']} ps"
            )
    print("Speedup (single / multi)")
    print(f"  Version A: {speedups['version_a']:.4f}x")
    print(f"  Version B: {speedups['version_b']:.4f}x")


if __name__ == "__main__":
    main()
