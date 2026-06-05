SECTOR_AGGREGATES = {
    "Industrie manufacturière": ("C", "ICA_INDCONS"),
    "Construction": ("A10_FZ", "ICA_INDCONS"),
    "Commerce": ("G", "ICA_COMM"),
    "Services": ("S", "ICA_SERV"),
}

IDX_TYPE_LABELS = {
    "ICA_INDCONS": "Industrie & Construction",
    "ICA_COMM": "Commerce (CA)",
    "ICA_SERV": "Services (CA)",
    "IPS": "Services (Production)",
    "IVVC": "Commerce (Volume des ventes)",
}

SEASONAL_LABELS = {
    "Y": "CVS-CJO (corrigé)",
    "N": "Brut",
    "W": "CJO uniquement",
}

MARCHE_LABELS = {
    "_T": "Total",
    "F": "Marché intérieur",
    "W": "Marché extérieur",
}
