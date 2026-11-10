import json
import subprocess
import sys

import pytest

from steward_datos.config import CARPETA_POLITICAS
from steward_datos.rag.fragmentar import fragmentar, leer_politica
from steward_datos.reglas.catalogo import catalogo

RAIZ = CARPETA_POLITICAS.parent


@pytest.mark.parametrize("ruta", sorted(CARPETA_POLITICAS.glob("*.md")), ids=lambda p: p.name)
def test_politicas_se_fragmentan(ruta):
    meta, cuerpo = leer_politica(ruta.read_text(encoding="utf-8"))
    frags = fragmentar(meta, cuerpo)
    assert frags and all(f.texto.startswith(f"{meta.id} v{meta.version}") for f in frags)
    assert all(len(f.texto.split()) < 320 for f in frags)


def test_cada_regla_del_catalogo_aparece_en_su_politica():
    textos = {}
    for ruta in CARPETA_POLITICAS.glob("*.md"):
        meta, cuerpo = leer_politica(ruta.read_text(encoding="utf-8"))
        textos[(meta.id, meta.version)] = cuerpo
    for r in catalogo().reglas.values():
        cuerpo = textos[(r.politica_id, r.politica_version)]
        assert f"{r.id} v{r.version}" in cuerpo, f"{r.id} v{r.version} no aparece en {r.politica_id} v{r.politica_version}"


def test_metadatos_obligatorios():
    with pytest.raises(ValueError):
        leer_politica("# sin metadatos")
    with pytest.raises(ValueError):
        leer_politica("---\nid: P-9\n---\ncuerpo")


def test_convertidor_fatura(tmp_path):
    """Simula la estructura de FATURA con dos formas de anotación y verifica selección y conversión."""
    from PIL import Image
    img_dir, ann_dir = tmp_path / "invoices_dataset_final" / "images", tmp_path / "invoices_dataset_final" / "Annotations" / "Original_Format"
    img_dir.mkdir(parents=True)
    ann_dir.mkdir(parents=True)
    for t in (1, 2):
        for i in range(3):
            nombre = f"Template{t}_Instance{i}"
            Image.new("RGB", (10, 10), "white").save(img_dir / f"{nombre}.jpg")
            ann = {"TOTAL": {"text": "$ 422,55", "bbox": [[1, 2, 3, 4]]}, "DATE": {"text": "06/11/2014", "bbox": [[1, 1, 2, 2]]},
                   "SELLER NAME": {"text": "Henry Inc", "bbox": [[0, 0, 5, 1]]}} if t == 1 else \
                  [{"label": "SUB-TOTAL", "text": "384,14", "bbox": [1, 1, 2, 2]}, {"label": "NUMBER", "text": "71177260", "bbox": [0, 0, 1, 1]}]
            (ann_dir / f"{nombre}.json").write_text(json.dumps(ann))
    salida = tmp_path / "piloto"
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "fatura_piloto.py"), "seleccionar", "--fatura", str(tmp_path),
                    "--por-plantilla", "2", "--salida", str(salida)], check=True)
    convertidas = sorted(salida.glob("*.json"))
    assert len(convertidas) == 4
    datos = [json.loads(p.read_text()) for p in convertidas]
    t1 = next(d for d in datos if d["plantilla"] == "Template1")
    assert t1["verdad"]["campos"] == {"total": "$ 422,55", "fecha": "06/11/2014", "emisor_nombre": "Henry Inc"}
    t2 = next(d for d in datos if d["plantilla"] == "Template2")
    assert t2["verdad"]["campos"] == {"subtotal": "384,14", "folio": "71177260"}
