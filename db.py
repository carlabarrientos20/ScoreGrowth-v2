"""
Conexiones a bases de datos para el proyecto Score Growth.

Dos fuentes:
  - Redshift (datalake): venta, CVR. Usa run_query().
  - Postgres (eiffel-ledger): sponsored products. Usa run_query_pg().

Requiere:
  - VPN de Cencosud activa.
  - Un archivo .env en la carpeta con las credenciales de ambas bases.

.env esperado:
  # Redshift
  REDSHIFT_HOST=...
  REDSHIFT_PORT=5439
  REDSHIFT_DB=...
  REDSHIFT_USER=...
  REDSHIFT_PASSWORD=...

  # Postgres (eiffel-ledger)
  PG_HOST=cl-mkp-eiffel-ledger.cluster-ro-...
  PG_PORT=5432
  PG_DB=postgres
  PG_USER=ledger_user
  PG_PASSWORD=...
"""

import os
import redshift_connector
import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """Abre una conexion a Redshift."""
    return redshift_connector.connect(
        host=os.getenv("REDSHIFT_HOST"),
        port=int(os.getenv("REDSHIFT_PORT", 5439)),
        database=os.getenv("REDSHIFT_DB"),
        user=os.getenv("REDSHIFT_USER"),
        password=os.getenv("REDSHIFT_PASSWORD"),
    )


def run_query(sql: str) -> pd.DataFrame:
    """Ejecuta una consulta en Redshift y devuelve un DataFrame."""
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()

def get_connection_pg():
    """Abre una conexion a Postgres (eiffel-ledger)."""
    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=int(os.getenv("PG_PORT", 5432)),
        dbname=os.getenv("PG_DB"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
    )


def run_query_pg(sql: str) -> pd.DataFrame:
    """Ejecuta una consulta en Postgres y devuelve un DataFrame."""
    conn = get_connection_pg()
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()


if __name__ == "__main__":
    print("Redshift:")
    print(run_query("SELECT CURRENT_DATE AS hoy"))
    print("\nPostgres:")
    print(run_query_pg("SELECT CURRENT_DATE AS hoy"))