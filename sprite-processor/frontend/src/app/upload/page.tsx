'use client'

import { useState } from 'react'
import { FileUpload } from '@/components/upload/FileUpload'
import { ImagePreview } from '@/components/upload/ImagePreview'
import { ProcessingStatus } from '@/components/upload/ProcessingStatus'
import { AllModelsResults } from '@/components/upload/AllModelsResults'
import { apiClient, AllModelsResponse } from '@/lib/api'
import { ArrowLeft, Download, Zap, Settings } from 'lucide-react'
import Link from 'next/link'

export default function UploadPage() {
    const [uploadedFile, setUploadedFile] = useState<File | null>(null)
    const [isProcessing, setIsProcessing] = useState(false)
    const [result, setResult] = useState<{ downloadUrl?: string; error?: string } | null>(null)
    const [allModelsResult, setAllModelsResult] = useState<AllModelsResponse | null>(null)
    const [processingMode, setProcessingMode] = useState<'single' | 'all'>('all')

    const handleFileSelect = (file: File) => {
        setUploadedFile(file)
        setResult(null)
        setAllModelsResult(null)
    }

    const handleProcess = async () => {
        if (!uploadedFile) return

        setIsProcessing(true)
        setResult(null)
        setAllModelsResult(null)

        try {
            if (processingMode === 'all') {
                const response = await apiClient.removeBackgroundAllModels(uploadedFile)
                setAllModelsResult(response)
            } else {
                const response = await apiClient.removeBackground(uploadedFile)
                setResult(response)
            }
        } catch (error) {
            setResult({
                error: error instanceof Error ? error.message : 'Processing failed'
            })
        } finally {
            setIsProcessing(false)
        }
    }

    return (
        <div className="max-w-7xl mx-auto">
            <div className="mb-8">
                <Link
                    href="/"
                    className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-4"
                >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Home
                </Link>
                <h1 className="text-3xl font-bold text-gray-900">AI Model Comparison</h1>
                <p className="text-gray-600 mt-2">
                    Upload an image to compare results from all available AI models side by side.
                </p>
            </div>

            <div className="grid lg:grid-cols-2 gap-8">
                {/* Upload Section */}
                <div className="space-y-6">
                    <FileUpload onFileSelect={handleFileSelect} />

                    {uploadedFile && (
                        <div className="space-y-4">
                            <ImagePreview file={uploadedFile} />

                            {/* Processing Mode Selection */}
                            <div className="bg-white rounded-lg border p-4">
                                <div className="flex items-center gap-2 mb-3">
                                    <Settings className="w-5 h-5 text-gray-600" />
                                    <h3 className="font-semibold text-gray-900">Processing Mode</h3>
                                </div>
                                <div className="grid grid-cols-2 gap-2">
                                    <button
                                        onClick={() => setProcessingMode('all')}
                                        className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${processingMode === 'all'
                                                ? 'bg-blue-600 text-white'
                                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                            }`}
                                    >
                                        <Zap className="w-4 h-4" />
                                        Compare All Models
                                    </button>
                                    <button
                                        onClick={() => setProcessingMode('single')}
                                        className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${processingMode === 'single'
                                                ? 'bg-blue-600 text-white'
                                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                            }`}
                                    >
                                        <Download className="w-4 h-4" />
                                        Single Model
                                    </button>
                                </div>
                                <p className="text-xs text-gray-500 mt-2">
                                    {processingMode === 'all'
                                        ? 'Process with all 6 AI models for comparison'
                                        : 'Process with the default model only'
                                    }
                                </p>
                            </div>

                            <button
                                onClick={handleProcess}
                                disabled={isProcessing}
                                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-6 py-3 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
                            >
                                {isProcessing ? (
                                    <>
                                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                        Processing...
                                    </>
                                ) : (
                                    <>
                                        <Zap className="w-4 h-4" />
                                        {processingMode === 'all' ? 'Compare All Models' : 'Remove Background'}
                                    </>
                                )}
                            </button>
                        </div>
                    )}
                </div>

                {/* Results Section */}
                <div>
                    {processingMode === 'all' ? (
                        <AllModelsResults
                            isProcessing={isProcessing}
                            results={allModelsResult}
                            originalFile={uploadedFile}
                        />
                    ) : (
                        <ProcessingStatus
                            isProcessing={isProcessing}
                            result={result}
                            originalFile={uploadedFile}
                        />
                    )}
                </div>
            </div>
        </div>
    )
}
