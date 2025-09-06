'use client'

import { useState } from 'react'
import { Download, CheckCircle, XCircle, Loader2, Zap } from 'lucide-react'
import { AllModelsResponse } from '@/lib/api'

interface AllModelsResultsProps {
    isProcessing: boolean
    results: AllModelsResponse | null
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

export function AllModelsResults({ isProcessing, results, originalFile }: AllModelsResultsProps) {
    const [selectedModel, setSelectedModel] = useState<string | null>(null)

    if (!originalFile && !isProcessing && !results) {
        return (
            <div className="bg-gray-50 rounded-lg p-8 text-center">
                <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Zap className="w-8 h-8 text-gray-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Compare All Models</h3>
                <p className="text-gray-600">
                    Upload an image to see results from all available AI models side by side.
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
                <h3 className="text-lg font-semibold text-blue-900 mb-2">Processing with All Models</h3>
                <p className="text-blue-700 mb-4">
                    AI is processing your image with 6 different models. This may take a few moments...
                </p>
                <div className="w-full bg-blue-200 rounded-full h-2">
                    <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '75%' }}></div>
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
                <h3 className="text-2xl font-bold text-gray-900 mb-2">Model Comparison Results</h3>
                <p className="text-gray-600">
                    Compare results from {successfulModels.length} AI models
                </p>
            </div>

            {/* Model Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {Object.entries(results.models).map(([modelName, result]) => {
                    const info = modelInfo[modelName as keyof typeof modelInfo]
                    const isSelected = selectedModel === modelName

                    return (
                        <div
                            key={modelName}
                            className={`bg-white rounded-lg border-2 p-4 cursor-pointer transition-all ${isSelected ? 'border-blue-500 shadow-lg' : 'border-gray-200 hover:border-gray-300'
                                }`}
                            onClick={() => setSelectedModel(isSelected ? null : modelName)}
                        >
                            {/* Model Header */}
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-2">
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${info.color}`}>
                                        {info.name}
                                    </span>
                                    <div className="flex">
                                        {Array.from({ length: 5 }).map((_, i) => (
                                            <Zap
                                                key={i}
                                                className={`w-3 h-3 ${i < info.strength ? 'text-yellow-500 fill-current' : 'text-gray-300'
                                                    }`}
                                            />
                                        ))}
                                    </div>
                                </div>
                                {result.success ? (
                                    <CheckCircle className="w-5 h-5 text-green-500" />
                                ) : (
                                    <XCircle className="w-5 h-5 text-red-500" />
                                )}
                            </div>

                            {/* Model Description */}
                            <p className="text-sm text-gray-600 mb-3">{info.description}</p>

                            {/* Result */}
                            {result.success ? (
                                <div className="space-y-3">
                                    {/* Preview Image */}
                                    <div className="aspect-video bg-gray-100 rounded-lg overflow-hidden">
                                        <img
                                            src={`data:image/png;base64,${result.data}`}
                                            alt={`${info.name} result`}
                                            className="w-full h-full object-contain"
                                        />
                                    </div>

                                    {/* File Info */}
                                    <div className="text-xs text-gray-500">
                                        <p>Size: {(result.size! / 1024).toFixed(1)} KB</p>
                                    </div>

                                    {/* Download Button */}
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            const link = document.createElement('a')
                                            link.href = `data:image/png;base64,${result.data}`
                                            link.download = `${results.original_filename?.split('.')[0] || 'processed'}_${modelName}.png`
                                            link.click()
                                        }}
                                        className="w-full bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded text-sm font-medium transition-colors flex items-center justify-center gap-2"
                                    >
                                        <Download className="w-4 h-4" />
                                        Download
                                    </button>
                                </div>
                            ) : (
                                <div className="text-center py-4">
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
                            {modelInfo[selectedModel as keyof typeof modelInfo]?.name} - Full View
                        </h4>
                        <button
                            onClick={() => setSelectedModel(null)}
                            className="text-gray-400 hover:text-gray-600"
                        >
                            ✕
                        </button>
                    </div>

                    <div className="aspect-video bg-gray-100 rounded-lg overflow-hidden mb-4">
                        <img
                            src={`data:image/png;base64,${results.models[selectedModel].data}`}
                            alt={`${selectedModel} full result`}
                            className="w-full h-full object-contain"
                        />
                    </div>

                    <div className="flex gap-4">
                        <button
                            onClick={() => {
                                const link = document.createElement('a')
                                link.href = `data:image/png;base64,${results.models[selectedModel].data}`
                                link.download = `${results.original_filename?.split('.')[0] || 'processed'}_${selectedModel}.png`
                                link.click()
                            }}
                            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium transition-colors flex items-center justify-center gap-2"
                        >
                            <Download className="w-4 h-4" />
                            Download Full Size
                        </button>
                    </div>
                </div>
            )}

            {/* Summary */}
            <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-semibold text-gray-900 mb-2">Processing Summary</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <span className="text-gray-600">Original file:</span>
                        <p className="font-medium">{results.original_filename}</p>
                    </div>
                    <div>
                        <span className="text-gray-600">Original size:</span>
                        <p className="font-medium">{(results.original_size / 1024).toFixed(1)} KB</p>
                    </div>
                    <div>
                        <span className="text-gray-600">Successful models:</span>
                        <p className="font-medium text-green-600">{successfulModels.length}/6</p>
                    </div>
                    <div>
                        <span className="text-gray-600">Failed models:</span>
                        <p className="font-medium text-red-600">{failedModels.length}/6</p>
                    </div>
                </div>
            </div>
        </div>
    )
}
