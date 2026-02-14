// ═══════════════════════════════════════════════════════════════════════════
// 🎭 TTS_NopoloMultiVoz.cs
// ═══════════════════════════════════════════════════════════════════════════
// 
// ¿QUÉ HACE?
// ----------
// Envía texto con MÚLTIPLES VOCES y EFECTOS a Nopolo usando sintaxis especial.
// 
// SINTAXIS NOPOLO:
// ----------------
// • voz: texto                    → Usa una voz específica
// • voz.filtro: texto            → Voz + efecto de audio
// • voz.fondo: texto             → Voz + música de fondo
// • (sonido)                     → Reproduce un sonido
// • (sonido.filtro)              → Sonido + efecto de audio
// • (sonido.fondo)               → Sonido + música de fondo
// 
// EJEMPLOS:
// ---------
// homero: Hola mundo
// homero.r: Hola con eco (filtro r = reverb)
// homero.fa: Hola con fondo de ambiente
// (aplausos) dross: Gracias a todos
// (disparo.r) homero: Auch! con eco en el disparo
// (ambiente.fa) dross: Sonido con fondo de ambiente
// 
// FILTROS DISPONIBLES:
// --------------------
// r  = Eco/Reverberación
// p  = Llamada telefónica
// pu = Voz aguda (chipmunk)
// pd = Voz grave (monstruo)
// m  = Voz apagada
// a  = Robot
// l  = Saturada/distorsionada
//
// CONFIGURACIÓN:
// --------------
// 1. Servidor Nopolo debe estar corriendo en http://localhost:8000
// 2. Iniciar con: ./run_nopolo_full.sh (para habilitar API)
// 3. Variables de Streamer.bot:
//    - cleanedText o speakerMessage = Texto a sintetizar
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
    // ═══════════════════════════════════════════════════════════════════════
    // MÉTODO PRINCIPAL
    // ═══════════════════════════════════════════════════════════════════════
    public bool Execute()
    {
        try
        {
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            // PASO 1: Obtener el texto del mensaje
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            string texto = ObtenerTextoDelMensaje();
            
            // Si no hay texto, salir
            if (string.IsNullOrEmpty(texto))
            {
                CPH.LogWarn("❌ [Nopolo Multi-Voz] No hay texto para leer");
                return false;
            }
            
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            // PASO 2: Enviar al servidor Nopolo
            // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            bool exito = EnviarANopolo(texto);
            
            if (exito)
            {
                CPH.LogInfo("✅ [Nopolo Multi-Voz] Texto enviado: " + texto);
                return true;
            }
            else
            {
                CPH.LogWarn("⚠️ [Nopolo Multi-Voz] Error al enviar texto");
                return false;
            }
        }
        catch (Exception ex)
        {
            CPH.LogError("❌ [Nopolo Multi-Voz] Error: " + ex.Message);
            return false;
        }
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    // MÉTODOS AUXILIARES (NO MODIFICAR)
    // ═══════════════════════════════════════════════════════════════════════
    
    /// <summary>
    /// Obtiene el texto del mensaje desde Streamer.bot
    /// </summary>
    private string ObtenerTextoDelMensaje()
    {
        // Obtener el texto completo del comando
        if (CPH.TryGetArg("rawInput", out string texto))
        {
            return texto;
        }
        
        // No se encontró texto
        return null;
    }
    
    /// <summary>
    /// Envía el texto al servidor Nopolo usando el endpoint de multi-voz
    /// </summary>
    private bool EnviarANopolo(string texto)
    {
        try
        {
            // Configuración del servidor
            string servidor = "127.0.0.1";  // localhost
            int puerto = 8000;               // Puerto de Nopolo
            string ruta = "/api/tts/multivoice";  // Endpoint multi-voz
            
            // Crear JSON con el texto
            string textoEscapado = EscaparJSON(texto);
            string json = "{\"text\":\"" + textoEscapado + "\"}";
            
            // Enviar petición HTTP
            string respuesta = EnviarPeticionHTTP(servidor, puerto, ruta, json);
            
            // Verificar si fue exitoso
            if (respuesta.Contains("200 OK") || respuesta.Contains("\"success\":true"))
            {
                return true;
            }
            else if (respuesta.Contains("404"))
            {
                CPH.LogError("❌ [Nopolo Multi-Voz] Servidor no responde. ¿Iniciaste Nopolo con --with-api?");
                return false;
            }
            else
            {
                CPH.LogWarn("⚠️ [Nopolo Multi-Voz] Respuesta inesperada del servidor");
                CPH.LogDebug("Respuesta: " + respuesta.Substring(0, Math.Min(200, respuesta.Length)));
                return false;
            }
        }
        catch (SocketException)
        {
            CPH.LogError("❌ [Nopolo Multi-Voz] No se pudo conectar al servidor.");
            CPH.LogError("   → ¿Está Nopolo corriendo en http://localhost:8000?");
            CPH.LogError("   → Usa: ./run_nopolo_full.sh");
            return false;
        }
        catch (Exception ex)
        {
            CPH.LogError("❌ [Nopolo Multi-Voz] Error de conexión: " + ex.Message);
            return false;
        }
    }
    
    /// <summary>
    /// Escapa caracteres especiales para JSON
    /// </summary>
    private string EscaparJSON(string texto)
    {
        return texto
            .Replace("\\", "\\\\")  // Barra invertida
            .Replace("\"", "\\\"")  // Comillas
            .Replace("\n", "\\n")   // Nueva línea
            .Replace("\r", "\\r")   // Retorno de carro
            .Replace("\t", "\\t");  // Tabulación
    }
    
    /// <summary>
    /// Envía una petición HTTP POST al servidor
    /// </summary>
    private string EnviarPeticionHTTP(string servidor, int puerto, string ruta, string json)
    {
        // Convertir JSON a bytes UTF-8 (soporta tildes y emojis)
        byte[] cuerpoBytes = Encoding.UTF8.GetBytes(json);
        int longitudContenido = cuerpoBytes.Length;
        
        // Crear encabezados HTTP
        string encabezados = 
            "POST " + ruta + " HTTP/1.1\r\n" +
            "Host: " + servidor + ":" + puerto + "\r\n" +
            "Content-Type: application/json; charset=utf-8\r\n" +
            "Content-Length: " + longitudContenido + "\r\n" +
            "Connection: close\r\n" +
            "\r\n";

        // Conectar y enviar
        using (TcpClient cliente = new TcpClient())
        {
            cliente.SendTimeout = 5000;    // 5 segundos timeout envío
            cliente.ReceiveTimeout = 5000; // 5 segundos timeout recepción
            cliente.Connect(servidor, puerto);

            NetworkStream stream = cliente.GetStream();
            
            // Enviar encabezados (ASCII)
            byte[] encabezadosBytes = Encoding.ASCII.GetBytes(encabezados);
            stream.Write(encabezadosBytes, 0, encabezadosBytes.Length);
            
            // Enviar cuerpo JSON (UTF-8)
            stream.Write(cuerpoBytes, 0, cuerpoBytes.Length);
            stream.Flush();

            // Leer respuesta
            byte[] buffer = new byte[4096];
            int bytesLeidos = stream.Read(buffer, 0, buffer.Length);
            return Encoding.UTF8.GetString(buffer, 0, bytesLeidos);
        }
    }
}
