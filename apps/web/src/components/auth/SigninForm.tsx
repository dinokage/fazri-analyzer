'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { ArrowLeft, Eye, EyeOff, Lock, Shield, User } from 'lucide-react';
import { authClient } from '@/lib/auth-client';
import { useRouter } from 'next/navigation';
import { useRef, useState, useEffect } from 'react';
import { toast } from 'sonner';

const slideVariants = {
  enter: (d: number) => ({ x: d > 0 ? '3%' : '-3%', opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (d: number) => ({
    x: d > 0 ? '-3%' : '3%',
    opacity: 0,
    transition: { duration: 0.18, ease: 'easeIn' as const },
  }),
};

const features = [
  { title: 'Behavioral intelligence', desc: 'Detect anomalies before they become incidents' },
  { title: 'Graph-based entity resolution', desc: 'Connect the dots across your entire campus' },
  { title: 'Real-time alerting', desc: 'Sub-second anomaly detection and notification' },
];

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  );
}

type Step = "username" | "password";

export default function SigninPage() {
  const router = useRouter();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [hidePassword, setHidePassword] = useState(true);
  const [step, setStep] = useState<Step>("username");
  const [checkingUsername, setCheckingUsername] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [direction, setDirection] = useState<1 | -1>(1);
  const [activeFeature, setActiveFeature] = useState(0);
  const passwordRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const interval = setInterval(() => setActiveFeature(p => (p + 1) % features.length), 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (step === "password") {
      setTimeout(() => {
        passwordRef.current?.focus();
        passwordRef.current?.classList.add('ring-2', 'ring-neutral-400', 'dark:ring-neutral-400');
        setTimeout(() => {
          passwordRef.current?.classList.remove('ring-2', 'ring-neutral-400', 'dark:ring-neutral-400');
        }, 800);
      }, 420);
    }
  }, [step]);

  const handleUsernameContinue = async () => {
    const normalized = username.trim();
    if (!normalized) return;
    setUsername(normalized);
    setCheckingUsername(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_AUTH_SERVICE_URL}/api/check-username`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: normalized }),
      });
      if (!res.ok) {
        toast.error('Auth service error. Please try again later.', { id: 'auth-service-error' });
        setCheckingUsername(false);
        return;
      }
      const data = await res.json();
      if (!data.exists) {
        toast.error('No account found with that username.');
        setCheckingUsername(false);
        return;
      }
      setDirection(1);
      setStep('password');
    } catch {
      toast.error('Auth service is unreachable. Please try again later.', { id: 'auth-unreachable' });
    }
    setCheckingUsername(false);
  };

  const goBack = () => {
    setDirection(-1);
    setStep('username');
    setPassword('');
  };

  const login = async () => {
    setSubmitted(true);
    try {
      const { error } = await authClient.signIn.username({
        username,
        password,
        rememberMe: true,
      });
      if (error) {
        if (error.status === 429) {
          toast.error('Too many attempts. Please try again later.');
        } else if (error.status === 401 || (error as Record<string, unknown>).code === 'INVALID_PASSWORD') {
          toast.error('Invalid password. Please try again.');
        } else {
          toast.error('Authentication failed. Please try again.');
          console.error('Sign-in error:', error);
        }
        setSubmitted(false);
        return;
      }
      router.push('/dashboard');
    } catch {
      toast.error('Auth service is unreachable. Please try again later.', { id: 'auth-unreachable' });
      setSubmitted(false);
    }
  };

  const inputClass =
    'block w-full rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800/60 px-3.5 py-2.5 text-sm text-neutral-900 dark:text-neutral-50 placeholder-neutral-400 dark:placeholder-neutral-500 transition-all duration-150 focus:border-neutral-700 dark:focus:border-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-200 dark:focus:ring-neutral-700';

  return (
    <div className="flex min-h-screen bg-white dark:bg-neutral-950">
      {/* Left: form panel */}
      <div className="flex w-full flex-col justify-center px-6 py-12 lg:w-[52%] xl:px-20">
        <div className="mx-auto w-full max-w-sm">

          {/* Logo */}
          <div className="mb-8 flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-neutral-900 dark:bg-neutral-50">
              <Shield className="h-4 w-4 text-white dark:text-neutral-900" />
            </div>
            <span className="text-lg font-semibold tracking-tight text-neutral-900 dark:text-neutral-50">
              Fazri Analyzer
            </span>
          </div>

          {/* Sliding content */}
          <div className="overflow-hidden">
            <AnimatePresence mode="wait" initial={false} custom={direction}>
              {step === 'username' && (
                <motion.div
                  key="username"
                  custom={-direction}
                  variants={slideVariants}
                  initial="enter"
                  animate="center"
                  exit="exit"
                  transition={{ duration: 0.32, ease: 'easeOut' }}
                >
                  <h1 className="text-2xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-50">
                    Welcome back
                  </h1>
                  <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                    Enter your username to sign in
                  </p>

                  <div className="mt-7 space-y-4">
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
                        Username
                      </label>
                      <div className="relative">
                        <div className="pointer-events-none absolute inset-y-0 left-3.5 flex items-center">
                          <User size={14} className="text-neutral-400 dark:text-neutral-500" />
                        </div>
                        <input
                          type="text"
                          value={username}
                          onChange={e => setUsername(e.target.value)}
                          onKeyDown={e => {
                            if (e.key === 'Enter' && username.trim()) {
                              e.preventDefault();
                              handleUsernameContinue();
                            }
                          }}
                          placeholder="your-username"
                          className={`${inputClass} pl-9`}
                          autoComplete="username"
                          autoFocus
                        />
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={handleUsernameContinue}
                      disabled={checkingUsername || !username.trim()}
                      className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg bg-neutral-900 dark:bg-neutral-50 px-4 py-2.5 text-sm font-semibold text-white dark:text-neutral-900 transition-all duration-200 hover:bg-neutral-800 dark:hover:bg-neutral-200 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {checkingUsername ? <><Spinner /><span>Checking…</span></> : 'Continue'}
                    </button>
                  </div>
                </motion.div>
              )}

              {step === 'password' && (
                <motion.div
                  key="password"
                  custom={direction}
                  variants={slideVariants}
                  initial="enter"
                  animate="center"
                  exit="exit"
                  transition={{ duration: 0.32, ease: 'easeOut' }}
                >
                  <h1 className="text-2xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-50">
                    Enter password
                  </h1>
                  <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                    Signing in as <span className="font-medium text-neutral-700 dark:text-neutral-300">{username}</span>
                  </p>
                  <button
                    type="button"
                    onClick={goBack}
                    className="mt-2 inline-flex cursor-pointer items-center gap-1.5 text-sm text-neutral-400 transition-colors hover:text-neutral-700 dark:text-neutral-500 dark:hover:text-neutral-300"
                  >
                    <ArrowLeft size={13} />
                    Change username
                  </button>

                  <div className="mt-6 space-y-4">
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
                        Password
                      </label>
                      <div className="relative">
                        <div className="pointer-events-none absolute inset-y-0 left-3.5 flex items-center">
                          <Lock size={14} className="text-neutral-400 dark:text-neutral-500" />
                        </div>
                        <input
                          type={hidePassword ? 'password' : 'text'}
                          placeholder={hidePassword ? '••••••••••••' : 'Password'}
                          value={password}
                          onChange={e => setPassword(e.target.value)}
                          onKeyDown={e => {
                            if (e.key === 'Enter' && password.trim()) {
                              e.preventDefault();
                              login();
                            }
                          }}
                          autoComplete="current-password"
                          className={`${inputClass} pl-9 pr-10`}
                          ref={passwordRef}
                        />
                        <button
                          type="button"
                          onClick={() => setHidePassword(!hidePassword)}
                          className="absolute inset-y-0 right-3 flex cursor-pointer items-center text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors"
                          aria-label={hidePassword ? 'Show password' : 'Hide password'}
                        >
                          {hidePassword ? <EyeOff size={15} /> : <Eye size={15} />}
                        </button>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={login}
                      disabled={submitted || !password.trim()}
                      className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg bg-neutral-900 dark:bg-neutral-50 px-4 py-2.5 text-sm font-semibold text-white dark:text-neutral-900 transition-all duration-200 hover:bg-neutral-800 dark:hover:bg-neutral-200 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {submitted ? <><Spinner /><span>Signing in…</span></> : 'Sign in'}
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

        </div>
      </div>

      {/* Right: decorative panel */}
      <div className="relative hidden overflow-hidden bg-neutral-900 lg:flex lg:w-[48%] flex-col items-center justify-center">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.07) 1px, transparent 1px)',
            backgroundSize: '28px 28px',
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-br from-neutral-900 via-transparent to-neutral-900/80" />

        <div className="relative z-10 px-14 text-center max-w-md">
          <div className="mb-6 inline-flex rounded-xl bg-white/10 p-3.5">
            <Shield className="h-7 w-7 text-white" strokeWidth={2} />
          </div>
          <h2 className="text-3xl font-semibold tracking-tight text-white">
            Campus security intelligence, unified
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-neutral-400">
            Detect anomalies, resolve entities, and monitor your campus in real-time — from one platform.
          </p>

          <div className="mt-10 text-left">
            <div className="h-16 overflow-hidden">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeFeature}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -16 }}
                  transition={{ duration: 0.35, ease: [0.32, 0.72, 0, 1] }}
                  className="flex items-start gap-3.5"
                >
                  <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/15">
                    <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">{features[activeFeature].title}</p>
                    <p className="mt-0.5 text-xs text-neutral-400">{features[activeFeature].desc}</p>
                  </div>
                </motion.div>
              </AnimatePresence>
            </div>
            <div className="mt-4 flex gap-1.5">
              {features.map((_, i) => (
                <div key={i} className="relative h-px flex-1 overflow-hidden rounded-full bg-white/10">
                  {i === activeFeature && (
                    <motion.div
                      key={activeFeature}
                      className="absolute inset-y-0 left-0 rounded-full bg-white/50"
                      initial={{ width: '0%' }}
                      animate={{ width: '100%' }}
                      transition={{ duration: 3, ease: 'linear' }}
                    />
                  )}
                  {i < activeFeature && (
                    <div className="absolute inset-0 rounded-full bg-white/30" />
                  )}
                </div>
              ))}
            </div>

            <div className="mt-8 grid grid-cols-3 gap-3">
              {[
                { value: '99.9%', label: 'Uptime' },
                { value: '< 2s', label: 'Alert latency' },
                { value: '24/7', label: 'Monitoring' },
              ].map((stat, i) => (
                <motion.div
                  key={stat.value}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 0.3 + i * 0.08 }}
                  className="rounded-xl bg-white/5 px-3 py-3 text-center"
                >
                  <p className="text-base font-semibold text-white">{stat.value}</p>
                  <p className="mt-0.5 text-[11px] text-neutral-500">{stat.label}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
