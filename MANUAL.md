# Manual de Uso y Referencia Técnica: drake

> **DRAKE** — Fuzzer pedagógico guiado por límites y analizador de cobertura dinámica en C
> **Versión:** `0.1.0` · **CLI principal:** `drake` · **Plugin Ripley:** `fuzzing`

---

## 1. Arquitectura y Propósito Pedagógico

`drake` forma parte del ecosistema de herramientas de la cátedra de Programación 1 (UNRN). Su objetivo central es resolver de forma modular, determinista y automatizada las tareas asociadas a su dominio específico dentro del ciclo de desarrollo, evaluación y aprendizaje de software en C.

### Alcance Funcional (Qué cubre)
- Fuzzing pedagógico dirigido por límites numéricos y tipos de datos en programas C.
- Inyección automatizada de vectores de prueba con valores extremos (`INT_MAX`, `INT_MIN`, `UINT_MAX`, `0`, cadenas vacías, cadenas gigantes, caracteres no ASCII).
- Detección de caídas prematuras por segfault, desbordamientos de búfer en terminal y bucles infinitos.
- Emisión de reportes con entradas reproducibles mínimas para depuración.

### Límites de Responsabilidad y Delegación (Qué no cubre)
- Aislamiento del proceso con namespaces y cgroups (delegado a `nostromo`).
- Diagnóstico forense detallado del core dump con GDB (delegado a `hal`).

### Principios de Diseño
- **Enfoque Pedagógico:** Diagnósticos y mensajes en español rioplatense orientados a facilitar la comprensión de errores conceptuales.
- **Salida Estructurada Dual:** Soporte nativo para visualización enriquecida en terminal (Rich) y salida parseable para orquestadores (`--json`).
- **Integración Contractual:** Capacidad de emitir secciones de reporte para `dredd` (`dredd-section`) y actuar como satélite orquestado por `ripley`.
- **Idempotencia y Robustez:** Validación de precondiciones y comandos de autodiagnóstico (`doctor`) para verificación del entorno.

---

## 2. Instalación y Requisitos

### Requisitos del Sistema
- **Python:** `>= 3.10` (recomendado Python 3.11 o 3.12).
- **Gestor de paquetes:** [`uv`](https://github.com/astral-sh/uv) (entorno estándar de cátedra).
- **Toolchain C (si aplica):** GCC / Clang, Make, GDB y bibliotecas estándar de desarrollo.

### Instalación en el Entorno de Usuario
Para instalar la herramienta de forma global y aislada en el sistema mediante `uv tool`:
```bash
uv tool install --editable /home/mrtin/dev/tools/drake
```

### Verificación de Instalación
Ejecutá el comando `doctor` para constatar que todas las dependencias y binarios requeridos estén presentes y operativos:
```bash
drake doctor
```

---

## 3. Guía Integral de Comandos (CLI)

| Comando | Descripción Breve |
| :--- | :--- |
| [`drake check`](#check) | Ejecuta fuzzing enviando payloads extremos y mutados a la entrada estándar. |
| [`drake fuzz`](#fuzz) | Ejecuta fuzzing enviando payloads extremos y mutados a la entrada estándar. |
| [`drake report`](#report) | Genera directamente la sección de reporte Markdown de DRAKE para Dredd. |
| [`drake doctor`](#doctor) | Verifica el estado del entorno de DRAKE (Python, GCC). |

### `drake check`

Ejecuta fuzzing enviando payloads extremos y mutados a la entrada estándar.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `fuente` | `Path` | Archivo C a someter a fuzzing. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--runs`, `-n` | `int` | `50` | Cantidad de ejecuciones con mutaciones. |
| `--timeout`, `-t` | `float` | `1.0` | Timeout máximo por corrida en segundos. |
| `--seed`, `-s` | `Optional[int]` | `None` | Semilla para reproducir una campaña exacta (por defecto al azar; se informa en el reporte). |
| `--json` | `bool` | `False` | Salida estructurada en JSON. |
| `--md`, `--output-md`, `-o` | `Optional[Path]` | `None` | Generar sección de reporte en formato Markdown para fusión en Dredd. |

#### Ejemplo de Invocación
```bash
drake check <fuente>
```

### `drake fuzz`

Ejecuta fuzzing enviando payloads extremos y mutados a la entrada estándar.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `fuente` | `Path` | Archivo C a someter a fuzzing. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--runs`, `-n` | `int` | `50` | Cantidad de ejecuciones con mutaciones. |
| `--timeout`, `-t` | `float` | `1.0` | Timeout máximo por corrida en segundos. |
| `--seed`, `-s` | `Optional[int]` | `None` | Semilla para reproducir una campaña exacta (por defecto al azar; se informa en el reporte). |
| `--json` | `bool` | `False` | Salida estructurada en JSON. |
| `--md`, `--output-md`, `-o` | `Optional[Path]` | `None` | Generar sección de reporte en formato Markdown para fusión en Dredd. |

#### Ejemplo de Invocación
```bash
drake fuzz <fuente>
```

### `drake report`

Genera directamente la sección de reporte Markdown de DRAKE para Dredd.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `fuente` | `Path` | Archivo C a someter a fuzzing. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--output`, `-o` | `Optional[Path]` | `None` | Ruta de destino del archivo Markdown. |
| `--runs`, `-n` | `int` | `50` | Cantidad de ejecuciones con mutaciones. |
| `--seed`, `-s` | `Optional[int]` | `None` | Semilla para reproducir una campaña exacta. |

#### Ejemplo de Invocación
```bash
drake report <fuente>
```

### `drake doctor`

Verifica el estado del entorno de DRAKE (Python, GCC).

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--json` | `bool` | `False` | Emitir diagnóstico en formato JSON estructurado. |

#### Ejemplo de Invocación
```bash
drake doctor
```

---

## 4. Formatos de Salida e Integración con el Ecosistema

### Modo Interactivo / Terminal (Rich)
Por defecto, la herramienta renderiza paneles, árboles y tablas estilizadas para facilitar la lectura del estudiante y docente en terminales modernas con soporte ANSI.

### Modo Estructurado JSON (`--json`)
Para integración con pipelines de CI/CD, scripts de automatización u orquestadores externos, la opción `--json` emite un documento JSON estricto por la salida estándar (`stdout`), dirigiendo cualquier mensaje de logging a `stderr`:
```bash
drake check --json
```

### Integración con Dredd (`dredd-section`)
Cuando la herramienta genera reportes de evaluación para entregas de alumnos, produce una sección Markdown estandarizada conforme al contrato de integración de Dredd (v1.0.0):
```markdown
<!-- dredd-section: drake, tool=drake, version=0.1.0, status=ok -->
```
Este encabezado garantiza la agregación determinista de los hallazgos en la rúbrica docente.

### Integración con Ripley
`drake` está registrada en el catálogo de plugins satélites de Ripley (`SATELLITE_CATALOG`). Puede invocarse directamente a través del motor de evaluación de Ripley configurando el análisis en `ripley.toml`.

---

## 5. Diagnóstico y Códigos de Salida

### Códigos de Retorno (`exit code`)
| Código | Significado |
| :---: | :--- |
| `0` | Ejecución exitosa sin hallazgos críticos ni errores de sintaxis. |
| `1` | Hallazgos pedagógicos detectados, infracción de reglas o advertencias activas. |
| `2` | Error de sintaxis en argumentos CLI o archivo fuente no encontrado. |
| `>2` | Error no recuperable del sistema, fallo de memoria o excepción interna. |

### Diagnóstico del Entorno (`doctor`)
Ante comportamientos inesperados, verificá el estado operativo con:
```bash
drake doctor
```
Comprueba la presencia de las dependencias requeridas y la integridad de los componentes del paquete.