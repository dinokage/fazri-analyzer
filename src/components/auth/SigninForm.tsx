"use client";
import { signIn } from "next-auth/react";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Card,
  CardContent,
  CardHeader,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Loader2, Shield, Eye, EyeOff, Lock, User, ArrowRight } from "lucide-react";

export default function SigninPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [step, setStep] = useState<"username" | "password" | "loading" | "success">("username");
  // userExists state is no longer strictly needed if we just transition steps,
  // but we'll keep it for clarity if the UI relies on it.
  const [userExists, setUserExists] = useState(false);

  const handleUsernameSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) {
      setError("Please enter your username");
      return;
    }

    setError("");
    setLoading(true);

    try {
      // --- CHANGED LOGIC HERE ---
      // Check if user exists in your database via a custom API endpoint
      const response = await fetch("/api/check", { // <<< Changed endpoint
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim() }),
      });

      const data = await response.json();

      if (data.exists) {
        setUserExists(true); // User exists, proceed to password step
        console.log(userExists)
        setStep("password");
      } else {
        setError("Username not found. Please check your username and try again.");
      }
    } catch (error) {
      console.error("Username check error:", error); // Log the actual error for debugging
      setError(error instanceof Error ? error.message : "An unexpected error occurred during username check.");
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    setStep("loading"); // Show loading animation before signIn

    try {
      const res = await signIn("credentials", {
        // NextAuth.js Credentials provider expects 'entity_id' for your setup
        // 'username' here maps to the 'entity_id' in your auth.ts
        entity_id: username, // <<< Use 'entity_id' as defined in your auth.ts CredentialsProvider
        password: password,
        redirect: false, // Prevents automatic redirect on success/failure
      });

      if (res?.error) {
        // NextAuth.js error messages can be generic, customize as needed
        // For security, avoid giving too much detail if password or username failed
        setError("Invalid password. Please try again.");
        setStep("password"); // Go back to password step on error
      } else {
        // Authentication successful
        setStep("success"); // Show success animation
        setTimeout(() => {
          // You might want to get `res.url` or `router.push('/')` for more robust redirection
          window.location.href = "/dashboard"; // Redirect to home page
        }, 2000);
      }
    } catch (error) {
      console.error("Sign-in error:", error); // Log the actual error for debugging
      setError(error instanceof Error ? error.message : "An unexpected error occurred during sign-in.");
      setStep("password"); // Go back to password step on unexpected error
    } finally {
      setLoading(false); // Ensure loading state is reset
    }
  };

  const handleBackToUsername = () => {
    setStep("username");
    setPassword("");
    setError("");
    setUserExists(false); // Reset userExists state
  };

  return (
    <main className="min-h-screen flex items-center justify-center p-4 transition-all duration-500 relative overflow-hidden">


      <div className="w-full max-w-sm relative z-10">
        <Card className="backdrop-blur-sm bg-white/90 dark:bg-black/90 shadow-2xl border-0 ring-1 ring-slate-200/50 dark:ring-gray-800/50 transition-all duration-300">
          <CardHeader className="text-center space-y-6 pb-8">
            {/* Logo/Icon */}
            <motion.div
              className="mx-auto w-20 h-20 bg-gradient-to-br from-blue-600 to-indigo-600 dark:from-blue-500 dark:to-indigo-500 rounded-2xl flex items-center justify-center shadow-lg"
              whileHover={{ scale: 1.05 }}
              transition={{ duration: 0.3 }}
            >
              <Shield className="w-10 h-10 text-white" />
            </motion.div>

            {/* Title */}
            <div className="space-y-2">
              <h1 className="text-[2.5rem] font-bold leading-[1.1] tracking-tight bg-gradient-to-r from-slate-900 to-slate-600 dark:from-white dark:to-slate-300 bg-clip-text text-transparent">
                Welcome Back
              </h1>
              <p className="text-[1.25rem] text-muted-foreground font-light">
                Sign in to access <span className="font-semibold text-blue-600 dark:text-blue-400">Fazri Analyzer</span>
              </p>
            </div>
          </CardHeader>

          <CardContent className="space-y-6">
            <AnimatePresence mode="wait">
              {step === "username" && (
                <motion.div
                  key="username-step"
                  initial={{ opacity: 0, x: -100 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 100 }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                  className="space-y-6"
                >
                  <form className="space-y-5" onSubmit={handleUsernameSubmit}>
                    {error && (
                      <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3 }}
                      >
                        <Alert variant="destructive">
                          <User className="w-4 h-4" />
                          <AlertTitle>Username Error</AlertTitle>
                          <AlertDescription>{error}</AlertDescription>
                        </Alert>
                      </motion.div>
                    )}

                    {/* Username Field */}
                    <div className="space-y-2">
                      <Label htmlFor="username" className="text-slate-700 dark:text-slate-300 font-medium">
                        Username
                      </Label>
                      <div className="relative rounded-full py-4 px-5 border border-border bg-transparent">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 mr-3">
                            <User className="h-5 w-5 text-muted-foreground" />
                          </div>
                          <Input
                            id="username"
                            type="text"
                            placeholder="Enter your username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            className="border-none bg-transparent focus:ring-0 focus-visible:ring-0 focus-visible:border-none px-0  placeholder:text-muted-foreground"
                            required
                            autoFocus
                            disabled={loading}
                          />
                          {username.trim() && (
                            <button
                              type="submit"
                              disabled={loading || !username.trim()}
                              className={`flex-shrink-0 ml-3 w-9 h-9 flex items-center justify-center rounded-full transition-all duration-300 group overflow-hidden ${
                                username.trim() && !loading
                                  ? "bg-foreground/10 hover:bg-foreground/20 cursor-pointer"
                                  : "bg-transparent cursor-not-allowed opacity-50"
                              }`}
                            >
                              {loading ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <span className="relative w-full h-full block overflow-hidden">
                                  <span className={`absolute inset-0 flex items-center justify-center transition-transform duration-300 ${
                                    username.trim() && !loading ? "group-hover:translate-x-full" : ""
                                  }`}>
                                    →
                                  </span>
                                  <span className={`absolute inset-0 flex items-center justify-center transition-transform duration-300 ${
                                    username.trim() && !loading ? "-translate-x-full group-hover:translate-x-0" : "-translate-x-full"
                                  }`}>
                                    →
                                  </span>
                                </span>
                              )}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Continue Button */}
                    <motion.div
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      transition={{ duration: 0.2 }}
                    >
                      <Button
                        type="submit"
                        disabled={loading || !username.trim()}
                        className="w-full h-12 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 dark:from-blue-500 dark:to-indigo-500 dark:hover:from-blue-600 dark:hover:to-indigo-600 text-white font-semibold rounded-full shadow-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed group"
                      >
                        <div className="flex items-center justify-center">
                          {loading ? (
                            <>
                              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                              <span>Checking username...</span>
                            </>
                          ) : (
                            <>
                              <User className="w-5 h-5 mr-2" />
                              <span>Continue</span>
                              <ArrowRight className="w-4 h-4 ml-2 transition-transform group-hover:translate-x-1" />
                            </>
                          )}
                        </div>
                      </Button>
                    </motion.div>
                  </form>

                  {/* Info Section */}
                  <div className="bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0">
                        <svg
                          className="w-5 h-5 text-blue-500 mt-0.5"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </div>
                      <div className="text-left">
                        <p className="text-sm text-blue-800 dark:text-blue-200 font-medium">
                          Secure Authentication
                        </p>
                        <p className="text-xs text-blue-600 dark:text-blue-300 mt-1">
                          Enter your username to continue to password verification
                        </p>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {step === "password" && (
                <motion.div
                  key="password-step"
                  initial={{ opacity: 0, x: -100 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 100 }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                  className="space-y-6"
                >
                  <form className="space-y-5" onSubmit={handlePasswordSubmit}>
                    {error && (
                      <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3 }}
                      >
                        <Alert variant="destructive">
                          <Lock className="w-4 h-4" />
                          <AlertTitle>Authentication Failed</AlertTitle>
                          <AlertDescription>{error}</AlertDescription>
                        </Alert>
                      </motion.div>
                    )}

                    {/* Username Display */}
                    <div className="space-y-2">
                      <Label className="text-slate-700 dark:text-slate-300 font-medium">
                        Username
                      </Label>
                      <div className="relative rounded-full py-4 px-5 border border-border bg-muted/50">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 mr-3">
                            <User className="h-5 w-5 text-muted-foreground" />
                          </div>
                          <span className="text-foreground font-medium">{username}</span>
                          <button
                            type="button"
                            onClick={handleBackToUsername}
                            className="flex-shrink-0 ml-auto text-muted-foreground hover:text-foreground transition-colors text-sm"
                          >
                            Change
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Password Field */}
                    <div className="space-y-2">
                      <Label htmlFor="password" className="text-slate-700 dark:text-slate-300 font-medium">
                        Password
                      </Label>
                      <div className="relative rounded-full py-4 px-5 border border-border bg-background">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 mr-3">
                            <Lock className="h-5 w-5 text-muted-foreground" />
                          </div>
                          <Input
                            id="password"
                            type={showPassword ? "text" : "password"}
                            placeholder="Enter your password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="border-none bg-background focus:ring-0 focus-visible:ring-0 focus-visible:border-none px-0 pr-10 text-foreground placeholder:text-muted-foreground"
                            required
                            autoFocus
                            autoComplete="off"
                            disabled={loading}
                          />
                          <button
                            type="button"
                            className="flex-shrink-0 ml-3 text-muted-foreground hover:text-foreground transition-colors duration-200"
                            onClick={() => setShowPassword(!showPassword)}
                          >
                            {showPassword ? (
                              <EyeOff className="h-5 w-5" />
                            ) : (
                              <Eye className="h-5 w-5" />
                            )}
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Submit Button */}
                    <div className="flex gap-3">
                      <motion.div
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        transition={{ duration: 0.2 }}
                        className="w-[30%]"
                      >
                        <Button
                          type="button"
                          onClick={handleBackToUsername}
                          variant="outline"
                          className="w-full h-12 rounded-full border-border hover:bg-muted"
                        >
                          Back
                        </Button>
                      </motion.div>

                      <motion.div
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        transition={{ duration: 0.2 }}
                        className="flex-1"
                      >
                        <Button
                          type="submit"
                          disabled={loading || !password.trim()}
                          className="w-full h-12 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 dark:from-blue-500 dark:to-indigo-500 dark:hover:from-blue-600 dark:hover:to-indigo-600 text-white font-semibold rounded-full shadow-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed group"
                        >
                          <div className="flex items-center justify-center">
                            {loading ? (
                              <>
                                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                                <span>Signing in...</span>
                              </>
                            ) : (
                              <>
                                <Shield className="w-5 h-5 mr-2" />
                                <span>Sign In</span>
                                <ArrowRight className="w-4 h-4 ml-2 transition-transform group-hover:translate-x-1" />
                              </>
                            )}
                          </div>
                        </Button>
                      </motion.div>
                    </div>
                  </form>

                  {/* Info Section */}
                  <div className="bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0">
                        <svg
                          className="w-5 h-5 text-green-500 mt-0.5"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </div>
                      <div className="text-left">
                        <p className="text-sm text-green-800 dark:text-green-200 font-medium">
                          Username Verified
                        </p>
                        <p className="text-xs text-green-600 dark:text-green-300 mt-1">
                          Please enter your password to complete authentication
                        </p>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {step === "loading" && (
                <motion.div
                  key="loading-step"
                  initial={{ opacity: 0, x: -100 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 100 }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                  className="space-y-6 text-center py-8"
                >
                  <div className="space-y-4">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                      className="mx-auto w-16 h-16 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center"
                    >
                      <Loader2 className="w-8 h-8 text-white animate-spin" />
                    </motion.div>
                    <div>
                      <h2 className="text-2xl font-bold text-foreground">Signing you in...</h2>
                      <p className="text-muted-foreground">Please wait while we verify your credentials</p>
                    </div>
                  </div>
                </motion.div>
              )}

              {step === "success" && (
                <motion.div
                  key="success-step"
                  initial={{ opacity: 0, x: -100 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                  className="space-y-6 text-center py-8"
                >
                  <div className="space-y-4">
                    <motion.div
                      initial={{ scale: 0.8, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ duration: 0.5, delay: 0.2 }}
                      className="mx-auto w-16 h-16 rounded-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="h-8 w-8 text-white"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </motion.div>
                      <div>
                        <h2 className="text-2xl font-bold text-foreground">Welcome back!</h2>
                        <p className="text-muted-foreground">Redirecting to your dashboard...</p>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }