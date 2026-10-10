"""
8 reinas con Búsqueda Tabú.
Estado: lista de 8 números, estado[columna] = fila de la reina.
"""
import random
import time

N = 8           # número de reinas
TENENCIA = 3    # tamaño de la lista tabú


def costo(estado):
    """Número de pares de reinas que se atacan (misma fila o diagonal)."""
    ataques = 0
    for i in range(N):
        for j in range(i + 1, N):
            if estado[i] == estado[j] or abs(estado[i] - estado[j]) == j - i:
                ataques += 1
    return ataques


def generar_vecindario(estado):
    """Cada swap de dos columnas genera una nueva solución vecina."""
    vecindario = []
    for i in range(N):
        for j in range(i + 1, N):
            vecino = estado.copy()
            vecino[i], vecino[j] = vecino[j], vecino[i]
            vecindario.append(((i, j), vecino))
    return vecindario


def busqueda_tabu(estado):
    actual = estado
    mejor = estado
    lista_tabu = []
    movimientos = 0

    while costo(mejor) > 0:
        # 1. Generar el vecindario con swaps
        vecindario = generar_vecindario(actual)
        random.shuffle(vecindario)                    # desempate aleatorio
        vecindario.sort(key=lambda v: costo(v[1]))    # 2. Ordenar del mejor al peor

        # 3. Elegir el mejor vecino que no sea tabú (o que cumpla aspiración)
        for swap, vecino in vecindario:
            if swap not in lista_tabu or costo(vecino) < costo(mejor):
                break

        # 4. Moverse a ese vecino (aunque sea peor que el actual)
        actual = vecino
        movimientos += 1

        # 5. Actualizar la lista tabú (entra el swap, sale el más viejo)
        lista_tabu.append(swap)
        if len(lista_tabu) > TENENCIA:
            lista_tabu.pop(0)

        # 6. Guardar la mejor solución encontrada
        if costo(actual) < costo(mejor):
            mejor = actual

    return mejor, movimientos


def imprimir_tablero(estado):
    for fila in range(N):
        print(" ".join("Q" if estado[col] == fila else "." for col in range(N)))


# Estado inicial aleatorio: las filas 0..7 en orden aleatorio
inicial = random.sample(range(N), N)
print("Estado inicial:", inicial, " ataques:", costo(inicial))
imprimir_tablero(inicial)

inicio = time.perf_counter()
solucion, movimientos = busqueda_tabu(inicial)
tiempo = time.perf_counter() - inicio

print("\nSolución:", solucion, " ataques:", costo(solucion))
imprimir_tablero(solucion)
print(f"\nMovimientos: {movimientos}")
print(f"Tiempo: {tiempo * 1000:.3f} ms")