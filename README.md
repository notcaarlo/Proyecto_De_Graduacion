# Sistema de Detección de Somnolencia en Conductores de Transporte Pesado

**Universidad Mariano Gálvez de Guatemala**  
Facultad de Ingeniería en Sistemas de Información  
Proyecto de Graduación – 2025

---

## 1. Descripción General

Este proyecto consiste en el desarrollo de un **sistema inteligente de detección de somnolencia** para conductores de transporte pesado.  
Su objetivo principal es **prevenir accidentes viales** provocados por la fatiga o la distracción, utilizando **técnicas de visión por computadora e inteligencia artificial** para analizar el rostro del conductor y detectar comportamientos que indiquen somnolencia.

El sistema está implementado en la empresa **Grúas y Multiservicios F.C.**, ubicada en Escuintla, Guatemala, y cuenta con una plataforma web que permite la **gestión de conductores, vehículos y alertas** en tiempo real.

---

## 2. Objetivos del Sistema

- Detectar signos de somnolencia mediante análisis facial con IA.  
- Emitir alertas automáticas cuando se identifiquen eventos de riesgo.  
- Registrar sesiones de conducción y generar reportes estadísticos.  
- Proporcionar a los administradores una herramienta centralizada de gestión vehicular.  
- Contribuir a la reducción de accidentes por fatiga en transporte pesado.

---

## 3. Arquitectura General

La solución está compuesta por tres módulos principales:

### a) Módulo de Detección (IA)
- Captura y análisis de video en tiempo real.  
- Detección de ojos cerrados, parpadeo prolongado y movimientos de cabeza.  
- Registro automático de alertas y evidencias.  
- Implementado con **OpenCV**, **MediaPipe** y **TensorFlow Lite**.

### b) Módulo Web (Administrador y Conductor)
- Plataforma desarrollada con **Flask** y **Bootstrap 5**.  
- Permite la gestión de usuarios, vehículos, sesiones y alertas.  
- Ofrece dashboards informativos y formularios dinámicos.

### c) Módulo de Base de Datos
- Implementado con **PostgreSQL** y **SQLAlchemy ORM**.  
- Gestiona las tablas de usuarios, vehículos, alertas, sesiones y configuraciones.  
- Incluye respaldo automático (`backup.sql`) y conexión centralizada.

---

## 4. Características Principales

| Rol | Funcionalidades |
|------|------------------|
| **Administrador** | Iniciar sesión, crear y gestionar vehículos, asignar conductores, consultar alertas y registros. |
| **Conductor** | Iniciar sesión, visualizar su vehículo asignado, iniciar jornada, recibir alertas en tiempo real. |
| **Sistema IA** | Analiza el rostro del conductor y genera alertas de somnolencia automáticamente. |

---
## 5. Tecnologías Utilizadas

| Categoría | Herramientas / Tecnologías |
|------------|----------------------------|
| Lenguaje principal | Python 3.10 |
| Framework backend | Flask |
| Base de datos | PostgreSQL |
| ORM | SQLAlchemy |
| Frontend | HTML5, Bootstrap 5, CSS3 |
| Inteligencia artificial | OpenCV, MediaPipe |
| Autenticación | Flask-Login, MFA TOTP |
| Pruebas automatizadas | Robot Framework, SeleniumLibrary, Pytest |
| Control de versiones | Git y GitHub |
| IDE / Entorno | Visual Studio Code, HeidiSQL |

---
## 7. Instalación y Ejecución

### 7.1 Clonar el repositorio
```bash
git clone https://github.com/notcaarlo/Proyecto_De_Graduacion.git
cd Proyecto_De_Graduacion

7.2 Crear el entorno virtual
python -m venv venv
venv\Scripts\activate

7.3 Instalar dependencias
pip install -r requirements.txt

7.4 Configurar la base de datos
Modificar las credenciales de conexión:

DB_USER = 'postgres'
DB_PASS = 'tu_contraseña'
DB_HOST = 'localhost'
DB_NAME = 'somnolencia'

7.5 Ejecutar el servidor
python main.py

8. Ejecución de Pruebas Automatizadas
robot -d reports/ui tests-ui/admin.robot

Los reportes generados se almacenan en:
reports/ui/

Incluyen los archivos:
output.xml
report.html
log.html

Pruebas Unitarias (Pytest)
pytest --maxfail=1 --disable-warnings -q
El proyecto implementa métricas básicas de aseguramiento de calidad:
	Cobertura de código	Porcentaje de líneas cubiertas por pruebas unitarias.
	Densidad de defectos	Número de errores por módulo detectados durante el ciclo de pruebas.
	MTTR (Mean Time to Repair)	Tiempo promedio para corregir defectos identificados.
	
10. Licencia y Derechos
Este proyecto fue desarrollado como parte del Proyecto de Graduación de la Universidad Mariano Gálvez de Guatemala.
Su uso, reproducción o modificación está autorizada únicamente con fines académicos y de investigación, citando la fuente original.

11. Autor
Carlo André Villanueva Cordón
Facultad de Ingeniería en Sistemas de Información
Universidad Mariano Gálvez de Guatemala – 2025
Escuintla, Guatemala