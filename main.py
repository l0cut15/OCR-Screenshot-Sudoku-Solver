"""AI Sudoku Solver FastAPI Server.

A production-ready web application that processes Sudoku puzzle images,
performs OCR digit recognition, and provides complete solutions with
an interactive web interface.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Tuple, Optional
import uvicorn
import numpy as np
from PIL import Image
import io
import logging
import argparse
import os
from dotenv import load_dotenv
from loguru import logger
from ocr_processor import OCRProcessor
from sudoku_solver import SudokuSolver, create_sudoku_validator

app = FastAPI(title="AI Sudoku Solver", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize OCR processor and Sudoku solver
ocr_processor = OCRProcessor()
sudoku_solver = SudokuSolver()
sudoku_validator = create_sudoku_validator()

class SudokuResult(BaseModel):
    """Response model for Sudoku solving results.
    
    Contains the complete processing results including original grid,
    solved grid, confidence scores, and validation information.
    """
    original_grid: List[List[int]]
    solved_grid: Optional[List[List[int]]]
    given_positions: List[Tuple[int, int]]
    confidence_scores: List[List[float]]
    recognition_sources: List[List[List[str]]]
    uncertain_cells: List[Tuple[int, int]]
    validation_conflicts: Optional[List[dict]]
    processing_time: float
    valid_puzzle: bool
    unique_solution: bool
    accuracy_estimate: float

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web interface"""
    with open("static/index.html", "r") as f:
        html_content = f.read()
    return html_content

@app.get("/api")
async def api_root():
    return {"message": "AI Sudoku Solver API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/solve", response_model=SudokuResult)
async def solve_sudoku(file: UploadFile = File(...)):
    """Process and solve a Sudoku puzzle from an uploaded image.
    
    Args:
        file: Uploaded image file containing a Sudoku puzzle
        
    Returns:
        SudokuResult with complete processing and solving results
        
    Raises:
        HTTPException: If file is not an image or processing fails
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # Process image with OCR
        ocr_result = ocr_processor.process_image(image)
        
        # Validate and solve the detected puzzle
        detected_grid = ocr_result["original_grid"]
        validation_result = sudoku_validator.validate_ocr_result(detected_grid)
        
        solved_grid = None
        if validation_result['is_valid'] and validation_result['solvable']:
            # Make a copy and solve
            solution_grid = [row[:] for row in detected_grid]
            if sudoku_solver.solve(solution_grid):
                solved_grid = solution_grid
        
        # Convert to response format
        result = SudokuResult(
            original_grid=ocr_result["original_grid"],
            solved_grid=solved_grid,
            given_positions=ocr_result["given_positions"],
            confidence_scores=ocr_result["confidence_scores"],
            recognition_sources=ocr_result["recognition_sources"],
            uncertain_cells=ocr_result["uncertain_cells"],
            validation_conflicts=ocr_result.get("validation_conflicts", []),
            processing_time=ocr_result["processing_time"],
            valid_puzzle=validation_result['is_valid'],
            unique_solution=solved_grid is not None,
            accuracy_estimate=ocr_result["accuracy_estimate"]
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="AI Sudoku Solver Server")
    parser.add_argument("--port", "-p", type=int, 
                       default=int(os.getenv("SUDOKU_PORT", 8000)),
                       help="Port to run the server on (default: from .env or 8000)")
    parser.add_argument("--host", type=str, 
                       default=os.getenv("SUDOKU_HOST", "0.0.0.0"),
                       help="Host to bind the server to (default: from .env or 0.0.0.0)")
    args = parser.parse_args()
    
    # Command line arguments override environment variables
    port = args.port
    host = args.host
    
    print(f"Starting AI Sudoku Solver server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)