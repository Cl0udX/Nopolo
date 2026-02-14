// ═══════════════════════════════════════════════════════════════════════════
// 📢 TTS_Simple.cs - VERSIÓN SIMPLIFICADA
// ═══════════════════════════════════════════════════════════════════════════
// 
// ¿QUÉ HACE?
// ----------
// Envía texto al TTS de Nopolo con la voz por defecto.
// 
// CÓMO USAR:
// ----------
// 1. Crear comando en Streamer.bot: !tts
// 2. El usuario escribe: !tts Hola, esto es una prueba
// 3. Nopolo reproduce el mensaje con la voz por defecto
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
            // PASO 1: Obtener el mensaje que escribió el usuario
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if (!CPH.TryGetArg("rawInput", out string mensaje))
            {
                CPH.LogError("❌ [TTS Simple] No hay mensaje para leer");
                return false;
            }

            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            // PASO 2: Preparar el mensaje para enviarlo
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            string mensajeSeguro = PrepararMensajeParaJSON(mensaje);
            string json = "{\"text\":\"" + mensajeSeguro + "\"}";

            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            // PASO 3: Enviar al servidor de Nopolo
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            bool exito = EnviarANopolo(json);
            
            if (exito)
            {
                CPH.LogInfo("✅ [TTS Simple] Mensaje enviado: " + mensaje);
                return true;
            }
            else
            {
                CPH.LogWarn("⚠️ [TTS Simple] No se pudo enviar el mensaje");
                return false;
            }
        }
        catch (Exception ex)
        {
            CPH.LogError("❌ [TTS Simple] Error: " + ex.Message);
            return false;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // FUNCIONES AUXILIARES (No es necesario modificar nada aquí)
    // ═══════════════════════════════════════════════════════════════════════
    
    /// <summary>
    /// Convierte el texto a un formato seguro para JSON
    /// (Reemplaza comillas y caracteres especiales)
    /// </summary>
    private string PrepararMensajeParaJSON(string texto)
    {
        return texto
            .Replace("\\", "\\\\")  // Barra invertida
            .Replace("\"", "\\\"")  // Comillas dobles
            .Replace("\n", "\\n")   // Salto de línea
            .Replace("\r", "\\r")   // Retorno de carro
            .Replace("\t", "\\t");  // Tabulación
    }

    /// <summary>
    /// Envía el mensaje al servidor de Nopolo
    /// </summary>
    private bool EnviarANopolo(string json)
    {
        try
        {
            // Configuración del servidor
            string servidor = "127.0.0.1";  // localhost
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
            CPH.LogError("❌ [TTS Simple] No se pudo conectar a Nopolo.");
            CPH.LogError("   → ¿Está corriendo en http://localhost:8000?");
            return false;
        }
        catch (Exception ex)
        {
            CPH.LogError("❌ [TTS Simple] Error: " + ex.Message);
            return false;
        }
    }
}