BIN := austral
SRC := lib/*.ml lib/*.mli lib/*.mll lib/*.mly lib/dune bin/dune bin/austral.ml lib/BuiltInModules.ml
PREFIX ?= /usr/local

.PHONY: all
all: $(BIN) hasum

lib/BuiltInModules.ml: lib/builtin/*.aui lib/builtin/*.aum lib/prelude.h lib/prelude.c
	python3 concat_builtins.py

$(BIN): $(SRC)
	dune build
	cp _build/default/bin/austral.exe $(BIN)

.PHONY: test
test: $(BIN)
	dune runtest

.PHONY: install
install: $(BIN)
	install -D -m 755 austral $(PREFIX)/bin/austral

.PHONY: uninstall
uninstall:
	sudo rm $(PREFIX)/bin/austral

.PHONY: clean
clean:
	rm -f $(BIN); rm -rf _build; rm -f lib/BuiltInModules.ml; rm -f hasum/*.hs hasum/parallel_demo

HASUM_FILES := $(wildcard hasum/*.hasum)

.PHONY: hasum
hasum:
	@if [ -n "$(HASUM_FILES)" ]; then \
	  if command -v ghc >/dev/null 2>&1; then \
	    python3 tools/hasum_compiler.py $(HASUM_FILES); \
	  else \
	    echo "warning: ghc not found; skipping .hasum compilation"; \
	  fi; \
	else \
	  echo "no .hasum files found"; \
	fi
