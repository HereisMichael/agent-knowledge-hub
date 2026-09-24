import { useCallback, useEffect, useRef, useState } from "react";

interface SpeechRecognitionResult {
  transcript: string;
  isListening: boolean;
  supported: boolean;
  error: string | null;
  start: () => void;
  stop: () => void;
  reset: () => void;
}

interface SR {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>>; resultIndex: number }) => void) | null;
  onerror: ((e: { error?: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

interface SRConstructor {
  new (): SR;
}

function getSRClass(): SRConstructor | null {
  const w = window as unknown as { webkitSpeechRecognition?: SRConstructor; SpeechRecognition?: SRConstructor };
  return w.webkitSpeechRecognition ?? w.SpeechRecognition ?? null;
}

export function useSpeechRecognition(lang = "zh-CN"): SpeechRecognitionResult {
  const SRClass = getSRClass();
  const supported = SRClass !== null;
  const [transcript, setTranscript] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recRef = useRef<SR | null>(null);

  const start = useCallback(() => {
    if (!SRClass) {
      setError("当前浏览器不支持语音识别（建议用 Chrome/Edge）");
      return;
    }
    setError(null);
    setTranscript("");
    const rec = new SRClass();
    rec.lang = lang;
    rec.continuous = true;
    rec.interimResults = true;
    rec.onresult = (e) => {
      let text = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        text += e.results[i][0].transcript;
      }
      setTranscript(text);
    };
    rec.onerror = (e) => setError(e.error ?? "识别失败");
    rec.onend = () => setIsListening(false);
    recRef.current = rec;
    try {
      rec.start();
      setIsListening(true);
    } catch (err) {
      setError(String(err));
    }
  }, [SRClass, lang]);

  const stop = useCallback(() => {
    recRef.current?.stop();
    setIsListening(false);
  }, []);

  const reset = useCallback(() => {
    setTranscript("");
    setError(null);
  }, []);

  useEffect(() => {
    return () => {
      recRef.current?.stop();
    };
  }, []);

  return { transcript, isListening, supported, error, start, stop, reset };
}