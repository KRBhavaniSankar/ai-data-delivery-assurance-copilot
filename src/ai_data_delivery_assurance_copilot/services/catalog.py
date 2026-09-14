import json
from pathlib import Path

from ai_data_delivery_assurance_copilot.models.contracts import CatalogDataset

CATALOG_DIR = Path(__file__).resolve().parents[3] / "data" / "catalog"

def load_catalog() -> list[CatalogDataset]:
    datasets = []
    for path in sorted(CATALOG_DIR.glob("*.json")):
        datasets.append(CatalogDataset.model_validate(json.loads(path.read_text())))
    return datasets

def search_catalog(query: str) -> list[CatalogDataset]:
    terms = {t for t in query.lower().replace("/", " ").split() if len(t) > 2}
    scored = []
    for dataset in load_catalog():
        haystack = " ".join([
            dataset.table_name,
            dataset.description,
            " ".join(c.name for c in dataset.columns),
            " ".join(c.description for c in dataset.columns),
            " ".join(dataset.relationships),
        ]).lower()
        score = sum(1 for term in terms if term in haystack)
        if score:
            scored.append((score, dataset))
    return [d for _, d in sorted(scored, key=lambda x: (-x[0], x[1].table_name))]
