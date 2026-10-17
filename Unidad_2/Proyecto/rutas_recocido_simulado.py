import math
import random
import pandas as pd
import matplotlib.pyplot as plt


PORCENTAJE_ABASTO = 0.35       # cada tienda recibe el 35 % de su capacidad de almacenamiento
TEMP_INICIAL = 100.0           # temperatura inicial
FACTOR_ENFRIAMIENTO = 0.99     # cada ciclo: temperatura = temperatura * 0.99
ITERACIONES = 300              # intentos por temperatura
TEMP_MIN = 0.001               # cuando la temperatura baja de aquí
SEMILLA = 3                    # semilla para reproducibilidad

# ==============================================================================
# 1. CARGA DE DATOS Y MATRICES DEL PROFESOR
# ==============================================================================
df_info = pd.read_excel('datos_distribucion_tiendas.xlsx', sheet_name='Sheet1')
D = pd.read_excel('matriz_distancias.xlsx', sheet_name='Sheet1').values.tolist()
cost_matrix = pd.read_excel('matriz_costos_combustible.xlsx', sheet_name='Sheet1').values.tolist()

# Coordenadas geográficas únicamente para la representación gráfica en el mapa
lat_deg = df_info['Latitud_WGS84'].to_numpy()
lon_deg = df_info['Longitud_WGS84'].to_numpy()

cds = df_info[df_info['Tipo'] == 'Centro de Distribución'].index.tolist()   # 0-9
tiendas = df_info[df_info['Tipo'] == 'Tienda'].index.tolist()               # 10-99
nombres = df_info['Nombre'].tolist()

almacenamiento = df_info['Capacidad_Almacenamiento'].tolist()
abasto = {t: PORCENTAJE_ABASTO * almacenamiento[t] for t in tiendas}
capacidad = {cd: almacenamiento[cd] for cd in cds}
total_abasto = sum(abasto.values())

if total_abasto > sum(capacidad.values()):
    raise SystemExit("El abasto total supera la capacidad de todos los centros: baja PORCENTAJE_ABASTO.")

# ==============================================================================
# 2. EVALUACIÓN DE RUTAS Y DEMANDAS
# ==============================================================================
def evaluar_ruta(cd, ruta, matriz=None):
    """Calcula la distancia o el costo de combustible de una ruta."""
    if not ruta:
        return 0.0
    M = D if matriz is None else matriz
    total = M[cd][ruta[0]] + M[ruta[-1]][cd]
    for i in range(len(ruta) - 1):
        total += M[ruta[i]][ruta[i + 1]]
    return total


def carga_ruta(ruta):
    """Calcula el abasto total surtido en una ruta."""
    return sum(abasto[t] for t in ruta)


# ==============================================================================
# 3. MOVIMIENTOS DE VECINDAD
# ==============================================================================
def generar_vecino(rutas, ubicacion):
    """Genera una variación sencilla de las rutas (Reubicar, Intercambiar o 2-opt)."""
    m = random.random()

    if m < 0.40:
        # 1. Reubicar: pasa una tienda al azar a otra ruta o a otra posición
        t = random.choice(tiendas)
        orig = ubicacion[t]
        dest = random.choice(cds)
        r_orig = [x for x in rutas[orig] if x != t]
        r_dest = r_orig if dest == orig else list(rutas[dest])
        r_dest.insert(random.randint(0, len(r_dest)), t)
        return {orig: r_dest} if dest == orig else {orig: r_orig, dest: r_dest}

    elif m < 0.70:
        # 2. Intercambiar: cambia dos tiendas de lugar
        t1, t2 = random.sample(tiendas, 2)
        cd1, cd2 = ubicacion[t1], ubicacion[t2]
        r1 = list(rutas[cd1])
        r2 = r1 if cd1 == cd2 else list(rutas[cd2])
        i1, i2 = r1.index(t1), r2.index(t2)
        r1[i1], r2[i2] = t2, t1
        return {cd1: r1} if cd1 == cd2 else {cd1: r1, cd2: r2}

    else:
        # 3. 2-opt: invierte un tramo de tiendas dentro de una ruta para quitar cruces
        centros_con_tiendas = [c for c in cds if len(rutas[c]) >= 2]
        if not centros_con_tiendas:
            return None
        cd = random.choice(centros_con_tiendas)
        r = list(rutas[cd])
        i, j = sorted(random.sample(range(len(r)), 2))
        r[i:j + 1] = reversed(r[i:j + 1])
        return {cd: r}


# ==============================================================================
# 4. RECOCIDO SIMULADO
# ==============================================================================
def recocido_simulado():
    # Solución inicial: asignar cada tienda a un centro con capacidad disponible
    rutas = {cd: [] for cd in cds}
    for t in sorted(tiendas, key=lambda x: -abasto[x]):
        cd = random.choice([c for c in cds if carga_ruta(rutas[c]) + abasto[t] <= capacidad[c]])
        rutas[cd].append(t)
    for cd in cds:
        random.shuffle(rutas[cd])
    inicial = {cd: list(r) for cd, r in rutas.items()}

    ubicacion = {t: cd for cd in cds for t in rutas[cd]}
    dist_actual = sum(evaluar_ruta(c, rutas[c]) for c in cds)
    mejor_rutas, mejor_dist = {cd: list(r) for cd, r in rutas.items()}, dist_actual

    temp = TEMP_INICIAL
    while temp > TEMP_MIN:
        for _ in range(ITERACIONES):
            cambios = generar_vecino(rutas, ubicacion)
            if not cambios:
                continue

            # Validar que ningún centro sobrepase su capacidad física
            if any(carga_ruta(r) > capacidad[c] for c, r in cambios.items()):
                continue

            # Diferencia de distancia entre las rutas modificadas
            delta = sum(evaluar_ruta(c, r) - evaluar_ruta(c, rutas[c]) for c, r in cambios.items())

            # Criterio de aceptación de Metropolis
            if delta < 0 or random.random() < math.exp(-delta / temp):
                for c, r in cambios.items():
                    rutas[c] = r
                    for t in r:
                        ubicacion[t] = c
                dist_actual += delta
                if dist_actual < mejor_dist - 1e-9:
                    mejor_dist = dist_actual
                    mejor_rutas = {c: list(rt) for c, rt in rutas.items()}

        temp *= FACTOR_ENFRIAMIENTO

    return inicial, mejor_rutas


# ==============================================================================
# 5. GRÁFICA DE LAS RUTAS
# ==============================================================================
def graficar_rutas(rutas, dist_total):
    colores = plt.cm.tab10.colors
    plt.figure(figsize=(10, 9))

    # Conectar los nodos con líneas rectas siguiendo el orden de cada ruta
    for i, cd in enumerate(c for c in cds if rutas[c]):
        rec = [cd] + rutas[cd] + [cd]
        plt.plot(lon_deg[rec], lat_deg[rec], '-o', color=colores[i % 10], markersize=4, linewidth=1.5,
                 label=f"{nombres[cd]} ({len(rutas[cd])} tiendas, {evaluar_ruta(cd, rutas[cd]):.1f} km)")

    plt.scatter(lon_deg[cds], lat_deg[cds], marker='s', s=120, color='black', zorder=5, label='Centros de Distribución')
    for cd in cds:
        plt.annotate(f"CD {cd + 1}", (lon_deg[cd], lat_deg[cd]), xytext=(6, 6), textcoords='offset points',
                     fontsize=9, weight='bold')

    plt.title(f"Rutas optimizadas (Matriz del Profesor): {dist_total:.2f} km")
    plt.xlabel("Longitud")
    plt.ylabel("Latitud")
    plt.grid(alpha=0.3)
    plt.legend(fontsize=8, loc='upper center', bbox_to_anchor=(0.5, -0.08), ncol=2)
    plt.tight_layout()
    plt.savefig('mapa_rutas.png', dpi=150)
    print("\nGráfica guardada como mapa_rutas.png")
    plt.show()


# ==============================================================================
# 6. EJECUCIÓN Y RESULTADOS
# ==============================================================================
if __name__ == '__main__':
    random.seed(SEMILLA)
    print("Optimizando rutas con matrices del profesor, espera un momento...")
    inicial, rutas = recocido_simulado()

    visitadas = [t for cd in cds for t in rutas[cd]]
    assert sorted(visitadas) == tiendas, "Cada tienda debe visitarse exactamente una vez"
    assert all(carga_ruta(rutas[cd]) <= capacidad[cd] for cd in cds), "Un centro excede su capacidad"

    print("=" * 85)
    print("RESULTADOS DE OPTIMIZACIÓN DE RUTAS (MATRICES DEL PROFESOR)")
    print("=" * 85)
    costo_total = 0.0
    for cd in cds:
        ruta = rutas[cd]
        if not ruta:
            print(f"\n[{nombres[cd]}] sin tiendas asignadas")
            continue
        dist = evaluar_ruta(cd, ruta, D)
        costo = evaluar_ruta(cd, ruta, cost_matrix)
        costo_total += costo
        carga = carga_ruta(ruta)
        print(f"\n[{nombres[cd]}] ({len(ruta)} tiendas)")
        print(f"  - Abasto surtido:       {carga:,.0f} de {capacidad[cd]:,.0f} ({100 * carga / capacidad[cd]:.1f} % de su capacidad)")
        print(f"  - Distancia Optimizada: {dist:.2f} km")
        print(f"  - Costo Combustible:    ${costo:.2f}")
        print(f"  - Ruta: " + " -> ".join([nombres[cd]] + [nombres[t] for t in ruta] + [nombres[cd]]))

    dist_inicial = sum(evaluar_ruta(c, inicial[c], D) for c in cds)
    dist_opt = sum(evaluar_ruta(c, rutas[c], D) for c in cds)
    costo_inicial = sum(evaluar_ruta(c, inicial[c], cost_matrix) for c in cds)
    ahorro_dist = dist_inicial - dist_opt
    ahorro_costo = costo_inicial - costo_total
    centros_usados = sum(1 for cd in cds if rutas[cd])

    print("\n" + "=" * 85)
    print(f"DISTANCIA TOTAL INICIAL:     {dist_inicial:.2f} km   (rutas al azar)")
    print(f"DISTANCIA TOTAL OPTIMIZADA:  {dist_opt:.2f} km")
    print(f"AHORRO TOTAL EN RECORRIDO:   {ahorro_dist:.2f} km ({100 * ahorro_dist / dist_inicial:.2f}%)")
    print(f"COSTO TOTAL DE COMBUSTIBLE:  ${costo_total:.2f} ")
    print(f"AHORRO EN COMBUSTIBLE:       ${ahorro_costo:.2f} ({100 * ahorro_costo / costo_inicial:.2f}%)")
    print(f"CENTROS UTILIZADOS:          {centros_usados} de {len(cds)}")
    print(f"ABASTO TOTAL SURTIDO:        {total_abasto:,.0f} ({PORCENTAJE_ABASTO:.0%} del almacenamiento de cada tienda)")
    print("=" * 85)

    graficar_rutas(rutas, dist_opt)
