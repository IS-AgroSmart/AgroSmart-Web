# MVP

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=IS-AgroSmart_MVP&metric=alert_status)](https://sonarcloud.io/dashboard?id=IS-AgroSmart_MVP)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=IS-AgroSmart_MVP&metric=coverage)](https://sonarcloud.io/dashboard?id=IS-AgroSmart_MVP)
![CI](https://github.com/IS-AgroSmart/AgroSmart-Web/workflows/CI/badge.svg)

# Development environment setup

### Programas

1. Docker y Docker Compose
2. En Windows, Docker Desktop contiene ambos programas.
3. En Linux, deben instalarse con apt-get. Además hay pasos adicionales.
4. IDE de Python (por ejemplo, Pycharm Community o Pycharm Professional con la licencia de estudiante)
5. Python 3.6 o superior
6. IDE para Vue (Visual Studio Code es gratuito)

### Instalación y configuración

1. Confirmar que Docker funcione (docker run hello-world debe mostrar el mensaje de éxito, y docker-compose --version debe imprimir una versión)
2. Seleccionar o crear una carpeta raíz (por ejemplo, el escritorio, Descargas o la carpeta Home). En adelante, esta carpeta será llamada PREFIX (por ejemplo, /home/username/Desktop)
3. Descargar el archivo docker-compose.yml y moverlo a PREFIX.
4. Crear una carpeta llamada nginx en PREFIX.
5. Descargar el archivo nginx.conf y moverlo a PREFIX/nginx.
6. Crear una carpeta llamada projects en PREFIX.
7. Clonar el repositorio del código en PREFIX (cd <PREFIX>; git clone https://github.com/IS-AgroSmart/AgroSmart-Web). La carpeta se llamará AgroSmart-Web por defecto.
8. Renombrar AgroSmart-Web a app.
9. (Opcional) Crear un virtualenv para Python.
10. Instalar los paquetes indicados en requirements.txt (django, djangorestframework, python-decouple, requests). Se pueden instalar manualmente o ejecutar pip install -r requirements.txt.
11. En este punto, PREFIX debe contener los siguientes archivos/carpetas:
  1. El archivo docker-compose.yml
  2. Una carpeta nginx con el archivo nginx.conf
  3. Una carpeta projects, vacía
  4. Una carpeta app con el código de la app de Django (core/, templates/, IngSoft1/, manage.py, etc) Y ADEMÁS una carpeta frontend con el código de la aplicación de Vue
  (HACK) Por ahora, ejecutar npm install en la carpeta PREFIX/app/frontend

### Ejecución

1. Abrir un terminal en la carpeta PREFIX
2. Ejecutar PREFIX=. docker-compose up para iniciar los servidores de NodeODM (puerto 3000), Geoserver (puerto 8080), PostgreSQL (puerto 5432), Vue (puerto 8001) y Django (puerto 8000), además de Nginx.
3. El servidor de Django se inicia con los demás cuando se ejecuta docker-compose. Por lo tanto, NO se debe ejecutar el servidor de Django desde Pycharm.
4. (HACK) Ejecutar python manage.py migrate y python manage.py createsuperuser desde Pycharm. Estos cambios serán detectados por el servidor, pero solamente porque usa una base de datos SQLite y el archivo db.sqlite3 está compartido entre la computadora y el contenedor.
5. En este punto, se puede visitar http://localhost:X (donde X es el puerto de uno de los servicios activos) para visitarlo. Además, el puerto 80 permite acceder a todos los servicios (http://localhost/nodeodm para NodeODM, http://localhost/geoserver para Geoserver, http://localhost/api, http://localhost/admin y http://localhost/static para Django, y http://localhost para la app de Vue).
6. Para detener los servidores, presionar Ctrl+C en la consola que muestra los logs de Docker. Si algún servidor no se detiene, PREFIX=. docker-compose down fuerza la detención.



