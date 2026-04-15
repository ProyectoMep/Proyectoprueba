"""
Módulo de limpieza post-enriquecimiento.
Elimina filas según criterios especificados.
"""
import os
import pandas as pd
from openpyxl import load_workbook
from typing import List, Dict, Any
from ..core import limpiar_ruta, leer_configuracion_limpieza
from ..core.file_utils import aplicar_formato_encabezados

def limpiar_datos_enriquecidos(ruta_excel: str, ruta_configuracion: str):
    """
    Limpia datos enriquecidos eliminando filas según grupos de condiciones.
    Grupos se combinan con OR, condiciones dentro de un grupo con AND.
    """
    ruta_excel = limpiar_ruta(ruta_excel)
    
    if not os.path.exists(ruta_excel):
        print(f"❌ Excel no existe: {ruta_excel}")
        return
    
    configuraciones = leer_configuracion_limpieza(ruta_configuracion)
    
    if not configuraciones:
        print("ℹ️  No hay configuraciones de limpieza")
        return
    
    try:
        print(f"\n📄 Limpiando: {os.path.basename(ruta_excel)}")
        print("─" * 70)
        
        excel_file = pd.ExcelFile(ruta_excel)
        hojas_existentes = set(excel_file.sheet_names)
        
        hojas_modificadas = 0
        
        with pd.ExcelWriter(ruta_excel, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            for config in configuraciones:
                hoja = config['hoja']
                grupos_condiciones = config.get('grupos_condiciones', [])
                
                if hoja not in hojas_existentes:
                    continue
                
                if not grupos_condiciones:
                    continue
                
                print(f"\n  🧹 Limpiando hoja: '{hoja}'")
                
                df = excel_file.parse(hoja)
                filas_iniciales = len(df)
                
                # Normalizar columnas para comparación
                df.columns = [str(c).strip().strip('"').strip("'").strip().lower() for c in df.columns]
                
                print(f"     🔍 {len(grupos_condiciones)} grupo(s) de condiciones (conectados con OR):")
                
                mask_eliminar_global = pd.Series([False] * len(df))
                
                for idx_grupo, grupo in enumerate(grupos_condiciones, 1):
                    print(f"\n     [{idx_grupo}] Grupo AND ({len(grupo)} condicion(es)):");
                    
                    # Todas las condiciones del grupo deben cumplirse (AND)
                    mask_grupo = pd.Series([True] * len(df))
                    
                    for cond in grupo:
                        columna = cond['columna']
                        operador = cond['operador']
                        valor = cond['valor']
                        
                        if columna not in df.columns:
                            print(f"        ❌ Columna '{columna}' no existe")
                            mask_grupo = pd.Series([False] * len(df))
                            break
                        
                        # Aplicar operador de comparación
                        if operador == "==":
                            mask_cond = df[columna].astype(str).str.strip().str.lower() == valor.lower()
                            print(f"        • {columna} = '{valor}'")
                        elif operador == "!=":
                            mask_cond = df[columna].astype(str).str.strip().str.lower() != valor.lower()
                            print(f"        • {columna} != '{valor}'")
                        elif operador == "contains":
                            mask_cond = df[columna].astype(str).str.contains(valor, case=False, na=False)
                            print(f"        • {columna} contiene '{valor}'")
                        elif operador == "not_contains":
                            mask_cond = ~df[columna].astype(str).str.contains(valor, case=False, na=False)
                            print(f"        • {columna} NO contiene '{valor}'")
                        elif operador == "vacio":
                            mask_cond = df[columna].isna() | (df[columna].astype(str).str.strip() == "")
                            print(f"        • {columna} está vacío")
                        elif operador == "no_vacio":
                            mask_cond = df[columna].notna() & (df[columna].astype(str).str.strip() != "")
                            print(f"        • {columna} NO está vacío")
                        else:
                            mask_cond = pd.Series([False] * len(df))
                            print(f"        ⚠️  Operador desconocido: {operador}")
                        
                        mask_grupo = mask_grupo & mask_cond
                    
                    # Combinar grupo con OR
                    mask_eliminar_global = mask_eliminar_global | mask_grupo
                    print(f"        → {mask_grupo.sum()} fila(s) cumplen este grupo")
                
                filas_a_eliminar = mask_eliminar_global.sum()
                # Invertir máscara: mantener filas que NO cumplen ningún grupo
                df_limpio = df[~mask_eliminar_global]
                filas_finales = len(df_limpio)
                
                print(f"\n     📊 Resultado:")
                print(f"        • Filas iniciales: {filas_iniciales}")
                print(f"        • Filas eliminadas: {filas_a_eliminar}")
                print(f"        • Filas restantes: {filas_finales}")
                
                df_limpio.to_excel(writer, sheet_name=hoja, index=False)
                hojas_modificadas += 1
        
        # Reaplicar formato visual
        if hojas_modificadas > 0:
            wb = load_workbook(ruta_excel)
            aplicar_formato_encabezados(wb)
            wb.save(ruta_excel)
            print(f"\n  ✅ {hojas_modificadas} hoja(s) limpiada(s)")
        else:
            print(f"\n  ℹ️  No se encontraron hojas para limpiar")
        
    except Exception as e:
        print(f"\n  ❌ Error durante limpieza: {e}")
        import traceback
        traceback.print_exc()
