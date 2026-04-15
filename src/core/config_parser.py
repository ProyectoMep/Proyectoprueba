import os
import re
from typing import Dict, List, Any
from .file_utils import limpiar_ruta

def leer_instrucciones(ruta_instrucciones: str) -> List[Dict[str, str]]:
    """
    Lee el archivo de instrucciones y retorna lista de configuraciones.
    Soporta múltiples columnas criterio (criterio 2, criterio 3, etc.)
    Soporta operaciones con múltiples condiciones: 
    operacion: "nombre" -> columna=X, valor=Y && columna=Z, valor=W
    """
    ruta_instrucciones = limpiar_ruta(ruta_instrucciones)
    instrucciones = []
    instruccion = {}
    operaciones = []
    
    with open(ruta_instrucciones, 'r', encoding='utf-8') as archivo:
        for linea in archivo.read().splitlines():
            if linea.strip():
                if linea.lower().startswith("archivo:"):
                    if instruccion:
                        if operaciones:
                            instruccion['operaciones'] = operaciones
                        instrucciones.append(instruccion)
                    instruccion = {}
                    operaciones = []
                
                # Parsear operaciones
                if linea.lower().startswith("operacion:"):
                    # Formato: operacion: "nombre" -> columna=X, valor=Y && columna=Z, valor=W
                    parte = linea.split(":", 1)[1].strip()
                    # Extraer nombre entre comillas
                    match = re.match(r'^"([^"]+)"\s*->\s*(.+)$', parte)
                    if match:
                        nombre_op = match.group(1).strip()
                        params_str = match.group(2)
                        
                        # Dividir por && para múltiples condiciones
                        condiciones_raw = params_str.split("&&")
                        condiciones = []
                        
                        for cond_raw in condiciones_raw:
                            # Parsear cada condición: columna=X, valor=Y
                            params = {}
                            for param in cond_raw.split(","):
                                if "=" in param:
                                    k, v = param.split("=", 1)
                                    params[k.strip().lower()] = v.strip()
                            
                            if 'columna' in params and 'valor' in params:
                                condiciones.append({
                                    'columna': params['columna'],
                                    'valor': params['valor']
                                })
                        
                        operaciones.append({
                            'nombre': nombre_op,
                            'condiciones': condiciones
                        })
                    continue
                
                if ":" in linea:
                    clave, valor = linea.split(":", 1)
                    clave_normalizada = clave.strip().lower()
                    if not clave_normalizada.startswith("operacion"):
                        instruccion[clave_normalizada] = valor.strip().strip('"')
        
        if instruccion:
            if operaciones:
                instruccion['operaciones'] = operaciones
            instrucciones.append(instruccion)
    
    return instrucciones

def leer_configuracion_enriquecimiento(ruta_configuracion: str) -> Dict[str, Any]:
    """
    Lee configuración de enriquecimiento con bloques y parámetros.
    """
    ruta_configuracion = limpiar_ruta(ruta_configuracion)
    configuraciones = []
    parametros: Dict[str, Any] = {}
    
    if not os.path.exists(ruta_configuracion):
        print(f"Archivo configuración no encontrado: {ruta_configuracion}")
        return {"bloques": configuraciones, "parametros": parametros}

    actual = {}
    calculos = []
    
    with open(ruta_configuracion, 'r', encoding='utf-8') as archivo:
        for linea in archivo.read().splitlines():
            l = linea.strip()
            if not l or l.startswith("#"):
                continue

            # Parsear parámetros globales
            if l.lower().startswith("parametro:"):
                parte = l.split(":", 1)[1].strip()
                if "=" in parte:
                    nombre, valor = parte.split("=", 1)
                    nombre = nombre.strip().lower()
                    valor = valor.strip().strip('"').strip("'")
                    parametros[nombre] = _cast_valor(valor)
                continue

            # Nueva hoja
            if l.lower().startswith("hoja:"):
                if actual:
                    if calculos:
                        actual["calculos"] = calculos
                    configuraciones.append(actual)
                actual = {}
                calculos = []

            # Parsear líneas con clave:valor
            if ":" in l:
                clave, valor = l.split(":", 1)
                clave_l = clave.strip().lower()
                valor = valor.strip()
                
                if clave_l == "columna calcular":
                    if "=" in valor:
                        nombre_col, formula = valor.split("=", 1)
                        calculos.append({
                            "nombre": nombre_col.strip().strip('"').strip("'").lower(),
                            "formula": formula.strip()
                        })
                else:
                    actual[clave_l] = valor.strip()
        
        if actual:
            if calculos:
                actual["calculos"] = calculos
            configuraciones.append(actual)

    return {"bloques": configuraciones, "parametros": parametros}

def leer_configuracion_separacion(ruta_configuracion: str) -> dict:
    """
    Lee configuración para separar archivos Excel.
    Soporta: exclusivo para = nombre_archivo (hoja solo va en ese archivo)
    """
    ruta_configuracion = limpiar_ruta(ruta_configuracion)
    if not os.path.exists(ruta_configuracion):
        print(f"Archivo configuración no encontrado: {ruta_configuracion}")
        return {'hojas_calculo': [], 'hojas': []}

    hojas_calculo = []
    hojas = []
    modo = 'hojas_calculo'
    actual_calc = None
    actual_hoja = None

    with open(ruta_configuracion, 'r', encoding='utf-8') as f:
        for linea in f.read().splitlines():
            l = linea.strip()
            if not l or l.startswith("#"):
                continue

            if re.fullmatch(r'-{3,}', l):
                if actual_calc:
                    hojas_calculo.append(actual_calc)
                    actual_calc = None
                modo = 'hojas'
                continue

            if modo == 'hojas_calculo':
                if re.match(r'(?i)^(name|hoja de calculo ?\d*)\s*:', l):
                    if actual_calc:
                        hojas_calculo.append(actual_calc)
                    valor = l.split(":", 1)[1].strip().strip('"').strip("'")
                    actual_calc = {'name': valor, 'identificadores': []}
                    continue
                if l.lower().startswith("identificadores:"):
                    if not actual_calc:
                        continue
                    ids_raw = l.split(":", 1)[1].strip()
                    ids = [x.strip().strip('"').strip("'") for x in ids_raw.split(",") if x.strip()]
                    actual_calc['identificadores'] = ids
                    continue

            if modo == 'hojas':
                if l.lower().startswith("hoja:"):
                    if actual_hoja:
                        hojas.append(actual_hoja)
                    nombre = l.split(":", 1)[1].strip().strip('"').strip("'")
                    actual_hoja = {
                        'hoja': nombre, 
                        'columna_id': '',
                        'exclusivo_para': None
                    }
                    continue
                if l.lower().startswith("columna id:"):
                    if not actual_hoja:
                        continue
                    col = l.split(":", 1)[1].strip().strip('"').strip("'")
                    actual_hoja['columna_id'] = col
                    continue
                if l.lower().startswith("exclusivo para:"):
                    if not actual_hoja:
                        continue
                    archivo = l.split(":", 1)[1].strip().strip('"').strip("'")
                    actual_hoja['exclusivo_para'] = archivo
                    continue

    if actual_calc:
        hojas_calculo.append(actual_calc)
    if actual_hoja:
        hojas.append(actual_hoja)

    return {'hojas_calculo': hojas_calculo, 'hojas': hojas}

def leer_configuracion_limpieza(ruta_configuracion: str) -> List[Dict[str, Any]]:
    """
    Lee configuración de limpieza post-enriquecimiento.
    
    Sintaxis:
    - Eliminar si: columna = valor &&  → AND (requiere siguiente condición)
    - Eliminar si: columna = valor ||  → OR (alternativa)
    - Eliminar si: columna = valor     → Última condición del grupo
    
    Operadores soportados en valores:
    - +valor+     → Contiene "valor"
    - *+valor+*   → NO contiene "valor"
    - *valor*     → Diferente de "valor"
    - []          → Vacío
    - *[]*        → NO vacío
    - valor       → Igual a "valor"
    
    Returns:
        Lista de diccionarios con:
        - hoja: nombre de la hoja
        - grupos_condiciones: lista de grupos (cada grupo es una lista de condiciones con AND)
    """
    ruta_configuracion = limpiar_ruta(ruta_configuracion)
    configuraciones = []
    
    if not os.path.exists(ruta_configuracion):
        print(f"Archivo configuración no encontrado: {ruta_configuracion}")
        return configuraciones

    actual = None
    grupo_actual = []
    
    with open(ruta_configuracion, 'r', encoding='utf-8') as archivo:
        for linea in archivo.read().splitlines():
            l = linea.strip()
            if not l or l.startswith("#"):
                continue

            # Nueva hoja
            if l.lower().startswith("hoja:"):
                # Guardar configuración anterior
                if actual and grupo_actual:
                    if 'grupos_condiciones' not in actual:
                        actual['grupos_condiciones'] = []
                    actual['grupos_condiciones'].append(grupo_actual)
                    grupo_actual = []
                if actual:
                    configuraciones.append(actual)
                
                nombre_hoja = l.split(":", 1)[1].strip().strip('"').strip("'")
                actual = {
                    'hoja': nombre_hoja,
                    'grupos_condiciones': []
                }
                continue
            
            # Condición de eliminación
            if l.lower().startswith("eliminar si:"):
                if not actual:
                    continue
                
                condicion_raw = l.split(":", 1)[1].strip()
                
                # Detectar operador lógico al final
                operador_siguiente = None
                if condicion_raw.endswith("&&"):
                    operador_siguiente = "AND"
                    condicion_raw = condicion_raw[:-2].strip()
                elif condicion_raw.endswith("||"):
                    operador_siguiente = "OR"
                    condicion_raw = condicion_raw[:-2].strip()
                
                # Parsear condición (columna = valor)
                if "=" in condicion_raw:
                    partes = condicion_raw.split("=", 1)
                    columna = partes[0].strip().lower()
                    valor = partes[1].strip().strip('"').strip("'")
                    
                    # Detectar operador de comparación según el patrón del valor
                    operador_comp = "=="
                    
                    # *+valor+* - NO contiene
                    if valor.startswith("*+") and valor.endswith("+*"):
                        operador_comp = "not_contains"
                        valor = valor[2:-2]
                    # *[]* - NO vacío
                    elif valor == "*[]*":
                        operador_comp = "no_vacio"
                        valor = ""
                    # *valor* - Diferente
                    elif valor.startswith("*") and valor.endswith("*"):
                        operador_comp = "!="
                        valor = valor.strip("*")
                    # [] - Vacío
                    elif valor == "[]":
                        operador_comp = "vacio"
                        valor = ""
                    # +valor+ - Contiene
                    elif valor.startswith("+") and valor.endswith("+"):
                        operador_comp = "contains"
                        valor = valor.strip("+")
                    # valor normal - Igual
                    else:
                        operador_comp = "=="
                    
                    condicion = {
                        'columna': columna,
                        'operador': operador_comp,
                        'valor': valor
                    }
                    
                    grupo_actual.append(condicion)
                    
                    # Si el operador es OR, cerrar grupo actual y empezar uno nuevo
                    if operador_siguiente == "OR":
                        actual['grupos_condiciones'].append(grupo_actual)
                        grupo_actual = []
                    # Si es AND o no hay operador, continuar en el mismo grupo
    
    # Guardar último grupo y configuración
    if actual:
        if grupo_actual:
            actual['grupos_condiciones'].append(grupo_actual)
        configuraciones.append(actual)
    
    return configuraciones

def _cast_valor(valor: str) -> Any:
    """
    Intenta convertir un string a int o float, sino devuelve string.
    """
    if re.fullmatch(r'\d+', valor):
        return int(valor)
    elif re.fullmatch(r'\d+\.\d+', valor):
        return float(valor)
    return valor
