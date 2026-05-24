# QUICKSTART: Rodar testes C vs LLVM e gerar `report.html`

Este quickstart cria **um comando único** que:

1. compila o `austral`;
2. compila o mesmo código para C e para LLVM;
3. executa os testes primeiro no fluxo C e depois no fluxo LLVM;
4. gera o relatório final `report.html`.

## Comando único

```bash
bash LLVM_validator/run_c_llvm_tests.sh
```

## O que o comando faz internamente

- `make austral` (build do compilador)
- compila `examples/llvm_linear_api/linear_token_api.c` para binário C
- gera `.ll` com `clang -S -emit-llvm` e compila binário LLVM
- executa `make validate arquivo_em_c arquivo_em_LLVM`
- executa stress + benchmark (`stress_benchmark/run_stress_benchmark.py`)
- gera `LLVM_validator/stress_benchmark/report.html`

## Saídas principais

- `LLVM_validator/LLVM_validator.json`
- `LLVM_validator/stress_benchmark/stress_test.json`
- `LLVM_validator/stress_benchmark/benchmark_test.json`
- `LLVM_validator/stress_benchmark/tests_report.html`
- `LLVM_validator/stress_benchmark/report.html` ✅

## Requisitos

- `dune`
- `cc`
- `clang`
- `python3`
- `make`
