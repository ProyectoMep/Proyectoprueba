import pandas as pd

def evaluar_subcriterio(df: pd.DataFrame, columna_criterio: str, subcriterio: str) -> pd.DataFrame:
    """Evalúa un subcriterio y retorna filas que lo cumplen."""
    df[columna_criterio] = df[columna_criterio].astype(str).str.strip()
    
    # Operadores especiales con sintaxis específica
    if subcriterio.startswith("*+") and subcriterio.endswith("+*"):
        # *+valor+* = NO contiene
        valor = subcriterio[2:-2]
        print(f"     🔍 Diferente de lo que contiene '{valor}'")
        mask = ~df[columna_criterio].str.contains(valor, na=False, case=False)
        return df[mask]
    
    elif subcriterio == "*[]*":
        # *[]* = NO vacío
        print(f"     🔍 Valores NO vacíos")
        mask = (df[columna_criterio] != "") & (df[columna_criterio] != "[]") & (~df[columna_criterio].isna())
        return df[mask]
    
    elif subcriterio.startswith("*") and subcriterio.endswith("*"):
        # *valor* = Diferente de
        valor = subcriterio.strip("*")
        print(f"     🔍 Diferente de '{valor}'")
        mask = df[columna_criterio] != valor
        return df[mask]
    
    elif subcriterio == "[]":
        # [] = Vacío
        print(f"     🔍 Valores vacíos")
        mask = (df[columna_criterio] == "") | (df[columna_criterio] == "[]") | (df[columna_criterio].isna())
        return df[mask]
    
    elif subcriterio.startswith("+") and subcriterio.endswith("+"):
        # +valor+ = Contiene
        valor = subcriterio.strip("+")
        print(f"     🔍 Contiene '{valor}'")
        mask = df[columna_criterio].str.contains(valor, na=False, case=False)
        return df[mask]
    
    elif subcriterio.startswith('"') and subcriterio.endswith('"'):
        # "valor" = Igual exacto (con comillas explícitas)
        valor = subcriterio.strip('"')
        print(f"     🔍 Igual a '{valor}'")
        mask = df[columna_criterio] == valor
        return df[mask]
    
    else:
        # valor = Igual por defecto
        print(f"     🔍 Igual a '{subcriterio}'")
        mask = df[columna_criterio] == subcriterio
        return df[mask]

def aplicar_criterio(df: pd.DataFrame, columna_criterio: str, criterio: str) -> tuple[pd.DataFrame, list]:
    """
    Aplica criterio con soporte para OR (||) y AND (&&).
    Retorna (DataFrame filtrado, lista vacía para compatibilidad).
    """
    if not criterio or criterio.strip() == "":
        print("  ℹ️  Criterio vacío → Todas las filas incluidas")
        return df, []

    print(f"  🎯 Aplicando criterio: '{criterio}'")

    if "||" in criterio:
        # OR: combinar resultados de múltiples subcriterios
        subcriterios = [c.strip() for c in criterio.split("||")]
        print(f"     🔀 Operador OR: {len(subcriterios)} condiciones")
        df_filtrado = pd.DataFrame()
        
        for subcriterio in subcriterios:
            sub_df = evaluar_subcriterio(df, columna_criterio, subcriterio)
            if sub_df is not None and not sub_df.empty:
                df_filtrado = pd.concat([df_filtrado, sub_df]).drop_duplicates()
        
        print(f"  ✅ Resultado: {len(df_filtrado)} fila(s)\n")
        return df_filtrado, []
    
    elif "&&" in criterio:
        # AND: aplicar subcriterios secuencialmente
        subcriterios = [c.strip() for c in criterio.split("&&")]
        print(f"     🔗 Operador AND: {len(subcriterios)} condiciones")
        df_filtrado = df.copy()
        
        for subcriterio in subcriterios:
            df_filtrado = evaluar_subcriterio(df_filtrado, columna_criterio, subcriterio)
        
        print(f"  ✅ Resultado: {len(df_filtrado)} fila(s)\n")
        return df_filtrado, []
    
    else:
        # Criterio simple
        df_filtrado = evaluar_subcriterio(df, columna_criterio, criterio)
        print(f"  ✅ Resultado: {len(df_filtrado)} fila(s)\n")
        return df_filtrado, []

def aplicar_criterios_multiples(df: pd.DataFrame, criterios_config: dict) -> tuple[pd.DataFrame, list]:
    """
    Aplica múltiples criterios en diferentes columnas con operador AND.
    Retorna (DataFrame filtrado, lista vacía para compatibilidad).
    """
    df_filtrado = df.copy()
    
    criterios_encontrados = []
    
    # Criterio principal
    if 'columna criterio' in criterios_config:
        columna = criterios_config.get('columna criterio', '').strip().strip('"').strip("'").strip()
        criterio_valor = criterios_config.get('criterio', '').strip()
        if columna and criterio_valor:
            criterios_encontrados.append({'columna': columna, 'criterio': criterio_valor})
    
    # Criterios adicionales (criterio 2, 3, ...)
    i = 2
    while f'columna criterio {i}' in criterios_config or f'criterio {i}' in criterios_config:
        columna = criterios_config.get(f'columna criterio {i}', '').strip().strip('"').strip("'").strip()
        criterio_valor = criterios_config.get(f'criterio {i}', '').strip()
        if columna and criterio_valor:
            criterios_encontrados.append({'columna': columna, 'criterio': criterio_valor})
        i += 1
    
    if not criterios_encontrados:
        print("  ℹ️  No hay criterios válidos (columna + criterio) → Todas las filas incluidas")
        print(f"  ✅ Total: {len(df_filtrado)} fila(s)\n")
        return df_filtrado, []
    
    print(f"\n  🔗 Aplicando {len(criterios_encontrados)} criterio(s) con AND:")
    print("  " + "─" * 66)
    
    # Aplicar cada criterio secuencialmente (AND)
    for idx, config in enumerate(criterios_encontrados, 1):
        columna = config['columna'].strip().lower()
        criterio_valor = config['criterio']
        
        print(f"\n  [{idx}] Columna: '{columna}'")
        
        if columna not in df_filtrado.columns:
            print(f"      ❌ Columna no existe → Omitiendo")
            continue
        
        df_filtrado, _ = aplicar_criterio(df_filtrado, columna, criterio_valor)
    
    print("  " + "─" * 66)
    print(f"  ✅ TOTAL FINAL: {len(df_filtrado)} fila(s) cumplen TODOS los criterios\n")
    
    return df_filtrado, []
