"""

Capas:
  1. Segmento por score (cortes fijos, Premium >= 70)
  2. Banderas de brecha por variable (umbral < 40 en percentil)
  3. Perfil de banderas (texto) + conteo, para agrupar despues

"""

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# ======================================================================
# CAPA 1 - SEGMENTACION POR SCORE  (cortes fijos, continuos, sin huecos)
# ======================================================================
CORTE_PREMIUM = 70     # >= 70
CORTE_SOLIDO = 53      # 53 a 70
CORTE_DESARROLLO = 37  # 37 a 53   (< 37 = Riesgo)


def clasificar_segmento(score: float) -> str:
    if pd.isna(score):
        return "Sin score"
    if score >= CORTE_PREMIUM:
        return "Premium"
    if score >= CORTE_SOLIDO:
        return "Solido"
    if score >= CORTE_DESARROLLO:
        return "En desarrollo"
    return "Riesgo"


# ======================================================================
# CAPA 2 - BANDERAS DE BRECHA
# ======================================================================
UMBRAL_PERCENTIL = 40
UMBRAL_RECURRENCIA = 1.0

FLAGS = ["flag_venta_baja", "flag_stock_bajo", "flag_catalogo_bajo",
         "flag_cvr_bajo", "flag_intermitente", "flag_sin_inversion"]

ETIQUETAS = {
    "flag_venta_baja": "Venta",
    "flag_stock_bajo": "Stock",
    "flag_catalogo_bajo": "Catalogo",
    "flag_cvr_bajo": "CVR",
    "flag_intermitente": "Intermitente",
    "flag_sin_inversion": "SinInversion",
}


def perfilar(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica las 3 capas y devuelve el df enriquecido."""
    df = df.copy()

    for col in ["score", "venta_percentil", "percentil_stock",
                "percentil_volumen_stock", "percentil_cvr", "recurrencia"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["segmento"] = df["score"].apply(clasificar_segmento)

    df["flag_venta_baja"]    = df["venta_percentil"] < UMBRAL_PERCENTIL
    df["flag_stock_bajo"]    = df["percentil_stock"] < UMBRAL_PERCENTIL
    df["flag_catalogo_bajo"] = df["percentil_volumen_stock"] < UMBRAL_PERCENTIL
    df["flag_cvr_bajo"]      = df["percentil_cvr"] < UMBRAL_PERCENTIL
    df["flag_intermitente"]  = df["recurrencia"] < UMBRAL_RECURRENCIA
    df["flag_sin_inversion"] = df["invirtio"].astype(str).str.lower() == "no"
    for f in FLAGS:
        df[f] = df[f].fillna(False)


    df["n_banderas"] = df[FLAGS].sum(axis=1)

    def armar_perfil(fila):
        activas = [ETIQUETAS[f] for f in FLAGS if fila[f]]
        return " + ".join(activas) if activas else "Sin brechas"

    df["perfil_banderas"] = df.apply(armar_perfil, axis=1)
    return df


# ======================================================================
# ESCRIBIR HOJA "Resumen" 
# ======================================================================
COLS_RESUMEN = ["seller_id", "name", "estado_seller", "division_db",
                "score", "segmento",
                "flag_venta_baja", "flag_stock_bajo", "flag_catalogo_bajo",
                "flag_cvr_bajo", "flag_intermitente", "flag_sin_inversion",
                "n_banderas", "perfil_banderas"]

COLOR_SEGMENTO = {
    "Premium":       "63BE7B",   # verde
    "Solido":        "A9D08E",   # verde claro
    "En desarrollo": "FFEB84",   # amarillo
    "Riesgo":        "F8696B",   # rojo
    "Sin score":     "D9D9D9",   # gris
}


def escribir_hoja_resumen(df: pd.DataFrame, path: str = "score_growth.xlsx"):
    resumen = df[[c for c in COLS_RESUMEN if c in df.columns]].copy()

    for f in FLAGS:
        if f in resumen.columns:
            resumen[f] = resumen[f].map({True: "SI", False: ""})

    resumen = resumen.sort_values(["division_db", "score"], ascending=[True, False])

    wb = load_workbook(path)
    if "Resumen" in wb.sheetnames:  
        del wb["Resumen"]
    ws = wb.create_sheet("Resumen")

    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    cell_font = Font(name="Arial", size=10)
    center = Alignment(horizontal="center", vertical="center")
    thin = Side(style="thin", color="D9D9D9")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    cols = list(resumen.columns)

    for j, col in enumerate(cols, start=1):
        c = ws.cell(row=1, column=j, value=col)
        c.fill = header_fill
        c.font = header_font
        c.alignment = center
        c.border = border

    seg_idx = cols.index("segmento") + 1 if "segmento" in cols else None


    for i, (_, fila) in enumerate(resumen.iterrows(), start=2):
        for j, col in enumerate(cols, start=1):
            val = fila[col]
            if pd.isna(val):
                val = None
            c = ws.cell(row=i, column=j, value=val)
            c.font = cell_font
            c.alignment = center
            c.border = border
            if col == "score" and val is not None:
                c.number_format = "0"
    
        if seg_idx:
            seg_val = fila["segmento"]
            color = COLOR_SEGMENTO.get(seg_val)
            if color:
                ws.cell(row=i, column=seg_idx).fill = PatternFill("solid", fgColor=color)

    n_filas = len(resumen) + 1


    for j, col in enumerate(cols, start=1):
        letra = get_column_letter(j)
        ancho = min(max(len(str(col)), 12) + 2, 32)
        if col == "perfil_banderas":
            ancho = 30
        ws.column_dimensions[letra].width = ancho


    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{n_filas}"
    ws.freeze_panes = "A2"

    wb.save(path)
    print(f"Hoja 'Resumen' agregada a: {path}  ({len(resumen)} filas)")


def resumen_consola(df: pd.DataFrame):
    """Conteos rapidos por segmento y por perfil, en consola."""
    print("\n=== SELLERS POR SEGMENTO Y DUREZA ===")
    print(pd.crosstab(df["segmento"], df["division_db"]))

    print("\n=== PERFILES DE BRECHA MAS COMUNES (top 15) ===")
    print(df["perfil_banderas"].value_counts().head(15))


if __name__ == "__main__":
    RUTA = "score_growth.xlsx"
    df = pd.read_excel(RUTA)          

    df = perfilar(df)
    resumen_consola(df)
    escribir_hoja_resumen(df, RUTA)
    print("\nListo.")