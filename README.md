# ⚡ DRAKE — Fuzzer Pedagógico y Analizador de Límites en C

> 📖 **Manual de Usuario:** Para una guía exhaustiva de comandos, banderas, arquitectura y ejemplos, consultá el [Manual de Uso](MANUAL.md).

DRAKE es una herramienta de fuzzing liviana que genera entradas con valores límite (`INT_MAX`, `INT_MIN`, cadenas largas, carácteres nulos y mutaciones aleatorias) para poner a prueba la robustez de programas C y detectar segfaults antes de las entregas.

---

## 🎯 Alcance

### Qué cubre
- Fuzzing pedagógico dirigido por límites numéricos y tipos de datos en programas C.
- Inyección automatizada de vectores de prueba con valores extremos (`INT_MAX`, `INT_MIN`, `UINT_MAX`, `0`, cadenas vacías, cadenas gigantes, caracteres no ASCII).
- Detección de caídas prematuras por segfault, desbordamientos de búfer en terminal y bucles infinitos.
- Emisión de reportes con entradas reproducibles mínimas para depuración.

### Qué no cubre (Límites y Delegación)
- Aislamiento del proceso con namespaces y cgroups (delegado a `nostromo`).
- Diagnóstico forense detallado del core dump con GDB (delegado a `hal`).

---

## 📋 Requisitos

### Requisitos de Sistema y Entorno
- Linux / WSL / MSYS2. Python >= 3.10.

### Dependencias Externas y Binarios
- `gcc` o `clang`.

### Integración en el Ecosistema
- CLI `drake`. Plugin en `ripley.plugins` (`fuzzing`).

---

## Uso Rápido

```bash
# 1. Correr 50 iteraciones de fuzzing contra un programa C
drake fuzz main.c --runs 50

# 2. Salida estructurada JSON
drake fuzz main.c --runs 20 --json
```

<!-- p1:referencia:inicio — generado por p1-tools/scripts/readme_generado.py: no editar a mano -->

## Referencia rápida

### Requisitos

- Python ≥ 3.11 y [uv](https://docs.astral.sh/uv/getting-started/installation/).
- Programas del sistema: `gcc`.

| Sistema | `gcc` |
|:--|:--|
| Debian / Ubuntu | `sudo apt install gcc` |
| Fedora | `sudo dnf install gcc` |
| Windows | incluido en el entorno de la cátedra (MSYS2 UCRT64) |
| macOS | `xcode-select --install` (clang como `gcc`) |

### Comandos

| Comando | Descripción |
|:--|:--|
| `drake check`, `drake fuzz` | Ejecuta fuzzing enviando payloads extremos y mutados a la entrada estándar. |
| `drake report` | Genera directamente la sección de reporte Markdown de DRAKE para Dredd. |
| `drake doctor` | Verifica el estado del entorno de DRAKE (Python, GCC). |

Ayuda de cada comando: `drake <comando> -h`.

### Salida JSON

Con `--json`, estos comandos emiten el resultado como JSON por la salida estándar, para usarlo desde scripts, ripley o dredd: `drake check`, `drake fuzz`, `drake doctor`. El de `doctor --json` lleva `schema_version` y `ok`.

### Códigos de salida

| Código | Significado |
|:--|:--|
| `0` | Terminó bien (en `doctor`: está todo lo requerido). |
| `1` | El comando encontró problemas (hallazgos, pruebas que fallan, un umbral que no se alcanza) o un dato no se pudo usar (un archivo ilegible, un formato inválido). |
| `2` | Error de uso: comando, opción o argumento inválido. |

<!-- p1:referencia:fin -->
