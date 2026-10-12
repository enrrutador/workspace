# MCP — el sistema nervioso de la empresa

## Qué es, en 5 líneas

1. **MCP** (Model Context Protocol) es un estándar abierto para conectar agentes de IA con herramientas y datos.
2. Funciona con **servidores** que exponen herramientas (funciones que el agente puede llamar) y **clientes** que las consumen.
3. Un servidor MCP puede darle a un agente acceso a una base de datos, una API, un sistema de archivos o un producto entero.
4. Es un protocolo, no un producto: cualquier modelo y cualquier marco de trabajo (LangGraph incluido) pueden hablarlo.
5. Al ser abierto, evita quedar atado a un proveedor: si mañana cambia el proveedor de modelos, las integraciones siguen funcionando.

## La regla de la casa

**Cada sistema interno y cada producto futuro expone un servidor MCP. Los agentes consumen herramientas vía MCP, nunca con integraciones a medida.**

Esto convierte el problema de integración de **N×M en N+M**: sin un estándar, cada uno de los N agentes necesitaría una integración a medida con cada uno de los M sistemas. Con MCP, cada sistema expone *un* servidor y cada agente aprende *un* protocolo.

## Conexión con la tesis de la empresa

Nuestra tesis es **la conexión entre productos tecnológicos**: un ecosistema de productos interconectados, no productos sueltos. MCP es esa tesis hecha infraestructura:

- Cuando el producto B necesite datos o funciones del producto A, no hay proyecto de integración: el producto A ya expone un servidor MCP y el producto B lo consume.
- Los agentes internos usan los mismos servidores MCP que eventualmente usarán otros productos: **uso interno automático** de la interoperabilidad.
- Cada producto nuevo nace "listo para agentes" y "listo para el ecosistema" desde el día uno, porque exponer su servidor MCP es parte de la lista de verificación de construcción (ver `../pipeline/`).
- El **mapa de dependencias entre productos** del pipeline se vuelve concreto: es el grafo de quién consume el MCP de quién. Matar un producto implica revisar quién depende de su servidor.

## Riesgos y mitigaciones

| Riesgo | Qué es | Mitigación |
|---|---|---|
| **Envenenamiento de herramientas** | Un servidor MCP malicioso (o comprometido) describe sus herramientas de forma engañosa para manipular al agente | Solo servidores MCP de **fuentes confiables**: los nuestros o de proveedores verificados. Nunca conectar un servidor MCP de un tercero no auditado a un agente con permisos sensibles |
| Servidor comprometido | Un servidor legítimo es atacado y empieza a devolver datos maliciosos | Autenticación en cada servidor MCP; permisos mínimos por herramienta; los agentes validan los resultados críticos antes de actuar |
| Fuga de datos | Un agente expone datos de un sistema a otro a través de herramientas encadenadas | Aislamiento por producto/cliente (tenancy); ningún agente cruza datos entre clientes; datos personales ocultos en los registros |
| Superficie de ataque | Cada servidor MCP nuevo es un punto de entrada más | Inventario de servidores MCP conectados por agente (parte de la gobernanza mínima viable); revisión antes de conectar uno nuevo |

**Regla práctica**: tratar cada servidor MCP como se trata una dependencia de código — con fijación de versión, revisión y lista de permitidos. Un agente no conecta un servidor MCP nuevo sin que esté en su inventario aprobado.
