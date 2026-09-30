// ═══════════════════════════════════════════════════════════════════════════
// 🎭 TTS_NopoloMultiVozCommand.cs - VERSIÓN CON COMANDO
// ═══════════════════════════════════════════════════════════════════════════
//
// ¿QUÉ HACE?
// ----------
// Igual que TTS_NopoloMultiVoz.cs (envía texto con MÚLTIPLES VOCES y EFECTOS
// a Nopolo usando la sintaxis especial), pero en vez de leer CUALQUIER
// mensaje del chat, solo se activa con un comando explícito.
//
// CÓMO USAR:
// ----------
// 1. Crear un Command en Streamer.bot con el texto: !nopolo
//    (agrégalo para Twitch Y YouTube si transmites en ambas)
// 2. El usuario escribe: !nopolo homero: Hola mundo (aplausos) dross: Gracias
// 3. Nopolo reproduce el mensaje con la sintaxis multi-voz de siempre
//
// SINTAXIS NOPOLO (igual que TTS_NopoloMultiVoz.cs):
// ----------------
// • voz: texto                    → Usa una voz específica
// • voz.filtro: texto            → Voz + efecto de audio
// • voz.fondo: texto             → Voz + música de fondo
// • (sonido)                     → Reproduce un sonido
// • (sonido.filtro)              → Sonido + efecto de audio
// • (sonido.fondo)               → Sonido + música de fondo
//
// EJEMPLOS:
// ---------
// !nopolo homero: Hola mundo
// !nopolo homero.r: Hola con eco (filtro r = reverb)
// !nopolo (aplausos) dross: Gracias a todos
//
// FILTROS DISPONIBLES:
// --------------------
// r  = Eco/Reverberación
// p  = Llamada telefónica
// pu = Voz aguda (chipmunk)
// pd = Voz grave (monstruo)
// m  = Voz apagada
// a  = Robot
// l  = Saturada/distorsionada
//
// OVERLAY (Opcional):
// -------------------
// Puedes enviar el nombre del usuario que escribió el mensaje para que
// aparezca en el overlay de OBS en lugar de "Multi-Voz (modo Nopolo)".
// Para activarlo, descomenta las líneas indicadas más abajo (busca "OPCIONAL").
//
// CONFIGURACIÓN:
// --------------
// 1. Servidor Nopolo debe estar corriendo en http://localhost:8000
// 2. Iniciar con: ./run_nopolo_full.sh (para habilitar API)
//
// REFERENCIAS NECESARIAS:
// -----------------------
// System.dll, System.Net.Sockets.dll
//
// ═══════════════════════════════════════════════════════════════════════════

using System;
using System.Net.Sockets;
using System.Text;

public class CPHInline
{
    // El texto del comando en Streamer.bot (debe coincidir con lo que
    // configuraste ahí). Cámbialo aquí si usas otro texto de comando.
    private const string COMANDO = "!nopolo";

    // ═══════════════════════════════════════════════════════════════════════
    // MÉTODO PRINCIPAL
    // ═══════════════════════════════════════════════════════════════════════
    public bool Execute()
    {
        try
        {
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            // PASO 1: Obtener el texto del mensaje (sin el comando)
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            string texto = ObtenerTextoDelMensaje();

            // Si no hay texto, salir
            if (string.IsNullOrEmpty(texto))
            {
                CPH.LogWarn("❌ [Nopolo Multi-Voz Comando] No hay texto para leer (¿escribiste algo después de " + COMANDO + "?)");
                return false;
            }

            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            // PASO 2: Enviar al servidor Nopolo
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            bool exito = EnviarANopolo(texto);

            if (exito)
            {
                CPH.LogInfo("✅ [Nopolo Multi-Voz Comando] Texto enviado: " + texto);
                return true;
            }
            else
            {
                CPH.LogWarn("⚠️ [Nopolo Multi-Voz Comando] Error al enviar texto");
                return false;
            }
        }
        catch (Exception ex)
        {
            CPH.LogError("❌ [Nopolo Multi-Voz Comando] Error: " + ex.Message);
            return false;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // MÉTODOS AUXILIARES (NO MODIFICAR)
    // ═══════════════════════════════════════════════════════════════════════

    /// <summary>
    /// Obtiene el texto del mensaje desde Streamer.bot, quitando el comando
    /// del inicio si viniera incluido. Según cómo esté configurado el
    /// trigger en Streamer.bot, "rawInput" puede llegar SIN el comando
    /// (solo lo que escribió el usuario después) o CON el comando incluido
    /// -- por eso quitamos el prefijo solo si está presente, y si no,
    /// dejamos el texto tal cual.
    /// </summary>
    private string ObtenerTextoDelMensaje()
    {
        if (!CPH.TryGetArg("rawInput", out string texto) || texto == null)
        {
            return null;
        }

        texto = texto.Trim();

        if (texto.StartsWith(COMANDO, StringComparison.OrdinalIgnoreCase))
        {
            texto = texto.Substring(COMANDO.Length).TrimStart();
        }

        return texto;
    }

    /// <summary>
    /// Envía el texto al servidor Nopolo usando el endpoint de multi-voz
    /// </summary>
    private bool EnviarANopolo(string texto)
    {
        try
        {
            // Configuración del servidor
            string servidor = "127.0.0.1";  // localhost
            int puerto = 8000;               // Puerto de Nopolo
            string ruta = "/api/tts/multivoice";  // Endpoint multi-voz

            // Crear JSON con el texto
            string textoEscapado = EscaparJSON(texto);

            // OPCIONAL: Obtener nombre del usuario desde Streamer.bot
            // Descomenta las siguientes líneas si quieres mostrar el nombre del usuario en el overlay:
            // string usuario = "";
            // if (CPH.TryGetArg("userName", out string nombreUsuario))
            // {
            //     usuario = EscaparJSON(nombreUsuario);
            // }
            // string json = "{\"text\":\"" + textoEscapado + "\",\"author\":\"" + usuario + "\"}";

            // JSON sin author (comportamiento por defecto - muestra "Multi-Voz" en overlay)
            string json = "{\"text\":\"" + textoEscapado + "\"}";

            // Enviar petición HTTP
            string respuesta = EnviarPeticionHTTP(servidor, puerto, ruta, json);

            // Verificar si fue exitoso
            if (respuesta.Contains("200 OK") || respuesta.Contains("\"success\":true"))
            {
                return true;
            }
            else if (respuesta.Contains("404"))
            {
                CPH.LogError("❌ [Nopolo Multi-Voz Comando] Servidor no responde. ¿Iniciaste Nopolo con --with-api?");
                return false;
            }
            else
            {
                CPH.LogWarn("⚠️ [Nopolo Multi-Voz Comando] Respuesta inesperada del servidor");
                CPH.LogDebug("Respuesta: " + respuesta.Substring(0, Math.Min(200, respuesta.Length)));
                return false;
            }
        }
        catch (SocketException)
        {
            CPH.LogError("❌ [Nopolo Multi-Voz Comando] No se pudo conectar al servidor.");
            CPH.LogError("   → ¿Está Nopolo corriendo en http://localhost:8000?");
            CPH.LogError("   → Usa: ./run_nopolo_full.sh");
            return false;
        }
        catch (Exception ex)
        {
            CPH.LogError("❌ [Nopolo Multi-Voz Comando] Error de conexión: " + ex.Message);
            return false;
        }
    }

    /// <summary>
    /// Escapa caracteres especiales para JSON (soporta tildes, emojis, etc.)
    /// </summary>
    private string EscaparJSON(string texto)
    {
        return texto
            .Replace("\\", "\\\\")  // Barra invertida
            .Replace("\"", "\\\"")  // Comillas
            .Replace("\n", "\\n")   // Nueva línea
            .Replace("\r", "\\r")   // Retorno de carro
            .Replace("\t", "\\t")   // Tabulación
            .Replace("\b", "\\b")   // Retroceso
            .Replace("\f", "\\f");  // Form feed
    }

    /// <summary>
    /// Envía una petición HTTP POST al servidor
    /// </summary>
    private string EnviarPeticionHTTP(string servidor, int puerto, string ruta, string json)
    {
        // Convertir JSON a bytes UTF-8 (soporta tildes y emojis)
        byte[] cuerpoBytes = Encoding.UTF8.GetBytes(json);
        int longitudContenido = cuerpoBytes.Length;

        // Crear encabezados HTTP
        string encabezados =
            "POST " + ruta + " HTTP/1.1\r\n" +
            "Host: " + servidor + ":" + puerto + "\r\n" +
            "Content-Type: application/json; charset=utf-8\r\n" +
            "Content-Length: " + longitudContenido + "\r\n" +
            "Connection: close\r\n" +
            "\r\n";

        // Conectar y enviar
        using (TcpClient cliente = new TcpClient())
        {
            cliente.SendTimeout = 5000;    // 5 segundos timeout envío
            cliente.ReceiveTimeout = 5000; // 5 segundos timeout recepción
            cliente.Connect(servidor, puerto);

            NetworkStream stream = cliente.GetStream();

            // Enviar encabezados (ASCII)
            byte[] encabezadosBytes = Encoding.ASCII.GetBytes(encabezados);
            stream.Write(encabezadosBytes, 0, encabezadosBytes.Length);

            // Enviar cuerpo JSON (UTF-8)
            stream.Write(cuerpoBytes, 0, cuerpoBytes.Length);
            stream.Flush();

            // Leer respuesta completa. Un solo stream.Read() puede devolver
            // solo una parte si el body todavía no llegó del todo -- como
            // mandamos "Connection: close", el servidor cierra la conexión
            // cuando termina, así que leemos en bucle hasta Read()==0 (EOF).
            using (var memoria = new System.IO.MemoryStream())
            {
                byte[] buffer = new byte[4096];
                int bytesLeidos;
                while ((bytesLeidos = stream.Read(buffer, 0, buffer.Length)) > 0)
                {
                    memoria.Write(buffer, 0, bytesLeidos);
                }
                return Encoding.UTF8.GetString(memoria.ToArray());
            }
        }
    }
}
