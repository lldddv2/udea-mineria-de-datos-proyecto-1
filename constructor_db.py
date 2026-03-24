import sqlite3
import pandas as pd

# ----------- Carga y limpieza de datos -----------
tabla = pd.read_csv('datos_crudos.csv')

tabla_limpia = tabla.dropna()
# -------------------------------------------------

# -------- Construcción de la base de datos -------
conexion = sqlite3.connect('datos_mision.db')
cursor = conexion.cursor()
# columnas de la tabla: pl_name (text), pl_rade (float), pl_bmasse (float)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS exoplanetas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pl_name TEXT,
        pl_rade REAL,
        pl_bmasse REAL
    )
''')

# insertar datos
for index, row in tabla_limpia.iterrows():
    cursor.execute('''
        INSERT INTO exoplanetas (pl_name, pl_rade, pl_bmasse) VALUES (?, ?, ?)
    ''', (row['pl_name'], row['pl_rade'], row['pl_bmasse']))

# Guardar y cerrar la conexión
conexion.commit()
conexion.close()
# -------------------------------------------------

