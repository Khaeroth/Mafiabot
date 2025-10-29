import json
import os

def cargar_json(ruta):
    """Carga un archivo JSON y devuelve su contenido como diccionario."""
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ Error: {ruta} está dañado o no es un JSON válido.")
            return {}
    return {}

def guardar_json(ruta, datos):
    """Guarda un diccionario en un archivo JSON."""
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ No se pudo guardar {ruta}: {e}")
