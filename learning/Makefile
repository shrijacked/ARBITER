# Makefile for the Jev learning book.
# Engine: Tectonic (XeTeX). Bibliography: BibTeX + natbib (Tectonic runs bibtex automatically).
# The first build downloads packages from the Tectonic bundle and needs network access.

TECTONIC ?= tectonic
SRC      := main.tex
BUILD    := build
MASTER   := jev-learning-master.pdf
PDF      := $(BUILD)/main.pdf

.PHONY: pdf verify clean pages

pdf:
	@mkdir -p $(BUILD)
	$(TECTONIC) $(SRC) --outdir $(BUILD) --keep-logs --keep-intermediates
	cp $(PDF) $(MASTER)
	@echo "Master PDF updated: $(MASTER)"

# verify: build, then fail on LaTeX errors / undefined refs / undefined citations,
# grep the extracted text for '??', print the page count, and render every page.
verify: pdf
	@echo "=== log checks ==="
	@if grep -nE "Undefined control sequence|Undefined reference|Citation .* undefined|LaTeX Error|Runaway argument|! " $(BUILD)/main.log; then \
		echo "FAIL: LaTeX errors or undefined refs/citations found in the log"; exit 1; \
	else echo "OK: no LaTeX errors or undefined refs/citations in the log"; fi
	@echo "=== '??' check (unresolved cross-refs in the rendered PDF) ==="
	@if pdftotext $(MASTER) - | grep -n "??" ; then \
		echo "FAIL: found '??' in the rendered PDF (unresolved reference)"; exit 1; \
	else echo "OK: no '??' in the rendered text"; fi
	@echo "=== page count ==="
	@pdfinfo $(MASTER) | grep -E "^Pages:"
	@$(MAKE) pages
	@echo "=== self-check coverage (every Check-yourself has an appendix answer) ==="
	@qn=$$(grep -rho "begin{checkbox}" chapters/*.tex | wc -l | tr -d ' '); \
	 an=$$(grep -o "answitem" chapters/A3_answers.tex 2>/dev/null | wc -l | tr -d ' '); \
	 echo "Check-yourself boxes: $$qn ; appendix answers: $$an"; \
	 if [ "$$an" -lt "$$qn" ]; then echo "WARN: fewer answers than check-yourself boxes"; fi
	@echo "VERIFY OK"

# Render every page to PNG so figures/layout can be visually inspected.
pages: pdf
	@mkdir -p $(BUILD)/pages
	@pdftoppm -png -r 110 $(MASTER) $(BUILD)/pages/page >/dev/null 2>&1 || true
	@echo "Rendered pages to $(BUILD)/pages/ ($$(ls $(BUILD)/pages/*.png 2>/dev/null | wc -l | tr -d ' ') files)"

clean:
	rm -rf $(BUILD)
