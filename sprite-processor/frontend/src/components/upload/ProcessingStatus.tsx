'use client'

import { Download, CheckCircle, XCircle, Loader2 } from 'lucide-react'

interface ProcessingStatusProps {
    isProcessing: boolean
    result: { downloadUrl?: string; error?: string } | null
    originalFile: File | null
}

export function ProcessingStatus({ isProcessing, result, originalFile }: ProcessingStatusProps) {
    if (!originalFile && !isProcessing && !result) {
        return (
            <div className="bg-gray-50 rounded-lg p-8 text-center">
                <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Download className="w-8 h-8 text-gray-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Ready to Process</h3>
                <p className="text-gray-600">
                    Upload an image to see the processing status and results here.
                </p>
            </div>
        )
    }

    if (isProcessing) {
        return (
            <div className="bg-blue-50 rounded-lg p-8 text-center">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
                </div>
                <h3 className="text-lg font-semibold text-blue-900 mb-2">Processing Image</h3>
                <p className="text-blue-700">
                    AI is removing the background from your image. This may take a few moments...
                </p>
                <div className="mt-4">
                    <div className="w-full bg-blue-200 rounded-full h-2">
                        <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '60%' }}></div>
                    </div>
                </div>
            </div>
        )
    }

    if (result?.error) {
        return (
            <div className="bg-red-50 rounded-lg p-8 text-center">
                <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <XCircle className="w-8 h-8 text-red-600" />
                </div>
                <h3 className="text-lg font-semibold text-red-900 mb-2">Processing Failed</h3>
                <p className="text-red-700 mb-4">{result.error}</p>
                <p className="text-sm text-red-600">
                    Please try again with a different image or check your connection.
                </p>
            </div>
        )
    }

    if (result?.downloadUrl) {
        return (
            <div className="bg-green-50 rounded-lg p-8 text-center">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle className="w-8 h-8 text-green-600" />
                </div>
                <h3 className="text-lg font-semibold text-green-900 mb-2">Processing Complete!</h3>
                <p className="text-green-700 mb-6">
                    Your image has been processed successfully. The background has been removed.
                </p>

                <div className="space-y-4">
                    <a
                        href={result.downloadUrl}
                        download={`${originalFile?.name?.split('.')[0] || 'processed'}_no_bg.png`}
                        className="inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
                    >
                        <Download className="w-4 h-4" />
                        Download Processed Image
                    </a>

                    <div className="text-sm text-green-600">
                        <p>✓ Background removed</p>
                        <p>✓ Transparent PNG format</p>
                        <p>✓ Ready for use in your projects</p>
                    </div>
                </div>
            </div>
        )
    }

    return null
}
