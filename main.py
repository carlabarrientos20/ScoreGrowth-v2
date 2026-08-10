"""
main.py - Score Growth: union de todas las variables.

Junta las 4 variables en UNA tabla. Dos formatos:

  1. LARGO (una fila por seller-dureza): base para calcular el score.
     Cada fila es una unidad evaluable (un seller tiene un score en duros
     y otro en blandos). Venta y CVR son por dureza; rentabilidad e
     inversion son por seller y se repiten en las dos filas del seller.

  2. ANCHO (una fila por seller): para presentar/exportar. Se pivotan las
     variables de dureza a columnas separadas (duros / blandos).

Claves de cruce:
  - venta + cvr  -> por [seller_id, division_db]
  - rentabilidad + inversion -> por [seller_id] (se repiten en ambas durezas)
"""

import pandas as pd

import venta_percentil
import CVR
import Rentabilidad
import Inversion

from export_excel import exportar

def tabla_larga() -> pd.DataFrame:
    """Una fila por seller-dureza, con todas las variables. Base del score."""
    venta = venta_percentil.calcular()      
    cvr = CVR.calcular()                    

    venta_cols = venta[["seller_id", "name", "division_db", "venta", "venta_percentil"]]
    cvr_cols = cvr[["seller_id", "division_db", "cvr_seller", "percentil_cvr"]]

    df = venta_cols.merge(cvr_cols, on=["seller_id", "division_db"], how="outer")
    rent = Rentabilidad.calcular()          
    inv = Inversion.calcular()             

    rent_cols = rent[["seller_id", "rentable", "margen_pct"]]
    inv_cols = inv[["seller_id", "invirtio", "total_invertido"]]

    # left join por seller: pega el mismo valor de rent/inv a las filas de duros y blandos
    df = df.merge(rent_cols, on="seller_id", how="left")
    df = df.merge(inv_cols, on="seller_id", how="left")

    # estado del seller: pendiente por ahora
    df["estado_seller"] = "pendiente"

    # ordenar para que las dos filas de cada seller (duros/blandos) queden juntas
    df = df.sort_values(["seller_id", "division_db"]).reset_index(drop=True)

    return df


def tabla_ancha(df_largo: pd.DataFrame) -> pd.DataFrame:
    """Una fila por seller, con las variables de dureza desdobladas en columnas.
    Para presentar / exportar."""
    # separar las columnas que dependen de dureza vs las que son por seller
    idx = ["seller_id", "name", "estado_seller", "rentable", "margen_pct",
           "invirtio", "total_invertido"]

    # pivotar venta y su percentil, y cvr y su percentil, por dureza
    ancha = df_largo.pivot_table(
        index=[c for c in idx if c in df_largo.columns],
        columns="division_db",
        values=["venta", "venta_percentil", "percentil_cvr"],
        aggfunc="first"
    )
    # aplanar los nombres de columna: ('venta','duros') -> 'venta_duros'
    ancha.columns = [f"{var}_{dur}" for var, dur in ancha.columns]
    ancha = ancha.reset_index()

    return ancha


if __name__ == "__main__":
    largo = tabla_larga()
    print("=== TABLA LARGA (base del score) ===")
    print(f"Filas (seller-dureza): {len(largo)}")
    print(f"Sellers unicos: {largo['seller_id'].nunique()}")

    ancha = tabla_ancha(largo)
    print("\n=== TABLA ANCHA (para presentar) ===")
    print(f"Filas (sellers): {len(ancha)}")

    # guardar CSV (por si los quieres crudos) y el Excel formateado
    largo.to_csv("score_largo.csv", index=False)
    ancha.to_csv("score_ancho.csv", index=False)
    exportar(largo, "score_growth.xlsx")   # Excel con colores, %, filtros
    print("\nListo: score_largo.csv, score_ancho.csv y score_growth.xlsx")