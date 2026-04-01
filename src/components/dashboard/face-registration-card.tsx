'use client';

import { useRef, useState } from 'react';
import { Camera, CheckCircle2, AlertCircle, X } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';

type State = 'idle' | 'preview' | 'result';

interface ResultState {
  success: boolean;
  message: string;
}

interface FaceRegistrationCardProps {
  entityId: string;
}

export function FaceRegistrationCard({ entityId }: FaceRegistrationCardProps) {
  const [state, setState] = useState<State>('idle');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<ResultState | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;
    setFile(selected);
    setPreview(URL.createObjectURL(selected));
    setState('preview');
  };

  const clearFile = () => {
    setFile(null);
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    setState('idle');
  };

  const handleRegister = async () => {
    if (!file) return;
    setUploading(true);
    try {
      await apiClient.registerFace(entityId, file);
      setResult({ success: true, message: 'Face registered successfully.' });
    } catch (err) {
      setResult({
        success: false,
        message: err instanceof Error ? err.message : 'Registration failed.',
      });
    } finally {
      setUploading(false);
      setState('result');
    }
  };

  const reset = () => {
    clearFile();
    setResult(null);
    setState('idle');
  };

  return (
    <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
      <h2 className="text-lg font-semibold mb-4">Face Registration</h2>

      {state === 'idle' && (
        <>
          <label
            htmlFor="face-reg-upload"
            className="flex flex-col items-center justify-center h-36 rounded-lg border-2 border-dashed border-gray-700 cursor-pointer hover:border-gray-500 hover:bg-gray-800/20 transition-colors"
          >
            <Camera className="h-8 w-8 text-gray-500 mb-2" />
            <p className="text-sm text-gray-400">Click to upload a face photo</p>
            <p className="text-xs text-gray-600 mt-1">JPEG or PNG, front-facing</p>
          </label>
          <input
            ref={fileInputRef}
            id="face-reg-upload"
            type="file"
            accept="image/jpeg,image/png,image/jpg"
            className="hidden"
            onChange={handleFileChange}
          />
        </>
      )}

      {state === 'preview' && preview && (
        <div className="space-y-4">
          <div className="relative">
            <img
              src={preview}
              alt="Face preview"
              className="w-full h-48 object-cover rounded-lg border border-gray-700"
            />
            <button
              onClick={clearFile}
              className="absolute top-2 right-2 p-1 rounded-full bg-gray-900/80 hover:bg-gray-800 text-gray-300"
              type="button"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <Button
            onClick={handleRegister}
            disabled={uploading}
            className="w-full bg-blue-600 hover:bg-blue-700"
          >
            {uploading ? 'Registering…' : 'Register Face'}
          </Button>
        </div>
      )}

      {state === 'result' && result && (
        <div className="flex flex-col items-center text-center space-y-3 py-4">
          {result.success ? (
            <CheckCircle2 className="h-10 w-10 text-green-400" />
          ) : (
            <AlertCircle className="h-10 w-10 text-red-400" />
          )}
          <p className="text-sm text-gray-300">{result.message}</p>
          <Button onClick={reset} variant="outline" className="border-gray-700 mt-2">
            Register Another
          </Button>
        </div>
      )}
    </div>
  );
}
