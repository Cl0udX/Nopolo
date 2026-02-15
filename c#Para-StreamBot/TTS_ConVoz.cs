// ═══════════════════════════════════════════════════════════════════════════
// 📢 TTS_ConVoz.cs - VERSIÓN CON SELECCIÓN DE VOZ
// ═══════════════════════════════════════════════════════════════════════════
// 
// ¿QUÉ HACE?
// ----------
// Permite al usuario elegir una voz específica para el TTS.
// 
// CÓMO USAR:
// ----------
// 1. Crear comando en Streamer.bot: !voz
// 2. El usuario escribe: !voz homero Hola, soy Homero Simpson
// 3. Nopolo reproduce el mensaje con la voz de Homero
//
// VOCES DISPONIBLES:
// ------------------
// • homero, dross, bugs, patolucas (o las que hayas configurado)
// • random o aleatorio - Usa una voz aleatoria sin RVC (solo TTS)
// • Si la voz no existe, se usa automáticamente una voz aleatoria sin RVC
//
// OVERLAY (Opcional):
// -------------------
// Puedes enviar el nombre del usuario que escribió el mensaje para que
// aparezca en el overlay de OBS en lugar del nombre de la voz.
// Para esto, agrega el campo "author" al JSON (ver línea 73).
// Ejemplo: Si "postInCloud" escribe "!voz goku te amo", el overlay mostrará "postInCloud"
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
            // PASO 1: Obtener el mensaje completo
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if (!CPH.TryGetArg("rawInput", out string mensajeCompleto))
            {
                CPH.LogError("❌ [TTS Voz] No hay mensaje para leer");
                return false;
            }

            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            // PASO 2: Separar la voz del texto
            // Ejemplo: "homero Hola mundo" → voz="homero", texto="Hola mundo"
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            string[] partes = mensajeCompleto.Split(new char[] { ' ' }, 2);
            
            if (partes.Length < 2)
            {
                CPH.LogError("❌ [TTS Voz] Formato incorrecto.");
                CPH.LogError("   → Usa: !voz NOMBRE_VOZ tu mensaje aquí");
                return false;
            }

            string voz = partes[0].ToLower();  // Primera palabra = voz
            string texto = partes[1];           // Resto = texto a leer

            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            // PASO 3: Preparar el mensaje para enviarlo
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            string textoSeguro = PrepararMensajeParaJSON(texto);
            string vozSegura = PrepararMensajeParaJSON(voz);
            
            // OPCIONAL: Obtener nombre del usuario desde Streamer.bot
            // Descomenta las siguientes líneas si quieres mostrar el nombre del usuario en el overlay:
            // string usuario = "";
            // if (CPH.TryGetArg("userName", out string nombreUsuario))
            // {
            //     usuario = PrepararMensajeParaJSON(nombreUsuario);
            // }
            // string json = "{\"text\":\"" + textoSeguro + "\",\"voice_id\":\"" + vozSegura + "\",\"author\":\"" + usuario + "\"}";
            
            // JSON sin author (comportamiento por defecto - muestra nombre de voz en overlay)
            string json = "{\"text\":\"" + textoSeguro + "\",\"voice_id\":\"" + vozSegura + "\"}";

            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            // PASO 4: Enviar al servidor de Nopolo
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            bool exito = EnviarANopolo(json);
            
            if (exito)
            {
                CPH.LogInfo("✅ [TTS Voz] Voz: " + voz + " | Texto: " + texto);
                return true;
            }
            else
            {
                CPH.LogWarn("⚠️ [TTS Voz] No se pudo enviar el mensaje");
                return false;
            }
        }
        catch (Exception ex)
        {
            CPH.LogError("❌ [TTS Voz] Error: " + ex.Message);
            return false;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // FUNCIONES AUXILIARES (No es necesario modificar nada aquí)
    // ═══════════════════════════════════════════════════════════════════════
    
    /// <summary>
    /// Convierte el texto a un formato seguro para JSON
    /// </summary>
    private string PrepararMensajeParaJSON(string texto)
    {
        return texto
            .Replace("\\", "\\\\")
            .Replace("\"", "\\\"")
            .Replace("\n", "\\n")
            .Replace("\r", "\\r")
            .Replace("\t", "\\t");
    }

    /// <summary>
    /// Envía el mensaje al servidor de Nopolo
    /// </summary>
    private bool EnviarANopolo(string json)
    {
        try
        {
            // Configuración del servidor
            string servidor = "127.0.0.1";
            int puerto = 8000;
            string ruta = "/api/tts";
            
            // Convertir texto a bytes
            byte[] jsonBytes = Encoding.UTF8.GetBytes(json);
            
            // Crear petición HTTP
            string encabezados = 
                "POST " + ruta + " HTTP/1.1\r\n" +
                "Host: " + servidor + ":" + puerto + "\r\n" +
                "Content-Type: application/json; charset=utf-8\r\n" +
                "Content-Length: " + jsonBytes.Length + "\r\n" +
                "Connection: close\r\n" +
                "\r\n";

            // Conectar y enviar
            using (TcpClient cliente = new TcpClient())
            {
                cliente.SendTimeout = 5000;
                cliente.ReceiveTimeout = 5000;
                cliente.Connect(servidor, puerto);

                NetworkStream stream = cliente.GetStream();
                
                // Enviar encabezados
                byte[] encabezadosBytes = Encoding.ASCII.GetBytes(encabezados);
                stream.Write(encabezadosBytes, 0, encabezadosBytes.Length);
                
                // Enviar mensaje
                stream.Write(jsonBytes, 0, jsonBytes.Length);
                stream.Flush();

                // Leer respuesta
                byte[] buffer = new byte[4096];
                int bytesLeidos = stream.Read(buffer, 0, buffer.Length);
                string respuesta = Encoding.UTF8.GetString(buffer, 0, bytesLeidos);
                
                // Verificar si fue exitoso
                return respuesta.Contains("200 OK") || respuesta.Contains("\"success\":true");
            }
        }
        catch (SocketException)
        {
            CPH.LogError("❌ [TTS Voz] No se pudo conectar a Nopolo.");
            CPH.LogError("   → ¿Está corriendo en http://localhost:8000?");
            return false;
        }
        catch (Exception ex)
        {
            CPH.LogError("❌ [TTS Voz] Error: " + ex.Message);
            return false;
        }
    }
}