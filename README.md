# ⚡ DRAKE — Fuzzer Pedagógico y Analizador de Límites en C

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
