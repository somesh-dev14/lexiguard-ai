import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileUploader } from '../components/documents/FileUploader';
import { ProgressBar } from '../components/ui/ProgressBar';
import { Card, CardBody } from '../components/ui/Card';
import { useDocuments } from '../hooks/useDocuments';
import { useToast } from '../hooks/useToast';
import { ArrowLeft, FileText, Sparkles } from 'lucide-react';
import { Button } from '../components/ui/Button';

export function UploadPage() {
  const navigate = useNavigate();
  const { uploadDocument, isUploading, uploadProgress } = useDocuments();
  const { addToast } = useToast();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = (file: File) => {
    setError(null);
    setSelectedFile(file);
  };

  const handleStartAnalysis = async () => {
    if (!selectedFile) return;

    try {
      const doc = await uploadDocument(selectedFile);
      addToast('Document processed successfully!', 'success');
      navigate(`/analysis/${doc.id}`);
    } catch (err: any) {
      setError(err.message || 'An error occurred during file extraction');
      addToast(err.message || 'Failed to process document', 'error');
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/dashboard')}
          className="p-2 rounded-xl border border-gray-200 text-gray-500 hover:text-gray-900 hover:bg-gray-50 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Upload Contract</h1>
          <p className="text-sm text-gray-500">Provide a PDF agreement to extract text and analyze risks.</p>
        </div>
      </div>

      <Card>
        <CardBody className="p-8 space-y-6">
          <FileUploader
            onFileSelect={handleFileSelect}
            isUploading={isUploading}
            error={error}
          />

          {selectedFile && !isUploading && (
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-2xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 truncate max-w-sm">{selectedFile.name}</h4>
                  <p className="text-xs text-gray-400">{(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</p>
                </div>
              </div>
              <Button onClick={handleStartAnalysis}>
                <Sparkles className="w-4 h-4" />
                Analyze Contract
              </Button>
            </div>
          )}

          {isUploading && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-gray-700">Extracting text & analyzing structure...</span>
                <span className="text-gray-400 font-mono">{uploadProgress}%</span>
              </div>
              <ProgressBar value={uploadProgress} />
              <p className="text-xs text-gray-400 text-center">
                Processing PDF via PyMuPDF. Scanned images without text layers may have limited extraction.
              </p>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
