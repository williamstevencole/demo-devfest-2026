# Comisiones y tarifas

Versión: 2026-11-17

## Comisiones y retiro

### Comisión de acciones y ETFs

Comprar y vender acciones o ETFs tiene una comisión de `$0`. La app no cobra
comisión por operar en el mercado secundario. Los impuestos aplicables, si los
hubiera, se informan por separado.

La app trabaja con instrumentos en dólares. Los costos de convertir otra moneda
a dólares para comprar no están cubiertos por este documento; la app muestra
los costos aplicables antes de confirmar.

### Spread cambiario

Cuando el retiro se convierte de dólares a otra moneda, se aplica un spread
cambiario de `0.75%` sobre el monto solicitado. El spread cubre el costo de la
conversión y se muestra antes de confirmar el retiro. No se cobra dos veces
por la misma operación.

### Retiro y plazos

El dinero disponible en efectivo se usa primero. Si el efectivo no alcanza, la
diferencia se cubre vendiendo posiciones; esa venta liquida en T+1. El retiro
completo suele tardar de 2 a 3 días hábiles después de la liquidación.

### Ejemplo de costo de retiro

Si el retiro es de `$2,500` y se convierte a otra moneda, el spread de `0.75%`
es `$18.75`. La comisión de trading es `$0`; el total de costos es `$18.75`.
El efectivo disponible se usa primero; si no alcanza, la diferencia se cubre
vendiendo posiciones.

La demo opera con montos en dólares. Para otra moneda se necesita el tipo de
cambio, que la app muestra antes de confirmar; el corpus no fija una tasa.

### Cómo se muestra el costo total

Antes de confirmar un retiro, la app muestra el efectivo usado, el monto que
debe venderse, la comisión de trading, el spread cambiario y el total de
costos. Las cifras se calculan con código determinista y se redondean a dos
decimales.

## Custodia

La app no cobra comisión de custodia por mantener acciones o ETFs en la cuenta.
Los costos de mantenimiento de la cuenta se publican en la sección de tarifas
vigentes y no se descuentan sin aviso.
