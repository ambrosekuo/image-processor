# Sprite Processor - Video to Spritesheet with Background Removal

A powerful tool for converting videos to spritesheets with advanced background removal capabilities. Perfect for game development, character animation, and sprite creation.

## 🚀 Features

- **Video Processing**: Convert videos to GIFs with customizable FPS and duration
- **Frame Extraction**: Extract all frames from videos/GIFs (no limits!)
- **Background Removal**: 6 different AI models for perfect background removal
- **Per-Frame Control**: Choose different models for individual frames
- **Side-by-Side Comparison**: Compare original vs processed frames
- **Spritesheet Generation**: Compile selected frames into final spritesheets
- **Real-time Processing**: See results immediately with pre-processing
- **Modern UI**: Clean, intuitive interface built with Next.js and Tailwind CSS

## 🏗️ Architecture

- **Backend**: FastAPI (Python) - Handles video processing and AI model inference
- **Frontend**: Next.js (React) - Modern web interface
- **AI Models**: 6 different rembg models for various use cases
- **Video Processing**: MoviePy for video-to-GIF conversion
- **Image Processing**: Pillow for frame manipulation

## 📋 Prerequisites

- Python 3.11+
- Node.js 18+
- FFmpeg (for video processing)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd rembg-tool
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install dependencies
pip install -e .

# Install development dependencies
pip install -r requirements-test.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

## 🚀 Running the Application

### Option 1: Using Make (Recommended)

```bash
# Start both backend and frontend
make dev

# Or start them separately:
make api    # Backend only
make frontend  # Frontend only
```

### Option 2: Manual Setup

#### Start Backend (Terminal 1)

```bash
# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate  # On Windows

# Start API server
sprite-processor-api --host 0.0.0.0 --port 8002
```

#### Start Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

## 🌐 Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8002
- **API Documentation**: http://localhost:8002/docs

## 📖 How to Use

### 1. Video Upload & Analysis

1. **Upload Video**: Drag and drop or click to upload your video file
2. **Video Analysis**: The system automatically analyzes your video and suggests optimal settings:
   - **FPS**: Recommended frames per second
   - **Duration**: Suggested video length
   - **Frames**: Total number of frames to extract
   - **Grid**: Recommended spritesheet layout

### 2. Video to GIF Conversion

1. **Configure Settings**:
   - **FPS**: Set frames per second (3-30 recommended)
   - **Duration**: Limit video length (optional)
   - **Max Size**: Resize video (default: 480x480)

2. **Convert**: Click "Convert to GIF" to create a GIF from your video

### 3. Frame Extraction & Processing

1. **Extract Frames**: Click "Extract Frames" to get all frames from your GIF
   - **All Frames**: No more 10-frame limit! Get all frames from your video
   - **Auto-Processing**: All frames are automatically processed with the recommended model
   - **Dual Data**: Each frame includes both original and processed versions

2. **Frame Grid**: Browse through all extracted frames
   - **Status Indicators**: 
     - 🟢 Green dots: Frame selected for spritesheet
     - 🔵 Blue dots: Showing processed version
   - **Click Frames**: Click any frame for detailed view

### 4. Individual Frame Processing

1. **Select Frame**: Click any frame in the grid to see it in detail
2. **Side-by-Side Comparison**: 
   - **Left**: Original frame (with background)
   - **Right**: Processed frame (background removed)
3. **Model Selection**: Choose different AI models for individual frames:
   - **ISNet General Use** (Recommended): Best overall performance
   - **U2Net Human Seg**: Optimized for human characters
   - **U2Net**: Original model, can be aggressive
   - **U2NetP**: Lighter version
   - **U2Net Cloth Seg**: Good for clothing details
   - **Silueta**: Great for silhouettes
4. **Actions**:
   - **Process**: Apply selected model to frame
   - **Undo**: Revert to original
   - **Show Processed/Original**: Toggle between versions
   - **Include/Exclude**: Choose if frame goes in final spritesheet

### 5. Spritesheet Generation

1. **Select Frames**: Choose which frames to include in your spritesheet
2. **Configure Grid**: Set spritesheet layout (e.g., 5x2 for 10 frames)
3. **Generate**: Click "Reconstruct Spritesheet" to create final spritesheet
4. **Download**: Save your processed spritesheet

## 🎯 AI Models Explained

| Model | Best For | Speed | Quality |
|-------|----------|-------|---------|
| **ISNet General Use** | General purpose, characters, objects | Medium | ⭐⭐⭐⭐⭐ |
| **U2Net Human Seg** | Human characters, portraits | Fast | ⭐⭐⭐⭐ |
| **U2Net** | General objects, can be aggressive | Fast | ⭐⭐⭐ |
| **U2NetP** | Lightweight processing | Very Fast | ⭐⭐⭐ |
| **U2Net Cloth Seg** | Clothing, fabric details | Medium | ⭐⭐⭐⭐ |
| **Silueta** | Silhouettes, simple shapes | Fast | ⭐⭐⭐ |

## 🔧 Configuration

### Backend Configuration

The backend can be configured via environment variables:

```bash
# API Server
export API_HOST=0.0.0.0
export API_PORT=8002

# Processing
export MAX_FRAME_SIZE=480
export DEFAULT_MODEL=isnet-general-use
```

### Frontend Configuration

Edit `frontend/src/lib/api.ts` to change API endpoints:

```typescript
const API_BASE_URL = 'http://localhost:8002';
```

## 📁 Project Structure

```
rembg-tool/
├── src/sprite_processor/          # Backend Python code
│   ├── api.py                    # FastAPI endpoints
│   ├── video.py                  # Video processing
│   ├── pipeline.py               # Processing workflows
│   └── cli.py                    # Command-line interface
├── frontend/                     # Next.js frontend
│   ├── src/app/                  # App pages
│   ├── src/components/           # React components
│   └── src/lib/                  # Utilities
├── tests/                        # Test files
├── assets/                       # Sample files
└── makefile                      # Build automation
```

## 🧪 Testing

### Backend Tests

```bash
# Run all tests
python test

# Run specific test file
python -m pytest tests/test_api.py

# Run with coverage
python -m pytest --cov=src/sprite_processor
```

### Frontend Tests

```bash
cd frontend
npm test
```

## 🐛 Troubleshooting

### Common Issues

1. **"Cannot find module" errors**:
   ```bash
   # Reinstall dependencies
   pip install -e .
   cd frontend && npm install
   ```

2. **Video processing fails**:
   - Ensure FFmpeg is installed
   - Check video format compatibility
   - Try reducing video size/duration

3. **Background removal not working**:
   - Check if models are downloaded (first run downloads them)
   - Try different models for better results
   - Ensure good contrast between subject and background

4. **API connection issues**:
   - Verify backend is running on port 8002
   - Check CORS settings
   - Ensure no firewall blocking

### Performance Tips

- **Large Videos**: Use lower FPS and shorter duration for faster processing
- **Many Frames**: Process frames in batches to avoid memory issues
- **Model Selection**: Use faster models (U2NetP, Silueta) for quick previews

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [rembg](https://github.com/danielgatis/rembg) - Background removal library
- [MoviePy](https://github.com/Zulko/moviepy) - Video processing
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Next.js](https://nextjs.org/) - React framework
- [Tailwind CSS](https://tailwindcss.com/) - Styling

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Search existing issues
3. Create a new issue with detailed description

---

**Happy sprite processing! 🎮✨**
