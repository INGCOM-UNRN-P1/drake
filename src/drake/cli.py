"""CLI de DRAKE — Fuzzer pedagógico y análisis de límites en C."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from drake import __version__
from drake.core.fuzzer import ejecutar_fuzzing

console = Console()
err_console = Console(stderr=True)

app = typer.Typer(
    name="drake",
    help="⚡ DRAKE — Fuzzer pedagógico guiado por límites y analizador de robustez en C.",
    add_completion=True,
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold cyan]DRAKE[/bold cyan] versión [bold]{__version__}[/bold]")
        raise typer.Exit(code=0)


@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Muestra la versión de DRAKE.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    pass


@app.command("fuzz")
def fuzz_cmd(
    fuente: Path = typer.Argument(..., help="Archivo C a someter a fuzzing."),
    runs: int = typer.Option(50, "--runs", "-n", help="Cantidad de ejecuciones con mutaciones."),
    timeout: float = typer.Option(1.0, "--timeout", "-t", help="Timeout máximo por corrida en segundos."),
    json_output: bool = typer.Option(False, "--json", help="Salida estructurada en JSON."),
) -> None:
    """Ejecuta fuzzing enviando payloads extremos y mutados a la entrada estándar."""
    if not fuente.is_file():
        err_console.print(f"[red]Error:[/red] No se encontró el archivo '{fuente}'.")
        raise typer.Exit(code=2)

    reporte = ejecutar_fuzzing(fuente, total_runs=runs, timeout_por_run=timeout)

    if json_output:
        print(json.dumps(reporte.to_dict(), indent=2, ensure_ascii=False))
        raise typer.Exit(code=0 if reporte.ok else 1)

    if reporte.ok:
        console.print(Panel(
            f"[bold green]✓ Fuzzing completado exitosamente sin fallos ({reporte.total_ejecuciones} ejecuciones).[/bold green]\n"
            "El programa manejó robustamente todas las entradas límite y valores extremos.",
            title="DRAKE Robustness OK",
            border_style="green",
        ))
        raise typer.Exit(code=0)

    console.print(f"\n[bold red]💥 Se detectaron {reporte.total_crashes} fallos durante el fuzzing:[/bold red]\n")

    tabla = Table(title=f"Crashes Detectados por Fuzzing en {fuente.name}")
    tabla.add_column("# Run", justify="center")
    tabla.add_column("Señal / Fallo", style="bold red")
    tabla.add_column("Tiempo", justify="right")
    tabla.add_column("Payload de Entrada (repr)", style="yellow")

    for c in reporte.crashes[:10]:
        tabla.add_row(
            str(c.id_caso),
            c.senal_error or "CRASH",
            f"{c.tiempo_ms:.1f} ms",
            repr(c.payload_input[:40]),
        )

    console.print(tabla)
    raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
