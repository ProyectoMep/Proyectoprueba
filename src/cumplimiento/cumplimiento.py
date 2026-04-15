#!/usr/bin/env python3
"""
check_cumplimiento_full_doc.py

Versión documentada del motor de cumplimiento:
- Lee una plantilla .txt con bloques por métrica.
- Lee archivos CSV/XLSX (usa la función leer_excel_o_csv).
- Aplica enrichments (left merges).
- Crea columnas calculadas usando funciones registradas.
- Evalúa criterios lógicos (columna=..., valor=...) con && / || / paréntesis.
- Soporta métricas tipo '%' y 'N' (lista de no-conformes).
- Genera un DataFrame resumen y lo guarda como CSV.

Uso:
    python check_cumplimiento_full_doc.py plantilla_cumplimiento.txt
  o (interactivo)
    python check_cumplimiento_full_doc.py
    > ingresa la ruta cuando el script la solicite

Requisitos:
    pandas, openpyxl
"""

from __future__ import annotations
import os
import re
import sys
import math
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# -----------------------------------------------------------------------------
# 1) Funciones de lectura (tu función original, con docstring)
# -----------------------------------------------------------------------------
def limpiar_ruta(ruta: str) -> str:
    """
    Limpia rutas eliminando prefijos file:/// y caracteres especiales.
    """
    if ruta is None:
        return ""
    
    # Eliminar comillas dobles y simples del inicio y final
    ruta = ruta.strip().strip('"').strip("'")
    
    # Eliminar comillas internas que quedaron (como "valor")
    ruta = ruta.replace('"', '').replace("'", '')
    
    # Procesar prefijos file://
    if ruta.startswith("file:///"):
        ruta = ruta[8:].replace("%20", " ")
    elif ruta.startswith("file:"):
        ruta = ruta[5:].replace("%20", " ")
    
    return ruta

def leer_excel_o_csv(ruta: str, dtype=str, hoja: str = None) -> Optional[pd.DataFrame]:
    """
    Lee un archivo Excel (.xlsx/.xls) o CSV y retorna un DataFrame (o None si falla).

    Comportamiento:
    - Detecta separador de CSV entre ',' y ';' probando varias combinaciones de encoding.
    - Para Excel lee la primera hoja por defecto (o la hoja indicada por 'hoja').
    - Normaliza nombres de columnas a minúsculas y elimina comillas en los encabezados.
    - Si no existe el archivo o la lectura falla, devuelve None.

    Parámetros:
    - ruta: ruta al archivo (string).
    - dtype: tipo por defecto para pandas (aquí usamos str para leer todo como texto).
    - hoja: nombre de hoja (solo para Excel). Si None, lee la primera hoja.

    Retorna:
    - pd.DataFrame si se pudo leer, o None en caso de error.
    """
    ruta = limpiar_ruta(ruta)
    if not os.path.exists(ruta):
        print(f"  ❌ Archivo no existe: {ruta}")
        return None

    try:
        extension = os.path.splitext(ruta)[1].lower()

        if extension == ".csv":
            print(f"  📄 Leyendo CSV: {os.path.basename(ruta)}")
            # Detectar separador por inspección de primera línea
            with open(ruta, 'r', encoding='utf-8-sig') as f:
                primera_linea = f.readline()
            separador_detectado = ','
            if primera_linea.count(';') > primera_linea.count(','):
                separador_detectado = ';'
            # Probar distintas combinaciones de separador/encoding
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
                    df.columns = [str(c).strip().strip('"').strip("'").strip().lower() for c in df.columns]
                    # heurística: considerar leída correctamente si hay más de 1 columna
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
                df.columns = [str(c).strip().strip('"').strip("'").strip().lower() for c in df.columns]
                print(f"     ✅ Hoja '{hoja}' leída correctamente")
                return df
            df = pd.read_excel(ruta, dtype=dtype)
            df.columns = [str(c).strip().strip('"').strip("'").strip().lower() for c in df.columns]
            print(f"     ✅ Leído correctamente")
            return df
        else:
            print(f"  ❌ Extensión '{extension}' no soportada")
            return None

    except Exception as e:
        print(f"  ❌ Error al leer archivo: {e}")
        return None

def read_input_wrapper(path: str) -> pd.DataFrame:
    """
    Wrapper que usa leer_excel_o_csv y lanza excepción si no se pudo leer.
    Asegura que las columnas estén en minúsculas.
    """
    df = leer_excel_o_csv(path, dtype=str, hoja=None)
    if df is None:
        raise FileNotFoundError(f"No se pudo leer: {path}")
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df

# -----------------------------------------------------------------------------
# 2) Detección de "vacío" en Series / valores
# -----------------------------------------------------------------------------
def is_empty_series(s: pd.Series) -> pd.Series:
    """
    Devuelve una pd.Series booleana que indica si cada valor es considerado vacío.

    Considera vacío:
    - NaN nativo de pandas
    - cadena vacía "" o solo espacios
    - texto literal "[]" o "[ ]"
    - texto "none" o "nan" (case-insensitive)

    Parámetros:
    - s: pd.Series

    Retorna:
    - pd.Series(bool) con el mismo índice.
    """
    s_str = s.astype(str).str.strip().str.lower()
    return s.isna() | (s_str == "") | (s_str == "[]") | (s_str == "[ ]") | (s_str == "none") | (s_str == "nan")

def resolve_column_name(df: pd.DataFrame, requested: str) -> Optional[str]:
    """
    Intenta resolver el nombre de columna real en df dado un 'requested' (lo que viene en la plantilla).
    Reglas (en orden):
      1. Coincidencia exacta (case-insensitive) -> devuelve nombre real.
      2. Busca columnas que terminen con '_' + requested (sufijo por prefijo de enrich), devuelve la primera.
      3. Busca columnas que contengan '_' + requested + (espacio o fin) o ' ' + requested (más tolerante).
      4. Si hay exactamente una columna en df cuyo nombre contiene requested como substring -> la devuelve.
      5. Si no encuentra -> None.
    Esto evita falsos positivos intentando resolver aliases generados por prefijos.
    """
    if requested is None:
        return None
    req = requested.strip().lower()

    # 1) exact match
    for c in df.columns:
        if str(c).strip().lower() == req:
            return c

    # 2) columns that end with _{req}
    suffix = f"_{req}"
    candidates = [c for c in df.columns if str(c).strip().lower().endswith(suffix)]
    if candidates:
        return candidates[0]

    # 3) columns that contain _{req} or ' {req}' segments
    pattern = re.compile(rf"(_| |\b){re.escape(req)}($|_| )", flags=re.IGNORECASE)
    candidates = [c for c in df.columns if pattern.search(str(c))]
    if candidates:
        return candidates[0]

    # 4) loose substring (only if unique)
    candidates = [c for c in df.columns if req in str(c).strip().lower()]
    if len(candidates) == 1:
        return candidates[0]

    return None


# -----------------------------------------------------------------------------
# 3) Funciones utilitarias y funciones "columna calcular" documentadas
# -----------------------------------------------------------------------------
def _is_version_like(s: Optional[str]) -> bool:
    """
    Heurística para detectar si un string parece una versión (ej. '1.2.3', '10.0').
    """
    if s is None:
        return False
    s = str(s).strip()
    s_clean = s.lstrip("vV")
    return bool(re.match(r"^\d+(\.\d+)+($|[^0-9])", s_clean)) or bool(re.match(r"^\d+(\.\d+)*$", s_clean))

def _parse_version_to_tuple(s: str) -> Tuple[int, ...]:
    """
    Convierte un string de versión a una tupla de ints, por ejemplo '1.2.3' -> (1,2,3).
    Intenta extraer números si hay sufijos no numéricos.
    """
    s = str(s).strip().lstrip("vV")
    m = re.match(r"^(\d+(?:\.\d+)*)", s)
    ver = m.group(1) if m else s
    parts: List[int] = []
    for p in ver.split("."):
        p = p.strip()
        if p == "":
            parts.append(0)
            continue
        nums = re.findall(r"\d+", p)
        try:
            parts.append(int(nums[0]) if nums else 0)
        except Exception:
            parts.append(0)
    return tuple(parts)

def compare_versions(a: Any, b: Any) -> int:
    """
    Compara lexicalmente dos versiones parseadas.
    Returns:
        -1 si a < b
         0 si a == b
         1 si a > b
    Lanza excepción si no es posible parsear (se captura donde se llama).
    """
    ta = _parse_version_to_tuple(str(a))
    tb = _parse_version_to_tuple(str(b))
    L = max(len(ta), len(tb))
    for i in range(L):
        va = ta[i] if i < len(ta) else 0
        vb = tb[i] if i < len(tb) else 0
        if va < vb:
            return -1
        if va > vb:
            return 1
    return 0

# Parámetro configurable: umbral en días para considerar fecha "vieja"
DATE_THRESHOLD_DAYS = 180

def comparar_version(os_version_val: Any, ultima_actualizacion_val: Any) -> str:
    """
    Función registrada para 'Columna calcular' que implementa la lógica:
    - Si ambos parecen versiones, compara numeric. Si os_version < ultima_actualizacion -> "desactualizado (<ult>)"
      else -> "actualizado".
    - Si ultima_actualizacion parece fecha parseable y la fecha es mayor a DATE_THRESHOLD_DAYS -> desactualizado.
    - En caso de datos insuficientes o errores -> "N/A".

    Parámetros:
    - os_version_val: valor de la columna con versión del dispositivo
    - ultima_actualizacion_val: valor de la columna que indica versión o fecha de última actualización

    Retorna:
    - string: "actualizado", "desactualizado (<valor>)" o "N/A"
    """
    try:
        osv = None if pd.isna(os_version_val) else str(os_version_val).strip()
        ult = None if pd.isna(ultima_actualizacion_val) else str(ultima_actualizacion_val).strip()

        if not osv and not ult:
            return "N/A"

        # Si ambos parecen versiones -> comparar
        if osv and ult and _is_version_like(osv) and _is_version_like(ult):
            try:
                cmp_res = compare_versions(osv, ult)
            except Exception:
                return "N/A"
            if cmp_res < 0:
                return f"desactualizado ({ult})"
            else:
                return "actualizado"

        # Si ult parece version pero osv no -> no hay comparación fiable
        if ult and _is_version_like(ult) and osv and not _is_version_like(osv):
            return "N/A"

        # Intentar interpretar ultima_actualizacion como fecha
        if ult:
            dt = pd.to_datetime(ult, errors="coerce", dayfirst=False)
            if not pd.isna(dt):
                now = pd.Timestamp.now(tz=None)
                days_diff = (now - dt).days
                if days_diff > DATE_THRESHOLD_DAYS:
                    return f"desactualizado ({ult})"
                else:
                    return "actualizado"

        return "N/A"
    except Exception:
        return "N/A"

def dias_desde(fecha_val: Any) -> Optional[int]:
    """
    Devuelve número de días desde 'fecha_val' hasta hoy, o None si no parseable.
    """
    try:
        if pd.isna(fecha_val):
            return None
        dt = pd.to_datetime(fecha_val, errors="coerce", dayfirst=False)
        if pd.isna(dt):
            return None
        now = pd.Timestamp.now(tz=None)
        return (now - dt).days
    except Exception:
        return None

def es_vacio(val: Any) -> bool:
    """
    Versión escalar de la comprobación de vacío. Útil dentro de funciones de columna calcular.
    """
    if val is None:
        return True
    s = str(val).strip().lower()
    return s in ("", "[]", "[ ]", "none", "nan")

def concat(*vals: Any, sep: str = " ") -> str:
    """
    Concatena los valores no-vacíos con separador. Retorna cadena vacía si no hay partes.
    """
    parts = [str(v).strip() for v in vals if not (v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip() == "")]
    return sep.join(parts)

# Registro de funciones permitidas en 'Columna calcular'
FUNCIONES_CALCULO: Dict[str, Any] = {
    "comparar_version": comparar_version,
    "dias_desde": dias_desde,
    "es_vacio": es_vacio,
    "concat": concat,
}



# -----------------------------------------------------------------------------
# 4) Parser de plantilla (docstring)
# -----------------------------------------------------------------------------
def read_template(path: str) -> List[Dict[str, Any]]:
    """
    Parse minimalista de la plantilla de texto.

    Soporta:
    - Bloques separados por líneas vacías.
    - Claves simples 'Key: Value' (Input, Métrica, Cumplimiento, Criterio favor, Criterio total, Total-override, Sep).
    - Sección 'Enriquecer:' con items iniciados por '-' y claves indentadas (Archivo, Columna base, Columna cruzar, Columnas extraer, Prefijo, Tipo).
    - Líneas 'Columna calcular: name = func(arg1, arg2, ...)' (puede repetirse).

    Retorna:
    - Lista de dicts (un dict por bloque).
    """
    text = Path(path).read_text(encoding="utf-8")
    lines = [ln.rstrip() for ln in text.splitlines()]

    blocks: List[List[str]] = []
    cur: List[str] = []
    for ln in lines:
        if ln.strip().startswith("#"):
            continue
        if ln.strip() == "":
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(ln)
    if cur:
        blocks.append(cur)

        # --- PARCHE: fusionar bloques huérfanos de Enriquecer / Columna calcular ---
    merged_blocks: List[List[str]] = []
    for b in blocks:
        first_nonempty = None
        for ln in b:
            if ln.strip() != "":
                first_nonempty = ln.strip().lower()
                break
        if first_nonempty and first_nonempty.startswith(("enriquecer", "columna calcular", "columna calcular:", "columna calcular")):
            if not merged_blocks:
                merged_blocks.append(b)
            else:
                # anexar estas líneas al bloque anterior (preserva orden)
                merged_blocks[-1].extend(b)
        else:
            merged_blocks.append(b)
    blocks = merged_blocks

    parsed_blocks: List[Dict[str, Any]] = []
    for b in blocks:
        d: Dict[str, Any] = {}
        i = 0
        while i < len(b):
            ln = b[i].strip()
            # Key: value simple
            if ":" in ln and not ln.lower().startswith("enriquecer") and not ln.lower().startswith("columna calcular"):
                key, val = ln.split(":", 1)
                k = key.strip().lower()
                v = val.strip()
                if k == "input":
                    d["input"] = v.strip().strip('"').strip("'")
                elif k in ("métrica","metrica","métrica"):
                    d["metrica"] = v
                elif k == "cumplimiento":
                    d["cumplimiento_raw"] = v
                elif k == "criterio favor":
                    d["criterio_favor"] = v
                elif k == "criterio total":
                    d["criterio_total"] = v
                elif k == "sep":
                    d["sep"] = v
                elif k == "total-override":
                    try:
                        d["total_override"] = int(float(v))
                    except Exception:
                        d["total_override"] = None
                else:
                    d[k] = v
                i += 1
                continue

            # Sección Enriquecer
            if ln.lower().startswith("enriquecer"):
                enrich_list: List[Dict[str, str]] = []
                i += 1
                cur_en: Optional[Dict[str, str]] = None
                while i < len(b) and b[i].strip() != "":
                    line = b[i]
                    stripped = line.strip()
                    if stripped.startswith("-"):
                        if cur_en:
                            enrich_list.append(cur_en)
                        cur_en = {}
                        rest = stripped[1:].strip()
                        if ":" in rest:
                            k2, v2 = rest.split(":",1)
                            cur_en[k2.strip().lower()] = v2.strip()
                        i += 1
                        continue
                    if ":" in stripped and cur_en is not None:
                        k2, v2 = stripped.split(":",1)
                        cur_en[k2.strip().lower()] = v2.strip().strip('"').strip("'")
                    elif cur_en is None and ":" in stripped:
                        cur_en = {}
                        k2, v2 = stripped.split(":",1)
                        cur_en[k2.strip().lower()] = v2.strip().strip('"').strip("'")
                    i += 1
                if cur_en:
                    enrich_list.append(cur_en)
                d["enriquecer"] = enrich_list
                continue

            # Columna calcular
            if ln.lower().startswith("columna calcular"):
                rest = ln.split(":",1)[1].strip()
                if "=" in rest:
                    left, right = rest.split("=",1)
                    colname = left.strip()
                    expr = right.strip()
                    d.setdefault("columnas_calcular", []).append({"nombre": colname, "expr": expr})
                i += 1
                continue

            i += 1

        # Añadir bloque si tiene algo útil
        if "metrica" in d or "input" in d:
            parsed_blocks.append(d)
        else:
            print(f"[WARN] Bloque omitido (no tiene métrica ni input): {b[:2]}")
    return parsed_blocks

# -----------------------------------------------------------------------------
# 5) Evaluación de criterios lógicos (docstrings incluidas)
# -----------------------------------------------------------------------------
ATOM_RE = re.compile(
    r"""columna\s*=\s*(?P<col>[^,()]+?)\s*,\s*valor\s*=\s*(?P<val>.+)""",
    flags=re.IGNORECASE,
)

# Reemplaza la implementación previa de tokenize_logic por esta:
def tokenize_logic(expr: Optional[str]) -> List[str]:
    """
    Tokeniza una expresión lógica compuesta por:
      - átomos de la forma: columna=..., valor=...
      - operadores: &&, ||
      - paréntesis: ( )
    Esta versión es robusta frente a comas, paréntesis, espacios dentro de los átomos.
    """
    if not expr:
        return []
    s = expr.strip()
    tokens: List[str] = []
    i = 0
    L = len(s)

    def starts_at(sub: str) -> bool:
        return s.startswith(sub, i)

    while i < L:
        # saltar espacios
        if s[i].isspace():
            i += 1
            continue

        # operadores
        if starts_at("&&"):
            tokens.append("&&"); i += 2; continue
        if starts_at("||"):
            tokens.append("||"); i += 2; continue

        # paréntesis
        if s[i] == "(":
            tokens.append("("); i += 1; continue
        if s[i] == ")":
            tokens.append(")"); i += 1; continue

        # Si empieza un átomo (buscamos 'columna=' desde aquí, case-insensitive)
        # o puede empezar con 'columna' en minúsculas/ mayúsculas.
        rem = s[i:].lstrip()
        # recalcular offset if we stripped spaces
        leading_spaces = len(s[i:]) - len(rem)
        if leading_spaces:
            i += leading_spaces
            continue

        # Detectamos inicio de átomo si la porción actual comienza por 'columna'
        if re.match(r"(?i)^columna\s*=", s[i:]):
            # buscamos el final del átomo: es el primer punto donde aparece
            # un operador && o || o un paréntesis ')' a nivel actual.
            depth = 0
            j = i
            while j < L:
                if s.startswith("&&", j) or s.startswith("||", j):
                    # opérator encontrado -> atom ends before it (but ensure not inside parentheses)
                    if depth == 0:
                        break
                    else:
                        j += 2
                        continue
                ch = s[j]
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    if depth == 0:
                        # a closing paren at same level: atom ends before this
                        break
                    depth -= 1
                j += 1
            atom = s[i:j].strip()
            tokens.append(atom)
            i = j
            continue

        # Si no es columna=..., tomamos hasta el siguiente operador/paréntesis como token (fallback)
        # Esto permite tratar casos como valores solitarios o textos envueltos en paréntesis.
        j = i
        while j < L and not s.startswith("&&", j) and not s.startswith("||", j) and s[j] not in ("(", ")"):
            j += 1
        tok = s[i:j].strip()
        if tok:
            tokens.append(tok)
        i = j

    # Filtrar tokens vacíos y limpiarlos
    tokens = [t for t in tokens if t and t.strip()]
    return tokens

def atoms_to_series(df: pd.DataFrame, atom_tokens: List[str]) -> Dict[str, pd.Series]:
    """
    Convierte tokens-átomo a un map token -> pd.Series(bool) evaluando cada átomo sobre df.
    """
    res: Dict[str, pd.Series] = {}
    for atom in atom_tokens:
        if atom in ("&&","||","(",")"):
            continue
        if atom in res:
            continue
        m = ATOM_RE.search(atom)
        if not m:
            res[atom] = pd.Series(False, index=df.index)
            continue
        col = m.group("col").strip().lower()
        val = m.group("val").strip()
        res[atom] = eval_atom(df, col, val)
    return res

def eval_atom(df: pd.DataFrame, colname: str, val_token: str) -> pd.Series:
    """
    Evalúa un átomo sobre el DataFrame y retorna Series[bool].
    Soporta:
      - columna == '[]'  -> todas las filas (True)
      - val == '[]' -> vacío (is_empty_series)
      - val == '*[]*' -> NO vacío  (es decir, ~is_empty_series)
      - +X+ -> contiene X (case-insensitive)
      - *X* -> not equal X
      - *+X+* -> not contains X
      - plain equality (case-insensitive)
    Además resuelve nombres de columna enriquecidos (p.ej. 'name' -> 'cmdb_name') mediante resolve_column_name.
    """
    col = colname.strip().lower()
    val = val_token.strip()

    # special: total all
    if col == "[]":
        return pd.Series(True, index=df.index)

    # try to resolve requested column to actual df column
    actual_col = resolve_column_name(df, col)
    if actual_col is None:
        print(f"[WARN] Columna '{col}' no encontrada en dataframe. Intentando match sufix/prefijo no hallado. Se tratará como NO cumple.")
        return pd.Series(False, index=df.index)

    s = df[actual_col].astype(object)

    # valor vacío explícito
    if val == "[]":
        return is_empty_series(s)

    # valor not-empty expresado como *[]*
    if val == "*[]*":
        return ~is_empty_series(s)

    # contains +X+
    m = re.match(r"^\+(.*)\+$", val)
    if m:
        needle = m.group(1)
        return s.fillna("").astype(str).str.contains(re.escape(needle), case=False, na=False)

    # not equals *X*  or not contains *+X+*
    m = re.match(r"^\*(.+)\*$", val)
    if m:
        inner = m.group(1)
        m2 = re.match(r"^\+(.*)\+$", inner)
        if m2:
            needle = m2.group(1)
            return ~s.fillna("").astype(str).str.contains(re.escape(needle), case=False, na=False)
        else:
            return ~(s.fillna("").astype(str).str.lower() == inner.lower())

    # plain equality (case-insensitive)
    return s.fillna("").astype(str).str.lower() == val.lower()

def shunting_yard_to_rpn(tokens: List[str]) -> List[str]:
    """
    Transforma tokens infix a RPN usando la precedencia && > ||.
    """
    out: List[str] = []
    opstack: List[str] = []
    prec = {"&&":2, "||":1}
    for t in tokens:
        if t in ("&&","||"):
            while opstack and opstack[-1] not in ("(",")") and prec.get(opstack[-1],0) >= prec[t]:
                out.append(opstack.pop())
            opstack.append(t)
        elif t == "(":
            opstack.append(t)
        elif t == ")":
            while opstack and opstack[-1] != "(":
                out.append(opstack.pop())
            if opstack and opstack[-1] == "(":
                opstack.pop()
        else:
            out.append(t)
    while opstack:
        out.append(opstack.pop())
    return out

def eval_rpn_on_df(rpn: List[str], atom_series: Dict[str, pd.Series]) -> pd.Series:
    """
    Evalúa una expresión RPN sobre las Series booleanas de atom_series.
    """
    stack: List[pd.Series] = []
    for t in rpn:
        if t == "&&":
            b = stack.pop(); a = stack.pop(); stack.append(a & b)
        elif t == "||":
            b = stack.pop(); a = stack.pop(); stack.append(a | b)
        else:
            series = atom_series.get(t)
            if series is None:
                idx = next(iter(atom_series.values())).index if atom_series else pd.Index([])
                series = pd.Series(False, index=idx)
            stack.append(series)
    return stack[-1] if stack else pd.Series(False, index=next(iter(atom_series.values())).index if atom_series else pd.Index([]))

def evaluate_criteria(df: pd.DataFrame, crit_raw: Optional[str]) -> pd.Series:
    """
    Evalúa un criterio lógico completo y retorna una Series booleana con filas que cumplen.
    Si crit_raw es None o vacío -> todas las filas cumplen (True).
    """
    if crit_raw is None:
        return pd.Series(True, index=df.index)
    s = crit_raw.strip()
    if s == "":
        return pd.Series(True, index=df.index)
    if re.search(r"columna\s*=\s*\[\]\s*,\s*valor\s*=\s*\[\]", s, flags=re.IGNORECASE):
        return pd.Series(True, index=df.index)
    tokens = tokenize_logic(s)
    atom_tokens = [t for t in tokens if t not in ("&&","||","(",")")]
    atom_map = atoms_to_series(df, atom_tokens)
    rpn = shunting_yard_to_rpn(tokens)
    res_series = eval_rpn_on_df(rpn, atom_map)
    res_series.index = df.index
    return res_series.fillna(False)

# -----------------------------------------------------------------------------
# 6) Enriquecimiento (left merges)
# -----------------------------------------------------------------------------
def apply_enrichments(df: pd.DataFrame, enrich_list: List[Dict[str,str]]) -> pd.DataFrame:
    """
    Aplica una lista de enriquecimientos (left merges) sobre df.

    Cada item del enrich_list puede contener:
    - Archivo: ruta al archivo de enriquecimiento (soporta "ruta|hoja" o "ruta::hoja")
    - Columna base: columna(s) en df base (separadas por coma o '+')
    - Columna cruzar: columna(s) en archivo enrich
    - Columnas extraer: columnas a traer (separadas por '+' o ',')
    - Prefijo: prefijo para las columnas traídas (evita colisiones)
    - Tipo: 'left' o 'inner' (por defecto 'left')

    Retorna:
    - DataFrame resultante tras aplicar todos los merges en orden.
    """
    if not enrich_list:
        return df
    current = df.copy()

    for en in enrich_list:
        # normalizar claves posibles para la ruta/archivo
        archivo_raw = en.get("archivo") or en.get("Archivo") or en.get("file") or en.get("ruta") or en.get("ruta:")
        if not archivo_raw:
            print(f"[WARN] Enriquecer item sin 'Archivo': {en}")
            continue
        archivo_raw = str(archivo_raw).strip().strip('"').strip("'")

        # soportar "ruta|hoja" o "ruta::hoja"
        hoja = None
        if "|" in archivo_raw:
            archivo_path, hoja = archivo_raw.split("|", 1)
            archivo_path = archivo_path.strip()
            hoja = hoja.strip()
        elif "::" in archivo_raw:
            archivo_path, hoja = archivo_raw.split("::", 1)
            archivo_path = archivo_path.strip()
            hoja = hoja.strip()
        else:
            archivo_path = archivo_raw

        # otras keys
        col_base = en.get("columna base") or en.get("columna_base") or en.get("columna") or en.get("left")
        col_cruzar = en.get("columna cruzar") or en.get("columna_cruzar") or en.get("columna_cruza") or en.get("right")
        cols_extraer = en.get("columnas extraer") or en.get("columnas_extraer") or en.get("columnas") or en.get("extract") or ""
        prefijo = (en.get("prefijo") or en.get("pref") or Path(archivo_path).stem).lower().replace(" ", "_")
        how = (en.get("tipo") or en.get("type") or "left").lower()

        # parse keys
        left_keys = [c.strip().lower() for c in re.split(r",|\+", col_base)] if col_base else []
        right_keys = [c.strip().lower() for c in re.split(r",|\+", col_cruzar)] if col_cruzar else []
        extract_cols = [c.strip() for c in re.split(r"\+|,|\s\+\s", cols_extraer) if c.strip()]

        # leer archivo enrich (usar hoja si se indica)
        try:
            if hoja:
                df_en = leer_excel_o_csv(archivo_path, dtype=str, hoja=hoja)
            else:
                df_en = leer_excel_o_csv(archivo_path, dtype=str)
            if df_en is None:
                raise FileNotFoundError("None")
        except Exception as e:
            print(f"[WARN] No se pudo leer archivo de enriquecimiento '{archivo_path}' (hoja={hoja}): {e}")
            continue

        # normalizar nombres en df_en
        df_en.columns = [str(c).strip().lower() for c in df_en.columns]

        # construir rename_map: original_col_en -> prefijo_original_col_en
        rename_map: Dict[str,str] = {}
        for c in extract_cols:
            c_low = c.strip().lower()
            # si existe exactamente en df_en
            if c_low in df_en.columns:
                rename_map[c_low] = f"{prefijo}_{c_low}".lower()
            else:
                # intentar mapear a una columna candidata que contenga c_low
                for cand in df_en.columns:
                    if c_low == cand or c_low in cand:
                        rename_map[cand] = f"{prefijo}_{cand}".lower()
                        break

        # columnas necesarias para el subset (joins + extras)
        cols_needed: List[str] = []
        for rk in right_keys:
            if rk in df_en.columns:
                cols_needed.append(rk)
            else:
                print(f"[WARN] Columna join '{rk}' no encontrada en archivo de enrich {archivo_path}")
        # añadir columnas extraídas (orig o candidate)
        for orig in list(rename_map.keys()):
            # orig puede ser key real o candidate
            if orig in df_en.columns and orig not in cols_needed:
                cols_needed.append(orig)
        if not cols_needed:
            print(f"[WARN] No se encontraron columnas útiles en enrich '{archivo_path}'. Omitiendo.")
            continue

        # seleccionar subset y renombrar
        df_en_sub = df_en[cols_needed].copy()
        # rename_actual: mapping de nombres actuales en df_en_sub -> nuevo nombre prefijado
        rename_actual: Dict[str,str] = {}
        for k, v in rename_map.items():
            # si k existe en df_en_sub lo renombramos
            if k in df_en_sub.columns:
                rename_actual[k] = v
            else:
                # buscar candidate que contenga k
                for c in df_en_sub.columns:
                    if k in c:
                        rename_actual[c] = v
                        break
        if rename_actual:
            df_en_sub = df_en_sub.rename(columns=rename_actual)

        # validations for join keys
        if not left_keys or not right_keys:
            print(f"[WARN] Enriquecimiento mal configurado (falta columna base o columna cruzar) para archivo {archivo_path}")
            continue
        if len(left_keys) != len(right_keys):
            if len(right_keys) == 1:
                right_keys = right_keys * len(left_keys)
            else:
                print(f"[WARN] Número de columnas de join distinto entre base ({len(left_keys)}) y enrich ({len(right_keys)}). Omitiendo.")
                continue

        # resolver left_on usando resolve_column_name(current, key)
        left_on: List[str] = []
        for k in left_keys:
            resolved = None
            try:
                resolved = resolve_column_name(current, k)
            except Exception:
                resolved = None
            if resolved:
                left_on.append(resolved)
            else:
                # dejar la key literal (puede fallar si no existe)
                left_on.append(k)

        # ejecutar merge
        try:
            current = current.merge(df_en_sub, how=how, left_on=left_on, right_on=right_keys, suffixes=("", "_enrich"))
            # normalizar
            current.columns = [str(c).strip().lower() for c in current.columns]

            # crear alias sin prefijo para cada columna renombrada (si no existía previamente)
            for actual_pref in rename_actual.values():
                # actual_pref ejemplo: 'cmdb_name'
                if actual_pref in current.columns:
                    # bare: nombre original sin prefijo (todo después del primer '_')
                    bare = actual_pref.split("_", 1)[-1] if "_" in actual_pref else actual_pref
                    if bare not in current.columns:
                        current[bare] = current[actual_pref]
        except Exception as e:
            print(f"[WARN] Error al hacer merge con {archivo_path}: {e}")
            continue

    return current
# -----------------------------------------------------------------------------
# 7) Cálculo por bloque y reglas de cumplimiento
# -----------------------------------------------------------------------------
def parse_cumplimiento_field(raw: Optional[str]) -> Tuple[str, float]:
    """
    Parsea el campo 'Cumplimiento' de la plantilla.
    Formatos aceptados:
        '% 0.97'  -> retorna ('%', 0.97)
        'N 0'     -> retorna ('N', 0.0)
    Lanza ValueError si no puede parsear.
    """
    if not raw:
        raise ValueError("Campo cumplimiento vacío")
    raw = raw.strip()
    m = re.match(r"^(%|N)\s+([0-9]*\.?[0-9]+)", raw, flags=re.IGNORECASE)
    if not m:
        raise ValueError(f"No se pudo parsear cumplimiento: '{raw}'")
    t = m.group(1).upper()
    v = float(m.group(2))
    return t, v

def process_block(block: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa un bloque de la plantilla:
    - lee input
    - aplica enrichments
    - ejecuta columnas_calcular (si las hay)
    - evalúa criterios y produce una fila resumen con campos:
      'Métrica','Total','Favor','No Cumplen','Cumplimiento','Requerido','Status'
    """
    input_path = block.get("input")
    metrica = block.get("metrica", "SIN_NOMBRE")
    cumplimiento_raw = block.get("cumplimiento_raw")
    criterio_total_raw = block.get("criterio_total")
    criterio_favor_raw = block.get("criterio_favor")
    total_override = block.get("total_override", None)
    columnas_calcular = block.get("columnas_calcular", [])

 

    # 1) leer input
    try:
        df = read_input_wrapper(input_path)
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[ERROR] No se pudo leer input '{input_path}' para métrica '{metrica}': {e}")
        return {
            "Métrica": metrica,
            "Total": None,
            "Favor": None,
            "No Cumplen": None,
            "Cumplimiento": None,
            "Requerido": cumplimiento_raw or "",
            "Status": "Error: read",
        }

    # 2) aplicar enrichments
    enrich_list = block.get("enriquecer", [])
    if enrich_list:
        df = apply_enrichments(df, enrich_list)
        

    # 3) columnas calcular
    if columnas_calcular:
        for cc in columnas_calcular:
            nombre = cc.get("nombre").strip().lower()
            expr = cc.get("expr").strip()
            m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*)\)\s*$", expr)
            if not m:
                df[nombre] = pd.NA
                continue
            func_name = m.group(1)
            args_str = m.group(2).strip()
            args = [a.strip().lower() for a in re.split(r",", args_str) if a.strip()]
            func = FUNCIONES_CALCULO.get(func_name)
            if func is None:
                df[nombre] = pd.NA
                continue
            def _call_row(r):
                try:
                    vals = [r.get(a) for a in args]
                    return func(*vals)
                except Exception:
                    return "N/A"
            df[nombre] = df.apply(_call_row, axis=1)

    # 4) parsear cumplimiento
    try:
        tipo, valor = parse_cumplimiento_field(cumplimiento_raw) if cumplimiento_raw else ("% ", 1.0)
    except Exception as e:
        tipo, valor = ("% ", 1.0)

    # 5) lógica para '%' (inventario completo)
    if tipo == "%":
        total_mask = evaluate_criteria(df, criterio_total_raw)
        total = int(total_mask.sum())
        favor_mask = evaluate_criteria(df, criterio_favor_raw)
        favor = int((total_mask & favor_mask).sum())
        no_cumplen = total - favor
        cumplimiento_metric = (favor / total) if total > 0 else float("nan")
        requerido = valor
        status = "OK" if (total > 0 and cumplimiento_metric >= requerido) else ("Failed" if total > 0 else "Failed")
        
        return {
            "Métrica": metrica,
            "Total": total,
            "Favor": favor,
            "No Cumplen": no_cumplen,
            "Cumplimiento": round(cumplimiento_metric,3),
            "Requerido": requerido,
            "Status": status,
        }

    # 6) lógica para 'N' (archivo contiene lista de no-cumplimientos)
    if tipo == "N":
        no_cumplen = len(df)
        if isinstance(total_override, int) and total_override >= 0:
            total = int(total_override)
            favor = total - no_cumplen
            requerido = total - int(valor)
            status = "OK" if favor >= requerido else "Failed"
            return {
                "Métrica": metrica,
                "Total": total,
                "Favor": favor,
                "No Cumplen": no_cumplen,
                "Cumplimiento": favor,
                "Requerido": requerido,
                "Status": status,
            }
        else:
            status = "OK" if no_cumplen <= int(valor) else "Failed"
            return {
                "Métrica": metrica,
                "Total": None,
                "Favor": None,
                "No Cumplen": no_cumplen,
                "Cumplimiento": None,
                "Requerido": int(valor),
                "Status": status,
            }

    # 7) fallback
    return {
        "Métrica": metrica,
        "Total": None,
        "Favor": None,
        "No Cumplen": None,
        "Cumplimiento": None,
        "Requerido": cumplimiento_raw or "",
        "Status": "Unknown",
    }

# -----------------------------------------------------------------------------
# 8) Runner que procesa todos los bloques de la plantilla
# -----------------------------------------------------------------------------
def run_checks_from_template(template_path: str) -> pd.DataFrame:
    """
    Ejecuta el flujo completo para cada bloque en la plantilla y devuelve un DataFrame resumen.
    """
    blocks = read_template(template_path)
    results: List[Dict[str, Any]] = []
    for b in blocks:
        if "input" not in b:
            print(f"[WARN] Bloque '{b.get('metrica','SIN_NOMBRE')}' sin campo Input. Omitido.")
            continue
        if "metrica" not in b:
            print(f"[WARN] Bloque con input {b.get('input')} sin metrica. Se usará nombre de archivo.")
            b["metrica"] = Path(b["input"]).stem
        res = process_block(b)
        results.append(res)
    df_res = pd.DataFrame(results, columns=["Métrica","Total","Favor","No Cumplen","Cumplimiento","Requerido","Status"])
    return df_res
