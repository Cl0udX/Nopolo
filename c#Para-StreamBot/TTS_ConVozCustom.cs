// ========================================
// TTS_Nopolo.cs
// Envía el TTS a Nopolo usando tu estructura existente
// Usa: cleanedText (texto) y voiceToUse (voz)
// ========================================
// Referencias: System.dll, System.Net.Sockets.dll
// ========================================

using System;
using System.Net.Sockets;
using System.Text;

public class CPHInline
{
    public bool Execute()
    {
        try
        {
            string text = "";
            string voiceId = "";
            
            // Obtener texto de cleanedText
            if (args.ContainsKey("cleanedText"))
            {
                text = args["cleanedText"].ToString();
            }
            else if (args.ContainsKey("speakerMessage"))
            {
                text = args["speakerMessage"].ToString();
            }
            
            // Validar que tenemos texto
            if (string.IsNullOrEmpty(text))
            {
                CPH.LogWarn("[TTS Nopolo] No hay texto para leer");
                return false;
            }
            
            // Obtener voz de variable global voiceToUse
            voiceId = CPH.GetGlobalVar<string>("voiceToUse", false);
            String[] array = voiceId.Split('-');
            voiceId = array[1];
            
            // Si voiceToUse está vacía, usar voz por defecto
            if (string.IsNullOrEmpty(voiceId))
            {
                voiceId = "base_male"; // Voz por defecto de Nopolo
                CPH.LogInfo("[TTS Nopolo] Usando voz por defecto: " + voiceId);
            }
            
            // Escapar JSON
            string escapedMessage = EscapeJson(text);
            
            // Crear JSON con voz específica
            string jsonBody = "{\"text\":\"" + escapedMessage + "\",\"voice_id\":\"" + voiceId + "\"}";
            
            // Enviar request al servidor Nopolo
            string response = SendHttpPost("127.0.0.1", 8000, "/api/tts", jsonBody);
            
            // Verificar respuesta
            if (response.Contains("200 OK") || response.Contains("\"success\":true"))
            {
                CPH.LogInfo("[TTS Nopolo] ✓ Voz: " + voiceId + " | Mensaje: " + text);
                return true;
            }
            else if (response.Contains("404"))
            {
                CPH.LogWarn("[TTS Nopolo] Voz '" + voiceId + "' no encontrada. Usando voz por defecto.");
                // Reintentar con voz por defecto sin voice_id
                jsonBody = "{\"text\":\"" + escapedMessage + "\"}";
                response = SendHttpPost("127.0.0.1", 8000, "/api/tts", jsonBody);
                return response.Contains("200 OK");
            }
            else
            {
                CPH.LogWarn("[TTS Nopolo] Error del servidor");
                CPH.LogDebug("[TTS Nopolo] Respuesta: " + response.Substring(0, Math.Min(200, response.Length)));
                return false;
            }
        }
        catch (SocketException ex)
        {
            CPH.LogError("[TTS Nopolo] No se pudo conectar al servidor. ¿Está corriendo en http://localhost:8000?");
            CPH.LogError("[TTS Nopolo] Error: " + ex.Message);
            return false;
        }
        catch (Exception ex)
        {
            CPH.LogError("[TTS Nopolo] Error: " + ex.Message);
            return false;
        }
    }
    
    private string EscapeJson(string text)
    {
        // Escapar caracteres especiales JSON (Unicode se maneja automáticamente con UTF-8)
        return text
            .Replace("\\", "\\\\")
            .Replace("\"", "\\\"")
            .Replace("\n", "\\n")
            .Replace("\r", "\\r")
            .Replace("\t", "\\t")
            .Replace("\b", "\\b")
            .Replace("\f", "\\f");
    }
    
    private string SendHttpPost(string host, int port, string path, string jsonBody)
    {
        // IMPORTANTE: Calcular Content-Length en bytes UTF-8, no en caracteres
        // Esto maneja correctamente tildes, emojis y caracteres de otros idiomas
        byte[] bodyBytes = Encoding.UTF8.GetBytes(jsonBody);
        int contentLength = bodyBytes.Length;
        
        // Headers en ASCII
        string headers = 
            "POST " + path + " HTTP/1.1\r\n" +
            "Host: " + host + ":" + port + "\r\n" +
            "Content-Type: application/json; charset=utf-8\r\n" +
            "Content-Length: " + contentLength + "\r\n" +
            "Connection: close\r\n" +
            "\r\n";

        using (TcpClient client = new TcpClient())
        {
            client.SendTimeout = 5000;
            client.ReceiveTimeout = 5000;
            client.Connect(host, port);

            NetworkStream stream = client.GetStream();
            
            // Enviar headers (ASCII)
            byte[] headerBytes = Encoding.ASCII.GetBytes(headers);
            stream.Write(headerBytes, 0, headerBytes.Length);
            
            // Enviar body (UTF-8)
            stream.Write(bodyBytes, 0, bodyBytes.Length);
            stream.Flush();

            byte[] buffer = new byte[4096];
            int bytesRead = stream.Read(buffer, 0, buffer.Length);
            return Encoding.UTF8.GetString(buffer, 0, bytesRead);
        }
    }
}
