CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

from src.procesador import generar_excel_salida, crear_hoja_resumen
from src.enriquecedor import enriquecer_hojas, limpiar_datos_enriquecidos
from src.enriquecedor.lector_csv import generacion_softerra
from src.separador import flujo_separacion
from src.core.file_utils import limpiar_ruta
from src.ppt.ppt_comparador import generar_ppt_comparativo
from src.cumplimiento.cumplimiento import run_checks_from_template
import os
import pandas as pd
import glob

ruta_instrucciones = None
ruta_salida= None
ruta_configuracion= None
ruta_config_separacion= None
carpeta_salida = None
ruta_config_limpieza= None
ruta_excel_actual =None
ruta_excel_anterior =None
ruta_plantilla= None
ruta_salida_ppt= None
ruta_resumen_cumplimiento = None #Nueva ruta para el mapeo del excel de cumplimiento --Nuevo


def main():
    print(f"{CYAN}╔════════════════════════════════════════════════════════════╗")
    print(f"║              Bienvenido a BatXcel 🐍📊                     ║")
    print(f"╚════════════════════════════════════════════════════════════╝{RESET}")
    print("\nEste programa te ayudará a procesar y enriquecer archivos Excel.")
    print("Por favor, sigue las instrucciones para configurar tus archivos.")
    print("Ejecute las opciones en orden ascendente, si desea exceptuar pasos de tipo OPCIONAL, continue al siguiente paso.\n")

    try:
        print(f"{YELLOW}{'═' * 60}")
        print(f"MENÚ PRINCIPAL")
        print(f"{'═' * 60}{RESET}")
        print("1. Generar archivo Excel base y hoja resumen")
        print("2. Enriquecer archivo Excel (OPCIONAL)")
        print("3. Separar Excel en múltiples archivos (OPCIONAL)")
        print("4. Limpieza de datos enriquecidos (OPCIONAL)")
        print("5. Generar resumen de cumplimiento (OPCIONAL)")
        print("6. Generar presentación PPT comparativa")
        print("7. Salir")
        
        opcion = input(f"\n{YELLOW}Selecciona una opción: {RESET}").strip()
        
        if opcion == "1":
            generacion_archivo_base_resumen()
        elif opcion == "2":
            enriquecer()
        elif opcion == "3":
            separacion()
        elif opcion == "4":
            limpieza()
        elif opcion =="5":
            porcentajes_cumplimiento()
        elif opcion =="6":
            generar_ppt_solo()
        elif opcion == "7":
            print(f"{GREEN}Gracias por usar BatXcel. ¡Hasta luego!{RESET}")
            return
        else:
            print(f"{RED}Opción no válida{RESET}")

    except FileNotFoundError as e:
        print(f"{RED}✗ Error: Archivo no encontrado - {e}{RESET}")
    except KeyboardInterrupt:
        print(f"\n{YELLOW}⚠️  Proceso interrumpido por el usuario{RESET}")
    except Exception as e:
        print(f"{RED}✗ Error inesperado: {e}{RESET}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"{CYAN}╔════════════════════════════════════════════════════════════╗")
        print(f"║                     Proceso finalizado                    ║")
        print(f"╚════════════════════════════════════════════════════════════╝{RESET}")

def generacion_archivo_base_resumen():
    
    # PASO 1: Generación de archivo base y resumen
    print(f"\n{GREEN}{'═' * 60}")
    print(f"PASO 1: Generar archivo Excel base")
    print(f"{'═' * 60}{RESET}")
    global ruta_instrucciones
    ruta_instrucciones = input("📝 Ruta del archivo de instrucciones: ").strip()
    global ruta_salida
    ruta_salida = input("📂 Ruta del archivo Excel de salida: ").strip()
    
    generar_excel_salida(ruta_instrucciones, ruta_salida)
    print(f"{GREEN}✓ Archivo Excel generado exitosamente{RESET}\n")

    print(f"{GREEN}{'═' * 60}")
    print(f"PASO 1.1: Crear hoja(s) resumen")
    print(f"{'═' * 60}{RESET}")
    
    crear_hoja_resumen(ruta_salida, ruta_instrucciones)
    print(f"{GREEN}✓ Hoja(s) resumen creada(s) exitosamente{RESET}\n")
    print(f"  ✓ Archivo base generado: {ruta_salida}")

def enriquecer():
    # PASO 2: Enriquecimiento opcional
    print(f"{YELLOW}{'═' * 60}")
    print(f"PASO 2: Enriquecer archivo Excel (OPCIONAL)")
    print(f"{'═' * 60}{RESET}")
    global ruta_configuracion
    ruta_configuracion = input("📝 Ruta del archivo de configuración para enriquecimiento: ").strip()
    ruta_configuracion = limpiar_ruta(ruta_configuracion)
        
    if not os.path.exists(ruta_configuracion):
        print(f"{RED}✗ Archivo de configuración no encontrado: {ruta_configuracion}")
        print(f"⚠️  Saltando enriquecimiento...{RESET}\n")
    else:
        generacion_softerra()
        enriquecer_hojas(ruta_salida, ruta_configuracion)
        print(f"{GREEN}✓ Archivo Excel enriquecido exitosamente{RESET}\n")

    print(f"  ✓ Enriquecimiento aplicado")
   
def separacion():
    # PASO 3: Separación opcional
    
    print(f"{YELLOW}{'═' * 60}")
    print(f"PASO 3: Separar Excel en múltiples archivos (OPCIONAL)")
    print(f"{'═' * 60}{RESET}")
    
    global ruta_config_separacion
    ruta_config_separacion = input("📝 Ruta del archivo de configuración para separación: ").strip()
    ruta_config_separacion = limpiar_ruta(ruta_config_separacion)
        
    if not os.path.exists(ruta_config_separacion):
        print(f"{RED}✗ Archivo de configuración no encontrado: {ruta_config_separacion}")
        print(f"⚠️  Saltando separación...{RESET}\n")
    else:
        global carpeta_salida
        carpeta_salida = input("📂 Carpeta de salida para archivos separados (Enter=output/separados): ").strip() or "output/separados"
        
        flujo_separacion(ruta_salida, ruta_config_separacion, carpeta_salida, ruta_instrucciones)
        print(f"{GREEN}✓ Archivos separados generados exitosamente{RESET}")
        print(f"{GREEN}ℹ️  Las hojas ya contienen el enriquecimiento del archivo base{RESET}\n")
            
    print(f"  ✓ Archivos separados generados en: {carpeta_salida}")

def limpieza():
            print(f"{YELLOW}{'─' * 60}")
            print(f"PASO 4: Limpieza de datos enriquecidos (OPCIONAL)")
            print(f"{'─' * 60}{RESET}")
            print(f"{YELLOW}ℹ️  Elimina filas según criterios en TODOS los archivos separados.")
            print(f"   Ejemplo: Eliminar dispositivos actualizados y compliant.{RESET}")
            
            global ruta_config_limpieza

            ruta_config_limpieza = input("📝 Ruta del archivo de configuración para limpieza: ").strip()
            ruta_config_limpieza = limpiar_ruta(ruta_config_limpieza)
                
            if not os.path.exists(ruta_config_limpieza):
                print(f"{RED}✗ Archivo de configuración no encontrado: {ruta_config_limpieza}{RESET}\n")
            else:
                print(f"\n{GREEN}{'═' * 70}")
                print(f"🧹 LIMPIANDO ARCHIVOS SEPARADOS")
                print(f"{'═' * 70}{RESET}")
                global carpeta_salida
                carpeta_salida = limpiar_ruta(carpeta_salida)
                archivos_separados = glob.glob(os.path.join(carpeta_salida, "*.xlsx"))
                    
                print(f"\n📂 Carpeta: {carpeta_salida}")
                print(f"📋 Archivos a limpiar: {len(archivos_separados)}\n")
                    
                for idx, archivo in enumerate(archivos_separados, 1):
                    print(f"[{idx}/{len(archivos_separados)}] ", end="")
                    try:
                        limpiar_datos_enriquecidos(archivo, ruta_config_limpieza)
                    except Exception as e:
                        print(f"  {RED}⚠️ Error: {e}{RESET}")
                    
                print(f"\n{GREEN}{'═' * 70}")
                print(f"✅ LIMPIEZA COMPLETADA")
                print(f"{'═' * 70}{RESET}\n")
            

def porcentajes_cumplimiento():
    user_in = input("Introduce la ruta al archivo de plantilla cumplimiento: ").strip().replace('"', '')
    if os.path.exists(user_in):
        template_path = user_in
        template_path = limpiar_ruta(template_path)
    else:
        print(f"No se encontró el archivo: {user_in}. Intenta de nuevo.")

    if template_path is None:
        print("No hay plantilla a procesar. Saliendo.")

    print(f"Procesando plantilla: {template_path}")
    df_summary = run_checks_from_template(template_path)
    pd.set_option("display.max_columns", None)
    print("\nResumen de cumplimiento:\n")
    print(df_summary.to_string(index=False))
    out_csv = "output/resumen_cumplimiento.xlsx"
    df_summary.to_excel(out_csv, index=False)
    print(f"\nGuardado: {out_csv}")

def generar_ppt_solo():
    """Genera PPT comparativo"""
    
    print(f"\n{CYAN}{'═' * 60}")
    print(f"GENERADOR DE PRESENTACIÓN COMPARATIVA")
    print(f"{'═' * 60}{RESET}\n")
    
    while True:
        global ruta_excel_actual
        ruta_excel_actual = input("📄 Ruta del Excel ACTUAL: ").strip()
        ruta_excel_actual = limpiar_ruta(ruta_excel_actual)
        
        if not os.path.exists(ruta_excel_actual):
            print(f"{RED}✗ Excel actual no encontrado{RESET}\n")
            continue
        break
    
    while True:
        global ruta_excel_anterior
        ruta_excel_anterior = input("📄 Ruta del Excel de la SEMANA PASADA: ").strip()
        ruta_excel_anterior = limpiar_ruta(ruta_excel_anterior)
        
        if not os.path.exists(ruta_excel_anterior):
            print(f"{RED}✗ Excel anterior no encontrado{RESET}\n")
            continue
        break

    while True:
        global ruta_plantilla
        ruta_plantilla = input("🖼️ Ruta del archivo plantilla PPTX: ").strip()
        ruta_plantilla = limpiar_ruta(ruta_plantilla)
        
        if not os.path.exists(ruta_plantilla):
            print(f"{RED}✗ Plantilla PPT no encontrada{RESET}\n")
            continue
        break
    
    global ruta_instrucciones
    ruta_instrucciones = input("📝 Ruta del archivo instrucciones.txt (Enter=omitir): ").strip()
    if ruta_instrucciones:
        ruta_instrucciones = limpiar_ruta(ruta_instrucciones)
        if not os.path.exists(ruta_instrucciones):
            print(f"{YELLOW}⚠️  Instrucciones no encontradas, continuando sin categorías{RESET}")
            ruta_instrucciones = None
    else:
        ruta_instrucciones = None
#Nueva funcion para recibir la ruta del excel de cumplimiento, si no se ingresa, se omite el estatus de cumplimiento en el ppt comparativo -- Nuevo
        global ruta_resumen_cumplimiento
    ruta_resumen_cumplimiento = input("📊 Ruta del archivo resumen_cumplimiento.xlsx (Enter=omitir): ").strip()
    if ruta_resumen_cumplimiento:
        ruta_resumen_cumplimiento = limpiar_ruta(ruta_resumen_cumplimiento)
        if not os.path.exists(ruta_resumen_cumplimiento):
            print(f"{YELLOW}⚠️  Archivo resumen_cumplimiento no encontrado, continuando sin estatus de cumplimiento{RESET}")
            ruta_resumen_cumplimiento = None
    else:
        ruta_resumen_cumplimiento = None

    global ruta_salida_ppt
    ruta_salida_ppt = input("📄 Ruta de salida para el PPT (ej: output/comparativo.pptx): ").strip()
    if not ruta_salida_ppt:
        ruta_salida_ppt = "output/PPTGENERADO.pptx"
    # Validar que termine en .pptx
    if not ruta_salida_ppt.lower().endswith('.pptx'):
        # Agregar .pptx solo si no termina en eso
        ruta_salida_ppt = ruta_salida_ppt.rstrip('\\').rstrip('/') + "/comparativo_resultado.pptx"
    ruta_salida_ppt = limpiar_ruta(ruta_salida_ppt)

    # Crear carpeta de salida
    carpeta_salida_ppt = os.path.dirname(ruta_salida_ppt)
    if carpeta_salida_ppt and carpeta_salida_ppt.strip():
        os.makedirs(carpeta_salida_ppt, exist_ok=True)
    
    try:
        print(f"\n{GREEN}Generando presentación comparativa...{RESET}")
        generar_ppt_comparativo(ruta_excel_actual, ruta_excel_anterior, ruta_plantilla, ruta_salida_ppt, ruta_instrucciones, ruta_resumen_cumplimiento)
        print(f"\n{GREEN}{'═' * 60}")
        print(f"✅ PRESENTACIÓN GENERADA EXITOSAMENTE")
        print(f"📁 Ubicación: {ruta_salida_ppt}")
        print(f"{'═' * 60}{RESET}\n")
    except Exception as e:
        print(f"{RED}✗ Error generando PPT: {e}{RESET}\n")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    while True:
        main()
        repetir = input(f"\n{YELLOW}¿Desea realizar otra operación? (s/n): {RESET}").strip().lower()
        if repetir != 's':
            break
    print(f"{GREEN}Gracias por usar BatXcel. ¡Hasta luego!{RESET}")
