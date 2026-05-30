# ==============================================================================
#              MURLI-WORK CLI TEMPLATES DEVELOPMENT MAKEFILE
# ==============================================================================
# This Makefile provides a unified entry point to install dependencies,
# build implementations into a shared ./bin/ directory, and run them.

.PHONY: help install-deps build-all build-go build-go-cobra build-go-urfave \
        build-rust-clap build-zig build-ts build-ts-commander build-ts-yargs build-ts-oclif \
        setup-py-launchers run-go-cobra run-go-urfave run-rust-clap run-zig \
        run-py-click run-py-typer run-py-argparse run-ts-commander \
        run-ts-yargs run-ts-oclif clean

CMD ?= --help

# Default target prints help
help:
	@echo "========================================================================"
	@echo "             MURLI-WORK CLI TEMPLATES DEVELOPMENT MAKEFILE              "
	@echo "========================================================================"
	@echo "Install Targets:"
	@echo "  make install-deps             - Install all dependencies (Go, Python, TypeScript)"
	@echo ""
	@echo "Build Targets (outputs to ./bin/):"
	@echo "  make build-all                - Build all implementations (Go, Rust, TS, Zig)"
	@echo "  make build-go                 - Build both Go implementations"
	@echo "  make build-go-cobra           - Build Go Cobra implementation"
	@echo "  make build-go-urfave          - Build Go urfave/cli implementation"
	@echo "  make build-rust-clap          - Build Rust clap implementation"
	@echo "  make build-zig                - Build Zig clap implementation"
	@echo "  make build-ts                 - Build all TypeScript implementations"
	@echo "  make build-ts-commander       - Build TypeScript commander implementation"
	@echo "  make build-ts-yargs           - Build TypeScript yargs implementation"
	@echo "  make build-ts-oclif           - Build TypeScript oclif implementation"
	@echo "  make build-py                 - Setup Python direct binary launchers in ./bin/"
	@echo ""
	@echo "Run Targets (passes CMD=\"...\" flags, e.g. make run-go-cobra CMD=\"task list\"):"
	@echo "  make run-go-cobra"
	@echo "  make run-go-urfave"
	@echo "  make run-rust-clap"
	@echo "  make run-zig"
	@echo "  make run-py-click"
	@echo "  make run-py-typer"
	@echo "  make run-py-argparse"
	@echo "  make run-ts-commander"
	@echo "  make run-ts-yargs"
	@echo "  make run-ts-oclif"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean                    - Clean bin/ and build directories"
	@echo "========================================================================"

# --- Installation ---
install-deps:
	@echo "==> Resolving Go Cobra dependencies..."
	cd go/cobra && go mod tidy
	@echo "==> Resolving Go urfave/cli dependencies..."
	cd go/urfave && go mod tidy
	@echo "==> Creating Python virtual environment using uv..."
	uv venv
	@echo "==> Installing Python dependencies using uv pip..."
	uv pip install -r python/requirements.txt
	@echo "==> Installing TypeScript dependencies (Commander)..."
	cd typescript/commander && npm install
	@echo "==> Installing TypeScript dependencies (Yargs)..."
	cd typescript/yargs && npm install
	@echo "==> Installing TypeScript dependencies (Oclif)..."
	cd typescript/oclif && npm install
	@echo "==> Done!"

# --- Unified Builds ---
build-all: build-go build-rust-clap build-zig build-ts build-py
	@echo "==> All builds complete. Executables available in ./bin/"

build-go: build-go-cobra build-go-urfave build-go-urfavev3

build-go-cobra:
	@echo "==> Building Go Cobra..."
	mkdir -p bin
	cd go/cobra && go build -o ../../bin/murli-work-go-cobra .

build-go-urfave:
	@echo "==> Building Go urfave/cli..."
	mkdir -p bin
	cd go/urfave && go build -o ../../bin/murli-work-go-urfave .

build-go-urfavev3:
	@echo "==> Building Go urfave/cli v3..."
	mkdir -p bin
	cd go/urfavev3 && go build -o ../../bin/murli-work-go-urfavev3 .

build-rust-clap:
	@echo "==> Building Rust Clap..."
	mkdir -p bin
	cd rust/clap && cargo build --release
	cp rust/clap/target/release/work-clap bin/murli-work-rust-clap

build-zig:
	@echo "==> Building Zig clap..."
	mkdir -p bin
	cd zig && zig build
	cp zig/zig-out/bin/murli-work bin/murli-work-zig

build-ts: build-ts-commander build-ts-yargs build-ts-oclif

build-ts-commander:
	@echo "==> Building TS Commander..."
	mkdir -p bin
	rm -rf typescript/commander/shared
	cp -r typescript/shared typescript/commander/
	cd typescript/commander && [ -d node_modules ] || npm install
	cd typescript/commander && npm run build
	@echo '#!/usr/bin/env node\nrequire("../typescript/commander/dist/index.js")' > bin/murli-work-ts-commander
	chmod +x bin/murli-work-ts-commander

build-ts-yargs:
	@echo "==> Building TS Yargs..."
	mkdir -p bin
	rm -rf typescript/yargs/shared
	cp -r typescript/shared typescript/yargs/
	cd typescript/yargs && [ -d node_modules ] || npm install
	cd typescript/yargs && npm run build
	@echo '#!/usr/bin/env node\nrequire("../typescript/yargs/dist/index.js")' > bin/murli-work-ts-yargs
	chmod +x bin/murli-work-ts-yargs

build-ts-oclif:
	@echo "==> Building TS Oclif..."
	mkdir -p bin
	rm -rf typescript/oclif/src/shared
	cp -r typescript/shared typescript/oclif/src/
	cd typescript/oclif && [ -d node_modules ] || npm install
	cd typescript/oclif && npm run build
	@echo '#!/usr/bin/env node\nrequire("../typescript/oclif/bin/run.js")' > bin/murli-work-ts-oclif
	chmod +x bin/murli-work-ts-oclif

build-py:
	@echo "==> Setting up Python launchers in ./bin/ using uv..."
	mkdir -p bin
	[ -d .venv ] || (uv venv && uv pip install -r python/requirements.txt)
	# Python click launcher
	@echo '#!/usr/bin/env -S uv run python\nimport sys, os\nsys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../python/click")))\nimport main\nif __name__ == "__main__": main.cli()' > bin/murli-work-py-click
	chmod +x bin/murli-work-py-click
	# Python typer launcher
	@echo '#!/usr/bin/env -S uv run python\nimport sys, os\nsys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../python/typer")))\nimport main\nif __name__ == "__main__": main.app()' > bin/murli-work-py-typer
	chmod +x bin/murli-work-py-typer
	# Python argparse launcher
	@echo '#!/usr/bin/env -S uv run python\nimport sys, os\nsys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../python/argparse")))\nimport main\nif __name__ == "__main__": main.main()' > bin/murli-work-py-argparse
	chmod +x bin/murli-work-py-argparse

# --- Running ---
run-go-cobra: build-go-cobra
	@./bin/murli-work-go-cobra $(CMD)

run-go-urfave: build-go-urfave
	@./bin/murli-work-go-urfave $(CMD)

run-rust-clap: build-rust-clap
	@./bin/murli-work-rust-clap $(CMD)

run-zig: build-zig
	@./bin/murli-work-zig $(CMD)

run-py-click: build-py
	@./bin/murli-work-py-click $(CMD)

run-py-typer: build-py
	@./bin/murli-work-py-typer $(CMD)

run-py-argparse: build-py
	@./bin/murli-work-py-argparse $(CMD)

run-ts-commander: build-ts-commander
	@./bin/murli-work-ts-commander $(CMD)

run-ts-yargs: build-ts-yargs
	@./bin/murli-work-ts-yargs $(CMD)

run-ts-oclif: build-ts-oclif
	@./bin/murli-work-ts-oclif $(CMD)

# --- Cleanup ---
clean:
	@echo "==> Cleaning up bin/, venv, and compilation outputs..."
	rm -rf bin .venv
	rm -rf rust/clap/target
	rm -rf zig/zig-out zig/.zig-cache
	rm -rf typescript/commander/dist typescript/commander/node_modules typescript/commander/shared
	rm -rf typescript/yargs/dist typescript/yargs/node_modules typescript/yargs/shared
	rm -rf typescript/oclif/dist typescript/oclif/node_modules typescript/oclif/src/shared
	@echo "==> Clean complete!"
