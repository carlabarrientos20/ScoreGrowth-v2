"""
Variable 1: Venta.

Calcula la venta total de cada seller en los ultimos 3 meses cerrados,
clasificada por division (duros/blandos), y su percentil DENTRO de su dureza.

La pregunta que responde: "este seller vende mas o menos que sus pares
(mismo grupo de dureza)?" -> el percentil lo posiciona de 0 a 100.
"""

import pandas as pd
from db import run_query
from config import TABLA_SELLERS, TABLA_TRANSACCIONES, DUROS, BLANDOS, DIAS_ONBOARDING

_duros_sql = ", ".join(f"'{d}'" for d in DUROS)
_blandos_sql = ", ".join(f"'{b}'" for b in BLANDOS)

QUERY_VENTA = f"""
WITH sellers_validos AS (
    SELECT id AS seller_id, name, c.tier
    FROM {TABLA_SELLERS}
    LEFT JOIN cencosud_chile_txd_reporter.cluster_seller c ON id = c.id_seller
    WHERE created_at <= DATEADD(day, -{DIAS_ONBOARDING}, CURRENT_DATE)
      AND c.tier = 'Mid-Market'
      AND publish = 1
),
ventas_seller AS (
    SELECT
        t.seller_id,
        s.name,
        CASE
            WHEN t.division IN ({_duros_sql})   THEN 'duros'
            WHEN t.division IN ({_blandos_sql}) THEN 'blandos'
            ELSE 'otros'
        END AS division_db,
        SUM(t.precio_venta) AS venta
    FROM {TABLA_TRANSACCIONES} t
    INNER JOIN sellers_validos s
        ON t.seller_id = s.seller_id
    WHERE t.fecha_venta >= DATE_TRUNC('month', DATEADD(month, -3, CURRENT_DATE))
      AND t.fecha_venta <  DATE_TRUNC('month', CURRENT_DATE)
    GROUP BY t.seller_id, division_db, name
)
SELECT
    seller_id,
    name,
    division_db,
    venta,
    AVG(venta) OVER (PARTITION BY division_db) AS promedio_division,
    ROUND(PERCENT_RANK() OVER (PARTITION BY division_db ORDER BY venta) * 100, 0) AS venta_percentil
FROM ventas_seller
ORDER BY division_db, venta DESC
"""


def calcular() -> pd.DataFrame:
    """Devuelve: seller_id, name, division_db, venta, promedio_division, venta_percentil.

    Clave: seller_id + division_db (un seller mixto aparece en dos filas).
    """
    return run_query(QUERY_VENTA)


if __name__ == "__main__":
    df = calcular()
    print(f"Filas (seller-division): {len(df)}")
    print(f"Sellers unicos: {df['seller_id'].nunique()}")
    print(f"  en duros:   {df[df['division_db'] == 'duros']['seller_id'].nunique()}")
    print(f"  en blandos: {df[df['division_db'] == 'blandos']['seller_id'].nunique()}")
    print(f"  en otros:   {df[df['division_db'] == 'otros']['seller_id'].nunique()}")
    print(df.head(100))