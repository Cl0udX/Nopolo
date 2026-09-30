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

                    // En vez de mandar el mensaje directo desde el C# (que
                    // depende de que CPH.SendMessage sepa a qué plataforma
                    // responder), lo guardamos en una Global Variable de
                    // Streamer.bot (aparece en Variables > Global). Después,
                    // en cualquier Action, agrega una sub-acción nativa
                    // "Send Message" (Twitch o YouTube) y en su campo de
                    // mensaje escribe: %voces%
                    CPH.SetGlobalVar("voces", mensajeChat, false);
                    CPH.LogInfo("[Listar Voces] Global Variable 'voces' guardada: " + mensajeChat);
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

                // Leer respuesta
                byte[] buffer = new byte[8192];
                int bytesLeidos = stream.Read(buffer, 0, buffer.Length);
                return Encoding.UTF8.GetString(buffer, 0, bytesLeidos);
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