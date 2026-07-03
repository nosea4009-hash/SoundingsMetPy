# SoundingsMetPy

Script en Python (`sounding_plot.py`) para graficar sondeos meteorologicos
de estaciones de Argentina (y paises limitrofes) usando **MetPy**,
replicando el formato clasico de "Proximity Sounding" usado por el
NWS/SPC: Skew-T grande a la izquierda, hodografo storm-relative arriba a
la derecha y una caja de indices de severidad abajo a la derecha, todo
sobre fondo blanco con recuadros negros.

## Layout del grafico

- **Recuadro negro grande (izquierda):** diagrama Skew-T/Log-P con
  temperatura, temperatura virtual, punto de rocio, traza de la parcela
  de capa mezclada (ML), adiabatas secas/humedas, lineas de razon de
  mezcla, barbas de viento y marcas de LCL/LFC. Incluye etiquetas de
  altura aproximada (1, 3, 6, 9, 12 km).
- **Recuadro negro chico (arriba a la derecha):** "Storm Relative
  Hodograph", coloreado por capas de altura (0-3, 3-6, 6-9 y 9-12 km)
  usando el colormap configurable `HODO_CMAP` (por defecto `CMRmap`,
  ver nota abajo).
- **Recuadro negro (abajo a la derecha):** indices termodinamicos y
  cinematicos: ML CAPE, ML CINH, ML LCL, ML LFC, SBCAPE, MUCAPE,
  K-Index, Total Totals, componentes U/V del storm motion (Bunkers),
  helicidad relativa a la tormenta (SRH) 0-1 km y 0-3 km, cizalladura
  0-1 km y 0-6 km, parametro de tornado significativo y compuesto de
  supercelda.

## Nota sobre el colormap

No existe un colormap oficial llamado `"CMRmap2"` en Matplotlib. El
colormap real disponible (y el que usa este script) es **`CMRmap`**
(tambien existe su version invertida `CMRmap_r`). La variable
`HODO_CMAP` al inicio del script permite cambiarlo facilmente por
cualquier otro colormap de Matplotlib.

## Fuente de datos

Los datos del sondeo se descargan en tiempo real desde el archivo de la
Universidad de Wyoming
(https://weather.uwyo.edu/upperair/sounding.shtml), que cubre las
principales estaciones de radiosondeo de Argentina (Buenos Aires/Ezeiza,
Cordoba, Mendoza, Resistencia, Santa Rosa, Neuquen, Comodoro Rivadavia,
entre otras) en los horarios estandar 00Z y 12Z.

## Instalacion (entorno Miniconda + VSCode)

```bash
conda create -n sondeos python=3.11
conda activate sondeos
conda install -c conda-forge metpy matplotlib numpy pandas requests
```

(o alternativamente `pip install -r requirements.txt` dentro del
entorno conda ya activado).

## Uso

### Opcion A: linea de comandos (recomendada, no requiere editar el archivo)

```bash
python sounding_plot.py --estacion "Foz do Iguazu" --fecha 2025-11-07 --hora 12
python sounding_plot.py --estacion "Cordoba" --fecha 2025-01-15 --hora 12
python sounding_plot.py --estacion 87585 --fecha 2025-01-15 --hora 00
```

Argumentos disponibles:

| Argumento          | Descripcion                                                        |
|--------------------|---------------------------------------------------------------------|
| `--estacion`, `-e` | Nombre (ver tabla abajo) o codigo OMM de la estacion.               |
| `--fecha`, `-f`    | Fecha del sondeo, formato `YYYY-MM-DD`.                             |
| `--hora`, `-H`     | Hora UTC del sondeo: `00` o `12` (horas estandar de radiosondeo).   |
| `--salida`, `-o`   | Nombre del archivo PNG de salida (por defecto `sondeo.png`).        |
| `--sin-ventana`    | No abrir la ventana interactiva de Matplotlib (solo guarda el PNG). |

La busqueda de estacion por nombre ignora mayusculas/minusculas y
acentos (por ejemplo, "foz de iguacu", "FOZ DO IGUAZU" y "Foz do
Iguazu" resuelven a la misma estacion).

**Nota sobre la fuente de datos:** el archivo de Wyoming sirve los datos
bajo distintas "fuentes" (`BUFR`, `FM35`, etc.) segun la fecha, y no es
fija por estacion. El script prueba automaticamente todas las fuentes
conocidas hasta encontrar una con datos disponibles, por lo que no hace
falta indicarla manualmente.

### Opcion B: editar la seccion CONFIGURACION

1. Abrir `sounding_plot.py` en VSCode.
2. Editar la seccion `CONFIGURACION` al inicio del archivo:
   - `FECHA_HORA_UTC`: fecha/hora del sondeo (00Z o 12Z), formato
     `"YYYY-MM-DD HH:MM:SS"`.
   - `ESTACION_ID`: nombre (ver tabla abajo) o codigo OMM de la
     estacion.
   - `HODO_CMAP`: colormap para el hodografo (por defecto `"CMRmap"`).
3. Ejecutar:

   ```bash
   python sounding_plot.py
   ```

En ambos casos, el script descarga el sondeo, calcula los indices e
imprime un PNG (`sondeo.png` por defecto) en el mismo directorio,
ademas de abrir una ventana con el grafico (salvo que se use
`--sin-ventana`).

## Estaciones disponibles (catalogo `CATALOGO_ESTACIONES`)

| Nombre a usar en `--estacion` | Codigo | Estacion                        | Pais      |
|--------------------------------|--------|----------------------------------|-----------|
| `resistencia` / `corrientes`  | 87155  | Resistencia Aero                 | Argentina |
| `cordoba`                      | 87344  | Cordoba Aero                     | Argentina |
| `mendoza`                      | 87418  | Mendoza Aero                      | Argentina |
| `buenos aires` / `ezeiza`     | 87585  | Buenos Aires (Ezeiza)             | Argentina |
| `santa rosa`                   | 87623  | Santa Rosa Aero                  | Argentina |
| `neuquen`                      | 87715  | Neuquen Aero                     | Argentina |
| `comodoro rivadavia`           | 87860  | Comodoro Rivadavia Aero          | Argentina |
| `foz do iguazu` / `iguazu`    | 83827  | Foz do Iguacu (Aeroporto)        | Brasil    |
| `santa maria`                  | 83937  | Santa Maria (Aeroporto)          | Brasil    |
| `uruguaiana`                   | 83928  | Uruguaiana (Aeroporto)           | Brasil    |
| `campo grande`                 | 83612  | Campo Grande (Aeroporto)         | Brasil    |
| `londrina`                     | 83768  | Londrina (Aeroporto)              | Brasil    |
| `antofagasta`                  | 85442  | Antofagasta                      | Chile     |
| `santo domingo`                 | 85586  | Santo Domingo                    | Chile     |
| `puerto montt`                 | 85799  | Puerto Montt                     | Chile     |
| `punta arenas`                 | 85934  | Punta Arenas                     | Chile     |

Tambien se puede usar directamente el codigo OMM si se prefiere. Si el
nombre no se encuentra, el script muestra la lista completa de opciones
disponibles.
