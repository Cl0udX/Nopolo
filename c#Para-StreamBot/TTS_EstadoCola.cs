// ═══════════════════════════════════════════════════════════════════════════
// 📊 TTS_EstadoCola.cs - CONSULTAR ESTADO DE LA COLA
// ═══════════════════════════════════════════════════════════════════════════
// 
// ¿QUÉ HACE?
// ----------
// Consulta cuántos mensajes están en cola esperando ser reproducidos.
// 
// CÓMO USAR:
// ----------
// 1. Crear comando en Streamer.bot: !cola
// 2. El usuario escribe: !cola
// 3. El bot responde: "📊 Mensajes en cola TTS: 3"
//
// UTILIDAD:
// ---------
// Permite a los viewers saber cuánto tiempo falta para que se lea su mensaje.
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
            // PASO 1: Consultar el estado de la cola
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            string respuesta = ConsultarCola();

            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            // PASO 2: Extraer la información
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if (respuesta.Contains("200 OK"))
            {
                // Extraer el contenido JSON
                int inicioCuerpo = respuesta.IndexOf("\r\n\r\n");
                if (inicioCuerpo > 0)
                {
                    string json = respuesta.Substring(inicioCuerpo + 4);
                    
                    // Buscar el número de mensajes en cola
                    if (json.Contains("\"queue_size\""))
                    {
                        string tamañoCola = ExtraerTamañoCola(json);
                        
                        // Mostrar en el chat
                        CPH.SendMessage("📊 Mensajes en cola TTS: " + tamañoCola, true);
                        CPH.LogInfo("✅ [Estado Cola] " + tamañoCola + " mensajes en espera");
                    }
                }
                return true;
            }
            else
            {
                CPH.LogError("❌ [Estado Cola] No se pudo obtener el estado");
                CPH.LogError("   → ¿Está corriendo Nopolo en http://localhost:8000?");
                return false;
            }
        }
        catch (Exception ex)
        {
            CPH.LogError("❌ [Estado Cola] Error: " + ex.Message);
            return false;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // FUNCIONES AUXILIARES (No es necesario modificar nada aquí)
    // ═══════════════════════════════════════════════════════════════════════
    
    /// <summary>
    /// Consulta al servidor de Nopolo para obtener el estado de la cola
    /// </summary>
    private string ConsultarCola()
    {
        try
        {
            // Configuración del servidor
            string servidor = "127.0.0.1";
            int puerto = 8000;
            string ruta = "/api/queue";
            
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
                byte[] buffer = new byte[4096];
                int bytesLeidos = stream.Read(buffer, 0, buffer.Length);
                return Encoding.UTF8.GetString(buffer, 0, bytesLeidos);
            }
        }
        catch (SocketException)
        {
            CPH.LogError("❌ [Estado Cola] No se pudo conectar a Nopolo.");
            return "";
        }
        catch (Exception ex)
        {
            CPH.LogError("❌ [Estado Cola] Error: " + ex.Message);
            return "";
        }
    }

    /// <summary>
    /// Extrae el tamaño de la cola del JSON
    /// Ejemplo: {"queue_size": 5} → "5"
    /// </summary>
    private string ExtraerTamañoCola(string json)
    {
        try
        {
            // Buscar "queue_size": y extraer el número
            int inicio = json.IndexOf("\"queue_size\":") + 13;
            int fin = json.IndexOf(",", inicio);
            if (fin < 0) fin = json.IndexOf("}", inicio);
            
            return json.Substring(inicio, fin - inicio).Trim();
        }
        catch
        {
            return "?";
        }
    }
}