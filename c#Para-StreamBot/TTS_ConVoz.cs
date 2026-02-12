// ========================================
// TTS_ConVoz.cs
// Permite usar diferentes voces configuradas
// Uso: !tts goku hola soy Goku
//      !tts homero hola soy Homero
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
            // Obtener mensaje completo
            if (!CPH.TryGetArg("rawInput", out string rawInput))
            {
                CPH.LogError("[TTS] No se encontró rawInput");
                return false;
            }

            // Separar voz y mensaje (formato: "goku hola mundo")
            string voiceId = "base_male"; // Voz por defecto
            string message = rawInput;

            string[] parts = rawInput.Split(new[] { ' ' }, 2);
            if (parts.Length >= 2)
            {
                // Primer palabra es la voz, resto es el mensaje
                voiceId = parts[0].ToLower();
                message = parts[1];
            }

            // Escapar JSON
            string escapedMessage = EscapeJson(message);

            // Crear JSON con voz específica
            string jsonBody = "{\"text\":\"" + escapedMessage + "\",\"voice_id\":\"" + voiceId + "\"}";

            // Enviar request
            string response = SendHttpPost("127.0.0.1", 8000, "/api/tts", jsonBody);

            // Verificar respuesta
            if (response.Contains("200 OK") || response.Contains("\"success\":true"))
            {
                CPH.LogInfo("[TTS] ✓ Voz: " + voiceId + " | Mensaje: " + message);
                return true;
            }
            else if (response.Contains("404"))
            {
                CPH.LogWarn("[TTS] Voz '" + voiceId + "' no encontrada. Usando voz por defecto.");
                // Reintentar con voz por defecto
                jsonBody = "{\"text\":\"" + escapedMessage + "\"}";
                response = SendHttpPost("127.0.0.1", 8000, "/api/tts", jsonBody);
                return response.Contains("200 OK");
            }
            else
            {
                CPH.LogWarn("[TTS] Error del servidor");
                return false;
            }
        }
        catch (Exception ex)
        {
            CPH.LogError("[TTS] Error: " + ex.Message);
            return false;
        }
    }

    private string EscapeJson(string text)
    {
        return text
            .Replace("\\", "\\\\")
            .Replace("\"", "\\\"")
            .Replace("\n", "\\n")
            .Replace("\r", "\\r")
            .Replace("\t", "\\t");
    }

    private string SendHttpPost(string host, int port, string path, string jsonBody)
    {
        string httpRequest = 
            "POST " + path + " HTTP/1.1\r\n" +
            "Host: " + host + ":" + port + "\r\n" +
            "Content-Type: application/json\r\n" +
            "Content-Length: " + jsonBody.Length + "\r\n" +
            "Connection: close\r\n" +
            "\r\n" +
            jsonBody;

        using (TcpClient client = new TcpClient())
        {
            client.SendTimeout = 5000;
            client.ReceiveTimeout = 5000;
            client.Connect(host, port);

            NetworkStream stream = client.GetStream();
            byte[] data = Encoding.UTF8.GetBytes(httpRequest);
            stream.Write(data, 0, data.Length);
            stream.Flush();

            byte[] buffer = new byte[4096];
            int bytesRead = stream.Read(buffer, 0, buffer.Length);
            return Encoding.UTF8.GetString(buffer, 0, bytesRead);
        }
    }
}