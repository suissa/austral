# HASUM parallel + LinearAutoDestroy (experimental)

Este repositório agora inclui um fluxo experimental `.hasum` compilado com Haskell.

## Sintaxe

- Prefixo `parallel` antes da função:

```hasum
parallel heavy(x: Int): Int = x * x
```

- Declaração externa estilo Gleam/Erlang (não compila localmente, apenas assinatura):

```hasum
extern tokenApiCall(payload: Text): Text
```

- Paralelização de coleção com `benchmarkMap` (traduz para `parMap rdeepseq`):

```hasum
benchmarkMap heavy [1,2,3]
```

- Tipo `LinearAutoDestroy` + descarte automático explícito:

```hasum
letToken :: LinearAutoDestroy Int
letToken = LinearAutoDestroy 10
autodestroy letToken
```

Após `autodestroy`, qualquer referência posterior dispara erro em compilação do transpiler.

## Build

`make` agora também procura `hasum/*.hasum` e compila usando:

- `ghc -threaded`

Para executar usando todos os núcleos:

```bash
./hasum/parallel_demo +RTS -N
```

Ou fixando 4 núcleos:

```bash
./hasum/parallel_demo +RTS -N4
```
