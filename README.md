# BatXcel 2.0 - Procesador Avanzado de Excel

Herramienta automatizada para procesar, enriquecer y separar archivos Excel de manera inteligente. Diseñada para optimizar flujos de trabajo con hojas de cálculo complejas mediante filtrado, enriquecimiento con datos externos y división de archivos según identificadores.

---

## Características Principales

### 1. **Generación de Excel con Filtrado Inteligente**
- Lectura de múltiples fuentes (Excel y CSV)
- Filtrado avanzado con criterios complejos:
  - Operadores lógicos: `&&` (AND), `||` (OR)
  - Búsquedas: `+valor+` (contiene), `*valor*` (diferente)
  - Manejo de vacíos: `[]` (vacío), `*[]*` (no vacío)
- Generación automática de hoja resumen con referencias cruzadas

### 2. **Enriquecimiento de Datos**
- Integración con archivos externos mediante LOOKUP
- Soporte para fórmulas Excel traducidas a Python:
  - `VLOOKUP`, `SI` (IF), `SI.ERROR` (IFERROR)
  - `Y` (AND), `O` (OR)
  - Función personalizada `COMP_VER` para comparar versiones
- Enriquecimiento automático por coincidencia parcial
- Parámetros globales configurables

### 3. **Separación de Archivos**
- División de Excel en múltiples archivos según identificadores
- Soporte para valores `N/A` y vacíos
- Generación automática de hojas resumen por archivo
- Conservación de estructura original de hojas

---

## Instalación

### Requisitos Previos
- Python 3.8 o superior
- pip (gestor de paquetes)

### Instalación de Dependencias

**Opción 1: Instalación estándar**
```bash
pip install pandas openpyxl
```

**Opción 2: Con trusted-host**
```bash
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org pandas openpyxl
```

---

## Uso

### Ejecución Básica

```bash
python main.py
```

El programa te guiará paso a paso:

1. **Paso 1:** Generación del Excel base
   - Proporciona la ruta del archivo de instrucciones
   - Define la ruta del archivo de salida

2. **Paso 1.1:** Creación de hoja resumen
   - Se genera automáticamente con IDs de todas las hojas

3. **Paso 2:** Enriquecimiento
   - Proporciona el archivo de configuración de enriquecimiento
   - Se agregan columnas calculadas y datos externos

4. **Paso 3:** Separación (opcional)
   - Decide si separar el archivo en múltiples Excels
   - Configura identificadores y carpeta de salida

---

## Estructura del Proyecto

```
procesar_excel/
│
├── main.py                          # Punto de entrada principal
├── README.md                        # Este archivo
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/                        # Funcionalidades base
│   │   ├── __init__.py
│   │   ├── config_parser.py         # Lectura de configuraciones
│   │   ├── excel_reader.py          # Lectura de Excel/CSV
│   │   └── file_utils.py            # Utilidades de archivos
│   │
│   ├── procesador/                  # Generación y filtrado
│   │   ├── __init__.py
│   │   ├── generador.py             # Generación de Excel base
│   │   └── filtros.py               # Sistema de filtros avanzado
│   │
│   ├── enriquecedor/                # Enriquecimiento de datos
│   │   ├── __init__.py
│   │   ├── enricher.py              # Lógica principal
│   │   ├── formula_engine.py        # Motor de fórmulas Excel
│   │   └── lookup.py                # Funciones VLOOKUP/LOOKUP
│   │
│   ├── separador/                   # División de archivos
│   │   ├── __init__.py
│   │   └── splitter.py              # Separación por identificadores
│   │
│   └── utils/                       # Utilidades generales
│       ├── text_utils.py            # Procesamiento de texto
│       └── version_utils.py         # Comparación de versiones
│
└── output/                          # Carpeta de salida (generada)
    └── separados/                   # Archivos separados
```

---

## Archivos de Configuración

### 1. Archivo de Instrucciones (Generación)

Formato de texto plano con bloques por hoja:

```text
Archivo: NombreHoja1
Ruta: C:\datos\archivo1.xlsx
Columna criterio: Estado
Criterio: +Activo+ || *Inactivo*
Columna ID: ID_Usuario
Categoria: "Workstations"
Limpiar ID: "@empresa.com"

Archivo: NombreHoja2
Ruta: C:\datos\archivo2.csv
Columna criterio: Tipo
Criterio: [] && *[]*
Columna ID: User Principal Name
Categoria: "Dispositivos Móviles"
Limpiar ID: "@dominio.com.co"
```

**Campo Limpiar ID (Opcional):**
- Elimina extensiones o sufijos de los valores en la columna ID
- Útil para limpiar dominios de correo: `usuario@empresa.com` → `usuario`
- Ejemplo: `Limpiar ID: "@santander.com.co"`
- Se aplica antes de guardar los datos en el Excel final
- También funciona con cualquier patrón de texto que quieras eliminar

**Campo Categoria (Opcional):**
- Agrupa hojas en el resumen por categoría
- Si se define al menos una categoría, se crearán hojas de resumen separadas por categoría
- Ejemplo: `Categoria: "Workstations"`, `Categoria: "Dispositivos Móviles"`
- Si no se define categoría en ninguna hoja, se crea un único "Resumen" consolidado
- Hojas sin categoría (cuando otras sí tienen) se agrupan en "Resumen_General"
- **Importante**: Si hay categorías definidas, NO se crea "Resumen_Consolidado"

**Operadores de criterio:**
- `+texto+` → Contiene "texto"
- `*texto*` → Diferente de "texto"
- `*+texto+*` → No contiene "texto"
- `[]` → Vacío o N/A
- `*[]*` → No vacío
- `&&` → AND lógico
- `||` → OR lógico

**Múltiples columnas criterio:**
- Puedes definir hasta N criterios usando: `Columna criterio 2`, `Criterio 2`, `Columna criterio 3`, `Criterio 3`, etc.
- Todos los criterios se evalúan con operador AND (deben cumplirse todos)
- Ejemplo: Filtrar registros donde columna A = "X" **Y** columna B contiene "Y"

### 2. Archivo de Configuración de Enriquecimiento

```text
# Parámetros globales
Parametro: version_minima = 10.0
Parametro: umbral = 100

# Enriquecimiento por archivo externo
Hoja: "NombreHoja1"
Columna base: "ID_Usuario"
Ruta: "C:\datos\externos\usuarios.xlsx"
Hoja lookup: "Datos"
Alias lookup: "usuarios"
Columna cruzar: "ID"
Columna extraer: "Nombre", "Email", "Departamento"

# Enriquecimiento de hojas RESUMEN
Hoja: "Resumen_Workstations"
Columna base: "ID"
Ruta: "C:\datos\cmdb.xlsx"
Columna cruzar: "Name"
Columna extraer: "Employee ID"

Hoja: "Resumen_Consolidado"
Columna base: "ID"
Ruta: "C:\datos\cmdb.xlsx"
Columna cruzar: "Name"
Columna extraer: "Employee ID"

# Fórmulas calculadas
Columna calcular: Estado_Final = IF(version >= version_minima, "OK", "OBSOLETO")
```

**Enriquecimiento de hojas resumen:**
- Las hojas de resumen (Resumen_*, Resumen_Consolidado) pueden ser enriquecidas
- Usa la columna "ID" como columna base para buscar coincidencias
- Puedes agregar información como "Employee ID", "Departamento", etc.
- Las columnas agregadas se ordenarán: ID, Employee ID, luego las hojas alfabéticamente

### 3. Archivo de Configuración de Separación

```text
# Hojas de cálculo a generar
Name: "Archivo_Grupo_A"
Identificadores: "A", "A1", "A2"

Name: "Archivo_Grupo_B"
Identificadores: "B", "B1", "N/A"

---

# Mapeo de hojas y columnas ID
Hoja: "NombreHoja1"
Columna ID: "ID_Usuario"

Hoja: "NombreHoja2"
Columna ID: "Codigo"
```

---

## Ejemplos de Uso

### Ejemplo 1: Filtrado Simple

**Instrucciones:**
```text
Archivo: Clientes
Ruta: datos.xlsx
Columna criterio: Estado
Criterio: +Activo+
Columna ID: ClienteID
```

Resultado: Solo clientes con "Activo" en columna Estado.

### Ejemplo 2: Filtrado Complejo

**Instrucciones:**
```text
Criterio: (+Premium+ || +VIP+) && *Inactivo*
```

Resultado: Clientes Premium o VIP que NO están Inactivos.

### Ejemplo 3: Múltiples Columnas Criterio

**Instrucciones:**
```text
Archivo: Non-Phishing Enabled
Ruta: mtd.xlsx
Columna criterio: Methods Non Phishing Resistant
Criterio: *[]*
Columna criterio 2: Account Enabled
Criterio 2: Yes
Columna ID: User Principal Name
```

Resultado: Solo usuarios con valores en "Methods Non Phishing Resistant" **Y** con "Account Enabled" = "Yes".

### Ejemplo 4: Tres Criterios Combinados

**Instrucciones:**
```text
Archivo: Usuarios Activos Premium
Ruta: usuarios.xlsx
Columna criterio: Estado
Criterio: +Activo+
Columna criterio 2: Tipo
Criterio 2: +Premium+
Columna criterio 3: Verificado
Criterio 3: Yes
Columna ID: UserID
```

Resultado: Usuarios que son Activos **Y** Premium **Y** Verificados.

### Ejemplo 5: Limpiar Extensiones de Correo

**Instrucciones:**
```text
Archivo: Usuarios
Ruta: usuarios_cloud.xlsx
Columna criterio: Status
Criterio: Active
Columna ID: User Principal Name
Limpiar ID: "@company.com"
```

**Antes:**
```
User Principal Name
-------------------
usuario1@company.com
usuario2@company.com
empleado@empresa.com
```

**Después de limpiar:**
```
User Principal Name
-------------------
usuario1
usuario2
empleado@empresa
```

---

## Características Avanzadas

### Motor de Fórmulas Excel
- Traduce fórmulas Excel a Python automáticamente
- Soporta referencias a columnas del DataFrame actual
- Acceso a parámetros globales en fórmulas
- Funciones personalizadas como `COMP_VER` para versiones

### Búsquedas Inteligentes
- **VLOOKUP por letra de columna:** `VLOOKUP(valor, "hoja", "A", "C")`
- **LOOKUP por nombre:** `LOOKUP("hoja", "columna_clave", valor, "columna_resultado")`
- Coincidencia exacta y parcial
- Caché de hojas para optimización

### Manejo Robusto de Archivos
- Limpieza automática de rutas con `file:///`
- Soporte para múltiples encodings en CSV (UTF-8, Latin-1)
- Detección automática de separadores (`,` y `;`)
- Normalización de nombres de columnas

---

## Resolución de Problemas

### Error: "Columna no encontrada"
- Verifica que los nombres coincidan (sin distinción mayúsculas/minúsculas)
- El sistema normaliza automáticamente a minúsculas

### Error: "Archivo no se puede escribir"
- Cierra el archivo Excel de salida si está abierto
- Verifica permisos de escritura en la carpeta

### Fórmula no se evalúa correctamente
- Revisa la sintaxis (usa `,` como separador, no `;`)
- Asegúrate de que las columnas referenciadas existen
- Verifica que los parámetros globales estén definidos

### CSV no se lee correctamente
- El sistema intenta múltiples configuraciones automáticamente
- Verifica el encoding del archivo (UTF-8 o Latin-1)

### Error de instalación de dependencias
- Usa el comando con `--trusted-host` si estás en un entorno corporativo con proxy
- Verifica la conexión a internet y configuración del proxy

---


