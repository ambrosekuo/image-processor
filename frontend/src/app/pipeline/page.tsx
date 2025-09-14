'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, Video, Image, Download, Settings, Play, Pause, RotateCcw, Grid, Zap, Eye, FileVideo, FileImage, Layers, Clock } from 'lucide-react'
import { apiClient, VideoToGifConfig, VideoAnalysisResponse, SpritesheetConfig, SpritesheetAllModelsResponse } from '../../lib/api'
import SpritesheetAnimator from '../../components/spritesheet/SpritesheetAnimator'

type ProcessingMode = 'video' | 'gif' | 'spritesheet'

export default function PipelinePage() {
    const [selectedMode, setSelectedMode] = useState<ProcessingMode>('video')
    const [uploadedFile, setUploadedFile] = useState<File | null>(null)
    const [isProcessing, setIsProcessing] = useState(false)
    const [isAnalyzing, setIsAnalyzing] = useState(false)

    // Video/GIF states
    const [gifBlob, setGifBlob] = useState<Blob | null>(null)
    const [gifUrl, setGifUrl] = useState<string | null>(null)
    const [analysis, setAnalysis] = useState<VideoAnalysisResponse | null>(null)

    // Spritesheet states
    const [spritesheetBlob, setSpritesheetBlob] = useState<Blob | null>(null)
    const [spritesheetUrl, setSpritesheetUrl] = useState<string | null>(null)
    const [allModelsResult, setAllModelsResult] = useState<SpritesheetAllModelsResponse | null>(null)
    const [spritesheetAnalysis, setSpritesheetAnalysis] = useState<any>(null)
    const [detectedGrid, setDetectedGrid] = useState<{ rows: number, cols: number } | null>(null)

    // Configuration states
    const [videoConfig, setVideoConfig] = useState<VideoToGifConfig>({
        fps: 10,
        duration: undefined,
        maxWidth: 480,
        maxHeight: 480
    })
    const [spritesheetConfig, setSpritesheetConfig] = useState<SpritesheetConfig>({
        grid: 'auto',
        frames: 10
    })
    const [processingMode, setProcessingMode] = useState<'single' | 'all'>('all')
    const [frameRate, setFrameRate] = useState(10)
    const [generateMultipleRates, setGenerateMultipleRates] = useState(false)
    const [multipleRates, setMultipleRates] = useState([8, 12, 16, 20])
    const [spritesheetResults, setSpritesheetResults] = useState<{ [key: string]: { url: string, blob: Blob } }>({})

    const [error, setError] = useState<string | null>(null)

    const analyzeSpritesheet = async (file: File) => {
        try {
            console.log('Analyzing spritesheet:', file.name, file.type)
            const result = await apiClient.analyzeSpritesheet(file)
            console.log('Analysis result:', result)
            setSpritesheetAnalysis(result)

            // Auto-detect the best grid layout from the new API format
            if (result.best_guess) {
                const bestGuess = result.best_guess
                console.log('Best guess:', bestGuess)
                const [cols, rows] = bestGuess.grid.split('x').map(Number)
                console.log('Detected grid:', { cols, rows })
                console.log('Setting detectedGrid to:', { rows, cols })
                setDetectedGrid({ rows, cols })
                setSpritesheetConfig(prev => {
                    const newConfig = {
                        ...prev,
                        grid: bestGuess.grid,
                        frames: bestGuess.total_frames
                    }
                    console.log('Setting spritesheetConfig to:', newConfig)
                    return newConfig
                })
            } else {
                console.log('No best guess found, using fallback')
                // Try to estimate grid from spritesheet size
                const img = new Image()
                img.onload = () => {
                    const aspectRatio = img.width / img.height
                    let estimatedCols = 5
                    let estimatedRows = 2

                    // Simple estimation based on aspect ratio
                    if (aspectRatio > 2) {
                        estimatedCols = 8
                        estimatedRows = 2
                    } else if (aspectRatio > 1.5) {
                        estimatedCols = 6
                        estimatedRows = 2
                    } else if (aspectRatio < 0.5) {
                        estimatedCols = 2
                        estimatedRows = 8
                    } else if (aspectRatio < 0.75) {
                        estimatedCols = 3
                        estimatedRows = 6
                    }

                    console.log('Estimated grid from aspect ratio:', { cols: estimatedCols, rows: estimatedRows })
                    setDetectedGrid({ rows: estimatedRows, cols: estimatedCols })
                    setSpritesheetConfig(prev => ({
                        ...prev,
                        grid: `${estimatedCols}x${estimatedRows}`,
                        frames: estimatedCols * estimatedRows
                    }))
                }
                img.src = URL.createObjectURL(file)
            }
        } catch (err) {
            console.error('Spritesheet analysis failed:', err)
            // Fallback to default grid
            setDetectedGrid({ rows: 2, cols: 5 })
        }
    }

    const onDrop = useCallback((acceptedFiles: File[]) => {
        const file = acceptedFiles[0]
        if (file) {
            setUploadedFile(file)
            setError(null)

            // Reset all states
            setGifBlob(null)
            setGifUrl(null)
            setAnalysis(null)
            setSpritesheetBlob(null)
            setSpritesheetUrl(null)
            setAllModelsResult(null)
            setSpritesheetResults({})
            setSpritesheetAnalysis(null)
            setDetectedGrid(null)

            // Auto-analyze spritesheets
            if (selectedMode === 'spritesheet' || selectedMode === 'gif' || (file.type === 'image/png' || file.type === 'image/jpeg' || file.type === 'image/gif')) {
                console.log('Triggering spritesheet analysis for:', file.name, 'mode:', selectedMode)
                analyzeSpritesheet(file)
            }
        }
    }, [selectedMode])

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'video/*': ['.mp4', '.mov', '.avi', '.mkv', '.webm'],
            'image/*': ['.png', '.jpg', '.jpeg', '.gif']
        },
        multiple: false
    })

    const analyzeVideo = async () => {
        if (!uploadedFile || selectedMode !== 'video') return

        setIsAnalyzing(true)
        setError(null)

        try {
            const result = await apiClient.analyzeVideo(uploadedFile)
            setAnalysis(result)

            // Auto-update config with recommendations
            setVideoConfig(prev => ({
                ...prev,
                fps: result.analysis.recommended_fps,
                duration: result.analysis.recommended_duration,
                maxWidth: Math.min(480, result.analysis.size[0]),
                maxHeight: Math.min(480, result.analysis.size[1])
            }))
        } catch (err) {
            setError(`Analysis failed: ${err}`)
        } finally {
            setIsAnalyzing(false)
        }
    }

    const processVideo = async () => {
        if (!uploadedFile || selectedMode !== 'video') return

        setIsProcessing(true)
        setError(null)

        try {
            const blob = await apiClient.videoToGif(uploadedFile, videoConfig)
            setGifBlob(blob)

            // Create URL for display
            const url = URL.createObjectURL(blob)
            setGifUrl(url)
        } catch (err) {
            setError(`Processing failed: ${err}`)
        } finally {
            setIsProcessing(false)
        }
    }

    const processGifToSpritesheet = async () => {
        if (!uploadedFile) return

        setIsProcessing(true)
        setError(null)

        try {
            let fileToProcess = uploadedFile

            // If we have a GIF blob from video conversion, use that
            if (gifBlob && selectedMode === 'video') {
                fileToProcess = new File([gifBlob], 'converted.gif', { type: 'image/gif' })
            }

            if (selectedMode === 'spritesheet') {
                // For spritesheet mode, just remove backgrounds
                if (processingMode === 'all') {
                    const response = await apiClient.removeBackgroundAllModels(fileToProcess)
                    // Convert to spritesheet format for consistency
                    setAllModelsResult({
                        original_filename: fileToProcess.name,
                        original_size: fileToProcess.size,
                        spritesheet_size: 'unknown',
                        grid: '1x1',
                        frames_processed: 1,
                        frame_size: 'unknown',
                        models: response.models
                    })
                } else {
                    const response = await apiClient.removeBackground(fileToProcess)
                    if (response.success && response.downloadUrl) {
                        setSpritesheetUrl(response.downloadUrl)

                        // Fetch the blob for download functionality
                        const blobResponse = await fetch(response.downloadUrl)
                        const blob = await blobResponse.blob()
                        setSpritesheetBlob(blob)
                    } else {
                        throw new Error(response.message || 'Background removal failed')
                    }
                }
            } else {
                // For GIF mode, create spritesheet
                if (processingMode === 'all') {
                    const response = await apiClient.processSpritesheetAllModels(fileToProcess, spritesheetConfig)
                    setAllModelsResult(response)
                } else {
                    const response = await apiClient.processSpritesheet(fileToProcess, spritesheetConfig)
                    if (response.success && response.downloadUrl) {
                        setSpritesheetUrl(response.downloadUrl)

                        // Fetch the blob for download functionality
                        const blobResponse = await fetch(response.downloadUrl)
                        const blob = await blobResponse.blob()
                        setSpritesheetBlob(blob)
                    } else {
                        throw new Error(response.message || 'Spritesheet conversion failed')
                    }
                }
            }
        } catch (err) {
            setError(`Processing failed: ${err}`)
        } finally {
            setIsProcessing(false)
        }
    }

    const downloadGif = () => {
        if (!gifBlob) return

        const url = URL.createObjectURL(gifBlob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${uploadedFile?.name.replace(/\.[^/.]+$/, '') || 'video'}.gif`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }

    const downloadSpritesheet = () => {
        if (!spritesheetBlob) return

        const url = URL.createObjectURL(spritesheetBlob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${uploadedFile?.name.replace(/\.[^/.]+$/, '') || 'media'}_spritesheet.png`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }

    const reset = () => {
        setUploadedFile(null)
        setGifBlob(null)
        setGifUrl(null)
        setAnalysis(null)
        setSpritesheetBlob(null)
        setSpritesheetUrl(null)
        setAllModelsResult(null)
        setSpritesheetResults({})
        setSpritesheetAnalysis(null)
        setDetectedGrid(null)
        setError(null)
        setVideoConfig({
            fps: 10,
            duration: undefined,
            maxWidth: 480,
            maxHeight: 480
        })
        setSpritesheetConfig({
            grid: 'auto',
            frames: 10
        })
    }

    const getModeIcon = (mode: ProcessingMode) => {
        switch (mode) {
            case 'video': return <FileVideo className="w-6 h-6" />
            case 'gif': return <Image className="w-6 h-6" />
            case 'spritesheet': return <Layers className="w-6 h-6" />
        }
    }

    const getModeTitle = (mode: ProcessingMode) => {
        switch (mode) {
            case 'video': return 'Video to GIF'
            case 'gif': return 'GIF to Spritesheet'
            case 'spritesheet': return 'Spritesheet Processing'
        }
    }

    const getModeDescription = (mode: ProcessingMode) => {
        switch (mode) {
            case 'video': return 'Convert video files to optimized GIFs'
            case 'gif': return 'Convert GIFs to spritesheets for game development'
            case 'spritesheet': return 'Remove backgrounds from spritesheets with AI'
        }
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto px-4 py-8">
                {/* Header */}
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-bold text-gray-900 mb-4">
                        Media Processing Pipeline
                    </h1>
                    <p className="text-lg text-gray-600">
                        Choose your processing mode and upload your media
                    </p>
                </div>

                {/* Mode Selection */}
                <div className="mb-8">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {(['video', 'gif', 'spritesheet'] as ProcessingMode[]).map((mode) => (
                            <button
                                key={mode}
                                onClick={() => setSelectedMode(mode)}
                                className={`p-6 rounded-lg border-2 transition-all ${selectedMode === mode
                                    ? 'border-blue-500 bg-blue-50 shadow-md'
                                    : 'border-gray-200 bg-white hover:border-gray-300'
                                    }`}
                            >
                                <div className="flex items-center justify-center mb-3">
                                    <div className={`p-3 rounded-full ${selectedMode === mode ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'
                                        }`}>
                                        {getModeIcon(mode)}
                                    </div>
                                </div>
                                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                                    {getModeTitle(mode)}
                                </h3>
                                <p className="text-sm text-gray-600">
                                    {getModeDescription(mode)}
                                </p>
                            </button>
                        ))}
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Left Panel - Controls */}
                    <div className="space-y-6">
                        {/* File Upload */}
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                                <Upload className="w-5 h-5 mr-2" />
                                Upload Media
                            </h2>

                            <div
                                {...getRootProps()}
                                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${isDragActive
                                    ? 'border-blue-400 bg-blue-50'
                                    : 'border-gray-300 hover:border-gray-400'
                                    }`}
                            >
                                <input {...getInputProps()} />
                                {getModeIcon(selectedMode)}
                                {isDragActive ? (
                                    <p className="text-blue-600 mt-2">Drop the media file here...</p>
                                ) : (
                                    <div className="mt-2">
                                        <p className="text-gray-600 mb-2">
                                            Drag & drop a media file here, or click to select
                                        </p>
                                        <p className="text-sm text-gray-500">
                                            {selectedMode === 'video' && 'Supports MP4, MOV, AVI, MKV, WebM'}
                                            {selectedMode === 'gif' && 'Supports GIF files'}
                                            {selectedMode === 'spritesheet' && 'Supports PNG, JPG, JPEG'}
                                        </p>
                                    </div>
                                )}
                            </div>

                            {uploadedFile && (
                                <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="font-medium text-gray-900">{uploadedFile.name}</p>
                                            <p className="text-sm text-gray-500">
                                                {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                                            </p>
                                        </div>
                                        <button
                                            onClick={reset}
                                            className="text-gray-400 hover:text-gray-600"
                                        >
                                            <RotateCcw className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Video Analysis */}
                        {selectedMode === 'video' && uploadedFile && !analysis && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                                    <Settings className="w-5 h-5 mr-2" />
                                    Video Analysis
                                </h2>
                                <p className="text-gray-600 mb-4">
                                    Analyze your video to get recommended settings for optimal GIF conversion.
                                </p>
                                <button
                                    onClick={analyzeVideo}
                                    disabled={isAnalyzing}
                                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-4 py-2 rounded-lg font-medium transition-colors"
                                >
                                    {isAnalyzing ? 'Analyzing...' : 'Analyze Video'}
                                </button>
                            </div>
                        )}

                        {/* Video Analysis Results */}
                        {analysis && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                                    Video Analysis Results
                                </h2>
                                <div className="grid grid-cols-2 gap-4 text-sm">
                                    <div>
                                        <span className="text-gray-500">Duration:</span>
                                        <span className="ml-2 font-medium">{analysis.analysis.duration.toFixed(1)}s</span>
                                    </div>
                                    <div>
                                        <span className="text-gray-500">FPS:</span>
                                        <span className="ml-2 font-medium">{analysis.analysis.fps.toFixed(1)}</span>
                                    </div>
                                    <div>
                                        <span className="text-gray-500">Size:</span>
                                        <span className="ml-2 font-medium">
                                            {analysis.analysis.size[0]}×{analysis.analysis.size[1]}
                                        </span>
                                    </div>
                                    <div>
                                        <span className="text-gray-500">File Size:</span>
                                        <span className="ml-2 font-medium">
                                            {(analysis.analysis.file_size / 1024 / 1024).toFixed(1)} MB
                                        </span>
                                    </div>
                                </div>
                                <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                                    <p className="text-sm text-blue-800">
                                        <strong>Recommended:</strong> {analysis.analysis.recommended_fps} FPS,
                                        {analysis.analysis.recommended_duration.toFixed(1)}s duration,
                                        {analysis.analysis.recommended_frames} frames
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* GIF Settings */}
                        {selectedMode === 'video' && uploadedFile && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                                    <Settings className="w-5 h-5 mr-2" />
                                    GIF Settings
                                </h2>

                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Frames Per Second
                                        </label>
                                        <input
                                            type="number"
                                            min="1"
                                            max="30"
                                            value={videoConfig.fps}
                                            onChange={(e) => setVideoConfig(prev => ({ ...prev, fps: parseInt(e.target.value) || 10 }))}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Duration (seconds) - Leave empty for full video
                                        </label>
                                        <input
                                            type="number"
                                            min="0.1"
                                            step="0.1"
                                            value={videoConfig.duration || ''}
                                            onChange={(e) => setVideoConfig(prev => ({
                                                ...prev,
                                                duration: e.target.value ? parseFloat(e.target.value) : undefined
                                            }))}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            placeholder="Full video"
                                        />
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Max Width
                                            </label>
                                            <input
                                                type="number"
                                                min="100"
                                                max="1920"
                                                value={videoConfig.maxWidth}
                                                onChange={(e) => setVideoConfig(prev => ({ ...prev, maxWidth: parseInt(e.target.value) || 480 }))}
                                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Max Height
                                            </label>
                                            <input
                                                type="number"
                                                min="100"
                                                max="1080"
                                                value={videoConfig.maxHeight}
                                                onChange={(e) => setVideoConfig(prev => ({ ...prev, maxHeight: parseInt(e.target.value) || 480 }))}
                                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            />
                                        </div>
                                    </div>
                                </div>

                                <button
                                    onClick={processVideo}
                                    disabled={isProcessing}
                                    className="w-full mt-6 bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white px-4 py-2 rounded-lg font-medium transition-colors"
                                >
                                    {isProcessing ? 'Processing...' : 'Convert to GIF'}
                                </button>
                            </div>
                        )}

                        {/* Spritesheet Analysis */}
                        {(spritesheetAnalysis || (uploadedFile && (selectedMode === 'spritesheet' || selectedMode === 'gif'))) && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                                    <Eye className="w-5 h-5 mr-2" />
                                    Spritesheet Analysis
                                </h2>
                                <div className="space-y-3">
                                    {!spritesheetAnalysis && (
                                        <div className="text-center py-4">
                                            <p className="text-gray-600 mb-3">Analyze spritesheet to detect optimal grid layout</p>
                                            <button
                                                onClick={() => uploadedFile && analyzeSpritesheet(uploadedFile)}
                                                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
                                            >
                                                Analyze Spritesheet
                                            </button>
                                        </div>
                                    )}

                                    {/* Spritesheet Preview */}
                                    {uploadedFile && (
                                        <div className="mb-4">
                                            <div className="text-sm text-gray-600 mb-2">Spritesheet Preview:</div>
                                            <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
                                                <img
                                                    src={URL.createObjectURL(uploadedFile)}
                                                    alt="Spritesheet preview"
                                                    className="max-w-full h-auto max-h-48 mx-auto block"
                                                />
                                            </div>
                                        </div>
                                    )}

                                    {spritesheetAnalysis && (
                                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                            <h4 className="font-medium text-blue-900 mb-3">Spritesheet Analysis</h4>
                                            <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                                                <div>
                                                    <span className="text-gray-500">Size:</span>
                                                    <span className="ml-2 font-medium">{spritesheetAnalysis?.spritesheet_size || 'Unknown'}</span>
                                                </div>
                                                <div>
                                                    <span className="text-gray-500">Detected Grid:</span>
                                                    <span className="ml-2 font-medium">{detectedGrid ? `${detectedGrid.cols}×${detectedGrid.rows}` : 'Auto-detecting...'}</span>
                                                    <div className="text-xs text-gray-400 mt-1">
                                                        Debug: detectedGrid = {JSON.stringify(detectedGrid)}
                                                    </div>
                                                </div>
                                            </div>

                                            {/* New API Response Details */}
                                            {spritesheetAnalysis?.best_guess && (
                                                <div className="mt-4 p-3 bg-white rounded border">
                                                    <h5 className="font-medium text-gray-800 mb-2">Analysis Results:</h5>
                                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                                        <div>
                                                            <span className="text-gray-500">Grid:</span>
                                                            <span className="ml-2 font-medium">{spritesheetAnalysis.best_guess.grid}</span>
                                                        </div>
                                                        <div>
                                                            <span className="text-gray-500">Frame Size:</span>
                                                            <span className="ml-2 font-medium">{spritesheetAnalysis.best_guess.frame_size}</span>
                                                        </div>
                                                        <div>
                                                            <span className="text-gray-500">Total Frames:</span>
                                                            <span className="ml-2 font-medium">{spritesheetAnalysis.best_guess.total_frames}</span>
                                                        </div>
                                                        <div>
                                                            <span className="text-gray-500">Confidence:</span>
                                                            <span className="ml-2 font-medium">{(spritesheetAnalysis.best_guess.confidence * 100).toFixed(1)}%</span>
                                                        </div>
                                                    </div>
                                                    {spritesheetAnalysis.best_guess.estimated_effective_frames && (
                                                        <div className="mt-2 text-xs text-gray-500">
                                                            Effective frames: {spritesheetAnalysis.best_guess.estimated_effective_frames}
                                                            {spritesheetAnalysis.best_guess.estimated_empty_tiles > 0 &&
                                                                ` (${spritesheetAnalysis.best_guess.estimated_empty_tiles} empty)`
                                                            }
                                                        </div>
                                                    )}
                                                </div>
                                            )}

                                            {/* Spritesheet Animator Preview */}
                                            {detectedGrid && uploadedFile ? (
                                                <div className="mt-4">
                                                    <h5 className="font-medium text-blue-800 mb-2">Animation Preview:</h5>
                                                    <div className="text-xs text-gray-500 mb-2">
                                                        Debug: detectedGrid = {JSON.stringify(detectedGrid)}, frames = {detectedGrid.rows * detectedGrid.cols}
                                                    </div>
                                                    <div className="border border-blue-300 rounded-lg p-3 bg-white">
                                                        <SpritesheetAnimator
                                                            spritesheetUrl={URL.createObjectURL(uploadedFile)}
                                                            gridConfig={{
                                                                rows: detectedGrid.rows,
                                                                cols: detectedGrid.cols
                                                            }}
                                                            frames={detectedGrid.rows * detectedGrid.cols}
                                                            frameRate={8}
                                                            loop={true}
                                                        />
                                                    </div>
                                                </div>
                                            ) : (
                                                <div className="mt-4 text-sm text-gray-500">
                                                    {!detectedGrid && "No grid detected yet"}
                                                    {!uploadedFile && "No file uploaded"}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Manual Grid Input as Fallback */}
                                    <div className="border-t pt-3">
                                        <p className="text-sm text-gray-600 mb-2">Manual Grid Override:</p>
                                        <div className="flex gap-2 items-center">
                                            <input
                                                type="number"
                                                min="1"
                                                max="20"
                                                value={detectedGrid?.cols || 5}
                                                onChange={(e) => {
                                                    const cols = parseInt(e.target.value) || 5
                                                    const rows = detectedGrid?.rows || 2
                                                    setDetectedGrid({ rows, cols })
                                                    setSpritesheetConfig(prev => ({
                                                        ...prev,
                                                        grid: `${cols}x${rows}`,
                                                        frames: cols * rows
                                                    }))
                                                }}
                                                className="w-16 px-2 py-1 text-sm border border-gray-300 rounded"
                                                placeholder="5"
                                            />
                                            <span className="text-gray-500">×</span>
                                            <input
                                                type="number"
                                                min="1"
                                                max="20"
                                                value={detectedGrid?.rows || 2}
                                                onChange={(e) => {
                                                    const rows = parseInt(e.target.value) || 2
                                                    const cols = detectedGrid?.cols || 5
                                                    setDetectedGrid({ rows, cols })
                                                    setSpritesheetConfig(prev => ({
                                                        ...prev,
                                                        grid: `${cols}x${rows}`,
                                                        frames: cols * rows
                                                    }))
                                                }}
                                                className="w-16 px-2 py-1 text-sm border border-gray-300 rounded"
                                                placeholder="2"
                                            />
                                            <span className="text-sm text-gray-500">= {((detectedGrid?.cols || 5) * (detectedGrid?.rows || 2))} frames</span>
                                        </div>
                                    </div>

                                    {spritesheetAnalysis && spritesheetAnalysis.suggested_layouts && spritesheetAnalysis.suggested_layouts.length > 0 && (
                                        <div>
                                            <p className="text-sm text-gray-600 mb-2">Suggested layouts:</p>
                                            <div className="flex flex-wrap gap-2">
                                                {spritesheetAnalysis.suggested_layouts.slice(0, 5).map((layout: any, index: number) => (
                                                    <button
                                                        key={index}
                                                        onClick={() => {
                                                            const [cols, rows] = layout.grid.split('x').map(Number)
                                                            setDetectedGrid({ rows, cols })
                                                            setSpritesheetConfig(prev => ({
                                                                ...prev,
                                                                grid: layout.grid,
                                                                frames: layout.total_frames
                                                            }))
                                                        }}
                                                        className={`px-3 py-1 text-xs rounded ${detectedGrid && layout.grid === `${detectedGrid.cols}x${detectedGrid.rows}`
                                                            ? 'bg-blue-600 text-white'
                                                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                                            }`}
                                                    >
                                                        {layout.grid} ({layout.total_frames} frames)
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Spritesheet Settings */}
                        {(selectedMode === 'gif' || selectedMode === 'spritesheet' || gifUrl) && uploadedFile && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                                    <Grid className="w-5 h-5 mr-2" />
                                    {selectedMode === 'spritesheet' ? 'Background Removal Settings' : 'Spritesheet Settings'}
                                </h2>

                                <div className="space-y-4">
                                    {selectedMode !== 'spritesheet' && (
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Number of Frames
                                            </label>
                                            <input
                                                type="number"
                                                min="1"
                                                max="50"
                                                value={spritesheetConfig.frames}
                                                onChange={(e) => setSpritesheetConfig(prev => ({ ...prev, frames: parseInt(e.target.value) || 10 }))}
                                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            />
                                        </div>
                                    )}

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            <Clock className="w-4 h-4 inline mr-1" />
                                            Frame Rate (FPS)
                                        </label>
                                        <input
                                            type="number"
                                            min="1"
                                            max="30"
                                            value={frameRate}
                                            onChange={(e) => setFrameRate(parseInt(e.target.value) || 10)}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        />
                                    </div>

                                    {selectedMode !== 'spritesheet' && (
                                        <div className="space-y-3">
                                            <div className="flex items-center">
                                                <input
                                                    type="checkbox"
                                                    id="multipleRates"
                                                    checked={generateMultipleRates}
                                                    onChange={(e) => setGenerateMultipleRates(e.target.checked)}
                                                    className="rounded mr-2"
                                                />
                                                <label htmlFor="multipleRates" className="text-sm font-medium text-gray-700">
                                                    Generate multiple frame rate versions
                                                </label>
                                            </div>

                                            {generateMultipleRates && (
                                                <div className="ml-6 space-y-2">
                                                    <p className="text-sm text-gray-600">Frame rates to generate:</p>
                                                    <div className="flex flex-wrap gap-2">
                                                        {multipleRates.map((rate, index) => (
                                                            <div key={index} className="flex items-center space-x-1">
                                                                <input
                                                                    type="number"
                                                                    min="1"
                                                                    max="30"
                                                                    value={rate}
                                                                    onChange={(e) => {
                                                                        const newRates = [...multipleRates]
                                                                        newRates[index] = parseInt(e.target.value) || rate
                                                                        setMultipleRates(newRates)
                                                                    }}
                                                                    className="w-16 px-2 py-1 text-sm border border-gray-300 rounded"
                                                                />
                                                                <span className="text-sm text-gray-500">FPS</span>
                                                            </div>
                                                        ))}
                                                        <button
                                                            onClick={() => setMultipleRates([...multipleRates, 10])}
                                                            className="px-2 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
                                                        >
                                                            +
                                                        </button>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Processing Mode Selection */}
                                    <div className="space-y-2">
                                        <label className="block text-sm font-medium text-gray-700">
                                            Processing Mode
                                        </label>
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
                                        <p className="text-xs text-gray-500">
                                            {processingMode === 'all'
                                                ? 'Process with all 6 AI models for comparison'
                                                : 'Process with the default model only'
                                            }
                                        </p>
                                    </div>
                                </div>

                                <button
                                    onClick={processGifToSpritesheet}
                                    disabled={isProcessing}
                                    className="w-full mt-6 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white px-4 py-2 rounded-lg font-medium transition-colors"
                                >
                                    {isProcessing ? 'Processing...' : selectedMode === 'spritesheet' ? 'Remove Backgrounds' : 'Create Spritesheet'}
                                </button>
                            </div>
                        )}
                    </div>

                    {/* Right Panel - Results */}
                    <div className="space-y-6">
                        {/* GIF Preview */}
                        {gifUrl && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <div className="flex items-center justify-between mb-4">
                                    <h2 className="text-xl font-semibold text-gray-900 flex items-center">
                                        <Play className="w-5 h-5 mr-2" />
                                        GIF Preview
                                    </h2>
                                    <button
                                        onClick={downloadGif}
                                        className="flex items-center px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
                                    >
                                        <Download className="w-4 h-4 mr-1" />
                                        Download
                                    </button>
                                </div>

                                <div className="aspect-video bg-gray-100 rounded-lg overflow-hidden">
                                    <img
                                        src={gifUrl}
                                        alt="Generated GIF"
                                        className="w-full h-full object-contain"
                                    />
                                </div>

                                {gifBlob && (
                                    <div className="mt-4 text-sm text-gray-600">
                                        <p>File size: {(gifBlob.size / 1024 / 1024).toFixed(2)} MB</p>
                                        <p>Dimensions: {videoConfig.maxWidth}×{videoConfig.maxHeight}</p>
                                        <p>FPS: {videoConfig.fps}</p>
                                        {videoConfig.duration && <p>Duration: {videoConfig.duration}s</p>}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Spritesheet Preview */}
                        {spritesheetUrl && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <div className="flex items-center justify-between mb-4">
                                    <h2 className="text-xl font-semibold text-gray-900 flex items-center">
                                        <Eye className="w-5 h-5 mr-2" />
                                        Spritesheet Preview
                                    </h2>
                                    <button
                                        onClick={downloadSpritesheet}
                                        className="flex items-center px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium transition-colors"
                                    >
                                        <Download className="w-4 h-4 mr-1" />
                                        Download
                                    </button>
                                </div>

                                <div className="aspect-video bg-gray-100 rounded-lg overflow-hidden mb-4">
                                    <img
                                        src={spritesheetUrl}
                                        alt="Generated Spritesheet"
                                        className="w-full h-full object-contain"
                                    />
                                </div>

                                {/* Spritesheet Animator */}
                                <SpritesheetAnimator
                                    spritesheetUrl={spritesheetUrl}
                                    gridConfig={detectedGrid || { rows: 2, cols: 5 }}
                                    frames={spritesheetConfig.frames}
                                    frameRate={frameRate}
                                />

                                {spritesheetBlob && (
                                    <div className="mt-4 text-sm text-gray-600">
                                        <p>File size: {(spritesheetBlob.size / 1024 / 1024).toFixed(2)} MB</p>
                                        <p>Grid: {detectedGrid ? `${detectedGrid.cols}×${detectedGrid.rows}` : spritesheetConfig.grid}</p>
                                        <p>Frames: {spritesheetConfig.frames}</p>
                                        <p>Frame Rate: {frameRate} FPS</p>
                                        {spritesheetAnalysis && (
                                            <p>Original Size: {spritesheetAnalysis?.spritesheet_size || 'Unknown'}</p>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* All Models Results */}
                        {allModelsResult && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                                    <Zap className="w-5 h-5 mr-2" />
                                    All Models Comparison
                                </h2>

                                <div className="grid grid-cols-2 gap-4">
                                    {Object.entries(allModelsResult.models).map(([modelName, result]) => (
                                        <div key={modelName} className="border rounded-lg p-4">
                                            <h3 className="font-medium text-gray-900 mb-2">{modelName}</h3>
                                            {result.success && result.data ? (
                                                <div>
                                                    <img
                                                        src={`data:image/png;base64,${result.data}`}
                                                        alt={`${modelName} result`}
                                                        className="w-full h-32 object-contain bg-gray-100 rounded"
                                                    />
                                                    <p className="text-xs text-gray-500 mt-2">
                                                        Size: {((result.size || 0) / 1024).toFixed(1)} KB
                                                    </p>
                                                </div>
                                            ) : (
                                                <p className="text-red-600 text-sm">{result.error}</p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Error Display */}
                        {error && (
                            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                                <p className="text-red-800">{error}</p>
                            </div>
                        )}

                        {/* Instructions */}
                        {!uploadedFile && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                                    How to Use
                                </h2>
                                <ol className="space-y-2 text-gray-600">
                                    <li>1. <strong>Select your processing mode</strong> above</li>
                                    <li>2. <strong>Upload your media file</strong> using drag & drop or click to select</li>
                                    <li>3. <strong>Configure settings</strong> for your specific processing needs</li>
                                    <li>4. <strong>Click process</strong> to start the conversion</li>
                                    <li>5. <strong>Preview and download</strong> your results</li>
                                </ol>
                                <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                                    <p className="text-sm text-blue-800">
                                        <strong>Tip:</strong> Each mode is optimized for its specific use case!
                                    </p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}