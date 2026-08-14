
PESO_VENTA = 0.3
PESO_DISPONIBILIDAD_SKU = 0.2
PESO_VOLUMEN_SKU = 0.1
PESO_RENTABILIDAD = 0.2
PESO_CVR = 0.1
PESO_INVERSION = 0.1



def calcular_score(df):
    """
    Calcula el score de cada seller según los pesos definidos en Scoring.py
    """
    print("=== CALCULANDO SCORE ===")
    df["Rentabilidad_binaria"] = df["rentable"].map({"si": 100, "no": 0, "sin dato": 50})
    df["Inversion_binaria"] = df["invirtio"].map({"si": 100, "no": 0})

    df["score"] = (
        df["venta_percentil"].fillna(0) * PESO_VENTA +
        df["percentil_stock"].fillna(0) * PESO_DISPONIBILIDAD_SKU +
        df["percentil_volumen_stock"].fillna(0) * PESO_VOLUMEN_SKU +
        df["Rentabilidad_binaria"].fillna(50) * PESO_RENTABILIDAD +  #BINARIO
        df["percentil_cvr"].fillna(0) * PESO_CVR +
        df["Inversion_binaria"].fillna(0) * PESO_INVERSION  #BINARIO
    )
    print("=== SCORE CALCULADO ===")
    return df


