import os
import pandas as pd
from .file_utils import limpiar_ruta

def leer_excel_o_csv(ruta: str, dtype=str, hoja: str = None) -> pd.DataFrame | None:
    """
    Lee un archivo Excel o CSV y retorna un DataFrame.
    Detecta automáticamente el mejor separador para CSV.
    """
    ruta = limpiar_ruta(ruta)
    if not os.path.exists(ruta):
        print(f"  ❌ Archivo no existe: {ruta}")
        return None

    try:
        extension = os.path.splitext(ruta)[1].lower()

        if extension == ".csv":
            print(f"  📄 Leyendo CSV: {os.path.basename(ruta)}")
            
            # Leer las primeras líneas para detectar el separador
            with open(ruta, 'r', encoding='utf-8-sig') as f:
                primera_linea = f.readline()
            
            # Detectar el separador más probable
            separador_detectado = ','
            if primera_linea.count(';') > primera_linea.count(','):
                separador_detectado = ';'
            
            # Configuraciones a probar en orden de prioridad
            configs = [
                (separador_detectado, 'utf-8-sig'),
                (separador_detectado, 'utf-8'),
                (',' if separador_detectado == ';' else ';', 'utf-8-sig'),
                (',', 'latin-1'),
                (';', 'latin-1'),
            ]
            
            for sep, enc in configs:
                try:
                    df = pd.read_csv(ruta, sep=sep, encoding=enc, dtype=dtype, on_bad_lines="skip")
                    
                    # Normalizar nombres de columnas eliminando comillas
                    df.columns = [str(c).strip().strip('"').strip("'").strip().lower() for c in df.columns]
                    
                    # Verificar que se hayan separado las columnas correctamente
                    if len(df.columns) > 1:
                        print(f"     ✅ Leído correctamente (sep='{sep}', encoding='{enc}', {len(df.columns)} columnas)")
                        return df
                except Exception:
                    continue
            
            print(f"     ❌ No se pudo leer con ninguna configuración")
            return None

        elif extension in [".xlsx", ".xls"]:
            print(f"  📄 Leyendo Excel: {os.path.basename(ruta)}")
            if hoja:
                df = pd.read_excel(ruta, sheet_name=hoja, dtype=dtype)
                # Normalizar columnas
                df.columns = [str(c).strip().strip('"').strip("'").strip().lower() for c in df.columns]
                print(f"     ✅ Hoja '{hoja}' leída correctamente")
                return df
            df = pd.read_excel(ruta, dtype=dtype)
            # Normalizar columnas
            df.columns = [str(c).strip().strip('"').strip("'").strip().lower() for c in df.columns]
            print(f"     ✅ Leído correctamente")
            return df
        else:
            print(f"  ❌ Extensión '{extension}' no soportada")
            return None

    except Exception as e:
        print(f"  ❌ Error al leer archivo: {e}")
        return None
