// ═══════════════════════════════════════════════════════════════════════════
// 📋 TTS_ListarVoces.cs - LISTAR VOCES DISPONIBLES
// ═══════════════════════════════════════════════════════════════════════════
// 
// ¿QUÉ HACE?
// ----------
// Consulta al servidor de Nopolo para ver qué voces están configuradas.
// 
// CÓMO USAR:
// ----------
// 1. Crear comando en Streamer.bot: !voces
// 2. El usuario escribe: !voces
// 3. El script muestra en los logs las voces disponibles
//
// EJEMPLO DE RESPUESTA:
// ---------------------
// homero, dross, bugs, patolucas
//
// CONFIGURACIÓN:
// --------------
// • Servidor Nopolo corriendo en: http://localhost:8000
// • Iniciar con: ./run_nopolo_full.sh
//
// REFERENCIAS NECESARIAS:
// -----------------------
// System.dll, System.Net.Sockets.dll
//
// ═══════════════════════════════════════════════════════════════════════════

using System;
using System.Collections.Generic;
using System.Net.Sockets;
using System.Text;
using System.Text.RegularExpressions;

public class CPHInline
{
    public bool Execute()
    {
        try
        {
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            // PASO 1: Consultar al servidor de Nopolo
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            string respuesta = ConsultarVoces();

            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            // PASO 2: Verificar que la consulta fue exitosa
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if (respuesta.Contains("200 OK"))
            {
                // Extraer el contenido JSON (después de los encabezados HTTP)
                int inicioCuerpo = respuesta.IndexOf("\r\n\r\n");
                if (inicioCuerpo > 0)
                {
                    string json = respuesta.Substring(inicioCuerpo + 4);

                    CPH.LogInfo("✅ [Listar Voces] Voces disponibles:");
                    CPH.LogInfo(json);

                    // Sacar los profile_id del JSON (sin librería, con regex)
                    // y mandarlos al chat.
                    string listaVoces = ExtraerNombresVoces(json);

                    string mensajeChat = !string.IsNullOrEmpty(listaVoces)
                        ? "🎙️ Voces disponibles: " + listaVoces
                        : "🎙️ No hay voces configuradas";

                    // CPH.SendMessage es específico de Twitch -- no detecta
                    // sola la plataforma de origen del comando. Para que
                    // funcione tanto si !list vino de Twitch como de
                    // YouTube, mandamos el mensaje por las dos vías. Cada
                    // una en su propio try/catch para que si una falla (o
                    // no aplica, ej. no estás transmitiendo en esa
                    // plataforma) no impida la otra.
                    CPH.LogInfo("[Listar Voces] Enviando al chat: " + mensajeChat);

                    try
                    {
                        CPH.SendMessage(mensajeChat, false);
                    }
                    catch (Exception ex)
                    {
                        CPH.LogWarn("[Listar Voces] No se pudo enviar por Twitch: " + ex.Message);
                    }

                    try
                    {
                        CPH.SendYouTubeMessage(mensajeChat, false);
                    }
                    catch (Exception ex)
                    {
                        CPH.LogWarn("[Listar Voces] No se pudo enviar por YouTube: " + ex.Message);
                    }
                }
                return true;
            }
            else
            {
                CPH.LogError("❌ [Listar Voces] No se pudieron obtener las voces");
                CPH.LogError("   → ¿Está corriendo Nopolo en http://localhost:8000?");
                return false;
            }
        }
        catch (Exception ex)
        {
            CPH.LogError("❌ [Listar Voces] Error: " + ex.Message);
            return false;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // FUNCIONES AUXILIARES (No es necesario modificar nada aquí)
    // ═══════════════════════════════════════════════════════════════════════

    /// <summary>
    /// Saca los "profile_id" del JSON que devuelve /api/voices y los junta
    /// separados por coma, sin necesitar una librería de JSON.
    /// Ejemplo: [{"profile_id":"homero",...},{"profile_id":"dross",...}]
    ///          → "homero, dross"
    /// Nota: /api/voices devuelve TODAS las voces configuradas, incluidas
    /// las deshabilitadas -- si quieres ocultar esas, avísame y le agrego
    /// el filtro por "enabled":true.
    /// </summary>
    private string ExtraerNombresVoces(string json)
    {
        var nombres = new List<string>();
        var regex = new Regex("\"profile_id\"\\s*:\\s*\"([^\"]+)\"");

        foreach (Match match in regex.Matches(json))
        {
            nombres.Add(match.Groups[1].Value);
        }

        return string.Join(", ", nombres);
    }

    /// <summary>
    /// Consulta al servidor de Nopolo para obtener la lista de voces
    /// </summary>
    private string ConsultarVoces()
    {
        try
        {
            // Configuración del servidor
            string servidor = "127.0.0.1";
            int puerto = 8000;
            string ruta = "/api/voices";
            
            // Crear petición HTTP GET
            string peticion = 
                "GET " + ruta + " HTTP/1.1\r\n" +
                "Host: " + servidor + ":" + puerto + "\r\n" +
                "Connection: close\r\n" +
                "\r\n";

            // Conectar y enviar
            using (TcpClient cliente = new TcpClient())
            {
                cliente.SendTimeout = 5000;
                cliente.ReceiveTimeout = 5000;
                cliente.Connect(servidor, puerto);

                NetworkStream stream = cliente.GetStream();
                
                // Enviar petición
                byte[] datos = Encoding.UTF8.GetBytes(peticion);
                stream.Write(datos, 0, datos.Length);
                stream.Flush();

                // Leer respuesta completa. Un solo stream.Read() puede
                // devolver solo una parte si el body todavía no llegó del
                // todo -- como mandamos "Connection: close", el servidor
                // cierra la conexión cuando termina, así que leemos en
                // bucle hasta que Read() devuelva 0 (EOF real).
                using (var memoria = new System.IO.MemoryStream())
                {
                    byte[] buffer = new byte[8192];
                    int bytesLeidos;
                    while ((bytesLeidos = stream.Read(buffer, 0, buffer.Length)) > 0)
                    {
                        memoria.Write(buffer, 0, bytesLeidos);
                    }
                    return Encoding.UTF8.GetString(memoria.ToArray());
                }
            }
        }
        catch (SocketException)
        {
            CPH.LogError("❌ [Listar Voces] No se pudo conectar a Nopolo.");
            CPH.LogError("   → ¿Está corriendo en http://localhost:8000?");
            return "";
        }
        catch (Exception ex)
        {
            CPH.LogError("❌ [Listar Voces] Error: " + ex.Message);
            return "";
        }
    }
}