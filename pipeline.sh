#!/bin/bash

# Inicialización del entorno virtual
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

wget -O datos_crudos.csv "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=SELECT+pl_name,pl_rade,pl_bmasse+FROM+ps+WHERE+pl_rade+IS+NOT+NULL+AND+pl_bmasse+IS+NOT+NULL&amp;format=csv"

python constructor_db.py
python analisis_visual.py