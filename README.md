# Score Growth

Cálculo de un **score de salud** para cada seller del marketplace (Paris.cl), pensado para monitorear el desempeño del seller en un horizonte de corto plazo (2 a 3 meses).

Un mismo seller puede tener **dos scores separados**: uno en su negocio **duro** y otro en su negocio **blando**, según las divisiones en las que venda. La unidad de análisis es por lo tanto `seller_id` + `dureza`.

---

## Variables del score

| # | Variable | Estado | Detalle |
|---|----------|--------|---------|
| 1 | **Venta** | Activa | Promedio por equipo (duros/blandos) **o** percentil — |
| 2 | **Conversión (CVR)** | Activa | Promedio por equipo (duros/blandos) **o** percentil |
| 3 | **Productos visibles vs creados** | Por definir | Se evalúa más adelante |
| 4 | **Rentabilidad para marketplace** | Activa | Sí / No. Viene de un Google Sheet |
| 5 | **Inversión (sponsored products)** |  Por definir | Se evalúa más adelante |
| 6 | **Ticket promedio** | Por definir | Se evalúa más adelante|

---

## Horizonte temporal

- **3 meses cerrados**, tomando como referencia que estamos en la primera semana de cada mes.
  - Ejemplo: en **agosto** se consideran **julio, junio y mayo**.
- Solo se incluyen sellers que ya pasaron su proceso de **onboarding**: más de **90 días desde su creación**.

---

## Clasificación de divisiones

**Duros**
- DECO-HOGAR
- TECNOLOGIA
- ELECTRO-HOGAR
- NUEVOS NEGOCIOS *(cuando no hay categoría)*

**Blandos**
- ACCESORIOS
- DEPORTES
- HOMBRES
- MUJER
- CALZADO
- INFANTIL

Un seller que vende en divisiones duras y blandas genera dos filas (una por dureza) y se compara contra los pares de cada grupo por separado.

---

## Stack

- **Lenguaje:** Python
- **Base de datos:** Amazon Redshift (`redshift_connector`)
- **Credenciales:** archivo `.env` con `python-dotenv`


---