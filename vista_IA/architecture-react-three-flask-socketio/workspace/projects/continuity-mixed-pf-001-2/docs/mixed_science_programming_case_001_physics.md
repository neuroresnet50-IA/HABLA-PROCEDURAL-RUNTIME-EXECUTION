# Caso 001: caida libre desde reposo

- task_id: RUNTIME-20260602202938-001
- expected_file: docs/mixed_science_programming_case_001_physics.md
- materialized_at: 2026-06-02T20:30:08Z

## Problema

Un objeto se suelta desde el reposo a una altura `h = 20 m` sobre el suelo. Se desprecia la resistencia del aire y se toma `g = 9.8 m/s^2`. Calcular la rapidez justo antes de tocar el suelo usando dos caminos: conservacion de energia y ecuaciones cinematicas.

## Supuestos

- El objeto parte del reposo: `v0 = 0`.
- La aceleracion gravitacional es constante: `g = 9.8 m/s^2`.
- No hay perdidas por rozamiento ni resistencia del aire.
- El suelo se toma como referencia de energia potencial cero.

## Metodo 1: conservacion de energia

La energia potencial gravitatoria inicial se transforma en energia cinetica final:

```text
m g h = (1/2) m v^2
```

La masa aparece en ambos lados y se cancela:

```text
g h = v^2 / 2
v = sqrt(2 g h)
```

Sustituyendo valores:

```text
v = sqrt(2 * 9.8 m/s^2 * 20 m)
v = sqrt(392 m^2/s^2)
v = 19.8 m/s
```

## Metodo 2: cinematica

Para movimiento uniformemente acelerado:

```text
v^2 = v0^2 + 2 a Delta y
```

Como el objeto parte del reposo y cae una distancia `h`, se usa `a = g` y `Delta y = h` en magnitud:

```text
v^2 = 0 + 2 g h
v = sqrt(2 g h)
v = 19.8 m/s
```

## Verificacion dimensional

```text
2 g h -> (m/s^2) * m = m^2/s^2
sqrt(m^2/s^2) = m/s
```

La unidad final corresponde a rapidez, por lo que la expresion es dimensionalmente consistente.

## Conclusion

Ambos metodos dan el mismo resultado porque describen el mismo fenomeno desde perspectivas equivalentes: energia mecanica conservada y aceleracion constante. La rapidez justo antes del impacto es aproximadamente `19.8 m/s`, dirigida hacia abajo.
