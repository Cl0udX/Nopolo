// ========================================
// TTS_EstadoCola.cs
// Verifica cuántos mensajes hay en cola
// Uso: !cola
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
            // GET request a /api/queue
            string response = SendHttpGet("127.0.0.1", 8000, "/api/queue");

            if (response.Contains("200 OK"))
            {
                // Extraer body
                int bodyStart = response.IndexOf("\r\n\r\n");
                if (bodyStart > 0)
                {
                    string body = response.Substring(bodyStart + 4);
                    
                    // Buscar queue_size en el JSON
                    if (body.Contains("\"queue_size\""))
                    {
                        // Extracción simple del número
                        int sizeStart = body.IndexOf("\"queue_size\":") + 13;
                        int sizeEnd = body.IndexOf(",", sizeStart);
                        if (sizeEnd < 0) sizeEnd = body.IndexOf("}", sizeStart);
                        
                        string queueSize = body.Substring(sizeStart, sizeEnd - sizeStart).Trim();
                        
                        CPH.SendMessage("📊 Mensajes en cola TTS: " + queueSize, true);
                        CPH.LogInfo("[TTS] Cola: " + queueSize + " mensajes");
                    }
                }
                return true;
            }
            else
            {
                CPH.LogError("[TTS] No se pudo obtener el estado de la cola");
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

            byte[] buffer = new byte[4096];
            int bytesRead = stream.Read(buffer, 0, buffer.Length);
            return Encoding.UTF8.GetString(buffer, 0, bytesRead);
        }
    }
}