import re
from typing import Tuple, List

_version_split_regex = re.compile(r'[._,\-]')

def _version_to_tuple(s) -> Tuple[int, ...] | None:
    """Convierte string de versión a tupla de números para comparación."""
    s = "" if s is None else str(s).strip()
    if not s or s.upper() == "N/A":
        return None
    
    # Limpiar prefijos como "android 14", "ios 17", "windows 11"
    s = re.sub(r'^\s*(android|ios|ipad os|windows)\s*', '', s, flags=re.IGNORECASE)
    parts = _version_split_regex.split(s)
    nums: List[int] = []
    
    for p in parts:
        if not p:
            continue
        m = re.match(r'(\d+)', p)
        if m:
            nums.append(int(m.group(1)))
            continue
        if not nums:
            m_any = re.search(r'(\d+)', p)
            if m_any:
                nums.append(int(m_any.group(1)))
    
    if not nums:
        m_global = re.search(r'(\d+)', s)
        if m_global:
            nums = [int(m_global.group(1))]
    
    return tuple(nums) if nums else None

def COMP_VER(a, b) -> int:
    """
    Compara dos versiones.
    Retorna: -1 si a < b, 0 si a == b, 1 si a > b
    """
    ta = _version_to_tuple(a)
    tb = _version_to_tuple(b)
    
    if ta is None or tb is None:
        # Fallback: comparar primer número encontrado
        try:
            na = int(re.search(r'\d+', str(a)).group(0))
        except Exception:
            na = None
        try:
            nb = int(re.search(r'\d+', str(b)).group(0))
        except Exception:
            nb = None
        if na is None or nb is None:
            return 0
        return -1 if na < nb else (1 if na > nb else 0)
    
    if ta < tb:
        return -1
    if ta > tb:
        return 1
    return 0
