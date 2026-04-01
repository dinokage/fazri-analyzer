'use client';

import { useRef, useState } from 'react';
import { Camera, CheckCircle2, AlertCircle, Upload, X, UserCheck, Search, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

import { useSession } from '@/lib/auth-client';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';

type Step = 'search' | 'upload' | 'result';

interface EntityResult {
  entity_id: string;
  name: string;
  type: string;
  department?: string;
  face_id?: string;
}

interface ResultState {
  success: boolean;
  entityName: string;
  message: string;
}

export default function FaceEnrollmentPageContent() {
  const { data: session, isPending } = useSession();

  const [step, setStep] = useState<Step>('search');
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<EntityResult[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<EntityResult | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ done: number; total: number; errors: string[] } | null>(null);
  const [result, setResult] = useState<ResultState | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (isPending) return null;

  const role = (session?.user as Record<string, unknown>)?.role;
  if (role !== 'SUPER_ADMIN') {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-white mb-2">Access Denied</h2>
          <p className="text-gray-400">You do not have permission to view this page.</p>
        </div>
      </div>
    );
  }

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    setResults([]);
    try {
      const data = await apiClient.fuzzySearchByName(query.trim(), 0.7);
      setResults(data.results ?? data ?? []);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setSearching(false);
    }
  };

  const handleSelectEntity = (entity: EntityResult) => {
    setSelectedEntity(entity);
    setStep('upload');
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? []);
    if (!selected.length) return;
    setFiles((prev) => [...prev, ...selected]);
    setPreviews((prev) => [...prev, ...selected.map((f) => URL.createObjectURL(f))]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeFile = (index: number) => {
    URL.revokeObjectURL(previews[index]);
    setFiles((prev) => prev.filter((_, i) => i !== index));
    setPreviews((prev) => prev.filter((_, i) => i !== index));
  };

  const clearAllFiles = () => {
    previews.forEach((p) => URL.revokeObjectURL(p));
    setFiles([]);
    setPreviews([]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleEnroll = async () => {
    if (!files.length || !selectedEntity) return;
    setUploading(true);
    setUploadProgress({ done: 0, total: files.length, errors: [] });
    const errors: string[] = [];
    let successCount = 0;

    for (let i = 0; i < files.length; i++) {
      setUploadProgress({ done: i, total: files.length, errors });
      try {
        await apiClient.registerFace(selectedEntity.entity_id, files[i]);
        successCount++;
      } catch (err) {
        errors.push(`Photo ${i + 1}: ${err instanceof Error ? err.message : 'Failed'}`);
      }
    }

    setUploadProgress(null);
    if (successCount === files.length) {
      setResult({ success: true, entityName: selectedEntity.name, message: `${successCount} photo${successCount > 1 ? 's' : ''} enrolled successfully.` });
    } else if (successCount > 0) {
      setResult({ success: true, entityName: selectedEntity.name, message: `${successCount} of ${files.length} photos enrolled. ${errors.join('; ')}` });
    } else {
      setResult({ success: false, entityName: selectedEntity.name, message: errors.join('; ') });
    }
    setStep('result');
    setUploading(false);
  };

  const resetToSearch = () => {
    setStep('search');
    setQuery('');
    setResults([]);
    setSelectedEntity(null);
    clearAllFiles();
    setUploadProgress(null);
    setResult(null);
  };

  const cdnBase = process.env.NEXT_PUBLIC_CDN_URL;

  return (
    <div className="p-8 max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <UserCheck className="h-6 w-6 text-blue-400" />
        <div>
          <h1 className="text-2xl font-bold text-white">Face Enrollment</h1>
          <p className="text-sm text-gray-400">Register a face photo for an entity in the DeepFace database</p>
        </div>
      </div>

      {/* Step: Search */}
      {step === 'search' && (
        <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6 space-y-4">
          <h2 className="text-base font-semibold text-white">Search Entity</h2>
          <div className="flex gap-2">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search by name or entity ID..."
              className="bg-[#1a1a24] border-gray-700 text-white placeholder:text-gray-500 flex-1"
            />
            <Button
              onClick={handleSearch}
              disabled={searching || !query.trim()}
              className="bg-blue-600 hover:bg-blue-700"
            >
              <Search className="h-4 w-4 mr-1" />
              {searching ? 'Searching…' : 'Search'}
            </Button>
          </div>

          {results.length > 0 && (
            <div className="space-y-2">
              {results.map((entity) => (
                <button
                  key={entity.entity_id}
                  onClick={() => handleSelectEntity(entity)}
                  className="w-full flex items-center gap-3 p-3 rounded-lg border border-gray-700 bg-[#1a1a24] hover:border-blue-600 hover:bg-[#1e1e30] transition-colors text-left"
                >
                  <Avatar className="h-10 w-10 flex-shrink-0">
                    <AvatarImage
                      src={entity.face_id && cdnBase ? `${cdnBase}/${entity.face_id}.jpg` : ''}
                      alt={entity.name}
                    />
                    <AvatarFallback className="bg-gray-700 text-gray-300 text-sm">
                      {entity.name.slice(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white truncate">{entity.name}</p>
                    <p className="text-xs text-gray-400 truncate">
                      {entity.type}{entity.department ? ` · ${entity.department}` : ''}
                    </p>
                    <p className="text-xs text-gray-600">{entity.entity_id}</p>
                  </div>
                </button>
              ))}
            </div>
          )}

          {results.length === 0 && query && !searching && (
            <p className="text-sm text-gray-500 text-center py-4">No entities found for &quot;{query}&quot;</p>
          )}
        </div>
      )}

      {/* Step: Upload */}
      {step === 'upload' && selectedEntity && (
        <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6 space-y-4">
          {/* Selected entity */}
          <div className="flex items-center gap-3 p-3 rounded-lg border border-gray-700 bg-[#1a1a24]">
            <Avatar className="h-10 w-10 flex-shrink-0">
              <AvatarImage
                src={selectedEntity.face_id && cdnBase ? `${cdnBase}/${selectedEntity.face_id}.jpg` : ''}
                alt={selectedEntity.name}
              />
              <AvatarFallback className="bg-gray-700 text-gray-300 text-sm">
                {selectedEntity.name.slice(0, 2).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-white truncate">{selectedEntity.name}</p>
              <p className="text-xs text-gray-400 truncate">
                {selectedEntity.type}{selectedEntity.department ? ` · ${selectedEntity.department}` : ''}
              </p>
            </div>
            <button
              onClick={resetToSearch}
              className="text-xs text-blue-400 hover:text-blue-300 flex-shrink-0"
              type="button"
            >
              Change
            </button>
          </div>

          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white">Upload Photos</h2>
            <span className={`text-xs ${files.length >= 3 ? 'text-green-400' : 'text-amber-400'}`}>
              {files.length} photo{files.length !== 1 ? 's' : ''} · {files.length < 3 ? '3-5 recommended for best accuracy' : 'good coverage'}
            </span>
          </div>

          {/* Photo grid */}
          <div className="grid grid-cols-3 gap-2">
            {previews.map((src, i) => (
              <div key={i} className="relative aspect-square rounded-lg overflow-hidden border border-gray-700">
                <img src={src} alt={`Photo ${i + 1}`} className="w-full h-full object-cover" />
                <button onClick={() => removeFile(i)} type="button"
                  className="absolute top-1 right-1 p-0.5 rounded-full bg-gray-900/80 hover:bg-red-900/80 text-gray-300 hover:text-red-300">
                  <X className="h-3 w-3" />
                </button>
                <span className="absolute bottom-1 left-1 text-[10px] bg-black/60 px-1 rounded text-gray-300">{i + 1}</span>
              </div>
            ))}
            {/* Add more button */}
            <label htmlFor="face-upload"
              className="flex flex-col items-center justify-center aspect-square rounded-lg border-2 border-dashed border-gray-700 cursor-pointer hover:border-gray-500 hover:bg-gray-800/30 transition-colors">
              <Upload className="h-5 w-5 text-gray-500 mb-1" />
              <p className="text-[10px] text-gray-500">Add photo</p>
            </label>
          </div>
          <input
            ref={fileInputRef}
            id="face-upload"
            type="file"
            accept="image/jpeg,image/png,image/jpg"
            multiple
            className="hidden"
            onChange={handleFileChange}
          />
          <p className="text-xs text-gray-500">
            Upload multiple photos: frontal, left angle, right angle, different lighting.
            Each photo is registered as a separate embedding for better recognition.
          </p>

          {/* Upload progress */}
          {uploadProgress && (
            <div className="rounded-lg border border-blue-900 bg-blue-900/10 p-3">
              <div className="flex items-center gap-2 text-xs text-blue-300">
                <RefreshCw className="h-3 w-3 animate-spin" />
                Enrolling photo {uploadProgress.done + 1} of {uploadProgress.total}…
              </div>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <Button variant="outline" onClick={resetToSearch} disabled={uploading} className="border-gray-700 flex-1">
              Back
            </Button>
            <Button onClick={handleEnroll} disabled={!files.length || uploading}
              className="bg-blue-600 hover:bg-blue-700 flex-1">
              {uploading ? 'Enrolling…' : `Enroll ${files.length} Photo${files.length !== 1 ? 's' : ''}`}
            </Button>
          </div>
        </div>
      )}

      {/* Step: Result */}
      {step === 'result' && result && (
        <div className="bg-[#14141a] rounded-lg border border-gray-800 p-8 text-center space-y-4">
          {result.success ? (
            <CheckCircle2 className="h-12 w-12 text-green-400 mx-auto" />
          ) : (
            <AlertCircle className="h-12 w-12 text-red-400 mx-auto" />
          )}
          <div>
            <h2 className="text-lg font-semibold text-white mb-1">
              {result.success ? 'Face Enrolled' : 'Enrollment Failed'}
            </h2>
            <p className="text-sm text-gray-400">
              {result.success
                ? `Face registered for ${result.entityName}.`
                : result.message}
            </p>
          </div>
          <div className="flex gap-3 justify-center pt-2">
            <Button onClick={resetToSearch} className="bg-blue-600 hover:bg-blue-700">
              Enroll Another
            </Button>
            {!result.success && (
              <Button
                variant="outline"
                onClick={() => setStep('upload')}
                className="border-gray-700"
              >
                Try Again
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
