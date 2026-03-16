# Advanced Credit Limit Management (credit_limit_custom)

## Resumen
Gestiona y controla de manera avanzada los límites de crédito de tus clientes, integrando validaciones automáticas, flujos de aprobación de cuentas y seguimientos de pagos con cheques para proteger los ingresos de tu empresa.

## ¿Para qué sirve? (Propósito)
Este módulo resuelve el problema común de las ventas a crédito sin control estricto. Evita que los equipos comerciales vendan a clientes que tienen deudas atrasadas o que ya han superado su límite de crédito permitido. Al automatizar estos bloqueos y establecer un flujo de aprobación formal para la apertura de cuentas corrientes, la empresa minimiza el riesgo de incobrables y mejora la salud de su flujo de caja, manteniendo la agilidad en las ventas seguras.

## Funcionalidades Clave
* **Flujo de Aprobación de Cuentas:** Proceso estructurado (Solicitud -> Análisis -> Aprobación) para otorgar o modificar límites de crédito, con roles de seguridad bien definidos.
* **Delegación Dinámica de Aprobación:** El Aprobador puede habilitar o revocar desde Contabilidad > Ajustes la capacidad del Analista de Riesgo para aprobar o rechazar solicitudes de crédito.
* **Validación Estricta en Ventas:** Bloqueo automático de Órdenes de Venta si el cliente supera su límite de crédito disponible o tiene la cuenta bloqueada manualmente.
* **Gestión de Cheques:** Integración nativa con cheques (`l10n_latam_check`) para considerar el monto de cheques pendientes de cobro como parte del riesgo crediticio utilizado.
* **Panel de Información en Ventas:** Visualización en tiempo real del límite total, crédito utilizado y crédito disponible directamente al crear una Orden de Venta.
* **Control de Descuentos:** Restricciones en los porcentajes máximos de descuento por cliente, requiriendo autorización gerencial si se exceden.

## Configuración Post-Instalación
Una vez instalado el módulo, un administrador del sistema debe realizar los siguientes ajustes iniciales:

1. **Asignación de Roles de Seguridad:** Ve a *Ajustes > Usuarios y Compañías > Usuarios*. Asigna a tu equipo los nuevos permisos bajo la categoría "Credit and Discount Management":
   * **Credit Limit Applicant (Solicitante):** Puede pedir la apertura de una cuenta o el aumento de un límite. Típicamente asignado a Ejecutivos de Ventas.
   * **Credit Risk Analyst (Analista de Riesgo):** Analiza la documentación financiera, bloquea/desbloquea cuentas por falta de pago y valida las solicitudes. Típicamente Cuentas por Cobrar.
   * **Credit Limit Approver (Aprobador):** Tiene la decisión final para aprobar y habilitar el límite de crédito en el sistema. Típicamente Gerencia de Finanzas.
2. **Plazos de Pago Exentos:** Revisa tus "Plazos de Pago" en la aplicación de Contabilidad. Si tienes un plazo de pago de "Contado" o "Efectivo" que no debería validar el límite de crédito, marca su configuración para que se excluya de este control.
3. **Delegación de Aprobación al Analista (opcional):** Si deseas que el Analista de Riesgo también pueda aprobar o rechazar solicitudes (por ejemplo, cuando el Aprobador esté ausente), ve a *Contabilidad > Ajustes > Credit Workflow* y activa la opción **"Analyst Approval Delegation"**. Este permiso puede activarse y desactivarse en cualquier momento por el Aprobador.

## Guía de Uso (Paso a Paso)
El flujo diario para abrir una cuenta corriente y vender a crédito es muy orgánico dentro de Odoo:

**Paso 1: Solicitud de Crédito (Rol: Solicitante / Ventas)**
1. Ve a la aplicación de **Contactos** y abre la ficha de un cliente que desea comprar a crédito.
2. Haz clic en el botón verde **"Abrir Cuenta Cte"**.
3. Se abrirá una ventana donde podrás ingresar el *Límite Solicitado* y hacer un pedido formal.
4. Confirma la solicitud. El estado del crédito del cliente cambiará a "Solicitado" (Requested) y el botón de solicitar aprobación se habilitará.

**Paso 2: Análisis (Rol: Analista de Riesgo)**
1. El analista revisa el perfil del cliente en **Contactos**.
2. Puede usar el menú de acción **"Subir Documentación"** en la pestaña "Credit Limit" para adjuntar informes comerciales, balances o avales.
3. Una vez verificada la viabilidad, el analista hace clic en el botón superior **"Analizar Documentación"**. El estado visual cambiará a "Analizado".

**Paso 3: Aprobación (Rol: Aprobador / Gerencia)**
1. El gerente de finanzas ingresa al contacto del cliente.
2. Revisa el monto sugerido y la investigación previa, y hace clic en **"Aprobar Límite"**.
3. En este momento, la *Cuenta Corriente* queda activa oficialmente en el sistema para ese cliente.
4. **Nota:** Si el Aprobador ha habilitado la opción de *Delegación de Aprobación* en Contabilidad > Ajustes, el Analista de Riesgo también podrá aprobar o rechazar solicitudes directamente.

**Paso 4: Venta y Bloqueos Automáticos (Rol: Ventas)**
1. El equipo de ventas ve a la aplicación de **Ventas** y crea una Orden de Venta para este cliente.
2. Al agregar los productos o cambiar clientes, verán un panel informativo con el Límite Total, Crédito Utilizado y el Crédito Disponible.
3. Si hacen clic en **"Confirmar"** y el total de la orden sumado a la deuda actual excede el *Crédito Disponible*, el sistema lanzará un mensaje de error deteniendo la confirmación para evitar el riesgo financiero.
4. De igual manera, si un cliente no pagó, el Analista de Riesgo puede usar el botón **"Bloquear Cuenta"** directamente desde la ficha del contacto, impidiendo cualquier venta nueva al instante.

## Notas Adicionales
* **Dependencias:** Este módulo requiere los módulos estándar de Ventas (`sale`), Contabilidad (`account`) y la función de cheques (`l10n_latam_check`).
* **Cheques no cobrados:** Los ingresos de pago registrados en cheques que aún no fueron efectivizados o aplicados seguirán contando como parte del "Crédito Utilizado" para proteger a la empresa de posibles cheques rechazados.
