import os
import re
import pandas as pd
from openpyxl import load_workbook
from ..core import limpiar_ruta, leer_configuracion_enriquecimiento, leer_excel_o_csv
from ..core.file_utils import aplicar_formato_encabezados, colorear_pestanas_resumen
from ..utils import parse_lista_columnas
from .lookup import buscar_coincidencia_parcial
from .formula_engine import evaluar_formula

_cache_hojas_lookup = {}

def _preparar_cache_lookup(excel_base: pd.ExcelFile):
    """
    Prepara caché de hojas para funciones LOOKUP.
    """
    _cache_hojas_lookup.clear()
    for hoja in excel_base.sheet_names:
        try:
            _cache_hojas_lookup[hoja.lower()] = excel_base.parse(hoja)
        except Exception:
            pass

def enriquecer_hojas(ruta_excel: str, ruta_configuracion: str):
    """
    Enriquece hojas Excel con datos externos y fórmulas calculadas.
    Soporta enriquecimiento de hojas de resumen.
    """
    data_conf = leer_configuracion_enriquecimiento(ruta_configuracion)
    bloques = data_conf["bloques"]
    parametros = data_conf["parametros"]

    ruta_excel = limpiar_ruta(ruta_excel)
    if not os.path.exists(ruta_excel):
        print(f"❌ Excel base no existe: {ruta_excel}")
        return

    try:
        print("\n" + "═" * 70)
        print("🔧 INICIANDO ENRIQUECIMIENTO DE DATOS")
        print("═" * 70)
        
        if parametros:
            print(f"\n⚙️  Parámetros globales configurados: {len(parametros)}")
            for k, v in parametros.items():
                print(f"   • {k} = {v}")
        
        excel_base = pd.ExcelFile(ruta_excel)
        hojas_existentes = set(excel_base.sheet_names)
        _preparar_cache_lookup(excel_base)

        # Agrupar bloques por hoja
        bloques_por_hoja = {}
        for b in bloques:
            hoja = (b.get("hoja") or "").strip().strip('"')
            if not hoja:
                continue
            bloques_por_hoja.setdefault(hoja, []).append(b)

        print(f"\n📋 Total de hojas a enriquecer: {len(bloques_por_hoja)}")
        
        with pd.ExcelWriter(ruta_excel, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            for idx, (hoja, lista_ops) in enumerate(bloques_por_hoja.items(), 1):
                if hoja not in hojas_existentes:
                    print(f"\n  ⚠️  Hoja '{hoja}' no existe → Omitida")
                    continue

                df_base = excel_base.parse(hoja)
                # Normalizar columnas eliminando comillas
                df_base.columns = [str(c).strip().strip('"').strip("'").strip().lower() for c in df_base.columns]

                # Detectar si es una hoja de resumen
                es_resumen = hoja.startswith("Resumen")
                if es_resumen:
                    print(f"\n" + "─" * 70)
                    print(f"📊 [{idx}/{len(bloques_por_hoja)}] Enriqueciendo RESUMEN: {hoja}")
                    print(f"   🔧 {len(lista_ops)} operacion(es) configurada(s)")
                    print("─" * 70)
                else:
                    print(f"\n" + "─" * 70)
                    print(f"📄 [{idx}/{len(bloques_por_hoja)}] Enriqueciendo: {hoja}")
                    print(f"   🔧 {len(lista_ops)} operacion(es) configurada(s)")
                    print("─" * 70)

                for cfg in lista_ops:
                    # Enriquecimiento desde archivo externo
                    _enriquecer_desde_archivo(df_base, cfg, _cache_hojas_lookup)
                    
                    # Aplicar fórmulas calculadas
                    _aplicar_calculos(df_base, cfg, parametros, _cache_hojas_lookup)

                # Solo reordenar columnas en resúmenes: ID, Employee ID, luego el resto
                if es_resumen:
                    cols_base = []
                    if "id" in df_base.columns:
                        cols_base.append("id")
                    if "employee id" in df_base.columns:
                        cols_base.append("employee id")
                    otras_cols = sorted([c for c in df_base.columns if c not in cols_base])
                    df_base = df_base[cols_base + otras_cols]
                    print(f"  📋 Columnas reordenadas en resumen: {', '.join(cols_base)}")

                df_base.to_excel(writer, sheet_name=hoja, index=False)
                print(f"  ✅ Hoja '{hoja}' guardada")

        # Aplicar formato
        print(f"\n🎨 Aplicando formato visual...")
        wb = load_workbook(ruta_excel)
        aplicar_formato_encabezados(wb)
        
        # Colorear pestañas de hojas resumen
        colorear_pestanas_resumen(wb)
        
        wb.save(ruta_excel)
        
        print("\n" + "═" * 70)
        print("✅ ENRIQUECIMIENTO COMPLETADO")
        print("═" * 70 + "\n")
    except Exception as e:
        print(f"\n❌ Error durante enriquecimiento: {e}\n")

def _enriquecer_desde_archivo(df_base: pd.DataFrame, cfg: dict, cache_hojas: dict):
    """
    Enriquece DataFrame base con datos de archivo externo.
    """
    columna_base = (cfg.get("columna base") or "").strip().strip('"')
    ruta_ext = limpiar_ruta(cfg.get("ruta") or "")
    columna_cruzar = (cfg.get("columna cruzar") or "").strip().strip('"')
    columnas_extraer_raw = cfg.get("columna extraer") or ""

    columna_base_norm = columna_base.lower() if columna_base else ""

    # Logging de depuración
    print(f"\n  🔍 Verificando configuración de enriquecimiento:")
    print(f"     • Columna base: '{columna_base}' (norm: '{columna_base_norm}')")
    print(f"     • Ruta externa: '{ruta_ext}'")
    print(f"     • Columna cruzar: '{columna_cruzar}'")
    print(f"     • Columnas extraer: '{columnas_extraer_raw}'")

    if not ruta_ext:
        print(f"     ⚠️  No hay ruta de archivo externo configurada")
        return
    
    if not os.path.exists(ruta_ext):
        print(f"     ❌ Archivo externo no existe: {ruta_ext}")
        return
    
    if not columna_cruzar:
        print(f"     ⚠️  No hay columna de cruce configurada")
        return

    print(f"\n  🔗 Enriquecimiento desde archivo externo:")
    print(f"     📂 {os.path.basename(ruta_ext)}")
    
    # Leer archivo externo
    hoja_lookup = (cfg.get("hoja lookup") or cfg.get("hoja externa") or "").strip().strip('"').strip("'")
    df_ext = leer_excel_o_csv(ruta_ext, hoja=hoja_lookup if hoja_lookup else None)
    
    if df_ext is None:
        print(f"     ❌ No se pudo leer el archivo externo")
        return

    # Normalizar columnas eliminando comillas
    df_ext.columns = [str(c).strip().strip('"').strip("'").strip().lower() for c in df_ext.columns]
    
    print(f"     📊 Columnas del archivo externo: {list(df_ext.columns)[:10]}")
    
    # Agregar al caché con alias
    alias_cfg = (cfg.get("alias lookup") or "").strip().strip('"').strip("'")
    alias_base = alias_cfg.lower() if alias_cfg else os.path.splitext(os.path.basename(ruta_ext))[0].lower()
    variantes = {alias_base}
    sin_paren = re.sub(r'\(.*?\)', '', alias_base)
    compacto = re.sub(r'[^a-z0-9]+', ' ', sin_paren).strip()
    variantes.update({sin_paren.strip(), compacto})
    
    for a in variantes:
        cache_hojas[a] = df_ext

    # Validar columnas
    columna_cruzar_norm = columna_cruzar.lower()
    columnas_extraer = parse_lista_columnas(columnas_extraer_raw)
    
    print(f"     🔍 Buscando columna cruzar: '{columna_cruzar_norm}'")
    print(f"     🔍 Columnas a extraer: {columnas_extraer}")
    
    faltantes = [c for c in columnas_extraer if c not in df_ext.columns]
    
    if columna_cruzar_norm not in df_ext.columns:
        print(f"     ❌ Columna cruzar '{columna_cruzar_norm}' no existe en archivo externo")
        print(f"     💡 Columnas disponibles: {list(df_ext.columns)}")
        return
    
    if faltantes:
        print(f"     ❌ Columnas faltantes en archivo externo: {faltantes}")
        print(f"     💡 Columnas disponibles: {list(df_ext.columns)}")
        return
    
    if columna_base_norm and columna_base_norm not in df_base.columns:
        print(f"     ❌ Columna base '{columna_base_norm}' no existe en hoja base")
        print(f"     💡 Columnas disponibles en hoja: {list(df_base.columns)}")
        return

    # Agregar columnas si no existen
    for col in columnas_extraer:
        if col not in df_base.columns:
            df_base[col] = "N/A"

    # Buscar coincidencias y enriquecer
    if columna_base_norm:
        base_series = df_base[columna_base_norm]
        coincidencias = 0
        
        print(f"     🔄 Buscando coincidencias entre '{columna_base_norm}' y '{columna_cruzar_norm}'...")
        
        for idx_base, valor_base in base_series.items():
            idx_match = buscar_coincidencia_parcial(valor_base, df_ext[columna_cruzar_norm])
            if idx_match is not None:
                coincidencias += 1
                for col_extraer in columnas_extraer:
                    df_base.at[idx_base, col_extraer] = df_ext.at[idx_match, col_extraer]
        
        print(f"     ✅ {coincidencias} coincidencia(s) encontrada(s) de {len(df_base)} filas")
        print(f"     📊 Columnas agregadas: {', '.join(columnas_extraer)}")
    else:
        print(f"     ⚠️  No hay columna base configurada, no se puede enriquecer")

def _aplicar_calculos(df_base: pd.DataFrame, cfg: dict, parametros: dict, cache_hojas: dict):
    """
    Aplica fórmulas calculadas a DataFrame.
    """
    calculos = cfg.get("calculos", [])
    
    if not calculos:
        return

    print(f"\n  🧮 Aplicando fórmulas calculadas: {len(calculos)}")
    
    for calc in calculos:
        nombre = calc["nombre"]
        formula = calc["formula"]
        resultados = []
        
        for _, fila in df_base.iterrows():
            val = evaluar_formula(formula, fila, parametros, cache_hojas)
            if val is None or (isinstance(val, float) and pd.isna(val)):
                val = "N/A"
            resultados.append(val)
        
        df_base[nombre] = resultados
        print(f"     ✅ '{nombre}' → {formula[:50]}{'...' if len(formula) > 50 else ''}")
