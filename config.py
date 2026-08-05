"""
Constantes del proyecto 
"""

# --- Tablas en Redshift ---
TABLA_SELLERS = "eiffel_seller.seller"
TABLA_TRANSACCIONES = "cencosud_chile_txd_reporter.vm_new_report_transaccion_mkp"

# --- Clasificación de divisiones en dureza ---
DUROS = ["DECO-HOGAR", "TECNOLOGIA", "ELECTRO-HOGAR", "NUEVOS NEGOCIOS"]
BLANDOS = ["ACCESORIOS", "DEPORTES", "HOMBRES", "MUJER", "CALZADO", "INFANTIL"]

# --- Parámetros del score ---
DIAS_ONBOARDING = 90   # un seller entra al análisis tras 90 días de creado
HORIZONTE_MESES = 3    # ventana de 3 meses cerrados 