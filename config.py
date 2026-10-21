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
HORIZONTE_DIARIO = 90  #Cambio de granularidad temporal de meses a días para entregar la posibilidad de calcular el score de forma diaria
