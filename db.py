"""
Conexión a Redshift para el proyecto Score Growth.

Requiere:
  - VPN de Cencosud activa 
  - Un archivo .env en la misma carpeta con las credenciales.

.env esperado:
  REDSHIFT_HOST=...
  REDSHIFT_PORT=5439
  REDSHIFT_DB=...
  REDSHIFT_USER=...
  REDSHIFT_PASSWORD=...
"""

import os
import redshift_connector
import pandas as pd
from dotenv import load_dotenv

load_dotenv()  # carga el .env de la carpeta actual


def get_connection():
    """Abre una conexión a Redshift usando las credenciales del .env."""
    return redshift_connector.connect(
        host=os.getenv("REDSHIFT_HOST"),
        port=int(os.getenv("REDSHIFT_PORT", 5439)),
        database=os.getenv("REDSHIFT_DB"),
        user=os.getenv("REDSHIFT_USER"),
        password=os.getenv("REDSHIFT_PASSWORD"),
    )


def run_query(sql: str) -> pd.DataFrame:
    """Ejecuta una consulta y devuelve el resultado como DataFrame.

    Abre y cierra la conexión sola, así no dejas conexiones colgando.
    """
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()


if __name__ == "__main__":
    df = run_query("SELECT CURRENT_DATE AS hoy")
    print("Conexión OK:")
    print(df)