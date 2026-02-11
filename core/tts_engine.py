from TTS.api import TTS
import sounddevice as sd
import numpy as np
import os
import torch

class TTSEngine:
    def __init__(self):
        self.tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False, gpu=False)
        self.speaker_wav = "assets/speech.wav"
        
        # 🔥 Calcular embeddings una sola vez
        print("Calculando embeddings del speaker...")
        self.gpt_cond_latent, self.speaker_embedding = self.tts.synthesizer.tts_model.get_conditioning_latents(
            audio_path=[self.speaker_wav]
        )
        print("Embeddings listos.")

    def synthesize(self, text):
        # Usar el método de bajo nivel del modelo directamente
        wav = self.tts.synthesizer.tts_model.inference(
            text=text,
            language="es",
            gpt_cond_latent=self.gpt_cond_latent,
            speaker_embedding=self.speaker_embedding,
            temperature=0.7,
            length_penalty=1.0,
            repetition_penalty=5.0,
            top_k=50,
            top_p=0.85,
        )
        
        # Convertir de tensor a numpy si es necesario
        if isinstance(wav, torch.Tensor):
            wav = wav.cpu().numpy()
        
        return wav

    def play(self, wav):
        if isinstance(wav, list):
            wav = np.array(wav)
        if isinstance(wav, dict) and 'wav' in wav:
            wav = wav['wav']
        if wav.ndim > 1:
            wav = wav[:,0]
        sd.play(wav, samplerate=24000)
        sd.wait()