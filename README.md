Este sistema usa como base de datos mongodb, pydantic para el manejo de excepciones y errores y flet como frontend el cual está basado en flutter pero con una sintaxis más sencilla, por lo tanto se pueden realizar programas multiplataforma con el mismo código, sin embargo, nosotros solo obtimizamos su uso para desktop y web.
Por lo tanto, para poder ejecutar el sistema es necesario tener instalado flet, pymongo, pydantic, python y fastapi. Aquí se detallan los comandos necesarios para la ejecución:

Instalar mongodb comunity, si lo desea ejecutar localmente sin depender del servidor, para ello, acceda a este sitio: https://www.mongodb.com/try/download/community

MongoDB Driver: python -m pip install "pymongo[srv]"
Flet: python -m pip install flet
Variables de Entorno: pip install python-dotenv
Email Validator: pip install pydantic[email]
FastAPI: pip install fastapi

Para ejecutar el sistema, se debe ejecutar el archivo main.py, el cual contiene la función main(), la cual se encarga de iniciar el servidor de flet y el servidor de fastapi.