'use client'

import { useState } from 'react'
import { FileUpload } from '@/components/upload/FileUpload'
import { ImagePreview } from '@/components/upload/ImagePreview'
import { ProcessingStatus } from '@/components/upload/ProcessingStatus'
import { apiClient } from '@/lib/api'
import { ArrowLeft, Download } from 'lucide-react'
import Link from 'next/link'

export default function UploadPage() {
    const [uploadedFile, setUploadedFile] = useState<File | null>(null)
    const [isProcessing, setIsProcessing] = useState(false)
    const [result, setResult] = useState<{ downloadUrl?: string; error?: string } | null>(null)

    const handleFileSelect = (file: File) => {
        setUploadedFile(file)
        setResult(null)
    }

    const handleProcess = async () => {
        if (!uploadedFile) return

        setIsProcessing(true)
        setResult(null)

        try {
            const response = await apiClient.removeBackground(uploadedFile)
            setResult(response)
        } catch (error) {
            setResult({
                error: error instanceof Error ? error.message : 'Processing failed'
            })
        } finally {
            setIsProcessing(false)
        }
    }

    return (
        <div className="max-w-4xl mx-auto">
            <div className="mb-8">
                <Link
                    href="/"
                    className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-4"
                >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Home
                </Link>
                <h1 className="text-3xl font-bold text-gray-900">Single Image Processing</h1>
                <p className="text-gray-600 mt-2">
                    Upload an image to remove its background using AI technology.
                </p>
            </div>

            <div className="grid lg:grid-cols-2 gap-8">
                {/* Upload Section */}
                <div className="space-y-6">
                    <FileUpload onFileSelect={handleFileSelect} />

                    {uploadedFile && (
                        <div className="space-y-4">
                            <ImagePreview file={uploadedFile} />

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
                                        <Download className="w-4 h-4" />
                                        Remove Background
                                    </>
                                )}
                            </button>
                        </div>
                    )}
                </div>

                {/* Results Section */}
                <div>
                    <ProcessingStatus
                        isProcessing={isProcessing}
                        result={result}
                        originalFile={uploadedFile}
                    />
                </div>
            </div>
        </div>
    )
}
