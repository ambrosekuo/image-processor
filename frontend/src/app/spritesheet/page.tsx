'use client'

import { useState } from 'react'
import { FileUpload } from '@/components/upload/FileUpload'
import { GridConfig } from '@/components/spritesheet/GridConfig'
import { SpritesheetViewer } from '../../components/spritesheet/SpritesheetViewer'
import { ProcessingStatus } from '@/components/upload/ProcessingStatus'
import { AllModelsSpritesheetResults } from '../../components/spritesheet/AllModelsSpritesheetResults'
import { apiClient, SpritesheetConfig, SpritesheetAllModelsResponse } from '@/lib/api'
import { ArrowLeft, Grid, Download, Zap, Settings } from 'lucide-react'
import Link from 'next/link'

export default function SpritesheetPage() {
    const [uploadedFile, setUploadedFile] = useState<File | null>(null)
    const [gridConfig, setGridConfig] = useState({ rows: 2, cols: 5 })
    const [frames, setFrames] = useState(6)
    const [isProcessing, setIsProcessing] = useState(false)
    const [result, setResult] = useState<{
        frames?: string[];
        spritesheetUrl?: string;
        error?: string
    } | null>(null)
    const [allModelsResult, setAllModelsResult] = useState<SpritesheetAllModelsResponse | null>(null)
    const [processingMode, setProcessingMode] = useState<'single' | 'all'>('all')

    const handleFileSelect = (file: File) => {
        setUploadedFile(file)
        setResult(null)
        setAllModelsResult(null)
    }

    const testConnection = async () => {
        const timestamp = new Date().toISOString()
        console.log(`🔍 [${timestamp}] Testing API connection...`)
        try {
            const response = await apiClient.health()
            console.log(`✅ [${timestamp}] Health check successful:`, response)
            alert(`API is working! Response: ${JSON.stringify(response)}`)
        } catch (error) {
            console.error(`❌ [${timestamp}] Health check failed:`, error)
            alert(`API connection failed: ${error}`)
        }
    }

    const handleProcess = async () => {
        if (!uploadedFile) return

        const timestamp = new Date().toISOString()
        console.log(`🎬 [${timestamp}] Starting spritesheet processing...`)
        console.log(`   Processing mode: ${processingMode}`)
        console.log(`   Uploaded file: ${uploadedFile.name} (${uploadedFile.size} bytes)`)
        console.log(`   Grid config: ${gridConfig.cols}x${gridConfig.rows}`)
        console.log(`   Frames: ${frames}`)

        setIsProcessing(true)
        setResult(null)
        setAllModelsResult(null)

        try {
            const config: SpritesheetConfig = {
                grid: `${gridConfig.cols}x${gridConfig.rows}`,
                frames: frames,
            }

            console.log(`   Config:`, config)

            if (processingMode === 'all') {
                console.log(`   🔄 Calling processSpritesheetAllModels... (timeout: 2 minutes)`)
                const response = await apiClient.processSpritesheetAllModels(uploadedFile, config)
                console.log(`   ✅ Response received:`, response)
                setAllModelsResult(response)
            } else {
                console.log(`   🔄 Calling processSpritesheet...`)
                const response = await apiClient.processSpritesheet(uploadedFile, config)
                console.log(`   ✅ Response received:`, response)
                setResult(response)
            }
        } catch (error) {
            console.error(`   ❌ Processing error:`, error)
            setResult({
                error: error instanceof Error ? error.message : 'Processing failed'
            })
        } finally {
            console.log(`   🏁 Processing completed`)
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
                <h1 className="text-3xl font-bold text-gray-900">Spritesheet Model Comparison</h1>
                <p className="text-gray-600 mt-2">
                    Upload a spritesheet to compare results from all available AI models side by side.
                </p>
            </div>

            <div className="grid lg:grid-cols-2 gap-8">
                {/* Configuration Section */}
                <div className="space-y-6">
                    <FileUpload onFileSelect={handleFileSelect} />

                    {uploadedFile && (
                        <>
                            <GridConfig
                                config={gridConfig}
                                onChange={setGridConfig}
                                frames={frames}
                                onFramesChange={setFrames}
                            />

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
                                            ? 'bg-green-600 text-white'
                                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                            }`}
                                    >
                                        <Zap className="w-4 h-4" />
                                        Compare All Models
                                    </button>
                                    <button
                                        onClick={() => setProcessingMode('single')}
                                        className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${processingMode === 'single'
                                            ? 'bg-green-600 text-white'
                                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                            }`}
                                    >
                                        <Grid className="w-4 h-4" />
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

                            <div className="space-y-2">
                                <button
                                    onClick={testConnection}
                                    className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
                                >
                                    Test API Connection
                                </button>

                                <button
                                    onClick={handleProcess}
                                    disabled={isProcessing}
                                    className="w-full bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white px-6 py-3 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
                                >
                                    {isProcessing ? (
                                        <>
                                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                            Processing...
                                        </>
                                    ) : (
                                        <>
                                            <Zap className="w-4 h-4" />
                                            {processingMode === 'all' ? 'Compare All Models' : 'Process Spritesheet'}
                                        </>
                                    )}
                                </button>
                            </div>
                        </>
                    )}
                </div>

                {/* Results Section */}
                <div>
                    {uploadedFile && (
                        <SpritesheetViewer
                            file={uploadedFile}
                            gridConfig={gridConfig}
                            frames={frames}
                        />
                    )}

                    {processingMode === 'all' ? (
                        <AllModelsSpritesheetResults
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
