import os
import re
from datetime import datetime
from pptx import Presentation
from .ppt_utils import leer_hojas_excel, comparar_excel, buscar_bandera
from .ppt_bandera_handler import reemplazar_con_formato, reemplazar_simple

def generar_ppt_comparativo(
    ruta_excel_actual: str,
    ruta_excel_anterior: str,
    ruta_plantilla: str,
    ruta_salida: str,
    ruta_instrucciones: str = None
):
    """
    Genera un pptx comparando dos Excel (actual vs anterior).
    Soporta operaciones con banderas: <<archivo(operacion)>>
    """
    print("\n" + "═" * 70)
    print("📊 GENERADOR DE PRESENTACIÓN COMPARATIVA")
    print("═" * 70)
    
    print(f"\n📂 Leyendo archivos...")
    print(f"   Excel actual     : {ruta_excel_actual}")
    print(f"   Excel anterior   : {ruta_excel_anterior}")
    
    # Leer ambos Excel
    resumenes_actual = leer_hojas_excel(ruta_excel_actual)
    total_hojas_actual = len(resumenes_actual)
    print(f"   ✅ {total_hojas_actual} hoja(s) en Excel actual")
    
    resumenes_anterior = leer_hojas_excel(ruta_excel_anterior)
    total_hojas_anterior = len(resumenes_anterior)
    print(f"   ✅ {total_hojas_anterior} hoja(s) en Excel anterior")

    # Leer instrucciones para operaciones y categorías
    categorias_por_hoja = {}
    instrucciones = None
    
    if ruta_instrucciones:
        from ..core import leer_instrucciones
        try:
            instrucciones = leer_instrucciones(ruta_instrucciones)
            for inst in instrucciones:
                hoja = inst.get("archivo")
                categoria = inst.get("categoria", "").strip()
                if hoja and categoria:
                    categorias_por_hoja[hoja.lower()] = categoria
            print(f"   ✅ {len(categorias_por_hoja)} categoría(s) cargada(s)")
            print(f"   ✅ Instrucciones cargadas para operaciones")
        except Exception as e:
            print(f"   ⚠️  No se pudo leer instrucciones: {e}")
    
    print(f"\n🔍 Comparando datos...")
    comparativo = comparar_excel(resumenes_actual, resumenes_anterior)
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    print(f"   📅 Fecha actual     : {fecha_actual}")
    print(f"   ✅ Comparación completada")

    print(f"\n🖼️  Abriendo plantilla PowerPoint...")
    print(f"   📁 {ruta_plantilla}")
    prs = Presentation(ruta_plantilla)
    print(f"   ✅ {len(prs.slides)} diapositiva(s) cargada(s)")

    print(f"\n" + "═" * 70)
    print("🎨 PROCESANDO DIAPOSITIVAS")
    print("═" * 70)
    
    diapositivas_procesadas = 0
    diapositivas_con_cambios = 0
    banderas_reemplazadas = 0

    for idx_slide, slide in enumerate(prs.slides, 1):
        banderas_encontradas = set()
        for shape in slide.shapes:
            if not hasattr(shape, "text"):
                continue
            banderas = buscar_bandera(shape.text)
            banderas_encontradas.update(banderas)
        
        if not banderas_encontradas:
            print(f"\n[{idx_slide}] '{slide.name}'")
            print(f"    ⊘ Estado: SIN BANDERAS (omitida)")
            continue

        print(f"\n[{idx_slide}] '{slide.name}'")
        print(f"    📌 Banderas: {', '.join(sorted(banderas_encontradas))}")

        slide_name = slide.name.lower() if slide.name else ""
        nombre_archivo = None
        categoria = None
        
        # Estrategia 1: Detectar por banderas
        if banderas_encontradas:
            print(f"    🔍 Detectando archivo...")
            
            for bandera_encontrada in banderas_encontradas:
                bandera_lower = bandera_encontrada.lower()
                # Extraer nombre si es operación: archivo(op) -> archivo
                op_match = re.match(r'^([^\(]+)\(', bandera_lower)
                if op_match:
                    bandera_lower = op_match.group(1).strip()
                
                for hoja_nombre in comparativo.keys():
                    hoja_norm = hoja_nombre.lower().replace(" ", "_")
                    
                    if hoja_norm == bandera_lower:
                        nombre_archivo = list(comparativo.keys())[0] if comparativo else None
                        print(f"    ✅ Archivo detectado por bandera")
                        break
                
                if nombre_archivo:
                    break
        
        # Estrategia 2: Por nombre de diapositiva
        if not nombre_archivo and slide_name:
            for archivo_key in comparativo.keys():
                archivo_norm = archivo_key.lower().replace(" ", "_").replace(".xlsx", "")
                if archivo_norm in slide_name:
                    nombre_archivo = archivo_key
                    print(f"    ✅ Archivo detectado por nombre")
                    break
        
        # Estrategia 3: Único archivo disponible
        if not nombre_archivo and comparativo:
            if len(comparativo) == 1:
                nombre_archivo = list(comparativo.keys())[0]
                print(f"    ✅ Único archivo disponible: {nombre_archivo}")
            else:
                print(f"    ⚠️  No se detectó archivo ({len(comparativo)} disponibles)")

        # Preparar valores
        valores = {}
        valores["fecha"] = fecha_actual
        nombre_archivo_actual = os.path.splitext(os.path.basename(ruta_excel_actual))[0]
        valores["titulo"] = nombre_archivo_actual
        
        # Detectar categoría
        categoria = None
        hojas = comparativo
        
        if banderas_encontradas:
            print(f"    🔍 Detectando categoría...")
            
            for bandera_encontrada in banderas_encontradas:
                bandera_lower = bandera_encontrada.lower()
                # Extraer nombre si es operación
                op_match = re.match(r'^([^\(]+)\(', bandera_lower)
                if op_match:
                    bandera_lower = op_match.group(1).strip()
                
                for hoja_nombre in hojas.keys():
                    hoja_norm = hoja_nombre.lower().replace(" ", "_")
                    
                    if hoja_norm == bandera_lower:
                        if hoja_nombre.lower() in categorias_por_hoja:
                            categoria = categorias_por_hoja[hoja_nombre.lower()]
                            print(f"    ✅ Categoría: {categoria}")
                            break
                
                if categoria:
                    break
        
        if not categoria and hojas:
            categoria = list(hojas.keys())[0]
            print(f"    ⓘ Categoría por defecto: {categoria}")
        
        valores["categoria"] = categoria if categoria else ""
        
        print(f"    ┌─────────────────────────────────")
        print(f"    │ 📋 VALORES A REEMPLAZAR:")
        print(f"    ├─────────────────────────────────")
        print(f"    │ Titulo    : {valores['titulo']}")
        print(f"    │ Categoria : {valores['categoria']}")
        print(f"    │ Fecha     : {valores['fecha']}")
        
        for hoja, datos in hojas.items():
            bandera = hoja.lower()
            bandera = re.sub(r'[\s\-\.]+', '_', bandera)
            
            valores[bandera] = datos['texto']
            valores[f'{bandera}_color'] = datos['color']
            color_rgb = datos['color']
            if hasattr(color_rgb, 'rgb'):
                color_hex = f"#{color_rgb.rgb:06X}"
            else:
                color_int = (color_rgb[0] << 16) | (color_rgb[1] << 8) | color_rgb[2]
                color_hex = f"#{color_int:06X}"
            print(f"    │ {bandera:<20} : {datos['texto']:<20} | {color_hex}")
        
        print(f"    ├─────────────────────────────────")
        print(f"    │ 🔄 REEMPLAZANDO BANDERAS:")
        print(f"    └─────────────────────────────────")
        
        for idx_shape, shape in enumerate(slide.shapes, 1):
            if not hasattr(shape, "text"):
                continue
            
            texto_original = shape.text
            banderas_en_shape = buscar_bandera(texto_original)
            if not banderas_en_shape:
                continue
            
            print(f"       📄 Cuadro {idx_shape}: {len(banderas_en_shape)} bandera(s)")
            
            if hasattr(shape, "text_frame"):
                try:
                    reemplazar_con_formato(
                        shape.text_frame, 
                        texto_original, 
                        valores, 
                        excel_actual=ruta_excel_actual,
                        excel_anterior=ruta_excel_anterior, 
                        instrucciones=instrucciones
                    )
                    banderas_reemplazadas += len(banderas_en_shape)
                    print(f"          ✅ {len(banderas_en_shape)} reemplazada(s)")
                except Exception as e:
                    print(f"          ⚠️  Error: {str(e)[:40]}...")
                    nuevo_texto = reemplazar_simple(texto_original, valores)
                    if nuevo_texto != texto_original:
                        shape.text = nuevo_texto
                        banderas_reemplazadas += len(banderas_en_shape)
                        print(f"          ✅ {len(banderas_en_shape)} reemplazada(s) (fallback)")
            else:
                nuevo_texto = reemplazar_simple(texto_original, valores)
                if nuevo_texto != texto_original:
                    shape.text = nuevo_texto
                    banderas_reemplazadas += len(banderas_en_shape)
                    print(f"          ✅ {len(banderas_en_shape)} reemplazada(s) (simple)")
        
        diapositivas_con_cambios += 1
        diapositivas_procesadas += 1

    print(f"\n" + "═" * 70)
    print(f"📊 RESUMEN DE CAMBIOS")
    print("═" * 70)
    print(f"   📈 Diapositivas procesadas  : {diapositivas_procesadas}")
    print(f"   ✏️  Diapositivas con cambios : {diapositivas_con_cambios}")
    print(f"   🔀 Banderas reemplazadas    : {banderas_reemplazadas}")
    print("═" * 70)

    print(f"\n💾 Guardando archivo PowerPoint...")
    print(f"   📁 {ruta_salida}")
    prs.save(ruta_salida)
    print(f"   ✅ Archivo guardado exitosamente")
    
    print("\n" + "═" * 70)
    print("✅ PRESENTACION GENERADA COMPLETAMENTE")
    print("═" * 70 + "\n")
