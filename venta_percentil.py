"""
Variable 1: Venta.

Calcula la venta total de cada seller en los últimos 3 meses cerrados,
clasificada por división (duros/blandos), y su percentil DENTRO de su división.

La pregunta que responde: "¿este seller vende más o menos que sus pares
(mismo grupo de división)?" -> el percentil lo posiciona de 0 a 100.
"""

import pandas as pd
from db import run_query
from config import TABLA_SELLERS, TABLA_TRANSACCIONES, DUROS, BLANDOS, DIAS_ONBOARDING

_duros_sql = ", ".join(f"'{d}'" for d in DUROS)
_blandos_sql = ", ".join(f"'{b}'" for b in BLANDOS)

QUERY_VENTA = f"""

-- sellers que ya pasaron los 90 días de onboarding
WITH sellers_validos AS (
    SELECT id AS seller_id, name, c.tier
    FROM {TABLA_SELLERS}
    LEFT JOIN cencosud_chile_txd_reporter.cluster_seller c ON id = c.id_seller
    WHERE created_at <= DATEADD(day, -90, CURRENT_DATE) AND c.tier = 'Mid-Market'
),

 -- venta por seller y por su división, en el horizonte de 3 meses cerrados
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
    GROUP BY t.seller_id, division_db,name 
)

SELECT
    seller_id,
    name,
    division_db,
    venta,
    AVG(venta)          OVER (PARTITION BY division_db) AS promedio_division,
    PERCENT_RANK()      OVER (PARTITION BY division_db ORDER BY venta) AS percentil
FROM ventas_seller
WHERE division_db = 'duros'
ORDER BY division_db, venta DESC

"""


def calcular() -> pd.DataFrame:
    """Devuelve un DataFrame con: seller_id, division, venta, promedio_grupo, venta_percentil.
    """
    return run_query(QUERY_VENTA)


if __name__ == "__main__":
    df = calcular()
    print(f"Filas (seller-division): {len(df)}")
    print(df.head(100))