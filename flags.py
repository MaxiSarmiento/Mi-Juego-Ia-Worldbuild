# flags.py - Eventos importantes de la historia

def crear_flags():
    return {}

def agregar_flag(flags, clave, descripcion):
    if clave not in flags:
        flags[clave] = descripcion
        return True  # flag nuevo
    return False  # ya existía

def ver_flags(flags):
    if not flags:
        print("No hay eventos registrados todavía.")
        return
    print("\n=== EVENTOS IMPORTANTES ===")
    for clave, descripcion in flags.items():
        print(f"  ✓ {descripcion}")
    print("===========================\n")

def flags_para_prompt(flags):
    if not flags:
        return "Ninguno todavía."
    return "\n".join([f"- {desc}" for desc in flags.values()])