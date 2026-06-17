#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

MODULE_SRC="examples/llvm_linear_api/linear_token_api.c"
OUT_DIR="LLVM_validator/out"
mkdir -p "$OUT_DIR"

printf '[1/6] Build austral compiler\n'
make austral

printf '[2/6] Build reference C module\n'
cc "$MODULE_SRC" -O3 -o "$OUT_DIR/linear_api_c"

printf '[3/6] Build LLVM artifacts from same code\n'
clang -S -emit-llvm "$MODULE_SRC" -O3 -o "$OUT_DIR/linear_api.ll"
clang "$OUT_DIR/linear_api.ll" -O3 -o "$OUT_DIR/linear_api_llvm"

printf '[4/6] Run function-equivalence validator (C -> LLVM)\n'
cd LLVM_validator
make validate "$ROOT_DIR/$MODULE_SRC" "$ROOT_DIR/$OUT_DIR/linear_api.ll"

printf '[5/6] Run stress + benchmark on C and LLVM\n'
python3 stress_benchmark/run_stress_benchmark.py

printf '[6/6] Aggregate report.html\n'
python3 - <<'PY'
import json
from pathlib import Path
base=Path('stress_benchmark')
stress=json.loads((base/'stress_test.json').read_text())
bench=json.loads((base/'benchmark_test.json').read_text())
html=(base/'tests_report.html').read_text()
summary=f"""
<div style='font-family:system-ui;padding:12px;background:#0f172a;color:#e2e8f0;border-radius:8px;margin-bottom:12px'>
  <h2 style='margin:0 0 8px'>Quick Summary</h2>
  <div>Stress stages C: {len(stress.get('c',[]))} | LLVM: {len(stress.get('llvm',[]))}</div>
  <div>Bench avg latency ms - C: {bench['summary']['c_avg_ms']:.3f} | LLVM: {bench['summary']['llvm_avg_ms']:.3f}</div>
</div>
"""
(base/'report.html').write_text(html.replace("<h1 class='text-2xl font-bold mb-4'>Stress & Benchmark Report</h1>","<h1 class='text-2xl font-bold mb-4'>Stress & Benchmark Report</h1>"+summary))
print('Generated LLVM_validator/stress_benchmark/report.html')
PY

printf '\nDone. Open: LLVM_validator/stress_benchmark/report.html\n'
