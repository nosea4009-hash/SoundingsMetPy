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

1. Abrir `sounding_plot.py` en VSCode.
2. Editar la seccion `CONFIGURACION` al inicio del archivo:
   - `FECHA_HORA_UTC`: fecha/hora del sondeo (00Z o 12Z), formato
     `"YYYY-MM-DD HH:MM:SS"`.
   - `ESTACION_ID`: codigo OMM de la estacion (ver lista de ejemplos en
     los comentarios del script).
   - `HODO_CMAP`: colormap para el hodografo (por defecto `"CMRmap"`).
3. Ejecutar:

   ```bash
   python sounding_plot.py
   ```

4. El script descarga el sondeo, calcula los indices e imprime un PNG
   (`sondeo.png` por defecto) en el mismo directorio, ademas de abrir
   una ventana con el grafico.

## Estaciones argentinas de ejemplo

| Codigo | Estacion                  |
|--------|----------------------------|
| 87155  | Resistencia Aero           |
| 87344  | Cordoba Aero                |
| 87418  | Mendoza Aero                 |
| 87585  | Buenos Aires (Ezeiza)        |
| 87623  | Santa Rosa Aero              |
| 87715  | Neuquen Aero                 |
| 87860  | Comodoro Rivadavia Aero      |
