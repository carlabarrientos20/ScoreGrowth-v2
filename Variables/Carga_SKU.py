"""
Variable 3 y 6: Catalogo (disponibilidad + volumen).

Para cada seller-dureza calcula DOS cosas de su catalogo:

  1. % SKU con stock (disponibilidad / gestion):
     pct_con_stock = SKU con stock / SKU creados
     -> percentil_stock: ranking del % dentro de la dureza.

  2. Volumen de SKU con stock (compromiso real con la plataforma):
     sku_stock en numero absoluto
     -> percentil_volumen_stock: ranking del VOLUMEN dentro de la dureza.

Ambas comparten el ingrediente "SKU con stock" pero lo miran distinto: una como
proporcion (gestiona bien lo que tiene) y otra como volumen (cuanto tiene). Un
seller chico bien surtido gana en % pero pierde en volumen -> ya no se apalanca.

Mismo universo que venta y CVR: Mid-Market + 90 dias + publish.
SKU con stock = stock > 0 Y approval_status = 'approved'.
"""

import pandas as pd
from db import run_query
from config import TABLA_SELLERS, DUROS, BLANDOS, DIAS_ONBOARDING

_duros_sql = ", ".join(f"'{d}'" for d in DUROS)
_blandos_sql = ", ".join(f"'{b}'" for b in BLANDOS)

TABLA_CATALOGO = "cencosud_chile_txd_reporter.rpt_catalogo_cencopim_product_replicas"

QUERY_PRODUCTOS = f"""
WITH sellers_validos AS (
    SELECT id AS seller_id, name
    FROM {TABLA_SELLERS}
    LEFT JOIN cencosud_chile_txd_reporter.cluster_seller c ON id = c.id_seller
    WHERE created_at <= DATEADD(day, -{DIAS_ONBOARDING}, CURRENT_DATE)
      AND c.tier = 'Mid-Market'
      AND publish = 1
),
cant_sku_creados AS (
    SELECT
        cat.seller_id,
        CASE
            WHEN cat.division IN ({_duros_sql})   THEN 'duros'
            WHEN cat.division IN ({_blandos_sql}) THEN 'blandos'
            ELSE 'otros'
        END AS division_db,
        COUNT(DISTINCT cat.sku_marketplace) AS sku_creados
    FROM {TABLA_CATALOGO} cat
    INNER JOIN sellers_validos s ON cat.seller_id = s.seller_id
    GROUP BY cat.seller_id, division_db
),
sku_con_stock AS (
    SELECT
        cat.seller_id,
        CASE
            WHEN cat.division IN ({_duros_sql})   THEN 'duros'
            WHEN cat.division IN ({_blandos_sql}) THEN 'blandos'
            ELSE 'otros'
        END AS division_db,
        COUNT(DISTINCT cat.sku_marketplace) AS sku_stock
    FROM {TABLA_CATALOGO} cat
    INNER JOIN sellers_validos s ON cat.seller_id = s.seller_id
    WHERE cat.stock > 0 AND cat.approval_status = 'approved'
    GROUP BY cat.seller_id, division_db
),
base AS (
    SELECT
        c.seller_id,
        s.name,
        c.division_db,
        c.sku_creados,
        COALESCE(st.sku_stock, 0) AS sku_stock,
        COALESCE(st.sku_stock, 0)::decimal / NULLIF(c.sku_creados, 0) AS pct_con_stock
    FROM cant_sku_creados c
    LEFT JOIN sku_con_stock st
        ON c.seller_id = st.seller_id
       AND c.division_db = st.division_db
    INNER JOIN sellers_validos s ON c.seller_id = s.seller_id
)
SELECT
    seller_id,
    name,
    division_db,
    sku_creados,
    sku_stock,
    ROUND(pct_con_stock * 100, 2) || '%' AS pct_con_stock,
    ROUND(
        PERCENT_RANK() OVER (PARTITION BY division_db ORDER BY pct_con_stock) * 100, 0
    ) AS percentil_stock,
    ROUND(
        PERCENT_RANK() OVER (PARTITION BY division_db ORDER BY sku_stock) * 100, 0
    ) AS percentil_volumen_stock
FROM base
ORDER BY division_db, sku_stock DESC
"""


def calcular() -> pd.DataFrame:
    """Devuelve: seller_id, name, division_db, sku_creados, sku_stock,
    pct_con_stock (texto %), percentil_stock (% disponibilidad, 0-100),
    percentil_volumen_stock (volumen de SKU con stock, 0-100).

    Clave: seller_id + division_db.
    """
    return run_query(QUERY_PRODUCTOS)


if __name__ == "__main__":
    df = calcular()
    print(f"Filas (seller-division): {len(df)}")
    print(f"Sellers unicos: {df['seller_id'].nunique()}")
    print(f"  en duros:   {df[df['division_db'] == 'duros']['seller_id'].nunique()}")
    print(f"  en blandos: {df[df['division_db'] == 'blandos']['seller_id'].nunique()}")
    print(df.head(100))