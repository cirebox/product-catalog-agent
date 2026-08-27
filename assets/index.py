import csv
import re
import io

# ============================================
# CATEGORIAS REAIS DO BANCO (IDs confirmados)
# ============================================
CATEGORY_MAP = {
    "calcinhas":   1,
    "cuecas":      2,
    "sutias":      3,
    "camisetas":   4,
    "pijamas":     5,
    "meias":       6,
    "acessorios":  7,
    "body":        8,
}

# ============================================
# MARCAS REAIS (fabricantes de verdade)
# Nomes de modelos/peças NÃO são fabricantes
# ============================================
KNOWN_MANUFACTURERS = {
    "PATITEX": "Patitex",
    "LUNNA":   "Lunna",
    "HX":      "HX",
}


def infer_category_id(description: str) -> int:
    """Retorna o ID da categoria baseado no CATEGORY_MAP do banco."""
    desc_upper = description.upper()

    rules = [
        (r'\bCUECA\b',                             2),  # cuecas
        (r'\bTANGA\b|\bTANGAO\b',                 1),  # calcinhas
        (r'\bSOUTIEN\b|\bSUTI[ÃA]\b',             3),  # sutiãs
        (r'\bTOPPER\b',                           3),  # sutiãs (top similar)
        (r'\bBABY\s*DOLL\b',                      5),  # pijamas
        (r'\bCAMISOLA\b',                         5),  # pijamas
        (r'\bPIJAMA\b',                           5),  # pijamas
        (r'\bCONJUNTO\b',                         5),  # pijamas e conjuntos
        (r'\bMEIA\b',                             6),  # meias
        (r'\bSHORT\b',                            1),  # calcinhas (short íntimo)
        (r'\bCAL[ÇC]A\b|\bLEGGING\b|\bLEGGIN\b', 5),  # pijamas (legging)
        (r'\bSACOLA\b|\bKIT\b',                   7),  # acessórios
        (r'\bBODY\b',                             8),  # body
    ]

    for pattern, cat_id in rules:
        if re.search(pattern, desc_upper):
            return cat_id

    return 7  # acessórios (default)


def infer_category_name(category_id: int) -> str:
    """Retorna o nome da categoria pelo ID."""
    for name, cid in CATEGORY_MAP.items():
        if cid == category_id:
            return name
    return "desconhecido"


def infer_manufacturer(description: str) -> str:
    """
    Infer fabricante APENAS de marcas reais.
    Nomes de modelos/pessoas NÃO são fabricantes.
    """
    desc_upper = description.upper()

    # 1. Marcas reais conhecidas
    for pattern, brand in KNOWN_MANUFACTURERS.items():
        if pattern in desc_upper:
            return brand

    # 2. Importados
    if "IMPORTAD" in desc_upper or "IMPO" in desc_upper:
        return "Importado"

    # 3. Não identificado → vazio (usuário preenche manualmente)
    return ""


def infer_material(description: str) -> str:
    """Infer material baseado na descrição."""
    desc_upper = description.upper()

    rules = [
        (r'\bRENDA\b',                      "renda"),
        (r'\bMICROFIBRA\b|\bMICROFIB\b',    "microfibra"),
        (r'\bCOTTON\b|\bALGOD[ÃA]O\b|\bCOTO', "algodao"),
        (r'\bCANELAD[OA]\b',                "canelado"),
        (r'\bNEON\b',                       "neon"),
        (r'\bSEM\s*COSTURA\b',              "sem_costura"),
        (r'\bPALETAS\b',                    "paete"),
    ]

    for pattern, material in rules:
        if re.search(pattern, desc_upper):
            return material

    return ""


def infer_size(description: str) -> str:
    """Infer tamanho baseado na descrição."""
    desc_upper = description.upper()

    if "INFANTIL" in desc_upper or "INF " in desc_upper:
        return "infantil"
    if "JUVENIL" in desc_upper or "JUV " in desc_upper:
        return "juvenil"
    if "ADULTO" in desc_upper:
        return "adulto"
    if "PLUS SIZE" in desc_upper or "PLUS" in desc_upper:
        return "plus_size"
    if "MEIA" in desc_upper:
        return "unico"

    return ""


def process_csv(input_path: str, output_path: str):
    """Processa o CSV e adiciona colunas faltantes."""
    with open(input_path, "r", encoding="utf-8") as infile:
        reader = csv.reader(infile)
        rows = list(reader)

    header = [
        "ref", "description", "price", "stock",
        "manufacturer", "material", "size", "category", "category_id"
    ]
    processed = [header]

    for row in rows:
        if len(row) < 4:
            continue

        ref         = row[0].strip()
        description = row[1].strip()
        price       = row[2].strip()
        stock       = row[3].strip()

        manufacturer = infer_manufacturer(description)
        material     = infer_material(description)
        size         = infer_size(description)
        category_id  = infer_category_id(description)
        category_name = infer_category_name(category_id)

        processed.append([
            ref, description, price, stock,
            manufacturer, material, size, category_name, category_id
        ])

    # Escrever CSV final
    with open(output_path, "w", encoding="utf-8", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerows(processed)

    # Estatísticas
    total = len(processed) - 1
    print(f"✓ Processados {total} produtos → {output_path}\n")

    cats = {}
    manufs = {}
    sem_manuf = 0
    for r in processed[1:]:
        cat_label = f"{r[7]} (ID {r[8]})"
        cats[cat_label] = cats.get(cat_label, 0) + 1
        if r[4]:
            manufs[r[4]] = manufs.get(r[4], 0) + 1
        else:
            sem_manuf += 1

    print("📁 Categorias:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:<30} {count:>3} produtos")

    print(f"\n🏭 Fabricantes:")
    for m, count in sorted(manufs.items(), key=lambda x: -x[1]):
        print(f"  {m:<15} {count:>3} produtos")
    print(f"  {'(vazio → manual)':<15} {sem_manuf:>3} produtos")


if __name__ == "__main__":
    process_csv("produtos.csv", "produtos_completo.csv")