# AI Sudoku Solver

An AI web application that processes images of Sudoku puzzles, extracts digits through computer vision, and provides complete solutions with an interactive web interface.

## Features

- **Image Processing**: Upload Sudoku puzzle images via drag & drop
- **OCR Recognition**: Multi-layer digit detection with EasyOCR and template matching
- **Interactive Correction**: Click detected cells to fix recognition errors
- **Puzzle Solving**: Complete backtracking algorithm solution
- **Web Interface**: Professional responsive design for all devices
- **Export**: Download solutions as text files

## Quick Start

### Local Development

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run server
python main.py

# Access at http://localhost:8000
```

### Docker Deployment

#### Published Image (Recommended)
```bash
# Run latest published image
docker run -p 8000:8000 l0cut15/sudoku-solver:latest

# Or run specific version
docker run -p 8000:8000 l0cut15/sudoku-solver:v1.2.1

# Or using docker-compose with published image
version: '3.8'
services:
  sudoku-solver:
    image: l0cut15/sudoku-solver:latest
    ports:
      - "8000:8000"
    restart: unless-stopped

# Save as docker-compose-published.yml and run:
# docker-compose -f docker-compose-published.yml up -d
```

#### Build Locally
```bash
# Using docker-compose (builds from source)
docker-compose up -d

# Or using Docker directly
docker build -t sudoku-solver .
docker run -d -p 8000:8000 sudoku-solver

# Access at http://localhost:8000
```

## Configuration

Set server port and host via:

**Environment file (.env):**
```
SUDOKU_PORT=8000
SUDOKU_HOST=0.0.0.0
```

**Command line:**
```bash
python main.py --port 3000 --host 127.0.0.1
```

**Environment variables:**
```bash
SUDOKU_PORT=3000 python main.py
```

## API

- `GET /` - Web interface
- `POST /solve` - Process puzzle image (returns JSON with detected/solved grids)
- `GET /health` - Health check

## Dependencies

- FastAPI - Web framework
- OpenCV - Image processing
- EasyOCR - Text recognition
- Pillow - Image handling
- NumPy - Array operations

## Usage

1. Open web interface at `http://localhost:8000`
2. Drag & drop or click to upload a Sudoku puzzle image
3. Wait for automatic processing
4. Review detected digits (click cells to correct errors)
5. View complete solution
6. Export results if needed

The application works with clear images of printed Sudoku puzzles and provides real-time feedback during processing.