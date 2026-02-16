# Instrucciones para importar voces RVC

Puedes colocar aquí carpetas con tus modelos de voz RVC para importación automática.

Ejemplo de estructura:

voices/
├── homero/
│   ├── modelo.index
│   └── modelo.pth
├── bart/
│   ├── otro.index
│   └── otro.pth

- Al iniciar la app y presionar "Escanear voces", se detectarán automáticamente las carpetas y se configurarán con valores por defecto.
- Puedes tener tantas carpetas de voces como quieras.
- Los modelos pueden estar en cualquier ruta, pero si los pones aquí, la importación es más rápida.

**Opcional:** Puedes borrar este archivo si no lo necesitas.