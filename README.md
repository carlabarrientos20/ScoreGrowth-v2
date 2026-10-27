# Score Growth v2

Proyecto de Práctica v2.

**Score de salud** (0 a 100) para los sellers Mid-Market del marketplace de Paris.cl. A partir del score el pipeline:

1. segmenta a los sellers (Alto, Medio - Alto, Medio, Bajo),
2. detecta sus **variables débiles** (banderas),
3. sugiere una **acción comercial** (accionable + palanca), y
4. arma las listas de **tratamiento** (Regalo SP y Personalizado BD).

Un mismo seller puede tener **dos scores**: uno en su negocio **duro** y otro en su negocio **blando**, según las divisiones en las que venda. La unidad de análisis es `seller_id` + `division_db`, y cada seller se compara solo contra los sellers de su misma dureza.

---

## Cómo correrlo

1. Conectarse a la **VPN de Cencosud**.
2. Tener un archivo `.env` en la carpeta del proyecto (no se sube al repo):
   ```
   REDSHIFT_HOST=...
   REDSHIFT_PORT=5439
   REDSHIFT_DB=...
   REDSHIFT_USER=...
   REDSHIFT_PASSWORD=...
   PG_HOST=...
   PG_PORT=5432
   PG_DB=...
   PG_USER=...
   PG_PASSWORD=...
   ```
3. Instalar dependencias: `pip install pandas openpyxl redshift_connector psycopg2-binary python-dotenv` (`Analisis.py` y `Correlacion.py` además usan `matplotlib` y `seaborn`).
4. Desde la carpeta del proyecto:
   ```
   python main.py
   ```
5. **Cerrar `score_growth.xlsx` antes de correr.** Si está abierto en Excel, Windows no deja sobrescribirlo y el pipeline falla al final.

**Salidas**
- `score_growth.xlsx`
  - *Score Growth*: tabla completa con todas las variables, score y segmento.
  - *Resumen*: segmento, banderas, accionable y palanca de cada seller-dureza.
  - *Regalo SP* y *Personalizado BD*: listas de tratamiento.
- `score_largo.csv`: tabla completa, incluidas las banderas.

**Probar una variable por separado:** `python -m Variables.Recurrencia_venta` (o `Variables.CVR`, `Variables.Carga_SKU`, etc.). Cada módulo imprime un resumen de lo que trae.

**Cortes de conexión:** si se corta la VPN, el Wi-Fi o el DNS, `db.py` reintenta cada query hasta 3 veces (espera 10 s y luego 30 s). Los errores de SQL no se reintentan.

---

## Cómo funciona

```
Variables/*.py  ──►  main.py (une todo)  ──►  Scoring.py  ──►  Perfil.py  ──►  Excel
 una query por         merge por               score          segmento,        + Tratamiento.py
 variable              seller + dureza         ponderado      banderas,          (Regalo SP,
                                                              acción             Personalizado BD)
```

1. Cada módulo de `Variables/` corre una query y devuelve una tabla por `seller_id` (+ `division_db` cuando aplica).
2. `main.py` une venta, CVR y recurrencia (outer join) y después agrega catálogo, inversión, estado y reputación (left join).
3. `Scoring.py` calcula el score ponderado.
4. `Perfil.py` asigna segmento, banderas, accionable y palanca, y escribe la hoja *Resumen*.
5. `Tratamiento.py` filtra y escribe las hojas *Regalo SP* y *Personalizado BD*.

---

## Población y horizonte

| Parámetro | Valor | Dónde se cambia |
|---|---|---|
| Tier | Mid-Market (`cluster_seller.tier`) | En cada query |
| Publicado | `publish = 1` | En cada query |
| Onboarding | Creado hace más de **90 días** | `DIAS_ONBOARDING` en `config.py` |
| Horizonte | Últimos **90 días**, sin contar hoy | `HORIZONTE_DIARIO` en `config.py` |
| Tramos | El horizonte se divide siempre en **3 tramos iguales** (con 90 días, de 30 días cada uno) | `TRAMOS_TOTALES` en `config.py` |

- **Solo entran sellers con al menos una venta en el horizonte.** Venta, CVR y recurrencia se calculan desde las transacciones, así que un seller sin ventas no aparece. Es una decisión de diseño: el score mide la salud de sellers activos o recién apagados, no de los que ya se fueron.
- **Tramos:** el horizonte se parte en 3 tramos iguales, contados hacia atrás desde ayer. Con 90 días, el tramo 0 son los últimos 30 días, el tramo 1 los días 31 a 60 y el tramo 2 los días 61 a 90. Con 30 días serían 3 tramos de 10 días, y con 180 días, 3 de 60. Si el horizonte no es divisible por 3, los tramos más recientes quedan con un día más. Así las reglas "2 de 3" y "3 de 3" funcionan con cualquier horizonte.

---

## Variables del score

| Variable | Peso | Valor que entra al score (0-100) | Variable débil si | Módulo |
|---|---|---|---|---|
| Venta | 30% | `venta_percentil` | < P40 | `Variables/Venta_percentil.py` |
| SKU con stock | 20% | `percentil_stock` | < P60 | `Variables/Carga_SKU.py` |
| Volumen SKU | 10% | `percentil_volumen_stock` | < P60 | `Variables/Carga_SKU.py` |
| Frecuencia de venta | 15% | `percentil_recurrencia` (Primera venta = 50) | Vendió en menos de 2 de 3 tramos | `Variables/Recurrencia_venta.py` |
| CVR | 15% | `percentil_cvr` (sin visitas = 50) | < P40 | `Variables/CVR.py` |
| Inversión SP | 10% | 100 si invirtió, 0 si no | No invirtió | `Variables/Inversion.py` |

Los percentiles se calculan con `PERCENT_RANK` **dentro de cada dureza**, redondeados a entero. Si a un seller le falta venta, stock o volumen, ese componente aporta 0.

---

## Detalle de cada variable

### 1. Venta (`Variables/Venta_percentil.py`)

- **Fuente:** `cencosud_chile_txd_reporter.vm_new_report_transaccion_mkp`
- **Cálculo:** suma de `precio_venta` por seller y dureza en el horizonte. La dureza sale de la división de cada transacción. `venta_percentil` es el percentil de esa suma dentro de la dureza.
- **Se usa en:** score (30%) y bandera `flag_venta_baja` (percentil < 40).
- **Columnas:** `venta`, `venta_percentil`.
- **Limitaciones:**
  - No filtra por estado de la orden. Si la vista incluye órdenes anuladas o devueltas, se suman igual.
  - Es un percentil: mide la posición del seller frente a sus pares, no el monto absoluto. Si todos venden menos, el percentil de un seller puede no cambiar.

### 2. SKU con stock y 3. Volumen SKU (`Variables/Carga_SKU.py`)

- **Fuente:** `cencosud_chile_txd_reporter.rpt_catalogo_cencopim_product_replicas`
- **Cálculo:**
  - `sku_creados`: SKUs distintos del seller en esa dureza, en cualquier estado.
  - `sku_stock`: SKUs con `stock > 0` y `approval_status = 'approved'`.
  - `pct_con_stock`: `sku_stock / sku_creados` (texto con %).
  - `percentil_stock`: percentil de `pct_con_stock` → **disponibilidad**.
  - `percentil_volumen_stock`: percentil de `sku_stock` → **tamaño** del catálogo disponible.
- **Se usa en:** score (20% disponibilidad, 10% volumen), banderas `flag_stock_bajo` y `flag_catalogo_bajo` (percentil < 60), y tratamientos (`sku_creados >= 5`).
- **Limitaciones:**
  - Es una **foto del día en que se corre**, no un promedio del horizonte. Un seller que quebró stock ayer aparece sin stock aunque haya tenido stock 89 de los 90 días.
  - `sku_creados` incluye SKUs rechazados o pendientes, lo que baja el % con stock de sellers con mucho catálogo rechazado.
  - La disponibilidad se separa del volumen para que un seller con 2 SKUs al 100% no quede igual que uno con 500 al 100%.

### 4. Frecuencia de venta (`Variables/Recurrencia_venta.py`)

- **Fuente:** `cencosud_chile_txd_reporter.vm_new_report_transaccion_mkp`
- **Cálculo:**
  - `dias_vendidos`: días distintos con al menos una venta en el horizonte.
  - `recurrencia`: `dias_vendidos / dias del horizonte` (0 a 1). Es informativa y **no entra al score**.
  - `percentil_recurrencia`: percentil de `dias_vendidos` dentro de la dureza. **Esto es lo que entra al score.**
  - `tramos_con_venta`: en cuántos de los 3 tramos del horizonte vendió al menos una vez (0 a 3). **No entra al score.**
- **Se usa en:**
  - Score (15%) con `percentil_recurrencia`. Los sellers en estado **Primera venta** reciben 50 (neutro) porque no tienen historia para medir frecuencia.
  - Bandera `flag_intermitente`: `tramos_con_venta` < 2 (`UMBRAL_TRAMOS` en `Perfil.py`).
  - Tratamientos: Regla A pide ≥ 2 tramos y Regla B los 3 tramos.
- **Por qué hay dos medidas de frecuencia:** miden cosas distintas. Los días miden **cuánto** vende el seller; los tramos miden si vende de forma **constante** o concentrada. Dos sellers con 20 días de venta tienen el mismo percentil, pero si uno vendió los 20 días en el último mes (1 tramo) y el otro ~7 días cada mes (3 tramos), comercialmente son distintos. El score usa los días porque necesita muchos valores para ordenar sellers (los tramos solo van de 1 a 3 y casi todos los activos tendrían 3). Las banderas y los tratamientos usan los tramos porque son reglas de sí/no fáciles de explicar ("vendió en al menos 2 de 3 periodos"). Usar las dos en el score contaría la frecuencia dos veces.
- **Limitaciones:**
  - Muchos sellers venden pocos días, y `PERCENT_RANK` les da el mismo percentil a los empates. Todos los que vendieron 1 solo día comparten el percentil más bajo de su dureza.
  - Los tramos son bloques móviles (tercios del horizonte), no meses calendario. No calzan exactamente con el estado del seller, que sí usa meses calendario.
  - Con horizontes muy cortos los tramos quedan de pocos días (con 7 días, de 2 a 3 días cada uno) y medir constancia pierde sentido. Se recomienda un horizonte de al menos 30 días.
  - Los sellers en Primera venta casi siempre quedan con la bandera de frecuencia activa, porque tienen poca historia.

### 5. CVR (`Variables/CVR.py`)

- **Fuentes:** transacciones de `vm_new_report_transaccion_mkp` y visitas (`pdp_views`) de `source_bi_paristxd_product.product_data_daily`, cruzadas con el catálogo de réplicas para saber de qué seller y división es cada producto.
- **Cálculo:** `transacciones / visitas` sumando todo el seller (no se promedian CVR por producto). `percentil_cvr` es el percentil dentro de la dureza. `cvr_seller` es texto con %.
- **Se usa en:** score (15%), bandera `flag_cvr_bajo` (percentil < 40) y Regla B de Regalo SP (`percentil_cvr >= 60`).
- **Limitaciones:**
  - Los sellers **sin visitas** quedan fuera del cálculo para no recibir un percentil falso. En el score reciben 50 (neutro) y no se les marca la bandera de CVR.
  - Las transacciones se cuentan con `COUNT(oc)`, que cuenta filas. Si la vista tiene una fila por producto, una orden con varios productos suma varias transacciones.
  - Las visitas de productos que no están en el catálogo de réplicas se pierden, porque no se sabe de qué seller son.
  - La división de las visitas sale del catálogo actual. Si un producto cambió de división, sus visitas históricas quedan en la división nueva.

### 6. Inversión en Sponsored Products (`Variables/Inversion.py`)

- **Fuente:** Postgres `eiffel-ledger` (`invoice` + `invoice_detail` con `type = 'campaignCharge'`). Los sellers válidos salen de Redshift y el cruce se hace en Python.
- **Cálculo:** `invirtio` = si/no según si tiene cargos de campaña en el horizonte. `total_invertido` = suma de esos cargos.
- **Se usa en:** score (10%, binario) y bandera `flag_sin_inversion`.
- **Limitaciones:**
  - Es binaria: cualquier monto cuenta como 100, sea $1.000 o $1.000.000.
  - Usa la fecha de la factura, no la fecha en que corrió la campaña.
  - Se calcula por seller, no por dureza: un seller mixto tiene el mismo valor en sus dos filas.
  - Muy pocos sellers invierten (85 de 2.814 filas el 27-10-2026), así que la bandera aparece en casi todos y discrimina poco.

### Contexto: Estado del seller (`Variables/Estado.py`)

No entra al score. Clasifica a cada seller según el **último mes calendario cerrado**:

| Estado | Definición |
|---|---|
| Primera venta | Su primera venta histórica fue en el último mes cerrado |
| Activo | Vendió el último mes cerrado y también el anterior |
| Reactivado | Vendió el último mes cerrado, pero no el anterior |
| Dormant | No vendió el último mes cerrado; última venta hace 1-2 meses |
| Fugado | Última venta hace 3-6 meses |
| Out <12 / Out >12 | Última venta hace 6-12 / más de 12 meses |
| Sin venta / Ghost | Nunca vendió (con SKUs / sin SKUs) |

- **Se usa en:** frecuencia neutra para Primera venta (score), Regla A (Dormant), Regla B y Personalizado BD (Activo).
- **Limitaciones:**
  - Usa meses calendario mientras el resto usa días móviles. Un seller "Dormant" puede tener ventas en el mes en curso.
  - Un seller que vende por primera vez en el mes en curso queda como **Dormant**, no como Primera venta.
  - Fugado, Out, Sin venta y Ghost nunca aparecen en la salida porque esos sellers no tienen ventas en los últimos 90 días.

### Contexto: Reputación (`Variables/Reputacion.py`)

- **Fuente:** `cencosud_chile_txd_reporter.reputation_seller_kpis_mkp` (`categoria_reputacion`: Destacado, Bueno, Medio, Bajo, Plan Growth).
- **Se usa en:** solo en los tratamientos.
- **Limitaciones:** la query no filtra por fecha y asume una fila por seller (el 27-10-2026 no hubo duplicados). Si la tabla empieza a guardar historia, el merge duplicaría filas.

### No se usa: Rentabilidad (`Variables/Rentabilidad.py`)

Lee un Google Sheet con venta facturada y margen por seller. **No está conectada al pipeline.** Si se quiere usar, hay que adaptarla: el horizonte sigue fijo en 3 meses calendario y el onboarding está escrito como 90 días en vez de usar `config.py`.

---

## Segmentos (`Perfil.py`)

| Segmento | Score |
|---|---|
| Alto | ≥ 68 |
| Medio - Alto | 46 a 68 |
| Medio | 32 a 46 |
| Bajo | < 32 |

Los cortes se **recalibraron el 27-10-2026**, cuando la frecuencia pasó a ser percentil. Los cortes anteriores (70 / 53 / 37) dejaban cerca de 11% Alto, 40% Medio - Alto, 28% Medio y 21% Bajo con la versión mensual. Los nuevos mantienen esas proporciones con el score nuevo.

**Si cambian los pesos o las variables, hay que recalibrar los cortes.**

---

## Banderas y acción comercial (`Perfil.py`)

Cada variable débil activa una bandera. Si un seller tiene varias, la acción sale de la de **mayor prioridad**:

| Prioridad | Bandera | Accionable (por qué contactar) | Palanca (cómo) |
|---|---|---|---|
| 1 | `flag_stock_bajo` | Cargar stock (60% productos con stock) | Comunicación masiva |
| 2 | `flag_catalogo_bajo` | Arreglar catálogo | Comunicación masiva |
| 3 | `flag_intermitente` | Aumentar frecuencia de venta | Dscto comercial + Comunicación masiva |
| 4 | `flag_venta_baja` | Aumentar ventas (precio competitivo) | Dscto comercial + Comunicación masiva |
| 5 | `flag_cvr_bajo` | Mejorar conversión | SP + Comunicación masiva + Dscto comercial |
| 6 | `flag_sin_inversion` | Activar inversión en SP | SP + Comunicación masiva |

La hoja *Resumen* muestra todas las banderas activas (`flags`), cuántas son (`n_banderas`) y la acción de la prioritaria.

---

## Tratamientos (`Tratamiento.py`)

**Regalo SP:** cumple la Regla A o la Regla B (columna `regla_sp`).

| | Regla A - Dormant | Regla B - Activo |
|---|---|---|
| Segmento | Medio - Alto o Medio | Alto o Medio - Alto |
| Estado | Dormant | Activo |
| Tramos con venta | ≥ 2 de 3 | 3 de 3 |
| Percentil CVR | — | ≥ 60 |
| SKUs creados | ≥ 5 | ≥ 5 |
| Reputación | Medio, Bueno, Destacado o Plan Growth | Medio, Bueno, Destacado o Plan Growth |

**Personalizado BD:** segmento Alto, estado Activo y reputación Bueno, Destacado o Plan Growth.

Los parámetros están al inicio de `Tratamiento.py`.

---

## Limitaciones generales

1. **Solo sellers con venta en el horizonte.** Los sellers sin ventas en el horizonte (90 días por defecto) no tienen score.
2. **El score es relativo.** Todo son percentiles dentro de la dureza, así que el score mide la posición frente a los pares. Un mismo score en dos fechas distintas no significa el mismo desempeño absoluto.
3. **El grupo `otros` es muy chico** (12 filas el 27-10-2026). Sus percentiles se calculan igual, pero son poco confiables.
4. **Mezcla de cortes temporales:** venta, CVR, frecuencia e inversión usan el horizonte en días; el estado usa meses calendario; catálogo y reputación son una foto del día.
5. **Valores faltantes:** si falta venta, stock o volumen, ese componente aporta 0. CVR sin visitas y Primera venta reciben 50.
6. **Cortes de segmento fijos.** Se calibraron una vez con la data del 27-10-2026 y un horizonte de 90 días. No se ajustan solos. Con otro horizonte los percentiles siguen en la misma escala, pero algunas variables cambian de reparto (por ejemplo, en 30 días invierten menos sellers que en 90), así que conviene revisar cuántos sellers quedan en cada segmento.
7. **Sin pruebas automáticas contra Redshift.** Antes de usar una salida para una acción comercial, conviene revisar los conteos que imprime la consola.

---

## Configuración (`config.py`)

| Constante | Valor | Para qué |
|---|---|---|
| `DUROS` / `BLANDOS` | Listas de divisiones | Clasificación de dureza |
| `DIAS_ONBOARDING` | 90 | Antigüedad mínima del seller |
| `HORIZONTE_DIARIO` | 90 | Días del horizonte |
| `TRAMOS_TOTALES` | 3 | En cuántos tramos iguales se divide el horizonte (si se cambia, hay que revisar `UMBRAL_TRAMOS` en `Perfil.py` y `TRAMOS_MIN_*` en `Tratamiento.py`) |
| `HORIZONTE_MESES` | 3 | Ya no se usa |

Los pesos están en `Scoring.py`. Los cortes de segmento y los umbrales de las banderas están en `Perfil.py`. Los criterios de tratamiento están en `Tratamiento.py`.

### Clasificación de divisiones

- **Duros:** DECO-HOGAR, TECNOLOGIA, ELECTRO-HOGAR, NUEVOS NEGOCIOS
- **Blandos:** ACCESORIOS, DEPORTES, HOMBRES, MUJER, CALZADO, INFANTIL
- Las demás divisiones quedan como `otros`.

---

## Estructura

```
config.py            Divisiones, onboarding, horizonte y tramos
db.py                Conexión a Redshift y Postgres, con reintentos
main.py              Orquesta: une variables, calcula score, perfila y exporta
Scoring.py           Pesos y cálculo del score
Perfil.py            Segmentos, banderas, accionable y palanca + hoja Resumen
Tratamiento.py       Hojas Regalo SP y Personalizado BD
export_excel.py      Hoja Score Growth con formato
Variables/           Una query por variable
Analisis.py          Exploración de la distribución del score (gráficos)
Correlacion.py       Correlación entre variables del score (heatmap)
```

---

## Cambios respecto al repo anterior (ScoreGrowth, 21-10-2026)

El repo anterior ya había pasado de 3 meses calendario a días móviles. La v2 corrige lo que ese cambio dejó descalibrado:

| Tema | Antes | v2 |
|---|---|---|
| Frecuencia en el score | Días con venta / 90 (la mediana quedó en 0,10 y bajó todos los scores) | Percentil de días con venta dentro de la dureza |
| Frecuencia de Primera venta | 100 (quedaban sobre los Activos) | 50 (neutro) |
| Bandera de frecuencia | `dias_vendidos < 1` (nunca se activaba) | Vendió en menos de 2 de los 3 tramos del horizonte |
| Bandera de venta | P60 | P40 |
| Reglas de Regalo SP | ≥ 60 y ≥ 90 días con venta (casi nadie calificaba) | ≥ 2 y 3 de los 3 tramos del horizonte con venta |
| Tramos | — | Siempre 3 tramos iguales, sirve para cualquier horizonte |
| CVR | Ventana de 91 días; sin visitas = 0 | Ventana de 90 días; sin visitas = 50 (neutro) |
| Cortes de segmento | 70 / 53 / 37 | 68 / 46 / 32 |
| Conexión | Sin reintentos | Hasta 3 reintentos ante cortes de red |

---

## Stack

- **Lenguaje:** Python (pandas, openpyxl)
- **Bases de datos:** Amazon Redshift (`redshift_connector`) y Postgres eiffel-ledger (`psycopg2`)
- **Credenciales:** archivo `.env` con `python-dotenv`
