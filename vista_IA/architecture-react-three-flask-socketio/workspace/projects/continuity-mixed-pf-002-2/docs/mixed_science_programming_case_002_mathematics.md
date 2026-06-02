# Prueba por induccion: suma de los primeros n enteros positivos

## Enunciado

Para todo entero positivo `n`, se cumple:

```text
1 + 2 + 3 + ... + n = n(n + 1) / 2
```

## Caso base

Tomamos `n = 1`.

El lado izquierdo es `1`.
El lado derecho es:

```text
1(1 + 1) / 2 = 2 / 2 = 1
```

Como ambos lados valen `1`, la formula es verdadera para `n = 1`.

## Hipotesis inductiva

Suponemos que la formula es verdadera para algun entero positivo `k`.

Es decir, asumimos:

```text
1 + 2 + 3 + ... + k = k(k + 1) / 2
```

Esta suposicion se usa solo para demostrar el caso siguiente, `k + 1`.

## Paso inductivo

Debemos probar que:

```text
1 + 2 + 3 + ... + k + (k + 1) = (k + 1)((k + 1) + 1) / 2
```

Partimos del lado izquierdo y separamos la suma conocida:

```text
1 + 2 + 3 + ... + k + (k + 1)
= [1 + 2 + 3 + ... + k] + (k + 1)
```

Por la hipotesis inductiva:

```text
= k(k + 1) / 2 + (k + 1)
```

Factorizamos `k + 1`:

```text
= (k + 1)(k / 2 + 1)
= (k + 1)(k / 2 + 2 / 2)
= (k + 1)(k + 2) / 2
```

Como `k + 2 = (k + 1) + 1`, entonces:

```text
= (k + 1)((k + 1) + 1) / 2
```

Esto demuestra que si la formula vale para `k`, tambien vale para `k + 1`.

## Conclusion

La formula es verdadera para `n = 1` y el paso inductivo prueba que su verdad se transmite de `k` a `k + 1`.
Por el principio de induccion matematica, para todo entero positivo `n`:

```text
1 + 2 + 3 + ... + n = n(n + 1) / 2
```

## Verificacion rapida

Para `n = 5`:

```text
1 + 2 + 3 + 4 + 5 = 15
5(5 + 1) / 2 = 30 / 2 = 15
```

La verificacion concreta coincide con la formula general demostrada.
