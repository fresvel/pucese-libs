#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$SCRIPT_DIR}"
LATEX_DIR="${LATEX_DIR:-$PROJECT_ROOT/Latex}"
CONTENT_DIR="${CONTENT_DIR:-$LATEX_DIR/Contenido}"
MAIN_TEX="${MAIN_TEX:-$LATEX_DIR/main.tex}"
OUT_DIR="${OUT_DIR:-$PROJECT_ROOT/out}"
BUILD_DIR="$OUT_DIR/build"
LOG_DIR="$OUT_DIR/logs"
PDF_DIR="$OUT_DIR/pdfs"

mkdir -p "$BUILD_DIR" "$LOG_DIR" "$PDF_DIR"

if [[ ! -f "$MAIN_TEX" ]]; then
  echo "No se encontró el archivo principal de LaTeX: $MAIN_TEX" >&2
  exit 1
fi

compile_variant() {
  local variant="$1"
  local content_src="$CONTENT_DIR/Content_${variant}.tex"
  local content_target="$CONTENT_DIR/Content.tex"
  local variant_build="$BUILD_DIR/$variant"
  local log_file="$LOG_DIR/${variant}.log"
  local base_name
  base_name="$(basename "$MAIN_TEX" .tex)"

  if [[ ! -f "$content_src" ]]; then
    echo "No se encontró la entrada de tablas para '$variant': $content_src" >&2
    exit 1
  fi

  mkdir -p "$variant_build"
  cp "$content_src" "$content_target"

  if command -v latexmk >/dev/null 2>&1; then
    latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error \
      -outdir="$variant_build" "$MAIN_TEX" >"$log_file" 2>&1
  else
    pdflatex -interaction=nonstopmode -halt-on-error -file-line-error \
      -output-directory="$variant_build" "$MAIN_TEX" >"$log_file" 2>&1
    pdflatex -interaction=nonstopmode -halt-on-error -file-line-error \
      -output-directory="$variant_build" "$MAIN_TEX" >>"$log_file" 2>&1
  fi

  if [[ ! -f "$variant_build/$base_name.pdf" ]]; then
    echo "No se generó el PDF esperado para '$variant'. Revisa: $log_file" >&2
    exit 1
  fi

  cp "$variant_build/$base_name.pdf" "$PDF_DIR/${variant}.pdf"
  echo "Generado: $PDF_DIR/${variant}.pdf"
}

compile_variant "docentes"
compile_variant "niveles"
compile_variant "nrcs"

echo "Compilación finalizada."
echo "PDFs: $PDF_DIR"
echo "Logs: $LOG_DIR"
