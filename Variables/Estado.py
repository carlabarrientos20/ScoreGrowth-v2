"""
Estado del seller (CONTEXTO, no entra al score).

Un estado unico por seller MID-MARKET, respecto al ULTIMO MES CERRADO
(en agosto -> julio), alineado con el horizonte del resto de variables.

Sellers que SI vendieron en el mes de referencia:
  - Primera venta:    su primera venta fue justo ese mes.
  - Retenido Activo:  venia vendiendo seguido (tambien vendio el mes anterior).
  - Reactivado:       vendio ese mes pero venia de un hueco (no vendio el mes anterior).

Sellers que NO vendieron en el mes de referencia (apagados, por antiguedad
de su ultima venta):
  - Dormant:  ultima venta hace 1-2 meses.
  - Fugado:   ultima venta hace 3-6 meses.
  - Out <12:  ultima venta hace 6-12 meses.
  - Out >12:  ultima venta hace +12 meses.

Filtro MM via cluster_seller, igual que venta y CVR (universo consistente).
"""

import pandas as pd
from db import run_query

QUERY_ESTADO = """
WITH mm AS (
    SELECT id_seller
    FROM cencosud_chile_txd_reporter.cluster_seller
    WHERE tier = 'Mid-Market'
),
params AS (
    -- mes_sel = ultimo mes cerrado; mes_ant = el anterior a ese
    SELECT
        DATEADD(month, -1, DATE_TRUNC('month', CURRENT_DATE)) AS mes_sel,
        DATEADD(month, -2, DATE_TRUNC('month', CURRENT_DATE)) AS mes_ant
),
ventas_por_mes AS (
    SELECT
        t.seller_id,
        DATE_TRUNC('month', (t.año::text || '-' || LPAD(t.mes::text, 2, '0') || '-01')::date) AS mes_venta
    FROM cencosud_chile_txd_reporter.vm_new_report_transaccion_mkp t
    INNER JOIN mm ON t.seller_id = mm.id_seller
    GROUP BY t.seller_id, mes_venta
),
resumen AS (
    SELECT
        vpm.seller_id,
        MIN(vpm.mes_venta) AS primera_venta,
        MAX(vpm.mes_venta) AS ultima_venta,
        -- vendio en el mes de referencia?
        MAX(CASE WHEN vpm.mes_venta = p.mes_sel THEN 1 ELSE 0 END) AS vendio_sel,
        -- vendio en el mes anterior al de referencia?
        MAX(CASE WHEN vpm.mes_venta = p.mes_ant THEN 1 ELSE 0 END) AS vendio_ant
    FROM ventas_por_mes vpm
    CROSS JOIN params p
    GROUP BY vpm.seller_id
)
SELECT
    r.seller_id,
    CASE
        -- --- vendieron en el mes de referencia ---
        WHEN r.vendio_sel = 1 AND r.primera_venta = p.mes_sel THEN 'Primera venta'
        WHEN r.vendio_sel = 1 AND r.vendio_ant = 1 THEN 'Activo'
        WHEN r.vendio_sel = 1 AND r.vendio_ant = 0 THEN 'Reactivado'
        -- --- NO vendieron en el mes de referencia (apagados) ---
        -- ultima_venta se mide contra mes_sel: hace cuantos meses fue
        WHEN r.vendio_sel = 0 AND r.ultima_venta >= DATEADD(month, -2, p.mes_sel) THEN 'Dormant'
        WHEN r.vendio_sel = 0 AND r.ultima_venta >= DATEADD(month, -6, p.mes_sel) THEN 'Fugado'
        WHEN r.vendio_sel = 0 AND r.ultima_venta >= DATEADD(month, -12, p.mes_sel) THEN 'Out <12'
        WHEN r.vendio_sel = 0 AND r.ultima_venta <  DATEADD(month, -12, p.mes_sel) THEN 'Out >12'
        ELSE 'Otro'
    END AS estado_seller
FROM resumen r
CROSS JOIN params p
"""


def calcular() -> pd.DataFrame:
    """Devuelve: seller_id, estado_seller (una fila por seller MM)."""
    return run_query(QUERY_ESTADO)


if __name__ == "__main__":
    df = calcular()
    print(f"Sellers MM clasificados: {len(df)}")
    print("\nDistribucion de estados:")
    print(df["estado_seller"].value_counts())
    print()
    print(df.head(20))