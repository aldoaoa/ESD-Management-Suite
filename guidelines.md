Guía de Referencia de Desarrollo:
ESD Management Suire
Línea Base del Sistema: Sistema de Gestión y Auditoría de Áreas Protegidas ESD (Descargas
Electroestáticas) para plantas industriales multi-site.
Versión del Documento: 1.0
Propósito: Este documento sirve como manual técnico y referencia de arquitectura para los
desarrolladores que asuman la continuidad, mantenimiento y evolución del sistema de control
ESD.

1. Arquitectura General del Sistema
El sistema está diseñado bajo una arquitectura ágil y modular utilizando un enfoque SaaS
Multi-Tenant. Permite la segregación de datos por sucursal o planta utilizando un identificador
único (site_id).
● Frontend & Aplicación: Desarrollado completamente en Python utilizando Streamlit
como framework de interfaz de usuario reactiva. Se estructura mediante una navegación
lateral (st.sidebar) dividida por macroprocesos.
● Persistencia de Datos: Migrado de una arquitectura inicial basada en Google Sheets a
un motor relacional sólido en Supabase (PostgreSQL). Actualmente incluye planes de
migración o despliegue en entornos locales sobre Microsoft SQL Server mediante
contenedores Docker.
● Lógica de Fondo / Automatizaciones: Edge Functions (Supabase/Deno) para procesos
programados, como el envío automático de alertas de vencimiento por correo electrónico.
2. Stack Tecnológico y Dependencias
El núcleo del sistema depende de las siguientes herramientas y librerías clave de Python:
Librería / Herramienta Propósito y Uso en el Sistema
Streamlit (st) Framework principal de la aplicación. Maneja
el estado de la sesión (st.session_state),
formularios de captura y renderizado de la
interfaz de usuario.

Supabase Python Client Conector e interfaz con la base de datos en la
nube. Gestiona las consultas, inserciones y la
lógica de doble persistencia.

Pandas (pd) Manipulación y estructuración de datos.
Procesamiento de archivos adjuntos (como
reportes 4Q de hallazgos) y cruces

Librería / Herramienta Propósito y Uso en el Sistema

semanales de fechas mediante isocalendar().
Plotly Express (go / px) Generación de visualizaciones dinámicas,
gráficos de cumplimiento normativo y mapas
de calor interactivos para la pestaña 4Q del
Dashboard.

PyMuPDF (fitz) Renderizado, extracción de texto y
visualización interactiva de documentos PDF
en el sistema.

PyTesseract Motor de OCR (Reconocimiento Óptico de
Caracteres) para procesar y digitalizar texto
desde imágenes o evidencias escaneadas.
Werkzeug Security Capa de seguridad encargada del hash
(encriptación) y verificación de contraseñas
de los auditores en la pestaña de usuarios
(generate_password_hash y
check_password_hash).

Componentes HTML5 nativos Integración de escáneres QR reactivos en el
frontend web utilizando componentes
embebidos de Streamlit.
3. Estructura de Módulos y Vistas (Frontend)
La interfaz de usuario está organizada en las siguientes vistas lógicas clave:
1. Overview y Dashboard: Panel general de cumplimiento basado en la norma ANSI/ESD
S20.20-2021. Incluye el semáforo de vigencia (Verde: Vigente, Amarillo: Pendiente, Rojo:
Vencido).
2. Escáner y Detalles: Módulo de piso que consulta el historial del elemento escaneado vía
QR, aplicando doble persistencia en historial_mediciones e inventario_esd. Si un equipo
está dado de baja, muestra "NO OPERATIVO".
3. Mobiliario e Inventario (05_inventory.py): Gestión operativa de los elementos ESD en
planta.
4. Laboratorio de Pruebas (05_lab.py): Control de Event Meter y Walking Test.
5. Infraestructura y Planta (06_infrastructure.py): Supervisión de Tierras Auxiliares (< 25
ohms), Conexiones de Pulsera (< 2.0 ohms) y Pisos Conductivos/Disipativos (< 1.0x10^9
ohms).
6. Entrenamiento y Recursos Humanos (07_training.py): Control y validación del estatus
de capacitación del personal operativo.
7. Cronograma (Schedule): Filtro por línea de producción que muestra de forma visual
mediante emojis (🟢, 🟡, 🔴) las fechas de medición y vencimiento de equipos,
mobiliario e ionizadores.
8. Ajustes y Catálogos Maestros: Administración centralizada de Líneas/Ubicaciones,
Equipos de Medición y gestión segura de usuarios.

4. Flujo de Datos y Backend (Base de Datos)
El backend se apoya fuertemente en vistas unificadas mediante la instrucción UNION ALL para
consolidar la información de vencimientos de 4 fuentes críticas:
● inventario_esd
● mediciones_maquinaria (Etiquetado como 'Maquinaria y Líneas')
● validacion_esd
● equipos_medicion
El sistema calcula de forma automática la próxima fecha límite sumando la periodicidad
respectiva (por ejemplo, 1 año para maquinaria) y almacenándola en el campo
fecha_proxima_verif (o fecha_proxima) para evitar falsas alarmas.
Estrategia de Variables de Entorno y Despliegue
Para garantizar el ciclo de desarrollo seguro se implementa una lógica dual en la conexión
(init_connection):
● Desarrollo Local: Se lee de forma nativa desde el archivo local protegido
.streamlit/secrets.toml (nunca subido a repositorios públicos).
● Producción (Render / Cloud): El código captura dinámicamente las credenciales desde
variables de entorno del sistema (os.environ.get).
5. Estándares y Requerimientos de TI para Futuras
Migraciones
En caso de requerirse una migración al servidor interno corporativo, la dirección de TI ha
establecido los siguientes lineamientos estrictos:
1. Stack Corporativo Microsoft: C# / ASP.NET para páginas y APIs, junto con Microsoft
SQL Server/Express para la base de datos.
2. Entorno Offline Estricto: El servidor de producción cuenta con Cero acceso a Internet.
Todas las librerías, dependencias y paquetes (incluyendo drivers de bases de datos)
deben empaquetarse localmente previamente.
3. Alternativa por Docker (Recomendada para ROI de Tiempo): Para evitar reescribir la
potente lógica interactiva de Python a C#, se propone empaquetar la aplicación Streamlit
en un contenedor Docker con despliegue "en frío" (descargando todas las librerías
previamente en la máquina de desarrollo y configurando el Dockerfile para instalación
offline).
