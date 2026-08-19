"""
main.py - Score Growth: union de todas las variables.

Tabla LARGA: una fila por seller-dureza, base para calcular el score.
Cada fila es una unidad evaluable (un seller tiene un score en duros y otro
en blandos). Venta y CVR son por dureza; rentabilidad, inversion y estado
son por seller y se repiten en las dos filas del seller.

Claves de cruce:
  - venta + cvr              -> por [seller_id, division_db]
  - rentabilidad + inversion -> por [seller_id] (se repiten en ambas durezas)
  - estado                   -> por [seller_id] (contexto, no entra al score)
"""

import pandas as pd

from Scoring import calcular_score
import Variables.Venta_percentil as venta_percentil
import Variables.CVR as CVR
import Variables.Rentabilidad as Rentabilidad
import Variables.Inversion as Inversion
import Variables.Estado as Estado
import Variables.Carga_SKU as Carga_SKU
import Variables.Recurrencia_venta as Recurrencia

from export_excel import exportar


def tabla_larga() -> pd.DataFrame:
    """Una fila por seller-dureza, con todas las variables. Base del score."""

    print("=== CALCULANDO TABLA LARGA ===")
    print("=== VENTA ===")
    venta = venta_percentil.calcular()
    print("=== CVR ===")
    cvr = CVR.calcular()
    print("=== RECURRENCIA ===")
    rec = Recurrencia.calcular()

    venta_cols = venta[["seller_id", "name", "division_db", "venta", "venta_percentil"]]
    cvr_cols = cvr[["seller_id", "division_db", "cvr_seller", "percentil_cvr"]]
    rec_cols = rec[["seller_id", "division_db", "meses_vendidos", "recurrencia"]]

    print("=== MERGE VENTA + CVR + RECURRENCIA ===")
    df = venta_cols.merge(cvr_cols, on=["seller_id", "division_db"], how="outer")
    df = df.merge(rec_cols, on=["seller_id", "division_db"], how="outer")

    print("=== INVERSION ===")
    inv = Inversion.calcular()
    print("=== CARGA SKU ===")
    sku = Carga_SKU.calcular()

    print("=== MERGE + INVERSION + CARGA SKU ===")
    #rent_cols = rent[["seller_id", "rentable", "margen_pct"]]
    inv_cols = inv[["seller_id", "invirtio", "total_invertido"]]
    sku_cols = sku[["seller_id", "division_db", "sku_creados", "sku_stock",
                "pct_con_stock", "percentil_stock", "percentil_volumen_stock"]]
    # left join por seller: pega el mismo valor de rent/inv a las filas de duros y blandos
    #df = df.merge(rent_cols, on="seller_id", how="left")
    df = df.merge(inv_cols, on="seller_id", how="left")
    df = df.merge(sku_cols, on=["seller_id", "division_db"], how="left")

    # --- estado del seller (contexto) ---
    print("=== ESTADO DEL SELLER ===")
    est = Estado.calcular()                      
    df = df.merge(est, on="seller_id", how="left")
    df["estado_seller"] = df["estado_seller"].fillna("Sin venta mes ref")

    print("=== TABLA LARGA CALCULADA ===")
    # ordenar para que las dos filas de cada seller (duros/blandos) queden juntas
    df = df.sort_values(["seller_id", "division_db"]).reset_index(drop=True)

    orden = ["seller_id", "name", "estado_seller", "division_db", "score",
         "venta", "venta_percentil",
         "meses_vendidos", "recurrencia",
         "cvr_seller", "percentil_cvr",
         "sku_creados", "sku_stock", "pct_con_stock", "percentil_stock", "percentil_volumen_stock",
         "invirtio", "total_invertido"]
    df = df[[c for c in orden if c in df.columns]]

    return df


if __name__ == "__main__":
    largo = tabla_larga()
    largo = calcular_score(largo)
    print("=== TABLA LARGA (base del score) ===")
    print(f"Filas (seller-dureza): {len(largo)}")
    print(f"Sellers unicos: {largo['seller_id'].nunique()}")
    print("\nDistribucion de estados:")
    print(largo.drop_duplicates("seller_id")["estado_seller"].value_counts())

    orden = ["seller_id", "name", "estado_seller", "division_db", "score",
         "venta", "venta_percentil",
         "meses_vendidos", "recurrencia",
         "cvr_seller", "percentil_cvr",
         "sku_creados", "sku_stock", "pct_con_stock", "percentil_stock", "percentil_volumen_stock",
         "invirtio", "total_invertido"]
    largo = largo[[c for c in orden if c in largo.columns]]

    # guardar CSV crudo y el Excel formateado (tabla larga)
    print("=== GUARDANDO ARCHIVOS ===")
    largo.to_csv("score_largo.csv", index=False)
    exportar(largo, "score_growth.xlsx")
    print("\nListo: score_largo.csv y score_growth.xlsx")