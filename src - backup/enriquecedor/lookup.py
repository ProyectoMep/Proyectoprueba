import pandas as pd

def buscar_coincidencia_parcial(valor_base, serie_externa: pd.Series):
    """
    Busca coincidencia parcial entre valor_base y valores en serie_externa.
    Retorna índice de primera coincidencia o None.
    """
    if pd.isna(valor_base):
        return None
    
    valor_base_str = str(valor_base).lower().strip()
    if not valor_base_str:
        return None
    
    for idx, val_ext in serie_externa.items():
        if pd.isna(val_ext):
            continue
        val_ext_str = str(val_ext).lower().strip()
        if not val_ext_str:
            continue
        # Coincidencia bidireccional: "A" in "B" o "B" in "A"
        if valor_base_str in val_ext_str or val_ext_str in valor_base_str:
            return idx
    
    return None

def VLOOKUP(valor, hoja_rango, col_key_letra, col_val_letra, cache_hojas: dict, exact=True):
    """
    Implementación de VLOOKUP para fórmulas Excel.
    Busca valor en columna key y retorna valor de columna val.
    """
    hoja_norm = str(hoja_rango).strip().strip("'").strip('"').lower()
    if hoja_norm not in cache_hojas:
        return None
    
    df = cache_hojas[hoja_norm]
    col_key = _excel_col_a_indice(col_key_letra)
    col_val = _excel_col_a_indice(col_val_letra)
    
    if col_key >= len(df.columns) or col_val >= len(df.columns):
        return None
    
    serie_key = df.iloc[:, col_key]
    serie_val = df.iloc[:, col_val]
    valor_str = str(valor).strip().lower()
    
    for k, v in zip(serie_key, serie_val):
        if pd.isna(k):
            continue
        k_str = str(k).strip().lower()
        if (exact and k_str == valor_str) or (not exact and (valor_str in k_str or k_str in valor_str)):
            return v
    
    return None

def LOOKUP(hoja, col_key, valor, col_val, cache_hojas: dict, exact=True):
    """
    Búsqueda por nombre de columna (más flexible que VLOOKUP).
    """
    hoja_norm = str(hoja).strip().strip('"').strip("'").lower()
    if hoja_norm not in cache_hojas:
        return None
    
    df = cache_hojas[hoja_norm]
    df_cols_lower = {c.lower(): c for c in df.columns}
    col_key_norm = str(col_key).lower().strip()
    col_val_norm = str(col_val).lower().strip()
    
    if col_key_norm not in df_cols_lower or col_val_norm not in df_cols_lower:
        return None
    
    serie_key = df[df_cols_lower[col_key_norm]]
    serie_val = df[df_cols_lower[col_val_norm]]
    valor_str = str(valor).strip().lower()
    
    for k, v in zip(serie_key, serie_val):
        if pd.isna(k):
            continue
        k_str = str(k).strip().lower()
        if (exact and k_str == valor_str) or (not exact and (valor_str in k_str or k_str in valor_str)):
            return v
    
    return None

def _excel_col_a_indice(letra: str) -> int:
    """
    Convierte letra de columna Excel (A, B, AA) a índice numérico (0-based).
    Ejemplo: A=0, B=1, Z=25, AA=26
    """
    letra = str(letra).strip().upper()
    total = 0
    for c in letra:
        if not ('A' <= c <= 'Z'):
            return 0
        total = total * 26 + (ord(c) - ord('A') + 1)
    return total - 1
