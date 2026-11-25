# S3-38: lectura de CFDI 4.0 sin modelo visual

Rama `agentes/xml-cfdi-carlos-delgado`, basada en dev `ab2924c` con la integración
Qwen ya fusionada. PNG/JPEG/PDF conservan la vía visual. Un archivo con extensión
.xml (sin distinguir mayúsculas) pasa por defusedxml 0.7.1; no llama al modelo,
no obtiene texto de un PDF, ni modifica los importes que no cuadran.

## Qué se extrae

El resultado sigue siendo FacturaExtraida. Se añaden dos propiedades compatibles:
`origen_extraccion`, con valor por defecto `vision` y valor `xml_cfdi` para XML,
y `uuid_fiscal`, opcional. El UUID no sustituye a Folio ni se concatena con Serie.
Se conserva en Factura.salida_cruda y se devuelve en el detalle, sin migración SQL.
No se solicitan estas propiedades al modelo visual y se ignora una declaración
suya de origen XML o UUID.

| Campo | Atributo o nodo de origen |
| --- | --- |
| folio, fecha, moneda, subtotal, total | Comprobante/@Folio, @Fecha, @Moneda, @SubTotal, @Total |
| condiciones_pago | Comprobante/@CondicionesDePago |
| emisor_nombre, emisor_rfc | Emisor/@Nombre y @Rfc |
| receptor_nombre, receptor_rfc | Receptor/@Nombre y @Rfc |
| emisor_direccion | null: no se inventa una dirección a partir de LugarExpedicion |
| impuestos | Impuestos/@TotalImpuestosTrasladados, solo el total explícito global |
| retenciones | Impuestos/@TotalImpuestosRetenidos; null si no existe |
| tasa_iva | TasaOCuota de los traslados globales con Impuesto=002 y TipoFactor=Tasa, solo si hay una tasa única |
| conceptos | Concepto/@Descripcion, @Cantidad, @ValorUnitario, @Importe, en orden |
| uuid_fiscal | Complemento/TimbreFiscalDigital/@UUID, namespace oficial del timbre |

El tipo I se identifica como factura; E como nota_credito. Otros tipos (pagos,
nómina, traslado) se rechazan en esta vía. No se completan atributos ausentes,
no se suman impuestos por partida al total global ni se calcula un folio faltante.
Los datos monetarios, tasas y cantidades usan punto decimal, hasta 18 cifras
enteras y seis decimales; los formatos ambiguos se rechazan en lugar de repararse.

El namespace se identifica por URI, no por el prefijo elegido. Se admite XML
UTF-8/UTF-16 conforme a su declaración. DTD, entidades y referencias externas
están prohibidos; no se descargan XSD ni se ejecuta XInclude. Límite de 15 MiB,
64 niveles y 20000 nodos. Se rechazan nodos únicos repetidos y UUID con formato
incorrecto. XML incompleto o inseguro devuelve HTTP 422 y el caso queda en error,
sin resultado de extracción fabricado.

## Reglas, evidencia y revisión

Se usan las reglas existentes. R-003 (confianza de visión) no se evalúa para
atributos XML: confianza, bbox y página quedan null, paginas=0 y modelo=null.
Las evidencias de las reglas apuntan al atributo XML, sin fingir una página.
La API y el piloto por defecto conservan la revisión humana obligatoria; una
sugerencia aceptado del motor no cierra el caso. El original sigue en S3 y su
hash sigue calculándose sobre sus bytes.

La interfaz admite .xml, muestra UUID y procedencia, y ofrece descargar el
original en lugar de intentar mostrarlo como imagen. El XML no se inserta como
HTML en la página. Los avisos y conceptos se guardan igual que en la vía visual.

No se valida XSD, cadena original, certificado, sellos o estatus SAT. Un namespace,
UUID o aritmética correctos no acreditan autenticidad fiscal. Un XML sin UUID se
conserva con advertencia explícita, sin presentarlo como timbrado verificado.
Descuentos, IEPS, impuestos locales, tasas múltiples y complementos requieren
revisión: el contrato actual no modela todas sus particularidades. No se añaden
reglas fiscales nuevas ni se promete cobertura completa de cualquier CFDI.

La extracción XML no requiere Ollama. El grafo completo aún puede usar embeddings
para buscar políticas: ese servicio es independiente de la lectura XML.

## Archivos sintéticos y comprobación rápida en Windows

`db/semillas/sinteticos/facturas/cfdi/` contiene tres documentos de prueba sin
sellos válidos: correcto en aritmética, total incorrecto y RFC de emisor ausente.
Son ejemplos estructurales para el parser, no comprobantes fiscalmente válidos.
No se insertan solos en la base ni se agregan al corpus histórico de 39 pilotos.

Desde la nueva copia de trabajo XML, reutilizar la venv principal:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location).Path "datos"
& "..\Banamex_Monorepo\.venv\Scripts\python.exe" -m pip install defusedxml==0.7.1
& "..\Banamex_Monorepo\.venv\Scripts\python.exe" -B -m unittest discover -s backend/grafo_casos/tests -p test_cfdi_xml.py -v
```

Esta comprobación no toca los servicios Docker ni requiere base de datos u
Ollama. Para probar HTTP real, reconstruir el backend con esta rama en el entorno
de pruebas cuando no interrumpa la grabación. Debe instalarse la dependencia
nueva también en la imagen. No ejecutar down -v ni recargar semillas. Subir el
XML como application/xml usando la URL prefirmada y decidir explícitamente.

## Validación y fuentes

Pruebas de parser, grafo y reglas reales: campos y UUID, datos ausentes, total
incorrecto, nota de crédito, UTF-8/UTF-16, namespace por defecto, nodos repetidos,
DTD/XXE, límites, Addenda e importes ambiguos. Las pruebas HTTP ejercitan el
parser y grafo reales con S3/sesiones controlados, firma de URL, autenticación,
propiedad del caso y decisión explícita; no son una ejecución real de PostgreSQL.
Se comprueba la serialización del UUID en salida_cruda y su devolución en detalle.
Las regresiones de PDF e imágenes siguen cubiertas en la suite.

Evidencia reproducida localmente sin S3 ni base: `docs/evidencias/xml-cfdi/2026-11-24/`.
La prueba de navegador y de API con almacenamiento real quedan pendientes en Windows.

Referencias técnicas consultadas:
- Esquema oficial: https://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd
- Protección del parser: https://github.com/tiran/defusedxml

Consultar el esquema para el mapeo no equivale a validar cada archivo contra él.

Resultado de la suite en esta rama: 393 pruebas aprobadas, 80 omitidas y 97
subpruebas aprobadas. Ruff sin errores y compilación Vite aprobada. Las omisiones
requieren principalmente PostgreSQL de pruebas; no se presentan como aprobadas.
