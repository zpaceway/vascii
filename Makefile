# vascii skill installer — OpenCode + Claude Code
#
#   make install            install skill for current user (OpenCode + Claude)
#   make install-opencode   install to OpenCode user skills
#   make install-claude     install to Claude Code user skills
#   make install-deps       pip install light-flavor requirements
#   make install-full-deps  pip install full-flavor requirements (torch stack, ~2GB)
#   make check              run the skill's dependency check
#   make smoke              determinism smoke test (same input twice)
#   make uninstall          remove user-level installs
#   make help               this list
#
# Override destinations, e.g.:
#   make install OPENCODE_SKILLS=/tmp/oc-skills CLAUDE_SKILLS=/tmp/cl-skills
#   make install PREFIX=$HOME/.local/share/vascii   (staged layout)

SKILL        := skills/vascii
OPENCODE_SKILLS ?= $(HOME)/.config/opencode/skills
CLAUDE_SKILLS   ?= $(HOME)/.claude/skills
PYTHON       ?= python3
PIP          ?= pip

.PHONY: help install install-opencode install-claude install-deps install-full-deps check smoke uninstall uninstall-opencode uninstall-claude

help:
	@grep -E '^[a-z-]+ *:' $(MAKEFILE_LIST) | sed 's/:.* supplemental.*//'

install: install-opencode install-claude

install-opencode:
	mkdir -p "$(OPENCODE_SKILLS)"
	cp -r "$(SKILL)" "$(OPENCODE_SKILLS)/vascii"
	@echo "vascii skill installed to $(OPENCODE_SKILLS)/vascii"

install-claude:
	mkdir -p "$(CLAUDE_SKILLS)"
	cp -r "$(SKILL)" "$(CLAUDE_SKILLS)/vascii"
	@echo "vascii skill installed to $(CLAUDE_SKILLS)/vascii"

install-deps:
	$(PIP) install -r "$(SKILL)/requirements.txt"

install-full-deps:
	$(PIP) install -r "$(SKILL)/requirements-full.txt"

check:
	$(PYTHON) "$(SKILL)/scripts/check.py"

smoke:
	$(PYTHON) "$(SKILL)/scripts/img2ascii.py" --mode auto eval/dataset/fixtures/images.jpeg | sha256sum > /tmp/vascii_smoke_a
	$(PYTHON) "$(SKILL)/scripts/img2ascii.py" --mode auto eval/dataset/fixtures/images.jpeg | sha256sum > /tmp/vascii_smoke_b
	cmp /tmp/vascii_smoke_a /tmp/vascii_smoke_b && echo "SMOKE_OK deterministic"

uninstall: uninstall-opencode uninstall-claude

uninstall-opencode:
	rm -rf "$(OPENCODE_SKILLS)/vascii"

uninstall-claude:
	rm -rf "$(CLAUDE_SKILLS)/vascii"
