'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Shield, Smile, Sparkles, Camera, RotateCcw } from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { LoadingButton } from '@/components/ui/spinner';
import { getApiBase } from '@/lib/config';
import { apiClient } from '@/lib/api-client';

export const dynamic = 'force-dynamic';

const tabs = [
  { key: 'password', label: 'Mot de passe' },
  { key: 'facial', label: 'Reconnaissance faciale' },
];

export default function LoginPage() {
  const [mode, setMode] = useState<'password' | 'facial'>('password');
  const { login, loginWithToken } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [photo, setPhoto] = useState<string | null>(null);
  const [webcamReady, setWebcamReady] = useState(false);
  const apiBase = getApiBase();

  useEffect(() => {
    let cancelled = false;

    const stopStream = () => {
      try {
        streamRef.current?.getTracks?.().forEach((t) => t.stop());
      } catch {
        // ignore
      }
      streamRef.current = null;
      if (videoRef.current) {
        try {
          (videoRef.current as any).srcObject = null;
        } catch {
          // ignore
        }
      }
    };

    const startStream = async () => {
      setWebcamReady(false);
      if (mode !== 'facial' || photo) return;
      if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
        setError('Caméra non supportée par ce navigateur.');
        return;
      }

      // Prewarm the backend face engine to avoid cold-start latency
      try {
        await apiClient('/api/auth/login/facial/prewarm', { method: 'GET' });
      } catch {
        // Non-blocking: continue even if prewarm fails
      }

      const waitForVideoReady = async (video: HTMLVideoElement, timeoutMs: number) => {
        if (video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0) return true;
        await Promise.race([
          new Promise<void>((resolve) => {
            const onReady = () => resolve();
            video.addEventListener('loadeddata', onReady, { once: true });
            video.addEventListener('loadedmetadata', onReady, { once: true });
            video.addEventListener('canplay', onReady, { once: true });
          }),
          new Promise<void>((resolve) => setTimeout(resolve, timeoutMs)),
        ]);
        return video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0;
      };

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 480, height: 360, facingMode: 'user' },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          (videoRef.current as any).srcObject = stream;
          await videoRef.current.play().catch(() => undefined);
          const ready = await waitForVideoReady(videoRef.current, 2000);
          if (!cancelled && ready) {
            setWebcamReady(true);
            setError(null);
          }
        }
      } catch {
        setError('Caméra refusée. Vérifiez les permissions.');
      }
    };

    startStream();
    return () => {
      cancelled = true;
      stopStream();
    };
  }, [mode, photo]);

  const handleCapture = async () => {
    try {
      const canvas = canvasRef.current;
      if (!canvas) {
        setError('Canvas non disponible.');
        return;
      }

      const video = videoRef.current;
      if (!video) {
        setError('Vidéo non prête. Attendez quelques secondes.');
        return;
      }

      const ensureVideoReady = async (timeoutMs: number) => {
        if (video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0) return true;

        await Promise.race([
          new Promise<void>((resolve) => {
            const onReady = () => resolve();
            video.addEventListener('loadeddata', onReady, { once: true });
            video.addEventListener('loadedmetadata', onReady, { once: true });
          }),
          new Promise<void>((resolve) => setTimeout(resolve, timeoutMs)),
        ]);

        return video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0;
      };

      const ok = await ensureVideoReady(1500);
      if (!ok) {
        setError('Vidéo non prête. Attendez quelques secondes.');
        return;
      }

      const ctx = canvas.getContext('2d');
      if (!ctx) {
        setError('Erreur contexte canvas.');
        return;
      }

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0, video.videoWidth, video.videoHeight);
      
      // Encode at lower quality to reduce payload and speed up upload
      const b64 = canvas.toDataURL('image/jpeg', 0.7);
      if (b64 && b64.length > 100) {
        setPhoto(b64);
        setError(null);
      } else {
        setError('Capture vide. Réessayez.');
      }
    } catch (e) {
      setError('Erreur capture: ' + String(e).slice(0, 50));
    }
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === 'password') {
        await login(email, password);
      } else {
        if (!email.trim()) {
          throw new Error('Adresse e-mail requise.');
        }
        if (!photo) {
          throw new Error('Veuillez capturer votre visage.');
        }
        // First attempt: default threshold
        const attempt = async (thr: number) =>
          apiClient<any>('/api/auth/login/facial', {
            method: 'POST',
            data: {
              email,
              image_base64: photo,
              confidence_threshold: thr,
            },
          });

        let data = await attempt(0.62);
        if (!data?.access_token) {
          // If face not recognized, retry once with slightly lower threshold
          // to compensate for webcam variance.
          try {
            data = await attempt(0.58);
          } catch (retryErr: any) {
            const detail = retryErr?.response?.data?.detail;
            if (detail && typeof detail === 'string') {
              setError(detail === 'Face not recognized'
                ? "Visage non reconnu. Réessayez en vous rapprochant et avec un bon éclairage."
                : detail);
            } else {
              setError(retryErr?.message ?? 'Erreur connexion');
            }
            throw retryErr;
          }
        }
        if (data?.access_token) {
          await loginWithToken(String(data.access_token));
          return;
        }
        throw new Error('Login failed');
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      // Map 401s to clearer messages when detail is missing
      const status = err?.response?.status;
      if (!detail && status === 401) {
        setError('Non autorisé: visage non reconnu ou utilisateur introuvable.');
      } else {
        setError(detail || (err?.message ?? 'Erreur connexion'));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen px-4 py-10">
      <div className="mx-auto max-w-5xl rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-8 shadow-2xl">
        <div className="flex flex-col-reverse gap-6 md:flex-row">
          <div className="flex-1 space-y-6">
            <div className="flex items-center gap-3 text-amber-300">
              <Sparkles size={18} /> <span className="text-sm">Bienvenue</span>
            </div>
            <div>
              <h1 className="text-3xl font-bold">Smart Presence AI</h1>
              <p className="text-white/60">
                Choisissez votre méthode : email + mot de passe ou email + visage.
              </p>
            </div>

            <div className="flex gap-2 rounded-full bg-white/5 p-1 text-sm">
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setMode(tab.key as 'password' | 'facial')}
                  className={`flex-1 rounded-full px-4 py-2 transition ${mode === tab.key ? 'bg-gradient-to-r from-primary-500 to-amber-500 text-white' : 'text-white/70'}`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <form className="space-y-4" onSubmit={handleSubmit}>
              <div>
                <label className="text-sm text-white/70">Adresse e-mail</label>
                <input
                  type="email"
                  placeholder="vous@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                  required
                />
              </div>

              {mode === 'password' ? (
                <div>
                  <label className="text-sm text-white/70">Mot de passe</label>
                  <input
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                    required
                  />
                  <div className="mt-2 flex justify-between text-xs text-white/60">
                    <label className="inline-flex items-center gap-2">
                      <input type="checkbox" className="rounded border-white/20 bg-transparent" />
                      Se souvenir de moi
                    </label>
                    <a className="text-amber-300" href="#">
                      Mot de passe oublié ?
                    </a>
                  </div>
                </div>
              ) : null}

              {error && <div className="rounded bg-rose-900/30 border border-rose-500/30 px-3 py-2 text-sm text-rose-300">{error}</div>}
              <LoadingButton type="submit" className="btn-primary w-full" loading={loading}>
                Se connecter
              </LoadingButton>
            </form>

            <p className="text-xs text-white/60">
              En vous connectant, vous acceptez les Conditions et la Politique de confidentialité.
            </p>
          </div>

          <div className="card flex-1 space-y-4 border-white/10 bg-gradient-to-br from-white/5 to-primary-500/5">
            <div className="flex items-center gap-2 text-sm text-amber-300">
              <Camera size={16} /> Facial login optionnel
            </div>
            {mode === 'facial' ? (
              <>
                <p className="text-white/70">
                  Capturez votre visage pour vous identifier. Assurez-vous que votre visage est bien
                  éclairé et visible.
                </p>
                <div className="space-y-3">
                  <div className="overflow-hidden rounded-xl border-2 border-primary-500/50 bg-black">
                    {photo ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={photo} alt="Capture" className="w-full aspect-video object-cover" />
                    ) : (
                      <div className="relative aspect-video w-full bg-black">
                        <video
                          ref={videoRef}
                          className="w-full h-full"
                          autoPlay
                          playsInline
                          muted
                          onLoadedMetadata={() => {
                            setWebcamReady(true);
                            setError(null);
                          }}
                          onLoadedData={() => {
                            setWebcamReady(true);
                            setError(null);
                          }}
                          onCanPlay={() => {
                            setWebcamReady(true);
                            setError(null);
                          }}
                        />
                        {!webcamReady && (
                          <div className="absolute inset-0 flex items-center justify-center bg-black/80">
                            <p className="text-sm text-white text-center">
                              Caméra chargement...<br />
                              <span className="text-xs text-white/60">Cliquez pour autoriser</span>
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  <canvas ref={canvasRef} className="hidden" />
                  
                  <div className="flex gap-2">
                    {!photo ? (
                      <button
                        type="button"
                        disabled={!webcamReady || !email.trim()}
                        onClick={handleCapture}
                        className="btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {!email.trim() ? 'Entrez votre email' : webcamReady ? 'Capturer' : 'Chargement...'}
                      </button>
                    ) : (
                      <>
                        <button
                          type="button"
                          onClick={() => {
                            setPhoto(null);
                            setWebcamReady(false);
                          }}
                          className="btn-outline flex-1"
                        >
                          <RotateCcw size={14} className="mr-1" /> Reprendre
                        </button>
                        <LoadingButton
                          type="button"
                          className="btn-primary flex-1"
                          loading={loading}
                          onClick={handleSubmit}
                          disabled={!email.trim() || loading}
                        >
                          Valider
                        </LoadingButton>
                      </>
                    )}
                  </div>

                  <div className="flex gap-2 text-xs text-white/60">
                    <Badge icon={<Shield size={14} />}>Seuil 0.62</Badge>
                    <Badge icon={<Smile size={14} />}>Anti-spoof basique</Badge>
                  </div>
                </div>
              </>
            ) : (
              <>
                <p className="text-white/70">
                  L'authentification faciale est utilisée uniquement pour la connexion. Le pointage
                  de présence reste manuel ou validé par le formateur.
                </p>
                <div className="rounded-lg border border-white/5 bg-white/5 p-4 text-sm text-white/70">
                  <p className="font-semibold text-white">Flux simple</p>
                  <ol className="mt-2 list-decimal space-y-1 pl-4">
                    <li>Email</li>
                    <li>Choix mot de passe ou visage</li>
                    <li>Validation &lt; 2s, token JWT</li>
                  </ol>
                </div>
              </>
            )}
            <Link href="/" className="text-sm text-amber-300">
              Retour à l'accueil
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function Badge({ children, icon }: { children: React.ReactNode; icon: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1">
      {icon} {children}
    </span>
  );
}
