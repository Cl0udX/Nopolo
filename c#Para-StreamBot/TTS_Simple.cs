// ========================================
// TTS_Simple.cs
// Envía texto básico al TTS con voz por defecto
// ========================================
// Referencias necesarias (agregar en Settings):
// - System.dll
// - System.Net.Sockets.dll
// 
// Ubicación típica: C:\Windows\Microsoft.NET\Framework64\vx.xxxx\...
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
            // Obtener el mensaje del comando !tts
            if (!CPH.TryGetArg("rawInput", out string message))
            {
                CPH.LogError("[TTS] No se encontró el mensaje");
                return false;
            }

            // Escapar caracteres especiales para JSON
            string escapedMessage = EscapeJson(message);

            // Crear JSON payload
            string jsonBody = "{\"text\":\"" + escapedMessage + "\"}";

            // Enviar request HTTP al servidor TTS
            string response = SendHttpPost("127.0.0.1", 8000, "/api/tts", jsonBody);

            // Verificar respuesta
            if (response.Contains("200 OK") || response.Contains("\"success\":true"))
            {
                CPH.LogInfo("[TTS] ✓ Enviado: " + message);
                return true;
            }
            else
            {
                CPH.LogWarn("[TTS] Respuesta inesperada del servidor");
                return false;
            }
        }
        catch (Exception ex)
        {
            CPH.LogError("[TTS] Error: " + ex.Message);
            return false;
        }
    }

    // Escapa caracteres especiales para JSON
    private string EscapeJson(string text)
    {
        return text
            .Replace("\\", "\\\\")
            .Replace("\"", "\\\"")
            .Replace("\n", "\\n")
            .Replace("\r", "\\r")
            .Replace("\t", "\\t");
    }

    // Envía HTTP POST request
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