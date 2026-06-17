# LLVM Quickstart (Austral)

Este guia mostra como compilar código Austral para **LLVM IR** (`.ll`) e como validar a equivalência entre a saída em C e em LLVM.

## Pré-requisitos

- `austral` (binário do compilador)
- `clang`
- `cc` (gcc/clang como compilador C)
- `python3`
- `make`

## 1) Compilar um programa Austral para C

Exemplo (ajuste os caminhos conforme seu módulo):

```bash
austral compile \
  --target-type=c \
  --output /tmp/programa.c \
  --entrypoint Main:main \
  interface.aui,body.aum
```

Se seu módulo não usa interface separada:

```bash
austral compile \
  --target-type=c \
  --output /tmp/programa.c \
  --entrypoint Main:main \
  body.aum
```

## 2) Compilar o mesmo programa para LLVM IR

Use o novo target `llvm`:

```bash
austral compile \
  --target-type=llvm \
  --output /tmp/programa.ll \
  --entrypoint Main:main \
  interface.aui,body.aum
```

Ou, sem arquivo de interface:

```bash
austral compile \
  --target-type=llvm \
  --output /tmp/programa.ll \
  --entrypoint Main:main \
  body.aum
```

> Observação: nesta implementação, o alvo LLVM é gerado via pipeline C (Austral -> C -> LLVM IR com `clang -S -emit-llvm`).

## 3) Validar C vs LLVM

Entre na pasta do validador e execute exatamente como solicitado:

```bash
cd LLVM_validator
make
make validate /tmp/programa.c /tmp/programa.ll
```

### O que o validador faz

1. Lê o arquivo C e encontra funções no formato `int nome(void)`.
2. Executa essas funções no binário compilado a partir do C.
3. Salva os resultados em `LLVM_validator.json`.
4. Executa os mesmos testes usando o `.ll`.
5. Compara as saídas função por função.

Se houver divergência, o comando falha com erro.

## 4) Modo biblioteca (sem entrypoint)

Para gerar artefatos sem `main`, use `--no-entrypoint`:

```bash
austral compile --target-type=c    --output /tmp/lib.c  --no-entrypoint body.aum
austral compile --target-type=llvm --output /tmp/lib.ll --no-entrypoint body.aum
```

## 5) Dicas rápidas

- Se `clang` não estiver instalado, a geração de `.ll` falha.
- O validador atual compara funções `int fn(void)`; outras assinaturas não entram na comparação.
- Para depuração, abra o arquivo `/tmp/programa.ll` diretamente.
