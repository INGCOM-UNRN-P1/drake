# ⚡ DRAKE — Fuzzer Pedagógico y Analizador de Límites en C

DRAKE es una herramienta de fuzzing liviana que genera entradas con valores límite (`INT_MAX`, `INT_MIN`, cadenas largas, carácteres nulos y mutaciones aleatorias) para poner a prueba la robustez de programas C y detectar segfaults antes de las entregas.

## Uso Rápido

```bash
# 1. Correr 50 iteraciones de fuzzing contra un programa C
drake fuzz main.c --runs 50

# 2. Salida estructurada JSON
drake fuzz main.c --runs 20 --json
```
