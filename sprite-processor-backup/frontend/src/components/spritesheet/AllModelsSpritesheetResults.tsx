'use client'

import { useState } from 'react'
import { Download, CheckCircle, XCircle, Loader2, Zap, Grid, Maximize2 } from 'lucide-react'
import { SpritesheetAllModelsResponse } from '@/lib/api'

interface AllModelsSpritesheetResultsProps {
    isProcessing: boolean
    results: SpritesheetAllModelsResponse | null
    originalFile: File | null
}

const modelInfo = {
    'isnet-general-use': {
        name: 'ISNet General Use',
        description: 'Most advanced, best general purpose',
        strength: 5,
        color: 'bg-green-100 text-green-800'
    },
    'u2net_human_seg': {
        name: 'U2Net Human Segmentation',
        description: 'Best for human/character sprites',
        strength: 4,
        color: 'bg-blue-100 text-blue-800'
    },
    'u2net': {
        name: 'U2Net Original',
        description: 'Original model, can be aggressive',
        strength: 3,
        color: 'bg-orange-100 text-orange-800'
    },
    'u2netp': {
        name: 'U2Net Light',
        description: 'Lighter version of U2Net',
        strength: 2,
        color: 'bg-yellow-100 text-yellow-800'
    },
    'u2net_cloth_seg': {
        name: 'U2Net Cloth Segmentation',
        description: 'Good for clothing/character details',
        strength: 3,
        color: 'bg-purple-100 text-purple-800'
    },
    'silueta': {
        name: 'Silueta',
        description: 'Good for simple shapes/silhouettes',
        strength: 2,
        color: 'bg-gray-100 text-gray-800'
    }
}

export function AllModelsSpritesheetResults({ isProcessing, results, originalFile }: AllModelsSpritesheetResultsProps) {
    const [selectedModel, setSelectedModel] = useState<string | null>(null)

    if (!originalFile && !isProcessing && !results) {
        return (
            <div className="bg-gray-50 rounded-lg p-8 text-center">
                <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Grid className="w-8 h-8 text-gray-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Compare Spritesheet Models</h3>
                <p className="text-gray-600">
                    Upload a spritesheet to see results from all available AI models side by side.
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
                <h3 className="text-lg font-semibold text-blue-900 mb-2">Processing Spritesheet with All Models</h3>
                <p className="text-blue-700 mb-4">
                    AI is processing your spritesheet with 6 different models. This typically takes 1-2 minutes...
                </p>
                <div className="space-y-2">
                    <div className="w-full bg-blue-200 rounded-full h-2">
                        <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '60%' }}></div>
                    </div>
                    <p className="text-sm text-blue-600">
                        Please be patient - this is processing each frame with 6 different AI models
                    </p>
                </div>
            </div>
        )
    }

    if (!results) return null

    const successfulModels = Object.entries(results.models).filter(([_, result]) => result.success)
    const failedModels = Object.entries(results.models).filter(([_, result]) => !result.success)

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="text-center">
                <h3 className="text-2xl font-bold text-gray-900 mb-2">Spritesheet Model Comparison</h3>
                <p className="text-gray-600">
                    Compare spritesheet results from {successfulModels.length} AI models
                </p>
            </div>

            {/* Spritesheet Info */}
            <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-semibold text-gray-900 mb-3">Spritesheet Information</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                        <span className="text-gray-600">Original size:</span>
                        <p className="font-medium">{results.spritesheet_size}</p>
                    </div>
                    <div>
                        <span className="text-gray-600">Grid layout:</span>
                        <p className="font-medium">{results.grid}</p>
                    </div>
                    <div>
                        <span className="text-gray-600">Frame size:</span>
                        <p className="font-medium">{results.frame_size}</p>
                    </div>
                    <div>
                        <span className="text-gray-600">Frames processed:</span>
                        <p className="font-medium">{results.frames_processed}</p>
                    </div>
                </div>
            </div>

            {/* Model Grid - Image Focused */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {Object.entries(results.models).map(([modelName, result]) => {
                    const info = modelInfo[modelName as keyof typeof modelInfo]
                    const isSelected = selectedModel === modelName

                    return (
                        <div
                            key={modelName}
                            className={`bg-white rounded-lg border-2 p-2 cursor-pointer transition-all ${isSelected ? 'border-blue-500 shadow-lg' : 'border-gray-200 hover:border-gray-300'
                                }`}
                            onClick={() => setSelectedModel(isSelected ? null : modelName)}
                        >
                            {/* Result */}
                            {result.success ? (
                                <div className="space-y-2">
                                    {/* Preview Image - Much Larger */}
                                    <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden relative group">
                                        <img
                                            src={`data:image/png;base64,${result.data}`}
                                            alt={`${info.name} spritesheet result`}
                                            className="w-full h-full object-contain hover:scale-105 transition-transform duration-200"
                                        />
                                        {/* Fullscreen Button Overlay */}
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                const img = new Image()
                                                img.src = `data:image/png;base64,${result.data}`
                                                const newWindow = window.open('', '_blank')
                                                if (newWindow) {
                                                    newWindow.document.write(`
                                                        <html>
                                                            <head><title>${info.name} - Full Spritesheet</title></head>
                                                            <body style="margin:0; padding:20px; background:#f3f4f6; display:flex; justify-content:center; align-items:center; min-height:100vh;">
                                                                <img src="${img.src}" style="max-width:100%; max-height:100%; object-fit:contain;" />
                                                            </body>
                                                        </html>
                                                    `)
                                                }
                                            }}
                                            className="absolute top-2 right-2 bg-black bg-opacity-50 hover:bg-opacity-70 text-white p-2 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200"
                                            title="Open in Fullscreen"
                                        >
                                            <Maximize2 className="w-4 h-4" />
                                        </button>
                                    </div>

                                    {/* Model Name and Status - Minimal Info */}
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${info.color}`}>
                                                {info.name}
                                            </span>
                                            <CheckCircle className="w-4 h-4 text-green-500" />
                                        </div>
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                const link = document.createElement('a')
                                                link.href = `data:image/png;base64,${result.data}`
                                                link.download = `${results.original_filename?.split('.')[0] || 'spritesheet'}_${modelName}.png`
                                                link.click()
                                            }}
                                            className="bg-blue-600 hover:bg-blue-700 text-white p-2 rounded text-xs transition-colors"
                                            title="Download"
                                        >
                                            <Download className="w-3 h-3" />
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div className="text-center py-8">
                                    <XCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
                                    <p className="text-sm text-red-600">Processing failed</p>
                                    <p className="text-xs text-gray-500 mt-1">{result.error}</p>
                                </div>
                            )}
                        </div>
                    )
                })}
            </div>

            {/* Selected Model Full View */}
            {selectedModel && results.models[selectedModel]?.success && (
                <div className="bg-white rounded-lg border p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h4 className="text-lg font-semibold text-gray-900">
                            {modelInfo[selectedModel as keyof typeof modelInfo]?.name} - Full Spritesheet View
                        </h4>
                        <div className="flex gap-2">
                            <button
                                onClick={() => {
                                    const img = new Image()
                                    img.src = `data:image/png;base64,${results.models[selectedModel].data}`
                                    const newWindow = window.open('', '_blank')
                                    if (newWindow) {
                                        newWindow.document.write(`
                                            <html>
                                                <head><title>${selectedModel} - Full Spritesheet</title></head>
                                                <body style="margin:0; padding:20px; background:#f3f4f6; display:flex; justify-content:center; align-items:center; min-height:100vh;">
                                                    <img src="${img.src}" style="max-width:100%; max-height:100%; object-fit:contain;" />
                                                </body>
                                            </html>
                                        `)
                                    }
                                }}
                                className="bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded text-sm font-medium transition-colors flex items-center gap-2"
                                title="Open in Fullscreen"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                                </svg>
                                Fullscreen
                            </button>
                            <button
                                onClick={() => setSelectedModel(null)}
                                className="text-gray-400 hover:text-gray-600 p-2"
                                title="Close"
                            >
                                ✕
                            </button>
                        </div>
                    </div>

                    <div className="aspect-video bg-gray-100 rounded-lg overflow-hidden mb-4">
                        <img
                            src={`data:image/png;base64,${results.models[selectedModel].data}`}
                            alt={`${selectedModel} full spritesheet result`}
                            className="w-full h-full object-contain"
                        />
                    </div>

                    <div className="flex gap-4">
                        <button
                            onClick={() => {
                                const link = document.createElement('a')
                                link.href = `data:image/png;base64,${results.models[selectedModel].data}`
                                link.download = `${results.original_filename?.split('.')[0] || 'spritesheet'}_${selectedModel}.png`
                                link.click()
                            }}
                            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium transition-colors flex items-center justify-center gap-2"
                        >
                            <Download className="w-4 h-4" />
                            Download Full Spritesheet
                        </button>
                    </div>
                </div>
            )}

            {/* Summary - Compact */}
            <div className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-4">
                        <span className="text-gray-600">File: <span className="font-medium">{results.original_filename}</span></span>
                        <span className="text-gray-600">Size: <span className="font-medium">{(results.original_size / 1024).toFixed(1)} KB</span></span>
                    </div>
                    <div className="flex items-center gap-4">
                        <span className="text-green-600 font-medium">✓ {successfulModels.length}/6 models successful</span>
                        {failedModels.length > 0 && (
                            <span className="text-red-600 font-medium">✗ {failedModels.length} failed</span>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
