# Guía LACE Visual V5.1

Esta versión convierte el diagrama de LACE en documentación navegable y en modelo interno auditable.

## Archivos principales

```text
docs/visual/lace_system_diagram.html
    Diagrama visual del sistema LACE: arranque, ciclos, puerta y cierre.

docs/visual/lace_md_execution_explained.html
    Explicación visual de cómo un agente lee LACE.md y lo convierte en contexto operativo.

runtime/lace.py
    Política ejecutable, parser de ciclos, puerta de cierre y registro de ciclos.

runtime/lace_visual_cli.py
    CLI para imprimir el modelo visual de LACE desde terminal.
```

## Cómo abrir el diagrama

```bash
bash scripts/open_lace_visual.sh
```

O manualmente:

```bash
xdg-open docs/visual/lace_system_diagram.html
```

## Cómo inspeccionar el estado LACE en terminal

```bash
python -m runtime.lace_visual_cli --lace LACE.md --log LACE_LOG.md
```

## Cómo inicializar un proyecto con LACE

```bash
python -m runtime.lace_cli "Crear un juego en Python" --scaffold
```

Esto:

1. Lee `LACE.md`.
2. Valida que existan las 10 capas HABLA.
3. Crea `LACE_LOG.md`.
4. Inyecta directiva LACE al agente.
5. Prepara plantillas de ciclos sin fingir que ya se ejecutaron.

## Regla clave

El cierre no depende de decir “terminé”. Depende de que `LACE_LOG.md` contenga ciclos reales marcados como:

```text
¿El proyecto mejoró objetivamente? SI
```

La puerta de cierre usa ese registro como evidencia.
