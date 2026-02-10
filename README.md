# Nopolo

El proyecto actualmente esta hecho en windows, aunque se puede adaptar a otros sistemas operativos, este readme se enfoca en la instalación en windows.

Si lo que quiere es usar el proyecto ve a los releases y descarga el ejecutable, si quieres clonar el proyecto y usarlo desde el código fuente, sigue las instrucciones a continuación.

Este proyecto usa python3.11.9 , se recomienda usar un entorno virtual para instalar las dependencias de pip.

También es necesario instalar Chocolatey esto se hace a nivel de sistema, asi que ejecuta power shell como administrador y ejecuta el comando dentro de la pagina oficial de chocolatey:

https://chocolatey.org/install

lo siguente es instalar espeak-ng, use la misma consola de power shell y ejecuta el siguiente comando:

choco install espeak-ng

instalar Microsoft Visual C++ Build Tools para compilar Coqui TTS en Windows.
Ejecuta el instalador
Selecciona "Desktop development with C++"
Instala (ocupa ~6-7 GB)

Dentro del proyecto usando en entorno virtual donde se esta usando Python 3.11.9, instala las dependencias necesarias para el proyecto:

pip install PySide6 sounddevice numpy scipy TTS
pip install torch==2.1.0 torchaudio==2.1.0

Nota: si por alguna razon al iniciar la consola dice que no encuentra espeak-ng, es porque no se agrego a la variable de entorno PATH,
generalmente se encuentra en C:\Program Files\eSpeak NG.
Tambien puede intentar instalarlo manualmente, descargando el instalador desde la pagina oficial:
https://github.com/espeak-ng/espeak-ng/releases
instalandolo manualmente tambien es importante agregarlo a la variable de entorno PATH.
Si agrego espeak-ng a la variable de entorno PATH, es necesario reiniciar la consola o el sistema para que los cambios surtan efecto en el entorno.

<!-- # pyttsx3 is offline and doesn't need heavy dependencies
pip install pyttsx3

# or edge-tts which uses Microsoft's TTS service
pip install edge-tts -->


Modelo recomendado:
     Español: tts_models/multilingual/multi-dataset/xtts_v2 (Pesado)
     Español: tts_models/es/mai/tacotron2-DDC (Ligero)