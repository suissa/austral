#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
from pathlib import Path

FUNC_RE = re.compile(r"\bint\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*void\s*\)")
SKIP = {"main"}


def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        print(p.stderr, file=sys.stderr)
        raise SystemExit(p.returncode)
    return p


def extract_functions(c_path: Path):
    text = c_path.read_text()
    funcs = [m.group(1) for m in FUNC_RE.finditer(text) if m.group(1) not in SKIP]
    return sorted(set(funcs))


def build_runner(src_path: Path, funcs, out_bin: Path):
    lines = [
        '#include <stdio.h>',
        '#include <stdint.h>',
    ]
    for fn in funcs:
        lines.append(f'int {fn}(void);')
    lines.append('int main(void) {')
    for fn in funcs:
        lines.append(f'  printf("{fn}=%d\\n", {fn}());')
    lines.append('  return 0;')
    lines.append('}')
    runner = out_bin.parent / f"{out_bin.stem}_runner.c"
    runner.write_text("\n".join(lines) + "\n")
    run(["cc", str(src_path), str(runner), "-fwrapv", "-lm", "-o", str(out_bin)])


def build_runner_llvm(ll_path: Path, funcs, out_bin: Path):
    lines = [
        '#include <stdio.h>',
        '#include <stdint.h>',
    ]
    for fn in funcs:
        lines.append(f'int {fn}(void);')
    lines.append('int main(void) {')
    for fn in funcs:
        lines.append(f'  printf("{fn}=%d\\n", {fn}());')
    lines.append('  return 0;')
    lines.append('}')
    runner = out_bin.parent / f"{out_bin.stem}_runner.c"
    runner.write_text("\n".join(lines) + "\n")
    run(["clang", str(ll_path), str(runner), "-lm", "-o", str(out_bin)])


def parse_output(stdout: str):
    out = {}
    for line in stdout.strip().splitlines():
        if not line.strip():
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = int(v.strip())
    return out


def main():
    if len(sys.argv) != 3:
        print("uso: make validate arquivo_em_c arquivo_em_LLVM", file=sys.stderr)
        raise SystemExit(2)
    c_path = Path(sys.argv[1]).resolve()
    ll_path = Path(sys.argv[2]).resolve()
    funcs = extract_functions(c_path)
    if not funcs:
        print("Nenhuma função `int fn(void)` encontrada no arquivo C.", file=sys.stderr)
        raise SystemExit(1)

    out_dir = Path(__file__).parent
    c_bin = out_dir / "_c_validation_bin"
    ll_bin = out_dir / "_llvm_validation_bin"

    build_runner(c_path, funcs, c_bin)
    c_results = parse_output(run([str(c_bin)]).stdout)
    (out_dir / "LLVM_validator.json").write_text(json.dumps(c_results, indent=2, sort_keys=True) + "\n")

    build_runner_llvm(ll_path, funcs, ll_bin)
    ll_results = parse_output(run([str(ll_bin)]).stdout)

    if c_results != ll_results:
        print("Falha: saídas divergentes entre C e LLVM.", file=sys.stderr)
        print("C:", c_results, file=sys.stderr)
        print("LLVM:", ll_results, file=sys.stderr)
        raise SystemExit(1)

    print("Validação concluída: saídas idênticas para todas as funções.")


if __name__ == "__main__":
    main()
