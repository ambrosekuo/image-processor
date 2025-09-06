'use client'

import { useState } from 'react'
import { FileUpload } from '@/components/upload/FileUpload'
import { GridConfig } from '@/components/spritesheet/GridConfig'
import { SpritesheetViewer } from '@/components/spritesheet/SpritesheetViewer'
import { ProcessingStatus } from '@/components/upload/ProcessingStatus'
import { apiClient, SpritesheetConfig } from '@/lib/api'
import { ArrowLeft, Grid, Download } from 'lucide-react'
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

    const handleFileSelect = (file: File) => {
        setUploadedFile(file)
        setResult(null)
    }

    const handleProcess = async () => {
        if (!uploadedFile) return

        setIsProcessing(true)
        setResult(null)

        try {
            const config: SpritesheetConfig = {
                grid: `${gridConfig.cols}x${gridConfig.rows}`,
                frames: frames,
            }

            const response = await apiClient.processSpritesheet(uploadedFile, config)
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
        <div className="max-w-6xl mx-auto">
            <div className="mb-8">
                <Link
                    href="/"
                    className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-4"
                >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Home
                </Link>
                <h1 className="text-3xl font-bold text-gray-900">Spritesheet Processing</h1>
                <p className="text-gray-600 mt-2">
                    Upload a spritesheet and process individual frames with background removal.
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
                                        <Grid className="w-4 h-4" />
                                        Process Spritesheet
                                    </>
                                )}
                            </button>
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
