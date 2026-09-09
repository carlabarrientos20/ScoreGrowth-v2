"""
Variable: Recurrencia de venta.

Mide en cuantos meses  el seller efectivamente vendio.

  recurrencia = meses_con_venta / meses_totales_ventana   (valor 0.0 a 1.0)
"""

import pandas as pd
from db import run_query
from config import (
    TABLA_SELLERS,
    TABLA_TRANSACCIONES,
    DUROS,
    BLANDOS,
    DIAS_ONBOARDING,
    HORIZONTE_MESES
)

_duros_sql = ", ".join(f"'{d}'" for d in DUROS)
_blandos_sql = ", ".join(f"'{b}'" for b in BLANDOS)

QUERY_RECURRENCIA = f"""
WITH sellers_validos AS (
    SELECT id AS seller_id, name, admin_email, c.tier
    FROM {TABLA_SELLERS}
    LEFT JOIN cencosud_chile_txd_reporter.cluster_seller c ON id = c.id_seller
    WHERE created_at <= DATEADD(day, -{DIAS_ONBOARDING}, CURRENT_DATE)
      AND c.tier = 'Mid-Market'
      AND publish = 1
),
meses_con_venta AS (
    SELECT
        t.seller_id,
        s.name,
        s.admin_email,
        CASE
            WHEN t.division IN ({_duros_sql})   THEN 'duros'
            WHEN t.division IN ({_blandos_sql}) THEN 'blandos'
            ELSE 'otros'
        END AS division_db,
        COUNT(DISTINCT DATE_TRUNC('month', t.fecha_venta)) AS meses_vendidos
    FROM {TABLA_TRANSACCIONES} t
    INNER JOIN sellers_validos s
        ON t.seller_id = s.seller_id
    WHERE t.fecha_venta >= DATE_TRUNC('month', DATEADD(month, -{HORIZONTE_MESES}, CURRENT_DATE))
      AND t.fecha_venta <  DATE_TRUNC('month', CURRENT_DATE)
    GROUP BY t.seller_id, division_db, name, admin_email
)
SELECT
    seller_id,
    name,
    admin_email,
    division_db,
    meses_vendidos,
    {HORIZONTE_MESES} AS meses_ventana,
    ROUND(meses_vendidos::numeric / {HORIZONTE_MESES}, 3) AS recurrencia
FROM meses_con_venta
ORDER BY division_db, recurrencia DESC
"""


def calcular() -> pd.DataFrame:
    """Devuelve: seller_id, name, admin_email, division_db, meses_vendidos, meses_ventana, recurrencia.

    recurrencia va de 0.0 (nunca vendio) a 1.0 (vendio todos los meses).
    Para el score: aporte = recurrencia * PESO 
    """
    return run_query(QUERY_RECURRENCIA)


if __name__ == "__main__":
    df = calcular()
    print(f"Ventana: {HORIZONTE_MESES} meses")
    print(f"Filas (seller-division): {len(df)}")
    print(f"Sellers unicos: {df['seller_id'].nunique()}")
    print("\nDistribucion de recurrencia:")
    print(df["recurrencia"].value_counts().sort_index())
    print("\n", df.head(50))