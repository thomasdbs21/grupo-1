"""Comparación reproducible de fixtures locales con expectativas explícitas."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Prioriza el checkout oficial incluso si otro repositorio está instalado editable.
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ios_auditor.domain import RuleStatus
from ios_auditor.services.analyzer import analyze_file
from offline_integral import analyze_synthetic_scenario


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    filename: str
    expected: tuple[tuple[str, RuleStatus], ...]


SCENARIOS = (
    Scenario("seguro", "ESCENARIO A - CONFIGURACIÓN SEGURA", "escenario_seguro.cfg", (
        ("IOS-ADM-001", RuleStatus.PASS),
        ("IOS-SRV-001", RuleStatus.PASS),
        ("IOS-AUTH-001", RuleStatus.PASS),
        ("IOS-ADM-002", RuleStatus.PASS),
        ("IOS-SRV-002", RuleStatus.PASS),
        ("IOS-NTP-001", RuleStatus.PASS),
        ("IOS-LOG-001", RuleStatus.PASS),
        ("IOS-AUTH-002", RuleStatus.PASS),
        ("IOS-ACL-001", RuleStatus.PASS),
        ("IOS-OSPF-001", RuleStatus.PASS),
        ("IOS-SNMP-001", RuleStatus.PASS),
        ("IOS-DOC-001", RuleStatus.PASS),
        ("IOS-AUTH-003", RuleStatus.PASS),
        ("IOS-ADM-003", RuleStatus.PASS),
    )),
    Scenario("inseguro", "ESCENARIO B - ADMINISTRACIÓN INSEGURA", "escenario_inseguro.cfg", (
        ("IOS-ADM-001", RuleStatus.FAIL),
        ("IOS-SRV-001", RuleStatus.FAIL),
        ("IOS-AUTH-001", RuleStatus.FAIL),
        ("IOS-ADM-002", RuleStatus.FAIL),
        ("IOS-SRV-002", RuleStatus.FAIL),
        ("IOS-NTP-001", RuleStatus.PASS),
        ("IOS-LOG-001", RuleStatus.PASS),
        ("IOS-AUTH-002", RuleStatus.FAIL),
        ("IOS-ACL-001", RuleStatus.FAIL),
        ("IOS-OSPF-001", RuleStatus.FAIL),
        ("IOS-SNMP-001", RuleStatus.FAIL),
        ("IOS-DOC-001", RuleStatus.FAIL),
        ("IOS-AUTH-003", RuleStatus.FAIL),
        ("IOS-ADM-003", RuleStatus.FAIL),
    )),
    Scenario("no-evaluable", "ESCENARIO C - INFORMACIÓN INSUFICIENTE", "escenario_no_evaluable.cfg", (
        ("IOS-ADM-001", RuleStatus.PASS),
        ("IOS-SRV-001", RuleStatus.PASS),
        ("IOS-AUTH-001", RuleStatus.PASS),
        ("IOS-ADM-002", RuleStatus.NOT_EVALUATED),
        ("IOS-SRV-002", RuleStatus.PASS),
        ("IOS-NTP-001", RuleStatus.PASS),
        ("IOS-LOG-001", RuleStatus.PASS),
        ("IOS-AUTH-002", RuleStatus.NOT_EVALUATED),
        ("IOS-ACL-001", RuleStatus.NOT_EVALUATED),
        ("IOS-OSPF-001", RuleStatus.NOT_EVALUATED),
        ("IOS-SNMP-001", RuleStatus.NOT_EVALUATED),
        ("IOS-DOC-001", RuleStatus.PASS),
        ("IOS-AUTH-003", RuleStatus.NOT_EVALUATED),
        ("IOS-ADM-003", RuleStatus.NOT_EVALUATED),
    )),
)


@dataclass(frozen=True)
class Comparison:
    rule_id: str
    expected: RuleStatus | None
    obtained: RuleStatus | None

    @property
    def matches(self) -> bool:
        return self.expected is not None and self.expected == self.obtained


@dataclass(frozen=True)
class ScenarioResult:
    scenario: Scenario
    comparisons: tuple[Comparison, ...]
    findings_match: bool
    order_matches: bool

    @property
    def success(self) -> bool:
        return (
            all(row.matches for row in self.comparisons)
            and self.findings_match
            and self.order_matches
        )


def run_scenario(scenario: Scenario) -> ScenarioResult:
    """Reutiliza el servicio público; no recopila datos ni reimplementa reglas."""
    result = analyze_file(PROJECT_ROOT / "samples" / "evaluacion_2" / scenario.filename)
    obtained = {item.rule_id: item.status for item in result.evaluations}
    if len(obtained) != len(result.evaluations):
        raise ValueError("El análisis devolvió IDs duplicados.")
    expected = dict(scenario.expected)
    if len(expected) != len(scenario.expected):
        raise ValueError("Las expectativas contienen IDs duplicados.")
    rows = tuple(
        Comparison(rule_id, status, obtained.get(rule_id))
        for rule_id, status in scenario.expected
    ) + tuple(
        Comparison(rule_id, None, status)
        for rule_id, status in obtained.items() if rule_id not in expected
    )
    fail_ids = [item.rule_id for item in result.evaluations if item.status == RuleStatus.FAIL]
    finding_ids = [item.rule_id for item in result.findings]
    return ScenarioResult(
        scenario,
        rows,
        Counter(finding_ids) == Counter(fail_ids),
        tuple(obtained) == tuple(expected),
    )


OPERATIONAL_EXPECTATIONS = {
    "seguro": (RuleStatus.PASS,) * 7,
    "inseguro": (RuleStatus.PASS,) + (RuleStatus.FAIL,) * 4 + (RuleStatus.NOT_EVALUATED, RuleStatus.FAIL),
    "no-evaluable": (RuleStatus.PASS,) + (RuleStatus.NOT_EVALUATED,) * 6,
}
OPERATIONAL_IDS = ("IOS-IF-001", "IOS-INT-002", "IOS-ACL-002", "IOS-NTP-002",
                   "IOS-AVL-001", "IOS-OSPF-002", "IOS-INT-001")


def run_integral_scenario(scenario: Scenario) -> ScenarioResult:
    """Comparación integral pública con ocho evidencias sintéticas etiquetadas."""
    result = analyze_synthetic_scenario(PROJECT_ROOT, scenario.filename)
    expected = scenario.expected + tuple(zip(
        OPERATIONAL_IDS, OPERATIONAL_EXPECTATIONS[scenario.key], strict=True))
    expanded = Scenario(scenario.key, scenario.title + " (FUENTES SINTÉTICAS)",
                        scenario.filename, expected)
    observed = {item.rule_id: item.status for item in result.evaluations}
    if len(observed) != len(result.evaluations):
        raise ValueError("El análisis integral devolvió IDs duplicados.")
    rows = tuple(Comparison(rule_id, status, observed.get(rule_id))
                 for rule_id, status in expected) + tuple(
        Comparison(rule_id, None, status) for rule_id, status in observed.items()
        if rule_id not in dict(expected))
    return ScenarioResult(expanded, rows,
                          Counter(item.rule_id for item in result.findings) == Counter(
                              item.rule_id for item in result.evaluations
                              if item.status == RuleStatus.FAIL),
                          tuple(observed) == tuple(rule_id for rule_id, _ in expected))


def calculate_summary(results: tuple[ScenarioResult, ...]) -> dict[str, int]:
    """Cuenta coincidencias observadas, nunca resultados escritos a mano."""
    if not results:
        raise ValueError("Se requiere al menos un escenario.")
    sizes = {len(result.scenario.expected) for result in results}
    if len(sizes) != 1:
        raise ValueError("Los escenarios deben declarar igual cantidad de expectativas.")
    rows = tuple(row for result in results for row in result.comparisons)
    verified = Counter(row.obtained for row in rows if row.matches)
    matches = sum(row.matches for row in rows)
    return {
        "scenarios": len(results),
        "rules_per_scenario": sizes.pop(),
        "comparisons": len(rows),
        "matches": matches,
        "differences": len(rows) - matches,
        "pass": verified[RuleStatus.PASS],
        "fail": verified[RuleStatus.FAIL],
        "not_evaluated": verified[RuleStatus.NOT_EVALUATED],
        "not_applicable": verified[RuleStatus.NOT_APPLICABLE],
        "error": verified[RuleStatus.ERROR],
        "contract_errors": sum(not result.findings_match or not result.order_matches
                               for result in results),
    }


def render_scenario(result: ScenarioResult) -> str:
    lines = ["=" * 76, result.scenario.title, "=" * 76,
             f"{'Regla':<16}{'Esperado':<20}{'Obtenido':<20}Verificación"]
    for row in result.comparisons:
        expected = row.expected.value if row.expected is not None else "NO ESPERADA"
        obtained = row.obtained.value if row.obtained is not None else "AUSENTE"
        lines.append(f"{row.rule_id:<16}{expected:<20}{obtained:<20}"
                     f"{'OK' if row.matches else 'DIFERENCIA'}")
    matched = sum(row.matches for row in result.comparisons)
    lines.extend(("", f"Resultado: {matched}/{len(result.comparisons)} verificaciones coinciden.",
                  f"Orden del registro: {'OK' if result.order_matches else 'DIFERENCIA'}",
                  f"Findings exclusivamente desde FAIL: "
                  f"{'OK' if result.findings_match else 'DIFERENCIA'}"))
    return "\n".join(lines)


def render_summary(results: tuple[ScenarioResult, ...]) -> str:
    summary = calculate_summary(results)
    return "\n".join((
        "=" * 60,
        "EVALUACIÓN 2 - VALIDACIÓN DETERMINISTA",
        "FUENTES SINTÉTICAS - SIN CONEXIÓN SSH",
        "=" * 60,
        f"Escenarios ejecutados: {summary['scenarios']}",
        f"Reglas verificadas por escenario: {summary['rules_per_scenario']}",
        f"Comparaciones totales: {summary['comparisons']}",
        f"Coincidencias esperadas: {summary['matches']}",
        f"Diferencias: {summary['differences']}",
        "",
        f"PASS verificados: {summary['pass']}",
        f"FAIL verificados: {summary['fail']}",
        f"NOT_EVALUATED verificados: {summary['not_evaluated']}",
        f"NOT_APPLICABLE verificados: {summary['not_applicable']}",
        f"ERROR verificados: {summary['error']}",
        f"Errores de contrato (orden/findings): {summary['contract_errors']}",
        "",
        "RESULTADO: " + ("OK" if all(result.success for result in results) else "DIFERENCIA"),
    ))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=[item.key for item in SCENARIOS])
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args(argv)
    if args.scenario and args.summary_only:
        parser.error("--summary-only ejecuta la campaña completa; no combinar con --scenario.")
    selected = tuple(item for item in SCENARIOS if not args.scenario or item.key == args.scenario)
    results = tuple(run_integral_scenario(item) for item in selected)
    if not args.summary_only:
        print("\n\n".join(render_scenario(result) for result in results))
        print()
    print(render_summary(results))
    return 0 if all(result.success for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
