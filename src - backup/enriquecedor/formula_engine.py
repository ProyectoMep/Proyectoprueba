import re
import pandas as pd
from typing import Any, Dict
from .lookup import VLOOKUP, LOOKUP
from ..utils import COMP_VER

# Funciones Excel

def IF(cond, val_true, val_false):
    try:
        return val_true if cond else val_false
    except Exception:
        return val_false

def IFERROR(expr, fallback):
    try:
        v = expr
        if v is None or (isinstance(v, float) and pd.isna(v)) or (isinstance(v, str) and v.strip() == ""):
            return fallback
        return v
    except Exception:
        return fallback

def AND(*args):
    return all(bool(a) for a in args)

def OR(*args):
    return any(bool(a) for a in args)

def STR(x):
    try:
        return "" if x is None or (isinstance(x, float) and pd.isna(x)) else str(x)
    except Exception:
        return str(x)

# Traducción y evaluación

def traducir_formula_excel(formula: str) -> str:
    """
    Traduce fórmula Excel al formato Python.
    """
    f = formula.strip()
    if f.startswith("="):
        f = f[1:].strip()
    
    f = f.replace(";", ",")
    
    # Reemplazos de funciones
    reemplazos = {
        r"\bSI\.ERROR\s*\(": "IFERROR(",
        r"\bSI\s*\(": "IF(",
        r"\bBUSCARV\s*\(": "VLOOKUP(",
        r"\bY\s*\(": "AND(",
        r"\bO\s*\(": "OR("
    }
    for patron, sub in reemplazos.items():
        f = re.sub(patron, sub, f, flags=re.IGNORECASE)
    
    # Operadores
    f = f.replace("&", "+")
    f = re.sub(r'<>', '!=', f)
    f = re.sub(r'(?<![<>!=])=(?!=)', '==', f)
    
    return f

def reemplazar_referencias_columnas(expr: str, row: pd.Series, parametros: Dict[str, Any]) -> str:
    """
    Reemplaza referencias a columnas y parámetros en la expresión.
    """
    columnas_ordenadas = sorted(row.index, key=len, reverse=True)
    marcador = "___COL___"
    sustituciones = {}
    contador = 0
    
    # Reemplazar columnas con marcadores temporales
    for col in columnas_ordenadas:
        col_escaped = re.escape(col)
        patron = rf'(?<![A-Za-z0-9_\[\]\'"]){col_escaped}(?![A-Za-z0-9_\[\]\'":])'
        
        def reemplazar_con_marcador(match):
            nonlocal contador
            placeholder = f"{marcador}{contador}{marcador}"
            sustituciones[placeholder] = f"row['{col}']"
            contador += 1
            return placeholder
        
        expr = re.sub(patron, reemplazar_con_marcador, expr)
    
    # Sustituir parámetros globales
    for k in parametros.keys():
        k_escaped = re.escape(k)
        expr = re.sub(rf'(?<![A-Za-z0-9_]){k_escaped}(?![A-Za-z0-9_])', k, expr)
    
    # Restaurar marcadores
    for placeholder, sustitucion in sustituciones.items():
        expr = expr.replace(placeholder, sustitucion)
    
    return expr

def evaluar_formula(formula: str, row: pd.Series, parametros: Dict[str, Any], cache_hojas: dict) -> Any:
    """
    Evalúa una fórmula Excel en el contexto de una fila.
    """
    traducida = traducir_formula_excel(formula)
    traducida = reemplazar_referencias_columnas(traducida, row, parametros)
    
    # Entorno de ejecución
    entorno = {
        "IF": IF,
        "IFERROR": IFERROR,
        "AND": AND,
        "OR": OR,
        "VLOOKUP": lambda *args: VLOOKUP(*args, cache_hojas=cache_hojas),
        "LOOKUP": lambda *args: LOOKUP(*args, cache_hojas=cache_hojas),
        "COMP_VER": COMP_VER,
        "STR": STR,
        "row": row
    }
    entorno.update(parametros)
    
    try:
        return eval(traducida, {"__builtins__": {}}, entorno)
    except Exception as e:
        print(f"[DEBUG] Error evaluando fórmula '{formula}': {e}")
        print(f"[DEBUG] Fórmula traducida: {traducida}")
        return None
