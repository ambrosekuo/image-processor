import Link from 'next/link'
import { Upload, Grid, Download, Zap } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="max-w-6xl mx-auto">
      {/* Hero Section */}
      <div className="text-center mb-16">
        <h1 className="text-5xl font-bold text-gray-900 mb-6">
          AI-Powered Background Removal
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
          Remove backgrounds from single images or process entire spritesheets with our advanced AI technology.
          Perfect for game development, web design, and content creation.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/upload"
            className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-semibold transition-colors flex items-center gap-2"
          >
            <Upload className="w-5 h-5" />
            Upload Image
          </Link>
          <Link
            href="/spritesheet"
            className="bg-green-600 hover:bg-green-700 text-white px-8 py-3 rounded-lg font-semibold transition-colors flex items-center gap-2"
          >
            <Grid className="w-5 h-5" />
            Process Spritesheet
          </Link>
        </div>
      </div>

      {/* Features Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 mb-16">
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
            <Upload className="w-6 h-6 text-blue-600" />
          </div>
          <h3 className="text-lg font-semibold mb-2">Single Image Processing</h3>
          <p className="text-gray-600">
            Upload any image and get instant background removal with transparent output.
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
            <Grid className="w-6 h-6 text-green-600" />
          </div>
          <h3 className="text-lg font-semibold mb-2">Spritesheet Processing</h3>
          <p className="text-gray-600">
            Process entire spritesheets with automatic frame detection and grid layout.
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
            <Download className="w-6 h-6 text-purple-600" />
          </div>
          <h3 className="text-lg font-semibold mb-2">Batch Download</h3>
          <p className="text-gray-600">
            Download individual frames or combined spritesheets in PNG format.
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center mb-4">
            <Zap className="w-6 h-6 text-orange-600" />
          </div>
          <h3 className="text-lg font-semibold mb-2">Fast Processing</h3>
          <p className="text-gray-600">
            Powered by advanced AI models for quick and accurate background removal.
          </p>
        </div>
      </div>

      {/* Quick Start */}
      <div className="bg-white rounded-lg shadow-sm border p-8">
        <h2 className="text-2xl font-bold mb-6">Quick Start</h2>
        <div className="grid md:grid-cols-2 gap-8">
          <div>
            <h3 className="text-lg font-semibold mb-4">For Single Images</h3>
            <ol className="space-y-2 text-gray-600">
              <li>1. Click "Upload Image" above</li>
              <li>2. Drag & drop your image or click to select</li>
              <li>3. Wait for AI processing to complete</li>
              <li>4. Download your image with transparent background</li>
            </ol>
          </div>
          <div>
            <h3 className="text-lg font-semibold mb-4">For Spritesheets</h3>
            <ol className="space-y-2 text-gray-600">
              <li>1. Click "Process Spritesheet" above</li>
              <li>2. Upload your spritesheet image</li>
              <li>3. Configure grid layout (e.g., 5x2)</li>
              <li>4. Specify number of frames to process</li>
              <li>5. Download individual frames or combined spritesheet</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  )
}