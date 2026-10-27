"""
Constantes del proyecto 
"""

# --- Tablas en Redshift ---
TABLA_SELLERS = "eiffel_seller.seller"
TABLA_TRANSACCIONES = "cencosud_chile_txd_reporter.vm_new_report_transaccion_mkp"
TABLA_VISTAS = "source_bi_paristxd_product.product_data_daily"

# --- Clasificación de divisiones en dureza ---
DUROS = ["DECO-HOGAR", "TECNOLOGIA", "ELECTRO-HOGAR", "NUEVOS NEGOCIOS"]
BLANDOS = ["ACCESORIOS", "DEPORTES", "HOMBRES", "MUJER", "CALZADO", "INFANTIL"]

# --- Parámetros del score ---
DIAS_ONBOARDING = 90   # un seller entra al análisis tras 90 días de creado
HORIZONTE_MESES = 3    # ventana de 3 meses cerrados -> ya no se usa 
HORIZONTE_DIARIO = 90  #Cambio de granularidad temporal de meses a días para entregar la posibilidad de calcular el score en cualquier horizonte temporal de forma diaria

# --- Tramos de 30 días dentro del horizonte (reemplazan a los "meses" en los tratamientos) ---
# Con 90 días: tramo 0 = últimos 30 días, tramo 1 = días 31-60, tramo 2 = días 61-90.
# Si el horizonte no es múltiplo de 30, el último tramo queda más corto.
TAMANO_TRAMO = 30
TRAMOS_TOTALES = -(-HORIZONTE_DIARIO // TAMANO_TRAMO)   # división hacia arriba: 90 -> 3, 60 -> 2, 45 -> 2
