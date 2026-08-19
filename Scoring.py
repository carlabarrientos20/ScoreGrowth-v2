"""
Scoring.py - Calculo del score ponderado 

"""

PESO_VENTA = 0.3
PESO_DISPONIBILIDAD_SKU = 0.2
PESO_VOLUMEN_SKU = 0.1
PESO_RECURRENCIA = 0.15
PESO_CVR = 0.15
PESO_INVERSION = 0.1
VALOR_MAXIMO = 100


def calcular_score(df):

    print("=== CALCULANDO SCORE ===")

    df["Inversion_binaria"] = df["invirtio"].map({"si": 100, "no": 0})
    df["recurrencia_100"] = df["recurrencia"].fillna(0) * 100

    df.loc[df["estado_seller"] == "Primera venta", "recurrencia_100"] = VALOR_MAXIMO

    df["score"] = (
        df["venta_percentil"].fillna(0) * PESO_VENTA +
        df["percentil_stock"].fillna(0) * PESO_DISPONIBILIDAD_SKU +
        df["percentil_volumen_stock"].fillna(0) * PESO_VOLUMEN_SKU +
        df["recurrencia_100"] * PESO_RECURRENCIA +
        df["percentil_cvr"].fillna(0) * PESO_CVR +
        df["Inversion_binaria"].fillna(0) * PESO_INVERSION 
    )
    print("=== SCORE CALCULADO ===")
    return df