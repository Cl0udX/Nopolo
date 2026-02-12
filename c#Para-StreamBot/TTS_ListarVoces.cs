// ========================================
// TTS_ListarVoces.cs
// Lista todas las voces disponibles en el servidor
// Uso: !voces
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
            // Hacer GET request a /api/voices
            string response = SendHttpGet("127.0.0.1", 8000, "/api/voices");

            // Verificar respuesta
            if (response.Contains("200 OK"))
            {
                // Extraer el body JSON (después de los headers)
                int bodyStart = response.IndexOf("\r\n\r\n");
                if (bodyStart > 0)
                {
                    string body = response.Substring(bodyStart + 4);
                    
                    // Log simple del JSON (puedes parsearlo si quieres)
                    CPH.LogInfo("[TTS] Voces disponibles:");
                    CPH.LogInfo(body);
                    
                    // También puedes enviarlo al chat
                    CPH.SendMessage("Consulta los logs para ver las voces disponibles", true);
                }
                return true;
            }
            else
            {
                CPH.LogError("[TTS] No se pudieron obtener las voces");
                return false;
            }
        }
        catch (Exception ex)
        {
            CPH.LogError("[TTS] Error: " + ex.Message);
            return false;
        }
    }

    private string SendHttpGet(string host, int port, string path)
    {
        string httpRequest = 
            "GET " + path + " HTTP/1.1\r\n" +
            "Host: " + host + ":" + port + "\r\n" +
            "Connection: close\r\n" +
            "\r\n";

        using (TcpClient client = new TcpClient())
        {
            client.SendTimeout = 5000;
            client.ReceiveTimeout = 5000;
            client.Connect(host, port);

            NetworkStream stream = client.GetStream();
            byte[] data = Encoding.UTF8.GetBytes(httpRequest);
            stream.Write(data, 0, data.Length);
            stream.Flush();

            byte[] buffer = new byte[8192];
            int bytesRead = stream.Read(buffer, 0, buffer.Length);
            return Encoding.UTF8.GetString(buffer, 0, bytesRead);
        }
    }
}