import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, File, AlertCircle } from 'lucide-react';
import { cn } from '../../utils/cn';

interface FileUploaderProps {
  onFileSelect: (file: File) => void;
  isUploading?: boolean;
  error?: string | null;
  maxSizeMB?: number;
}

export function FileUploader({
  onFileSelect,
  isUploading = false,
  error = null,
  maxSizeMB = 50,
}: FileUploaderProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[], fileRejections: any[]) => {
      if (fileRejections.length > 0) {
        return;
      }
      if (acceptedFiles.length > 0) {
        onFileSelect(acceptedFiles[0]);
      }
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    maxSize: maxSizeMB * 1024 * 1024,
    disabled: isUploading,
  });

  const rejectionError = fileRejections[0]?.errors[0]?.message;

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-3xl p-10 text-center cursor-pointer transition-all duration-200 bg-white/50 backdrop-blur-sm',
          isDragActive ? 'border-blue-500 bg-blue-50/50 scale-[1.01]' : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50/50',
          isUploading && 'opacity-50 cursor-not-allowed pointer-events-none'
        )}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center justify-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center text-gray-500">
            <UploadCloud className="w-8 h-8 stroke-[1.5]" />
          </div>
          <div>
            <p className="text-lg font-medium text-gray-900">
              {isDragActive ? 'Drop your PDF here' : 'Click to upload or drag & drop'}
            </p>
            <p className="text-sm text-gray-400 mt-1">PDF contracts up to {maxSizeMB}MB</p>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-gray-100 rounded-full text-xs font-medium text-gray-600">
            <File className="w-3.5 h-3.5" />
            <span>Searchable PDF formats supported</span>
          </div>
        </div>
      </div>

      {(error || rejectionError) && (
        <div className="mt-3 flex items-center gap-2 text-sm text-red-600 bg-red-50 p-3 rounded-xl border border-red-100">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error || rejectionError}</span>
        </div>
      )}
    </div>
  );
}
