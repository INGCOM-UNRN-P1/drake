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


def generar_seccion_markdown(reporte) -> str:
    """Genera sección de auditoría de robustez y fuzzing para Dredd."""
    lines = [
        "<!-- dredd-section: drake v1.0.0 -->\n",
        "## Robustez y Fuzzing de Límites (Drake)\n",
    ]
    lines.append(f"- **Archivo analizado:** `{reporte.archivo.name}`")
    lines.append(f"- **Ejecuciones de prueba:** {reporte.total_ejecuciones}")
    lines.append(f"- **Fallos / Crashes detectados:** {reporte.total_crashes}\n")
    if reporte.ok:
        lines.append("> [!TIP]\n> **Robustez Verificada:** El programa resistió todas las entradas extremas (INT_MAX, overflows, strings largos, null bytes) sin colapsar.\n")
    else:
        lines.append("> [!WARNING]\n> **Vulnerabilidad de Robustez:** El programa cayó en crashes ante payloads límite.\n")
        lines.append("| Run # | Señal / Diagnóstico | Tiempo | Payload de Entrada |")
        lines.append("| :---: | :--- | :---: | :--- |")
        for c in reporte.crashes[:10]:
            diag_limpio = (c.senal_error or "CRASH").replace("|", "&#124;")
            payload_str = repr(c.payload_input[:30]).replace("|", "&#124;")
            lines.append(f"| {c.id_caso} | **{diag_limpio}** | {c.tiempo_ms:.1f} ms | `{payload_str}` |")
        lines.append("")
    return "\n".join(lines)


@app.command("fuzz")
@app.command("check")
def fuzz_cmd(
    fuente: Path = typer.Argument(..., help="Archivo C a someter a fuzzing."),
    runs: int = typer.Option(50, "--runs", "-n", help="Cantidad de ejecuciones con mutaciones."),
    timeout: float = typer.Option(1.0, "--timeout", "-t", help="Timeout máximo por corrida en segundos."),
    json_output: bool = typer.Option(False, "--json", help="Salida estructurada en JSON."),
    output_md: Optional[Path] = typer.Option(None, "--md", "--output-md", "-o", help="Generar sección de reporte en formato Markdown para fusión en Dredd."),
) -> None:
    """Ejecuta fuzzing enviando payloads extremos y mutados a la entrada estándar."""
    if not fuente.is_file():
        err_console.print(f"[red]Error:[/red] No se encontró el archivo '{fuente}'.")
        raise typer.Exit(code=2)

    reporte = ejecutar_fuzzing(fuente, total_runs=runs, timeout_por_run=timeout)

    if output_md:
        md_text = generar_seccion_markdown(reporte)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(md_text, encoding="utf-8")
        console.print(f"[green]✓ Sección Markdown generada en:[/green] [cyan]{output_md}[/cyan]")
        raise typer.Exit(code=0 if reporte.ok else 1)

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


@app.command("report")
def report_cmd(
    fuente: Path = typer.Argument(..., help="Archivo C a someter a fuzzing."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Ruta de destino del archivo Markdown."),
    runs: int = typer.Option(50, "--runs", "-n", help="Cantidad de ejecuciones con mutaciones."),
) -> None:
    """Genera directamente la sección de reporte Markdown de DRAKE para Dredd."""
    if not fuente.is_file():
        err_console.print(f"[red]Error:[/red] No se encontró el archivo '{fuente}'.")
        raise typer.Exit(code=2)
    reporte = ejecutar_fuzzing(fuente, total_runs=runs)
    md_content = generar_seccion_markdown(reporte)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(md_content, encoding="utf-8")
        console.print(f"[green]✓ Reporte Markdown generado en:[/green] [cyan]{output}[/cyan]")
    else:
        print(md_content)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
