# personaje.py - Todo lo relacionado al personaje femenino

def crear_personaje(nombre, personalidad, apariencia):
    return {
        "nombre": nombre,
        "personalidad": personalidad,
        "apariencia": apariencia,
        "stats": {
            "amistad": 10,
            "cariño": 0,
            "miedo": 0,
            "odio": 0
        }
    }

def ver_stats(personaje):
    s = personaje["stats"]
    print(f"""
--- Stats de {personaje['nombre']} ---
❤️  Amistad : {s['amistad']}/100
💕  Cariño  : {s['cariño']}/100
😨  Miedo   : {s['miedo']}/100
💢  Odio    : {s['odio']}/100
--------------------------------""")

def actualizar_stats(personaje, cambios):
    for stat, valor in cambios.items():
        if stat in personaje["stats"]:
            nuevo = personaje["stats"][stat] + valor
            personaje["stats"][stat] = max(0, min(100, nuevo))