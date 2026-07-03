#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sounding_plot.py
=================

Script para graficar sondeos meteorologicos de estaciones de Argentina
(y paises limitrofes disponibles en el archivo de la Universidad de
Wyoming) usando MetPy.

El layout replica el formato clasico de "RAP Proximity Sounding" (estilo
NWS/SPC):

    - Recuadro negro grande a la izquierda con el diagrama Skew-T/Log-P.
    - Recuadro negro mas chico arriba a la derecha con el "Storm Relative
      Hodograph" (colores por capas de altura: 0-3, 3-6, 6-9 y 9-12 km).
    - Recuadro negro abajo a la derecha con los indices termodinamicos y
      cinematicos (ML CAPE, ML CIN, ML LCL, ML LFC, SRH, cizalladura,
      componentes de storm motion, y varios indices de severidad).

Fondo blanco en toda la figura.

Requisitos (entorno Miniconda / VSCode)
----------------------------------------
    conda create -n sondeos python=3.11
    conda activate sondeos
    conda install -c conda-forge metpy matplotlib numpy pandas requests

Uso
---
Editar la seccion "CONFIGURACION" mas abajo (estacion, fecha, hora) y
ejecutar:

    python sounding_plot.py

El script descarga el sondeo desde el archivo de la Universidad de
Wyoming (https://weather.uwyo.edu/upperair/sounding.shtml) y genera un
archivo PNG con el grafico.

Autor: Generado con Kiro (MetPy + Matplotlib)
"""

from __future__ import annotations

import sys
import warnings
from datetime import datetime
from io import StringIO

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

import metpy.calc as mpcalc
from metpy.plots import Hodograph, SkewT
from metpy.units import units

warnings.filterwarnings("ignore")

# =============================================================================
# CONFIGURACION -- MODIFICAR ACA
# =============================================================================

# Fecha y hora UTC del sondeo (00Z o 12Z, que son las horas estandar de
# radiosondeo). Formato: "YYYY-MM-DD HH:MM:SS"
FECHA_HORA_UTC = "2025-01-15 12:00:00"

# Codigo de estacion (WMO) de la estacion argentina a graficar. Algunos
# codigos de estaciones argentinas con datos regulares en el archivo de
# Wyoming:
#
#   87155  Resistencia Aero
#   87344  Cordoba Aero
#   87418  Mendoza Aero
#   87585  Buenos Aires (Ezeiza)
#   87623  Santa Rosa Aero
#   87715  Neuquen Aero
#   87860  Comodoro Rivadavia Aero
#
ESTACION_ID = "87585"

# Fuente de datos en el archivo de Wyoming ("BUFR" es la que cubre la
# mayoria de las estaciones sudamericanas actuales).
FUENTE_DATOS = "BUFR"

# Titulo personalizado. Si se deja en None, se autogenera con el nombre
# de la estacion y la fecha/hora del sondeo.
TITULO_PERSONALIZADO = None

# Nombre del archivo de salida (PNG).
ARCHIVO_SALIDA = "sondeo.png"

# Colormap utilizado para colorear el hodografo. Nota: no existe un
# colormap oficial llamado "CMRmap2" en Matplotlib; el colormap real
# disponible es "CMRmap" (y su version invertida "CMRmap_r"). Se deja
# como variable para que sea facil de cambiar.
HODO_CMAP = "CMRmap"

# Profundidad de la capa de mezcla (ML) usada en los calculos, en hPa.
PROFUNDIDAD_ML = 50 * units.hPa

# =============================================================================
# DESCARGA DE DATOS (Universidad de Wyoming)
# =============================================================================

WYOMING_URL = "https://weather.uwyo.edu/wsgi/sounding"


def descargar_sondeo(fecha_hora_utc: str, estacion_id: str, fuente: str = "BUFR"):
    """
    Descarga y parsea un sondeo desde el archivo de la Universidad de
    Wyoming.

    Devuelve un DataFrame de pandas con las columnas:
    pressure, height, temperature, dewpoint, relh, mixr, direction, speed
    ademas de un diccionario con metadatos (nombre de estacion, titulo,
    lat/lon).
    """
    params = {
        "datetime": fecha_hora_utc,
        "id": estacion_id,
        "src": fuente,
        "type": "TEXT:LIST",
    }
    resp = requests.get(WYOMING_URL, params=params, timeout=30)
    resp.raise_for_status()
    texto = resp.text

    if "Unable to retrieve" in texto:
        raise ValueError(
            f"No se encontraron datos para la estacion {estacion_id} en "
            f"{fecha_hora_utc} (fuente={fuente}). Probar otra fecha/hora "
            "u otra estacion."
        )

    # --- Metadatos (titulo, nombre de estacion, lat/lon) ---
    def _extraer_tag(tag: str) -> str:
        i1 = texto.find(f"<{tag}>")
        i2 = texto.find(f"</{tag}>")
        if i1 == -1 or i2 == -1:
            return ""
        return texto[i1 + len(tag) + 2 : i2].strip()

    titulo_html = _extraer_tag("H1")
    nombre_estacion = _extraer_tag("H3")

    lat, lon = None, None
    idx_lat = texto.find("Latitude:")
    if idx_lat != -1:
        fragmento = texto[idx_lat : idx_lat + 80]
        try:
            lat = float(fragmento.split("Latitude:")[1].split("Longitude:")[0].strip())
            lon = float(fragmento.split("Longitude:")[1].split("</I>")[0].strip())
        except (IndexError, ValueError):
            pass

    # --- Bloque de datos tabulares dentro de <PRE> ... </PRE> ---
    i1 = texto.find("<PRE>")
    i2 = texto.find("</PRE>")
    bloque = texto[i1 + 5 : i2]
    lineas = bloque.split("\n")

    # Las lineas de separacion son '---...---'; los datos empiezan
    # despues de la segunda linea de guiones.
    idx_guiones = [i for i, l in enumerate(lineas) if l.startswith("---")]
    if len(idx_guiones) < 2:
        raise ValueError("No se pudo interpretar el formato del sondeo.")
    inicio_datos = idx_guiones[1] + 1
    lineas_datos = lineas[inicio_datos:]
    texto_datos = "\n".join(lineas_datos)

    # Formato de ancho fijo (columnas de 7 caracteres cada una) tal como
    # lo entrega el archivo de Wyoming.
    colspecs = [
        (0, 7), (7, 14), (14, 21), (21, 28), (28, 35),
        (35, 42), (42, 49), (49, 56), (56, 63), (63, 70), (70, 77),
    ]
    nombres = [
        "pressure", "height", "temperature", "dewpoint", "relh",
        "mixr", "direction", "speed", "theta", "thetae", "thetav",
    ]
    df = pd.read_fwf(StringIO(texto_datos), colspecs=colspecs, names=nombres)
    df = df.dropna(
        subset=["pressure", "height", "temperature", "dewpoint", "direction", "speed"]
    ).reset_index(drop=True)
    df = (
        df.drop_duplicates(subset="pressure")
        .sort_values("pressure", ascending=False)
        .reset_index(drop=True)
    )

    metadatos = {
        "titulo_html": titulo_html,
        "nombre_estacion": nombre_estacion,
        "lat": lat,
        "lon": lon,
    }
    return df, metadatos


# =============================================================================
# CALCULOS METEOROLOGICOS
# =============================================================================

def calcular_indices(p, T, Td, u, v, z):
    """
    Calcula el conjunto de indices termodinamicos y cinematicos que se
    muestran en el recuadro inferior del grafico.
    """
    resultados = {}

    # --- Parcela de capa mezclada (ML) ---
    ml_t, ml_td = mpcalc.mixed_layer(p, T, Td, depth=PROFUNDIDAD_ML)
    ml_p, ml_parcel_t, _ = mpcalc.mixed_parcel(p, T, Td, depth=PROFUNDIDAD_ML)
    mlcape, mlcin = mpcalc.mixed_layer_cape_cin(p, T, Td, depth=PROFUNDIDAD_ML)
    resultados["mlcape"] = mlcape
    resultados["mlcin"] = mlcin

    # Perfil de la parcela ML para trazar en el Skew-T
    ml_prof = mpcalc.parcel_profile(p, ml_parcel_t, ml_td).to("degC")
    resultados["ml_prof"] = ml_prof
    resultados["ml_parcel_t"] = ml_parcel_t
    resultados["ml_td"] = ml_td

    # LCL / LFC de la parcela ML
    ml_lcl_p, ml_lcl_t = mpcalc.lcl(ml_p, ml_parcel_t, ml_td)
    resultados["ml_lcl_p"] = ml_lcl_p
    resultados["ml_lcl_t"] = ml_lcl_t
    try:
        ml_lfc_p, ml_lfc_t = mpcalc.lfc(p, T, Td, parcel_temperature_profile=ml_prof)
    except Exception:
        ml_lfc_p, ml_lfc_t = np.nan * units.hPa, np.nan * units.degC
    resultados["ml_lfc_p"] = ml_lfc_p
    resultados["ml_lfc_t"] = ml_lfc_t

    # Altura del LCL y LFC en metros (interpolando con la altura del sondeo)
    try:
        resultados["ml_lcl_hgt"] = float(
            np.interp(ml_lcl_p.m, p.m[::-1], z.m[::-1])
        ) * units.m
    except Exception:
        resultados["ml_lcl_hgt"] = np.nan * units.m
    try:
        resultados["ml_lfc_hgt"] = float(
            np.interp(ml_lfc_p.m, p.m[::-1], z.m[::-1])
        ) * units.m
    except Exception:
        resultados["ml_lfc_hgt"] = np.nan * units.m

    # --- Storm motion (Bunkers) ---
    rm, lm, mean_wind = mpcalc.bunkers_storm_motion(p, u, v, z)
    u_storm, v_storm = rm
    resultados["u_storm"] = u_storm
    resultados["v_storm"] = v_storm
    resultados["rm"] = rm
    resultados["lm"] = lm
    resultados["mean_wind"] = mean_wind

    # --- Storm Relative Helicity (SRH) ---
    _, _, srh_1km = mpcalc.storm_relative_helicity(
        z, u, v, depth=1 * units.km, storm_u=u_storm, storm_v=v_storm
    )
    _, _, srh_3km = mpcalc.storm_relative_helicity(
        z, u, v, depth=3 * units.km, storm_u=u_storm, storm_v=v_storm
    )
    _, _, srh_6km = mpcalc.storm_relative_helicity(
        z, u, v, depth=6 * units.km, storm_u=u_storm, storm_v=v_storm
    )
    resultados["srh_1km"] = srh_1km
    resultados["srh_3km"] = srh_3km
    resultados["srh_6km"] = srh_6km

    # --- Cizalladura (bulk shear) ---
    ubshr1, vbshr1 = mpcalc.bulk_shear(p, u, v, height=z, depth=1 * units.km)
    ubshr3, vbshr3 = mpcalc.bulk_shear(p, u, v, height=z, depth=3 * units.km)
    ubshr6, vbshr6 = mpcalc.bulk_shear(p, u, v, height=z, depth=6 * units.km)
    resultados["shear_1km"] = mpcalc.wind_speed(ubshr1, vbshr1)
    resultados["shear_3km"] = mpcalc.wind_speed(ubshr3, vbshr3)
    resultados["shear_6km"] = mpcalc.wind_speed(ubshr6, vbshr6)

    # --- Indices termodinamicos clasicos ---
    resultados["k_index"] = mpcalc.k_index(p, T, Td)
    resultados["total_totals"] = mpcalc.total_totals_index(p, T, Td)

    # --- CAPE/CIN de superficie y de la parcela mas inestable (MU) ---
    sbcape, sbcin = mpcalc.surface_based_cape_cin(p, T, Td)
    resultados["sbcape"] = sbcape
    resultados["sbcin"] = sbcin

    mucape, mucin = mpcalc.most_unstable_cape_cin(p, T, Td, depth=PROFUNDIDAD_ML)
    resultados["mucape"] = mucape
    resultados["mucin"] = mucin

    # --- Significant Tornado Parameter y Supercell Composite ---
    try:
        sig_tor = mpcalc.significant_tornado(
            sbcape, resultados["ml_lcl_hgt"], srh_3km, resultados["shear_3km"]
        ).to_base_units()
        resultados["sig_tor"] = sig_tor
    except Exception:
        resultados["sig_tor"] = np.array([np.nan]) * units.dimensionless

    try:
        super_comp = mpcalc.supercell_composite(mucape, srh_3km, resultados["shear_3km"])
        resultados["super_comp"] = super_comp
    except Exception:
        resultados["super_comp"] = np.array([np.nan]) * units.dimensionless

    return resultados


# =============================================================================
# UTILIDADES DE FORMATO
# =============================================================================

def _fmt(valor, decimales=0):
    """Formatea una cantidad de pint (o escalar) como texto, tolerando NaN."""
    try:
        if hasattr(valor, "magnitude"):
            mag = valor.magnitude
        else:
            mag = valor
        if isinstance(mag, np.ndarray):
            mag = mag.item() if mag.size == 1 else mag[0]
        if np.isnan(mag):
            return "N/A"
        return f"{mag:.{decimales}f}"
    except Exception:
        return "N/A"


# =============================================================================
# CONSTRUCCION DEL GRAFICO
# =============================================================================

def graficar_sondeo(df, metadatos):
    p = df["pressure"].values * units.hPa
    z = df["height"].values * units.m
    T = df["temperature"].values * units.degC
    Td = df["dewpoint"].values * units.degC
    wdir = df["direction"].values * units.deg
    wspd = df["speed"].values * units("m/s")
    u, v = mpcalc.wind_components(wspd, wdir)

    # Temperatura virtual (para la linea "Virtual Temperature")
    mixing_ratio = mpcalc.saturation_mixing_ratio(p, Td)
    Tv = mpcalc.virtual_temperature(T, mixing_ratio)

    idx = calcular_indices(p, T, Td, u, v, z)

    # -------------------------------------------------------------------
    # Figura y ejes
    # -------------------------------------------------------------------
    fig = plt.figure(figsize=(13, 9.5))
    fig.patch.set_facecolor("white")

    # --- Skew-T (panel izquierdo, recuadro alto) ---
    skew_rect = (0.05, 0.05, 0.52, 0.85)
    skew = SkewT(fig, rotation=45, rect=skew_rect)
    skew.ax.set_facecolor("white")
    # IMPORTANTE: sin esto, Matplotlib recalcula el tamano de la caja de
    # ejes para respetar el aspect ratio fijo del Skew-T, encogiendola a
    # una franja angosta dentro del "rect". set_adjustable('datalim')
    # evita esa distorsion (ver ejemplos oficiales de MetPy).
    skew.ax.set_adjustable("datalim")

    skew.plot(p, T, color="red", lw=1.8, label="Temperature")
    skew.plot(p, Tv, color="lightgreen", lw=1.3, linestyle="-", label="Virtual Temperature")
    skew.plot(p, Td, color="green", lw=1.8, label="Dewpoint")

    interval = np.logspace(2, 3, 35) * units.hPa
    idx_barbs = mpcalc.resample_nn_1d(p, interval)
    skew.plot_barbs(p[idx_barbs], u[idx_barbs], v[idx_barbs])

    skew.plot(p, idx["ml_prof"], color="black", lw=1.8, label="ML Parcel Trace")

    skew.ax.set_ylim(1000, 100)
    skew.ax.set_xlim(-30, 40)
    skew.ax.set_xlabel("Temperature (\u00b0C)", fontsize=11, weight="bold")
    skew.ax.set_ylabel("Pressure (hPa)", fontsize=11, weight="bold")

    skew.plot_dry_adiabats(lw=0.6, alpha=0.5, color="tan")
    skew.plot_moist_adiabats(lw=0.6, alpha=0.5, color="cornflowerblue")
    skew.plot_mixing_lines(lw=0.6, alpha=0.5, color="gray", linestyle="--")

    # Marca del LCL de la parcela ML
    if np.isfinite(idx["ml_lcl_p"].m) and np.isfinite(idx["ml_lcl_t"].m):
        skew.plot(idx["ml_lcl_p"], idx["ml_lcl_t"], "ko", markerfacecolor="black", markersize=5)
        skew.ax.annotate(
            "LCL", (idx["ml_lcl_t"].m, idx["ml_lcl_p"].m),
            textcoords="offset points", xytext=(8, 0), fontsize=8, weight="bold",
        )

    # Marca del LFC de la parcela ML
    if np.isfinite(idx["ml_lfc_p"].m) and np.isfinite(idx["ml_lfc_t"].m):
        skew.ax.annotate(
            "LFC", (idx["ml_lfc_t"].m, idx["ml_lfc_p"].m),
            textcoords="offset points", xytext=(8, 0), fontsize=8, weight="bold",
        )

    # Etiquetas de altura aproximada (1, 3, 6, 9, 12 km) sobre el eje
    # derecho del Skew-T, interpolando presion desde la altura del sondeo.
    alturas_ref_km = [1, 3, 6, 9, 12]
    z_km = z.to("km").m
    p_hpa = p.m
    orden = np.argsort(z_km)
    for h in alturas_ref_km:
        if h < z_km.max():
            p_h = np.interp(h, z_km[orden], p_hpa[orden])
            if 100 < p_h < 1000:
                skew.ax.annotate(
                    f"{h} km", xy=(-29, p_h), xycoords=("data", "data"),
                    fontsize=8, weight="bold", color="black", ha="left", va="center",
                )

    skew.ax.legend(loc="upper right", fontsize=8, framealpha=0.9)

    # Recuadro negro alrededor del Skew-T
    _agregar_recuadro(fig, skew_rect)

    # -------------------------------------------------------------------
    # Hodografo storm-relative (panel superior derecho, recuadro chico)
    # -------------------------------------------------------------------
    hodo_rect = (0.63, 0.52, 0.33, 0.40)
    hodo_ax = fig.add_axes(hodo_rect)
    hodo_ax.set_facecolor("white")

    max_range = 60.0
    h = Hodograph(hodo_ax, component_range=max_range)
    h.add_grid(increment=20, color="gray", linestyle="-", lw=0.8, alpha=0.6)
    h.add_grid(increment=10, color="gray", linestyle="--", lw=0.5, alpha=0.3)

    hodo_ax.set_xlim(-max_range, max_range)
    hodo_ax.set_ylim(-max_range, max_range)
    hodo_ax.set_xticks([])
    hodo_ax.set_yticks([])
    hodo_ax.set_xlabel("")
    hodo_ax.set_ylabel("")
    for spine in hodo_ax.spines.values():
        spine.set_visible(False)

    # Etiquetas "knots" en los ejes, como en la imagen de referencia
    hodo_ax.annotate(
        "knots", xy=(max_range * 0.80, max_range * 0.05), fontsize=8, ha="left",
    )
    hodo_ax.annotate(
        "knots", xy=(max_range * 0.05, max_range * 0.90), fontsize=8, ha="left",
    )
    for val in [-60, -40, -20, 20, 40, 60]:
        hodo_ax.annotate(str(val), xy=(val, 1.5), fontsize=7, ha="center", alpha=0.7)
        hodo_ax.annotate(str(val), xy=(1.5, val), fontsize=7, va="center", alpha=0.7)

    # Wind storm-relative: se resta el vector de storm motion (Bunkers RM)
    u_sr = (u - idx["u_storm"]).to("knots")
    v_sr = (v - idx["v_storm"]).to("knots")
    z_km_full = z.to("km").m

    # Colores de las 4 capas tomados del colormap configurado (HODO_CMAP,
    # por defecto "CMRmap"), muestreado en 4 puntos espaciados a lo largo
    # del colormap para que cada capa reciba un color bien diferenciado.
    cmap_hodo = plt.get_cmap(HODO_CMAP)
    fracciones_cmap = [0.05, 0.30, 0.55, 0.75]
    colores_capas = [cmap_hodo(f) for f in fracciones_cmap]

    capas = [
        (0, 3, colores_capas[0], "0-3 km"),
        (3, 6, colores_capas[1], "3-6 km"),
        (6, 9, colores_capas[2], "6-9 km"),
        (9, 12, colores_capas[3], "9-12 km"),
    ]
    for z0, z1, color, etiqueta in capas:
        mascara = (z_km_full >= z0) & (z_km_full <= z1)
        if mascara.sum() >= 2:
            hodo_ax.plot(
                u_sr.m[mascara], v_sr.m[mascara], color=color, lw=2.2, label=etiqueta
            )

    hodo_ax.plot(0, 0, marker="+", color="black", markersize=10, mew=1.5)
    # Leyenda simple (sin marco), como en la imagen de referencia: solo
    # texto de color en la esquina superior izquierda.
    leyenda_y0 = max_range * 0.92
    for i, (_, _, color, etiqueta) in enumerate(capas):
        hodo_ax.annotate(
            etiqueta, xy=(-max_range * 0.95, leyenda_y0 - i * max_range * 0.075),
            fontsize=8, color=color, weight="bold", ha="left",
        )
    hodo_ax.set_title("Storm Relative Hodograph", fontsize=11, weight="bold")

    _agregar_recuadro(fig, hodo_rect)

    # -------------------------------------------------------------------
    # Recuadro de indices (panel inferior derecho)
    # -------------------------------------------------------------------
    indices_rect = (0.63, 0.05, 0.33, 0.40)
    _agregar_recuadro(fig, indices_rect)

    x0, y0, w0, h0 = indices_rect

    filas_izquierda = [
        ("ML CAPE:", f"{_fmt(idx['mlcape'])} J/kg"),
        ("ML CINH:", f"{_fmt(idx['mlcin'])} J/kg"),
        ("ML LCL:", f"{_fmt(idx['ml_lcl_hgt'])} m"),
        ("ML LFC:", f"{_fmt(idx['ml_lfc_hgt'])} m"),
        ("SBCAPE:", f"{_fmt(idx['sbcape'])} J/kg"),
        ("MUCAPE:", f"{_fmt(idx['mucape'])} J/kg"),
        ("K-INDEX:", f"{_fmt(idx['k_index'])}"),
        ("TOTAL TOTALS:", f"{_fmt(idx['total_totals'])}"),
    ]

    filas_derecha = [
        ("U Storm Motion:", f"{_fmt(idx['u_storm'].to('m/s'))} m/s"),
        ("V Storm Motion:", f"{_fmt(idx['v_storm'].to('m/s'))} m/s"),
        ("0-1 km Helicity:", f"{_fmt(idx['srh_1km'])} m\u00b2/s\u00b2"),
        ("0-3 km Helicity:", f"{_fmt(idx['srh_3km'])} m\u00b2/s\u00b2"),
        ("0-1 km Shear:", f"{_fmt(idx['shear_1km'])} m/s"),
        ("0-6 km Shear:", f"{_fmt(idx['shear_6km'])} m/s"),
        ("Sig. Tornado:", f"{_fmt(idx['sig_tor'][0] if hasattr(idx['sig_tor'], '__len__') else idx['sig_tor'])}"),
        ("Supercell Comp.:", f"{_fmt(idx['super_comp'][0] if hasattr(idx['super_comp'], '__len__') else idx['super_comp'])}"),
    ]

    fig.text(
        x0 + w0 / 2, y0 + h0 - 0.02, "SEVERE WEATHER INDICES",
        ha="center", va="top", fontsize=10, weight="bold",
    )

    _dibujar_indices_dos_columnas(fig, indices_rect, filas_izquierda, filas_derecha)

    # -------------------------------------------------------------------
    # Titulo general
    # -------------------------------------------------------------------
    if TITULO_PERSONALIZADO:
        titulo = TITULO_PERSONALIZADO
    else:
        fecha_dt = datetime.strptime(FECHA_HORA_UTC, "%Y-%m-%d %H:%M:%S")
        titulo = (
            f"{fecha_dt.strftime('%d %b %Y')} {fecha_dt.strftime('%H')}Z Sondeo\n"
            f"{metadatos.get('nombre_estacion', ESTACION_ID)}"
        )
    fig.suptitle(titulo, fontsize=13, weight="bold", y=0.98)

    return fig


def _agregar_recuadro(fig, rect, edgecolor="black", facecolor="none", linewidth=1.6):
    """Dibuja un recuadro negro (solo el borde, sin relleno) alrededor de
    la region (x0, y0, w, h) en coordenadas de figura, replicando el
    estilo de la imagen de referencia.

    IMPORTANTE: los parches agregados directamente a ``fig.patches`` se
    dibujan por encima de TODOS los ejes de la figura, sin importar su
    ``zorder`` (porque los artistas de la figura se renderizan en una
    capa separada, posterior a la de los Axes). Por eso este recuadro
    NUNCA debe llevar relleno opaco (facecolor distinto de "none"): si lo
    llevara, tapa por completo el contenido del Skew-T y del hodografo
    que estan debajo.
    """
    x0, y0, w, h = rect
    fig.patches.append(
        plt.Rectangle(
            (x0, y0), w, h,
            transform=fig.transFigure, figure=fig,
            edgecolor=edgecolor, facecolor="none", linewidth=linewidth, zorder=10,
        )
    )


def _dibujar_indices_dos_columnas(fig, rect, filas_izquierda, filas_derecha):
    """Dibuja las dos columnas de indices dentro del recuadro inferior,
    con etiquetas en negrita y valores resaltados, similar al estilo de
    la imagen de referencia (ML CAPE / ML CINH / ML LCL / ML LFC a la
    izquierda; storm motion / helicidad / cizalladura a la derecha)."""
    x0, y0, w, h = rect
    n_filas = max(len(filas_izquierda), len(filas_derecha))
    top = y0 + h - 0.065
    bottom = y0 + 0.02
    paso = (top - bottom) / max(n_filas - 1, 1)

    col1_label_x = x0 + 0.015
    col1_val_x = x0 + w * 0.30

    col2_label_x = x0 + w * 0.52
    col2_val_x = x0 + w * 0.86

    for i, (etiqueta, valor) in enumerate(filas_izquierda):
        y = top - i * paso
        fig.text(col1_label_x, y, etiqueta, ha="left", va="center",
                  fontsize=8.6, weight="bold", family="sans-serif")
        fig.text(col1_val_x, y, valor, ha="left", va="center",
                  fontsize=8.6, color="darkred", family="sans-serif")

    for i, (etiqueta, valor) in enumerate(filas_derecha):
        y = top - i * paso
        fig.text(col2_label_x, y, etiqueta, ha="left", va="center",
                  fontsize=8.6, weight="bold", family="sans-serif")
        fig.text(col2_val_x, y, valor, ha="left", va="center",
                  fontsize=8.6, color="navy", family="sans-serif")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print(f"Descargando sondeo: estacion {ESTACION_ID}, {FECHA_HORA_UTC} UTC ...")
    try:
        df, metadatos = descargar_sondeo(FECHA_HORA_UTC, ESTACION_ID, FUENTE_DATOS)
    except Exception as exc:
        print(f"ERROR al descargar el sondeo: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Estacion: {metadatos.get('nombre_estacion')}")
    print(f"Niveles de datos: {len(df)}")

    fig = graficar_sondeo(df, metadatos)
    fig.savefig(ARCHIVO_SALIDA, dpi=150, facecolor="white", bbox_inches="tight")
    print(f"Grafico guardado en: {ARCHIVO_SALIDA}")
    plt.show()


if __name__ == "__main__":
    main()
