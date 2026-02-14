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
using System.Net.Sockets;
using System.Text;

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
                    
                    // Opcional: Enviar mensaje al chat
                    CPH.SendMessage("🎙️ Consulta los logs para ver las voces disponibles", true);
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