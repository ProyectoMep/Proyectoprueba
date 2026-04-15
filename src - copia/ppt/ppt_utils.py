import os
import pandas as pd
from pptx.dml.color import RGBColor

def leer_hojas_excel(ruta_excel: str) -> dict:
    """
    Lee todas las hojas de un Excel y retorna {hoja: num_filas}.
    """
    hojas = {}
    try:
        xl = pd.ExcelFile(ruta_excel)
        for hoja in xl.sheet_names:
            if not hoja.startswith("Resumen"):
                df = xl.parse(hoja)
                hojas[hoja] = len(df)
    except Exception as e:
        print(f"   ❌ Error leyendo {ruta_excel}: {e}")
    return hojas

def comparar_excel(hojas_actual: dict, hojas_anterior: dict) -> dict:
    """
    Compara hojas de dos Excel y retorna datos formateados.
    Input: {hoja: num_filas}
    Output: {hoja: {actual, anterior, diferencia, texto, color}}
    """
    resultado = {}
    for hoja, n_actual in hojas_actual.items():
        n_ant = hojas_anterior.get(hoja, 0)
        texto_fmt, color, _ = formato_cambio(n_actual, n_ant)
        resultado[hoja] = {
            'actual': n_actual,
            'anterior': n_ant,
            'diferencia': n_actual - n_ant,
            'texto': texto_fmt,
            'color': color
        }
    return resultado

def formato_cambio(n_actual: int, n_anterior: int) -> tuple:
    """
    Retorna (texto_formateado, color_rgb, es_aumento)
    Colores:
    - Aumento: Rojo (#C00000)
    - Disminución: Verde (#008000)
    - Sin cambio: Azul (#0070C0)
    """
    diferencia = n_actual - n_anterior
    
    if diferencia > 0:
        # Aumento: flecha arriba en rojo
        simbolo = "↑"
        color = RGBColor(192, 0, 0)
        texto = f"{simbolo} {n_actual} con respecto a la semana pasada ({n_anterior})"
        es_aumento = True
    elif diferencia < 0:
        # Disminución: flecha abajo en verde
        simbolo = "↓"
        color = RGBColor(0, 128, 0)
        texto = f"{simbolo} {n_actual} con respecto a la semana pasada ({n_anterior})"
        es_aumento = False
    else:
        # Sin cambio: símbolo "=" en azul
        simbolo = "="
        color = RGBColor(0, 112, 192)
        texto = f"{simbolo} {n_actual} sin cambios respecto a la semana pasada ({n_anterior})"
        es_aumento = None
    
    return texto, color, es_aumento

def buscar_bandera(text, banderas=None) -> list:
    """
    Busca banderas tipo <<bandera>> en el texto.
    """
    import re
    return re.findall(r"<<(.*?)>>", text)
