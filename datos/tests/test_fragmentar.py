from steward_datos.rag.fragmentar import leer_politica


def test_mismo_hash_con_saltos_lf_y_crlf():
    texto_lf = (
        "---\n"
        "id: P-TEST\n"
        "nombre: Politica de prueba\n"
        'version: "1.0"\n'
        "vigente_desde: 2026-01-01\n"
        "---\n"
        "## Seccion\n"
        "Contenido de prueba.\n"
    )

    texto_crlf = texto_lf.replace("\n", "\r\n")

    meta_lf, _ = leer_politica(texto_lf)
    meta_crlf, _ = leer_politica(texto_crlf)

    assert meta_lf.sha256 == meta_crlf.sha256
