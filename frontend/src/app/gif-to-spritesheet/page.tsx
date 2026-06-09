'use client'

import { useState } from 'react'
import { FileUpload } from '@/components/upload/FileUpload'
import { GridConfig } from '@/components/spritesheet/GridConfig'
import { SpritesheetViewer } from '../../components/spritesheet/SpritesheetViewer'
import { ProcessingStatus } from '@/components/upload/ProcessingStatus'
import { AllModelsSpritesheetResults } from '../../components/spritesheet/AllModelsSpritesheetResults'
import { apiClient, SpritesheetConfig, SpritesheetAllModelsResponse } from '@/lib/api'
import { ArrowLeft, Grid, Zap, Settings } from 'lucide-react'
import Link from 'next/link'

function defaultFrameCount(totalFrames: number): number {
    if (totalFrames <= 24) return totalFrames
    return 24
}

export default function GifToSpritesheetPage() {
    const [uploadedFile, setUploadedFile] = useState<File | null>(null)
    const [gridConfig, setGridConfig] = useState({ rows: 2, cols: 5 })
    const [sourceFrameCount, setSourceFrameCount] = useState<number | null>(null)
    const [frames, setFrames] = useState(6)
    const [removeBackground, setRemoveBackground] = useState(true)
    const [isAnalyzing, setIsAnalyzing] = useState(false)
    const [isProcessing, setIsProcessing] = useState(false)
    const [analysisInfo, setAnalysisInfo] = useState<string | null>(null)
    const [result, setResult] = useState<{
        frames?: string[];
        spritesheetUrl?: string;
        error?: string
    } | null>(null)
    const [allModelsResult, setAllModelsResult] = useState<SpritesheetAllModelsResponse | null>(null)
    const [processingMode, setProcessingMode] = useState<'single' | 'all'>('single')

    const handleFileSelect = async (file: File) => {
        setUploadedFile(file)
        setResult(null)
        setAllModelsResult(null)
        setAnalysisInfo(null)
        setSourceFrameCount(null)

        const isGif =
            file.type === 'image/gif' ||
            file.name.toLowerCase().endsWith('.gif')

        if (!isGif) {
            setAnalysisInfo('Upload an animated GIF to extract its frames.')
            return
        }

        setIsAnalyzing(true)
        try {
            const analysis = await apiClient.analyzeGif(file)
            const { frames: frameCount, size } = analysis.analysis
            const extractCount = defaultFrameCount(frameCount)
            const cols = Math.ceil(Math.sqrt(extractCount))
            const rows = Math.ceil(extractCount / cols)

            setSourceFrameCount(frameCount)
            setFrames(extractCount)
            setGridConfig({ cols, rows })
            setAnalysisInfo(
                `Detected ${frameCount} animation frames at ${size[0]}×${size[1]}. ` +
                `Starting with ${extractCount} evenly-spaced frames — use presets below to adjust. ` +
                (frameCount > 24
                    ? ' Tip: turn off background removal first for a fast preview.'
                    : '')
            )
        } catch (error) {
            console.error('GIF analysis failed:', error)
            setAnalysisInfo('Could not analyze GIF automatically. Adjust frame count manually.')
        } finally {
            setIsAnalyzing(false)
        }
    }

    const handleProcess = async () => {
        if (!uploadedFile) return

        setIsProcessing(true)
        setResult(null)
        setAllModelsResult(null)

        try {
            const config: SpritesheetConfig = {
                grid: `${gridConfig.cols}x${gridConfig.rows}`,
                frames: frames,
                removeBackground,
                sampleEvenly: true,
            }

            if (processingMode === 'all') {
                const response = await apiClient.processSpritesheetAllModels(uploadedFile, config)
                setAllModelsResult(response)
            } else {
                const response = await apiClient.processSpritesheet(uploadedFile, config)
                setResult(response)
            }
        } catch (error) {
            console.error('Processing error:', error)
            setResult({
                error: error instanceof Error ? error.message : 'Processing failed'
            })
        } finally {
            setIsProcessing(false)
        }
    }

    const estimatedNote = (() => {
        if (!frames) return null
        if (!removeBackground) return 'Extract only — should finish in seconds.'
        const secondsPerFrame = processingMode === 'all' ? 12 : 2
        const totalSec = frames * secondsPerFrame
        if (totalSec < 60) return `Estimated ~${totalSec}s with background removal.`
        return `Estimated ~${Math.ceil(totalSec / 60)} min — reduce frames or disable background removal to go faster.`
    })()

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
                <h1 className="text-3xl font-bold text-gray-900">GIF to Spritesheet</h1>
                <p className="text-gray-600 mt-2">
                    Extract animation frames from a GIF and pack them into a spritesheet. Optionally remove backgrounds.
                </p>
            </div>

            <div className="grid lg:grid-cols-2 gap-8">
                <div className="space-y-6">
                    <FileUpload
                        onFileSelect={handleFileSelect}
                        accept={{ 'image/gif': ['.gif'] }}
                        hint="Supports animated GIF files"
                    />

                    {isAnalyzing && (
                        <p className="text-sm text-gray-600">Analyzing GIF frames...</p>
                    )}

                    {analysisInfo && (
                        <p className="text-sm text-blue-700 bg-blue-50 border border-blue-100 rounded-lg px-4 py-3">
                            {analysisInfo}
                        </p>
                    )}

                    {uploadedFile && (
                        <>
                            <GridConfig
                                config={gridConfig}
                                onChange={setGridConfig}
                                frames={frames}
                                onFramesChange={setFrames}
                                sourceFrameCount={sourceFrameCount ?? undefined}
                                gifMode
                            />

                            <div className="bg-white rounded-lg border p-4 space-y-4">
                                <div className="flex items-center gap-2">
                                    <Settings className="w-5 h-5 text-gray-600" />
                                    <h3 className="font-semibold text-gray-900">Processing Options</h3>
                                </div>

                                <label className="flex items-start gap-3 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={removeBackground}
                                        onChange={(e) => setRemoveBackground(e.target.checked)}
                                        className="mt-1"
                                    />
                                    <span>
                                        <span className="block text-sm font-medium text-gray-900">
                                            Remove background (AI)
                                        </span>
                                        <span className="block text-xs text-gray-500">
                                            Uncheck for extract-only (seconds, not minutes). Note: GIF frames may
                                            already have transparent areas — that is not AI background removal.
                                        </span>
                                    </span>
                                </label>

                                <div>
                                    <p className="text-sm font-medium text-gray-700 mb-2">Model mode</p>
                                    <div className="grid grid-cols-2 gap-2">
                                        <button
                                            type="button"
                                            onClick={() => setProcessingMode('single')}
                                            className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${processingMode === 'single'
                                                ? 'bg-green-600 text-white'
                                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                                }`}
                                        >
                                            <Grid className="w-4 h-4" />
                                            Single Model
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => setProcessingMode('all')}
                                            className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${processingMode === 'all'
                                                ? 'bg-green-600 text-white'
                                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                                }`}
                                        >
                                            <Zap className="w-4 h-4" />
                                            Compare All Models
                                        </button>
                                    </div>
                                    {processingMode === 'all' && frames > 12 && (
                                        <p className="text-xs text-amber-700 mt-2">
                                            Compare All runs 6 models × {frames} frames — very slow. Use Single Model or fewer frames.
                                        </p>
                                    )}
                                </div>

                                {estimatedNote && (
                                    <p className="text-xs text-gray-500">{estimatedNote}</p>
                                )}
                            </div>

                            <button
                                onClick={handleProcess}
                                disabled={isProcessing || isAnalyzing}
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
                                        {removeBackground
                                            ? (processingMode === 'all' ? 'Extract, Remove BG & Compare' : 'Extract & Remove Background')
                                            : 'Extract Frames to Spritesheet'}
                                    </>
                                )}
                            </button>
                        </>
                    )}
                </div>

                <div className="space-y-6">
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
                            removeBackground={removeBackground}
                        />
                    ) : (
                        <ProcessingStatus
                            isProcessing={isProcessing}
                            result={result}
                            originalFile={uploadedFile}
                            removeBackground={removeBackground}
                        />
                    )}
                </div>
            </div>
        </div>
    )
}
