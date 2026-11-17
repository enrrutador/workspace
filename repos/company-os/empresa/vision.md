# Visión

## La tesis: la conexión entre productos tecnológicos

Los productos tecnológicos no existen aislados: se usan en conjunto, comparten datos y se conectan entre sí. La tesis de esta empresa es que **diseñar cada producto como parte de un ecosistema interoperable** —en lugar de construir productos sueltos— es una ventaja estructural.

Concretamente:

- Cada producto expone un servidor MCP: integraciones, datos y capacidades son programáticamente accesibles por defecto.
- El ecosistema se vuelve la propuesta de valor: un producto nuevo se lanza ya conectado a los anteriores, no desde cero.
- La red de dependencias entre productos es un activo: matar un producto exige evaluar qué se rompe en la red (ver [pipeline y capa portafolio](diseno-operativo-v1.md)).

## Por qué el modelo multi-producto estilo Meta

El modelo es el de Meta: **una empresa, muchos productos; se crece construyendo y adquiriendo**. Las razones:

- **Diversificación del riesgo**: ningún producto solo define el destino de la empresa.
- **Infra compartida**: los productos corren sobre la misma base (modelos, gateway, observabilidad, aprobaciones). Cada producto nuevo nace "listo para agentes" y cuesta menos que el anterior.
- **Composabilidad**: la tesis hace que los productos se potencien mutuamente en vez de canibalizarse.
- **Crecimiento por adquisición**: el modelo admite comprar productos que encajen en el ecosistema, no solo construirlos.

La capa portafolio disciplina este modelo: los productos compiten entre sí por capacidad de agentes y por atención de Fabian; lo que no tracciona se mata o se pausa (con proceso de discontinuación para productos con clientes: comunicación, migración, reembolsos).

## Por qué un plantel de agentes: 1 humano + 26 agentes

Fabian es la única persona —para siempre— y [un solo humano tiene límites](restricciones.md). La alternativa no es contratar gente, sino operar con agentes:

- **Cada función la ejecuta un equipo de agentes con roles definidos**: ingeniería, ventas, soporte, finanzas, marketing, operaciones e IT. Ver el [organigrama](organigrama.md).
- **Permisos mínimos e identidad propia**: cada agente tiene su propia identidad no-humana, permisos acotados y un dueño nombrado (Fabian).
- **Supervisión humana solo donde importa**: lo reversible es autónomo, lo medio va on-the-loop, lo irreversible exige aprobación previa de Fabian (in-the-loop). Las aprobaciones se acumulan en lote para que no te interrumpan todo el día.
- **Escalabilidad sin empleados**: agregar capacidad es agregar agentes, no personas. Con agentes baratos el riesgo no es el costo salarial, es el cementerio de productos zombies — por eso el pipeline mata con la misma disciplina con la que crea.

## Cómo la tesis se vuelve ventaja estructural

1. **MCP como sistema nervioso.** El mismo estándar abierto que integra los sistemas internos (MCP es la capa de integraciones de la pila) es el que conecta los productos entre sí. La infraestructura técnica *es* la tesis: la empresa entera es interoperable porque se construyó sobre el mismo protocolo que venden sus productos.
2. **Cada producto interoperable desde el día uno.** La lista de verificación de Construcción lo exige: ningún producto sale al mercado como isla.
3. **Escala por producto, no por empresa.** Cada producto nuevo se lanza sobre infra compartida (Fase 3 del diseño): lo que se construye una vez —aprobaciones, observabilidad, presupuestos, identidad— se reutiliza siempre.
4. **MCP + datos = foso defensivo.** La red de conexiones y los flujos entre productos son difíciles de copiar incluso si se copia un producto individual.

---

*Consistente con el [diseño operativo v1](diseno-operativo-v1.md) (2026-10-07).*
