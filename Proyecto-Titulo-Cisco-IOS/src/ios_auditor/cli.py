from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from ios_auditor.services.analyzer import AnalysisError, analyze_file
from ios_auditor.services.serialization import to_primitive


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ios_auditor",
        description="Analizador offline de archivos running-config de Cisco IOS.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze_parser = subparsers.add_parser("analyze", help="Analiza un archivo local.")
    analyze_parser.add_argument("path", help="Ruta del archivo running-config en UTF-8.")
    analyze_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Formatea la salida JSON con indentación.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        result = analyze_file(args.path)
    except AnalysisError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    indent = 2 if args.pretty else None
    print(json.dumps(to_primitive(result), ensure_ascii=False, indent=indent))
    return 0
