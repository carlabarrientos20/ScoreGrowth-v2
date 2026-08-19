import psycopg2
import pandas as pd
from dotenv import load_dotenv
import os

# Carga las credenciales desde el .env (debe estar en la MISMA carpeta que este script)
load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("REDSHIFT_HOST"),
    port=5439,
    dbname="datalake",
    user=os.getenv("REDSHIFT_USER"),
    password=os.getenv("REDSHIFT_PASSWORD")
)

# Query original del proyecto heredado, SIN los filtros de Metabase [[and {{...}}]]
# (esa sintaxis solo funciona dentro de Metabase, no en psycopg2)
query_original = """
WITH ranked_venta_perdida_stock AS (
with transacciones as (
select
    seller_id,
    seller,
    sku_marketplace as sku_variante,
    nombre_producto,
    division,
    max(fecha_de_orden::date) as ultima_venta,
    count(sub_order) as total_transacciones,
    avg(precio) as precio_tmp_avg
from cencosud_chile_txd_reporter.ordenes_mkp
where fecha_de_orden::date between current_date - interval '14 days' and current_date - interval '0 day'
and descripcion_order_type != 'EASY'
group by 1,2,3,4,5),
base_oos AS (
    SELECT
        item_id AS sku,
        MAX(last_source_updated_at) AS fecha_quiebre,
        SUM(quantity) AS stock_oos
    FROM "eiffel-stock".supply_summary
    WHERE item_id LIKE '%-%'
    GROUP BY 1
    HAVING stock_oos = 0
),
frecuencia_mes as (
SELECT sku_marketplace as sku_variante,
    COUNT(DISTINCT fecha_de_orden::date)::decimal as días_venta,
    EXTRACT(day FROM date_trunc('month', current_date) - interval '1 day') as días_del_mes,
    EXTRACT(day FROM date_trunc('month', current_date) - interval '1 day') /
    COUNT(DISTINCT fecha_de_orden::date)::decimal AS frecuencia_venta
from cencosud_chile_txd_reporter.ordenes_mkp
WHERE fecha_de_orden >= date_trunc('month', current_date) - interval '1 month'
  AND fecha_de_orden <  date_trunc('month', current_date)
  and descripcion_order_type != 'EASY'
group by sku_marketplace
)
select
    s.seller_id,
    s.seller,
    s.sku_variante,
    s.nombre_producto,
    s.division,
    ss.fecha_quiebre,
    s.total_transacciones,
    GREATEST(1,current_date - s.ultima_venta::date) AS dias_venta_perdida,
    s.ultima_venta::date,
    f.frecuencia_venta,
    GREATEST(1,dias_venta_perdida/f.frecuencia_venta) as dias_reales_perdida,
    GREATEST(1,s.ultima_venta::date - (current_date - interval '14 day')::date) AS dias_de_venta,
    GREATEST(1,(round(s.total_transacciones::decimal/dias_de_venta,3)::decimal(18,3))) as transacciones_promedio,
    s.precio_tmp_avg AS precio_tmp,
    round(dias_reales_perdida * s.precio_tmp_avg * transacciones_promedio) as venta_perdida,
    DENSE_RANK() OVER (PARTITION BY s.seller ORDER BY venta_perdida DESC) AS ranking_perdida_venta
from base_oos ss
inner join (select variant_id, publish
    from source_cenco_pim.product_publish
    where publish = 'true') p
on ss.sku = p.variant_id
inner join transacciones s on ss.sku= s.sku_variante
left join frecuencia_mes f on f.sku_variante = ss.sku
where s.seller is not null
)
SELECT distinct
    c.account_executive,
    r.sku_variante,
    r.seller,
    r.nombre_producto,
    repli.division,
    r.fecha_quiebre::date,
    r.venta_perdida as venta_perdida_estimada
FROM ranked_venta_perdida_stock r
LEFT JOIN cencosud_chile_txd_reporter.cluster_seller c
ON r.seller_id = c.id_seller
LEFT JOIN (select distinct sku_marketplace, division
            from cencosud_chile_txd_reporter.rpt_catalogo_cencopim_product_replicas) repli
ON regexp_replace(r.sku_variante, '-.*$', '') = repli.sku_marketplace
"""

# ==========================================================================
# TOP 10 GLOBAL (los 10 SKUs con mayor venta perdida de todo el marketplace)
# Se envuelve la query original SIN modificarla y se filtra por fuera.
# ==========================================================================
query = f"""
SELECT * FROM (
    {query_original}
) sub
ORDER BY venta_perdida_estimada DESC
LIMIT 10
"""

# --------------------------------------------------------------------------
# SI NECESITAS TOP 10 POR SELLER (los 10 peores de CADA seller), comenta el
# bloque de arriba y descomenta este:
#
# query = f"""
# SELECT account_executive, sku_variante, seller, nombre_producto,
#        division, fecha_quiebre, venta_perdida_estimada
# FROM (
#     SELECT sub.*,
#            DENSE_RANK() OVER (PARTITION BY seller ORDER BY venta_perdida_estimada DESC) AS rk
#     FROM (
#         {query_original}
#     ) sub
# ) ranked
# WHERE rk <= 10
# ORDER BY seller, venta_perdida_estimada DESC
# """
# --------------------------------------------------------------------------

df = pd.read_sql(query, conn)
conn.close()

# Fuerza SKU y monto como texto para que Excel no los reinterprete
df["sku_variante"] = df["sku_variante"].astype(str)
df["venta_perdida_estimada"] = df["venta_perdida_estimada"].astype(str)

df.to_excel("venta_perdida_oos_top10.xlsx", index=False)

print(f"Filas exportadas: {len(df)}")
print(df)