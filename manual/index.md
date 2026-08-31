---
title: "Manual de Referencia: drake"
subtitle: "Drake — Fuzzer Guiado por Límites y Analizador de Robustez ante Entradas Extremas"
author: "Cátedra de Algoritmos y Programación"
date: "2026-08-31"
---

(manual-drake)=
# Drake — Fuzzer Guiado por Límites y Analizador de Robustez ante Entradas Extremas

````{abstract}
**Rol en el ecosistema:** Generación procedural de casos de prueba límite (valores frontera como INT_MAX, INT_MIN, cadenas sin terminador, buffers gigantes) para detectar desbordes y caídas inesperadas en C.
````

---

(manual-drake-proposito)=
## 1. Propósito y Filosofía Pedagógica

La herramienta **`drake`** forma parte del ecosistema oficial de software de la cátedra. Su diseño sigue principios pedagógicos rigurosos:

1. **Evidencia Técnica Directa**: Todo diagnóstico se fundamenta en la norma ISO C (C11/C23), en el modelo de memoria del sistema o en convenciones arquitectónicas formales.
2. **Acción Correctiva Concreta**: Cada advertencia incluye la prescripción técnica inmediata para resolver el defecto sin recurrir a conjeturas.
3. **Autonomía del Estudiante**: Facilita la autoevaluación local antes de la entrega final del trabajo práctico.
4. **Objetividad Docente**: Estandariza la corrección automática eliminando discrepancias subjetivas en la evaluación.

---

(manual-drake-instalacion)=
## 2. Instalación y Diagnóstico del Entorno

````{important}
Asegurate de contar con el compilador GCC/Clang y las librerías del sistema instaladas antes de ejecutar `drake`.
````

Para comprobar el estado de salud de tu entorno de trabajo y las dependencias auxiliares:

````{code-block} bash
# Comprobación de dependencias del sistema
drake doctor
````

Si se detecta la falta de alguna utilidad (como `gdb`, `valgrind`, `clang-format` o `typst`), el comando indicará el paquete exacto a instalar según tu distribución GNU/Linux o entorno MSYS2.

---

(manual-drake-comandos)=
## 3. Referencia Completa de Comandos CLI

A continuación se detallan los subcomandos principales disponibles en `drake`:

| Sintaxis del Comando | Descripción y Efecto |
| :--- | :--- |
| `drake fuzz --binary ./bin/programa` | Ejecuta fuzzing guiado por límites contra la entrada estándar del binario. |
| `drake fuzz --target <archivo.c> --runs 100` | Compila y ejecuta 100 mutaciones de estrés. |
| `drake boundaries --type int` | Lista los valores frontera recomendados para tipos enteros y punteros. |
| `drake doctor` | Verifica la disponibilidad de AFL++ o motor LLVM libFuzzer. |

````{tip}
Podés agregar el flag `--json` a la mayoría de los comandos para exportar resultados en formato estructurado o `--md` para generar reportes Markdown para el informe de entrega.
````

---

(manual-drake-tutorial)=
## 4. Tutorial Paso a Paso con Ejemplos Reales

### Caso de Estudio

Considerá el siguiente fragmento de código representativo:

````{code-block} c
:linenos:
#include <stdio.h>
#include <limits.h>

// Vulnerable a desborde aritmético si a + b supera INT_MAX
int sumar_seguro(int a, int b) {
    if ((b > 0 && a > INT_MAX - b) || (b < 0 && a < INT_MIN - b)) {
        return 0; // Desborde detectado
    }
    return a + b;
}
````

### Ejecución de la Herramienta

Ejecutá el análisis desde tu terminal:

````{code-block} bash
drake fuzz --binary ./bin/programa
````

### Salida Obtenida en Consola

````{code-block} text
[!] DRAKE FUZZER: Ejecutando 50 mutaciones de frontera...
[✓] Test 01: INT_MAX (2147483647) -> PASS (Manejado)
[✓] Test 02: INT_MIN (-2147483648) -> PASS (Manejado)
[✓] Test 03: Cadena de 65536 bytes -> PASS (Sin buffer overrun)
[✓] 50/50 escenarios de estrés superados sin caídas (0 SIGSEGV, 0 SIGFPE).
````

````{note}
Prestá atención a la explicación pedagógica generada: la herramienta no solo señala la línea del problema, sino que explica la causa raíz y el impacto en memoria o arquitectura.
````

---

(manual-drake-ejercicios)=
## 5. Ejercicios Prácticos y Desafíos

Practicá el uso avanzado de **`drake`** resolviendo los siguientes ejercicios:

````{exercise} Desafío 1: Fuzzing de Parser de Números
Ejecutar 50 iteraciones de valores extremos contra `parsear_entero()`.

**Instrucción de ejecución:**
```bash
drake fuzz --binary ./bin/parser_test --runs 50
```
````

````{solution} Desafío 1
```bash
drake fuzz --binary ./bin/parser_test --runs 50
# Verificá que la operación concluya exitosamente con código de salida 0.
```
````

````{exercise} Desafío 2: Detección de División por Cero
Inyectar denominador 0 y desbordes en calculadora aritmética.

**Instrucción de ejecución:**
```bash
drake fuzz --binary ./bin/calc --type math
```
````

````{solution} Desafío 2
```bash
drake fuzz --binary ./bin/calc --type math
# Revisá el archivo generado o el informe en terminal para confirmar la resolución del problema.
```
````

````{exercise} Desafío 3: Validación de Desbordes de String
Alimentar buffers de entrada con cadenas sin byte nulo `\0`.

**Instrucción de ejecución:**
```bash
drake fuzz --binary ./bin/string_app --type string
```
````

````{solution} Desafío 3
```bash
drake fuzz --binary ./bin/string_app --type string
# Comprobá que la salida confirme la ausencia de advertencias o errores pendientes.
```
````

---

(manual-drake-makefile)=
## 6. Integración en el Flujo de Trabajo y Makefile

Para incorporar `drake` de forma automática a tu flujo de desarrollo, agregá la siguiente regla en el `Makefile` de tu proyecto:

````{code-block} makefile
check-drake:
	@echo "=== Ejecutando verificación con drake ==="
	drake check src/ include/

.PHONY: check-drake
````

Ejecutá `make check-drake` antes de cada commit para asegurar que tu código conserve el estado de aprobación.
