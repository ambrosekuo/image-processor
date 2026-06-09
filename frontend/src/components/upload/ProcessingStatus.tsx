'use client'

import { Download, CheckCircle, XCircle, Loader2 } from 'lucide-react'

interface ProcessingStatusProps {
    isProcessing: boolean
    result: {
        downloadUrl?: string
        spritesheetUrl?: string
        error?: string
        has_transparency?: boolean
        config?: { has_transparency?: boolean; remove_background?: boolean }
    } | null
    originalFile: File | null
    removeBackground?: boolean
}

export function ProcessingStatus({ isProcessing, result, originalFile, removeBackground = true }: ProcessingStatusProps) {
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
                <h3 className="text-lg font-semibold text-blue-900 mb-2">Processing</h3>
                <p className="text-blue-700">
                    {removeBackground
                        ? 'Extracting frames and removing backgrounds. Large GIFs can take several minutes.'
                        : 'Extracting frames and building spritesheet...'}
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

    if (result?.downloadUrl || result?.spritesheetUrl) {
        const downloadUrl = result.downloadUrl || result.spritesheetUrl
        const hasTransparency =
            result.has_transparency ?? result.config?.has_transparency ?? false
        return (
            <div className="bg-green-50 rounded-lg p-8 text-center">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle className="w-8 h-8 text-green-600" />
                </div>
                <h3 className="text-lg font-semibold text-green-900 mb-2">Processing Complete!</h3>
                <p className="text-green-700 mb-6">
                    {hasTransparency
                        ? 'Your spritesheet is a transparent PNG — checkered preview below shows see-through areas.'
                        : removeBackground
                            ? 'Spritesheet saved as PNG, but no transparent pixels were detected. Try a different model or source GIF.'
                            : 'Spritesheet saved as PNG with original GIF pixels. Enable “Remove background” for transparent output on opaque GIFs.'}
                </p>

                {/* Show spritesheet preview if available */}
                {result.spritesheetUrl && (
                    <div
                        className="mb-6 rounded-lg border overflow-hidden mx-auto max-w-full"
                        style={{
                            backgroundImage:
                                'linear-gradient(45deg, #e5e7eb 25%, transparent 25%), linear-gradient(-45deg, #e5e7eb 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #e5e7eb 75%), linear-gradient(-45deg, transparent 75%, #e5e7eb 75%)',
                            backgroundSize: '16px 16px',
                            backgroundPosition: '0 0, 0 8px, 8px -8px, -8px 0px',
                            backgroundColor: '#f9fafb',
                        }}
                    >
                        <img
                            src={result.spritesheetUrl}
                            alt="Processed spritesheet"
                            className="max-w-full h-48 object-contain mx-auto block"
                        />
                    </div>
                )}

                <div className="space-y-4">
                    <a
                        href={downloadUrl}
                        download={`${originalFile?.name?.split('.')[0] || 'processed'}_spritesheet.png`}
                        className="inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
                    >
                        <Download className="w-4 h-4" />
                        Download PNG Spritesheet
                    </a>

                    <div className="text-sm text-green-600">
                        <p>✓ PNG format (.png)</p>
                        {hasTransparency ? (
                            <p>✓ Transparent alpha channel detected</p>
                        ) : (
                            <p>✓ Opaque output (no alpha transparency)</p>
                        )}
                        {removeBackground && <p>✓ AI background removal applied</p>}
                        {!removeBackground && <p>✓ Extract-only (no AI pass)</p>}
                    </div>
                </div>
            </div>
        )
    }

    return null
}
