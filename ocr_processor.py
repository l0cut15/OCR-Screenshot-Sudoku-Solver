"""OCR Processing Module for Sudoku Puzzle Recognition.

This module provides advanced computer vision and OCR capabilities for
processing Sudoku puzzle images, including:
- Geometric grid detection and perspective correction
- Multi-layer OCR with EasyOCR and template matching
- Enhanced digit recovery using histogram equalization
- Cell extraction with grid line contamination elimination
"""

import cv2
import numpy as np
import easyocr
from PIL import Image
from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger
import time
import os

@dataclass
class CellDetection:
    """Data class for storing OCR detection results for a single cell.
    
    Attributes:
        digit: Detected digit (0 for empty, 1-9 for digits)
        confidence: Confidence score (0.0 to 1.0)
        sources: List of OCR methods that detected this digit
        position: (row, col) position in the grid
    """
    digit: int
    confidence: float
    sources: List[str]
    position: Tuple[int, int]

class OCRProcessor:
    """Advanced OCR processor for Sudoku puzzle recognition.
    
    Provides comprehensive image processing and digit recognition using
    multiple OCR engines and computer vision techniques.
    """
    def __init__(self):
        """Initialize OCR processor with EasyOCR reader and digit templates."""
        self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
        
        # Create digit templates for template matching
        self.digit_templates = self._create_digit_templates()
        
        logger.info("OCR Processor initialized with multi-layer recognition")
    
    def _create_digit_templates(self) -> Dict[int, np.ndarray]:
        """Create digit templates for template matching recognition.
        
        Returns:
            Dictionary mapping digits (1-9) to their template images
        """
        """Create digit templates that are more similar to the actual Sudoku font"""
        templates = {}
        
        # Create better digit templates using different font style
        for digit in range(1, 10):
            template = np.ones((40, 30), dtype=np.uint8) * 255
            
            # Use FONT_HERSHEY_DUPLEX which is closer to Sudoku font
            font = cv2.FONT_HERSHEY_DUPLEX
            text_size = cv2.getTextSize(str(digit), font, 1.2, 2)[0]
            text_x = (30 - text_size[0]) // 2
            text_y = (40 + text_size[1]) // 2
            cv2.putText(template, str(digit), (text_x, text_y), font, 1.2, 0, 2)
            
            # Invert for matching
            template = 255 - template
            templates[digit] = template
            
        return templates
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Apply comprehensive image preprocessing for optimal OCR.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Preprocessed image ready for grid detection
        """
        """
        Preprocess the input image for better OCR accuracy
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Morph operations to clean up
        kernel = np.ones((2,2), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return cleaned
    
    def detect_grid(self, image: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Detect and extract the Sudoku grid from the image
        """
        # Find contours
        contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Find the largest rectangular contour
        largest_contour = None
        max_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > max_area:
                # Check if contour is roughly rectangular
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
                
                if len(approx) == 4 and area > 10000:  # Minimum area threshold
                    max_area = area
                    largest_contour = approx
        
        if largest_contour is None:
            logger.warning("No grid detected, using entire image")
            return image, False
        
        # Perspective correction
        grid = self.correct_perspective(image, largest_contour)
        return grid, True
    
    def correct_perspective(self, image: np.ndarray, corners: np.ndarray) -> np.ndarray:
        """
        Apply perspective correction to get a top-down view of the grid
        """
        # Order corners: top-left, top-right, bottom-right, bottom-left
        corners = corners.reshape(4, 2)
        
        # Calculate the distances and sort
        def order_points(pts):
            rect = np.zeros((4, 2), dtype="float32")
            s = pts.sum(axis=1)
            rect[0] = pts[np.argmin(s)]  # top-left
            rect[2] = pts[np.argmax(s)]  # bottom-right
            diff = np.diff(pts, axis=1)
            rect[1] = pts[np.argmin(diff)]  # top-right
            rect[3] = pts[np.argmax(diff)]  # bottom-left
            return rect
        
        rect = order_points(corners)
        
        # Define the destination points (square)
        width = height = 450  # Fixed size for processing
        dst = np.array([
            [0, 0],
            [width - 1, 0],
            [width - 1, height - 1],
            [0, height - 1]
        ], dtype="float32")
        
        # Calculate perspective transform matrix and apply it
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (width, height))
        
        return warped
    
    def analyze_grid_structure(self, grid: np.ndarray) -> Dict[str, Any]:
        """
        Analyze the grid structure to find exact line positions and thickness
        """
        height, width = grid.shape
        
        # Analyze horizontal line positions by looking at row sums
        row_sums = np.sum(grid < 127, axis=1)  # Count dark pixels per row
        row_avg = np.mean(row_sums)
        
        # Find rows with significantly more dark pixels (grid lines)
        horizontal_lines = []
        for i in range(height):
            if row_sums[i] > row_avg * 2:  # Much darker than average
                horizontal_lines.append(i)
        
        # Analyze vertical line positions by looking at column sums  
        col_sums = np.sum(grid < 127, axis=0)  # Count dark pixels per column
        col_avg = np.mean(col_sums)
        
        # Find columns with significantly more dark pixels (grid lines)
        vertical_lines = []
        for i in range(width):
            if col_sums[i] > col_avg * 2:  # Much darker than average
                vertical_lines.append(i)
        
        # Group consecutive line positions to find line centers and thickness
        def group_consecutive(lines):
            if not lines:
                return []
            groups = []
            current_group = [lines[0]]
            
            for line in lines[1:]:
                if line - current_group[-1] <= 3:  # Lines within 3 pixels are same line
                    current_group.append(line)
                else:
                    groups.append(current_group)
                    current_group = [line]
            groups.append(current_group)
            
            # Return center and thickness of each group
            result = []
            for group in groups:
                center = sum(group) // len(group)
                thickness = len(group)
                result.append({'center': center, 'thickness': thickness})
            return result
        
        h_groups = group_consecutive(horizontal_lines)
        v_groups = group_consecutive(vertical_lines)
        
        return {
            'horizontal_lines': h_groups,
            'vertical_lines': v_groups,
            'estimated_line_thickness': max(
                max([g['thickness'] for g in h_groups] + [1]),
                max([g['thickness'] for g in v_groups] + [1])
            )
        }
    
    def extract_cells_geometric(self, grid: np.ndarray) -> List[List[np.ndarray]]:
        """
        Extract cells using geometric analysis of actual line positions
        """
        height, width = grid.shape
        
        # Analyze grid structure to find actual line positions
        structure = self.analyze_grid_structure(grid)
        
        h_lines = structure['horizontal_lines']
        v_lines = structure['vertical_lines']
        line_thickness = structure['estimated_line_thickness']
        
        # We should have 10 horizontal lines and 10 vertical lines for a 9x9 grid
        # If we don't detect them all, fall back to uniform division
        if len(h_lines) < 8 or len(v_lines) < 8:
            # Fallback to uniform grid division with padding
            cell_height = height // 9
            cell_width = width // 9
            padding = max(6, line_thickness // 2)
            
            cells = []
            for i in range(9):
                row = []
                for j in range(9):
                    y1 = max(0, i * cell_height + padding)
                    y2 = min(height, (i + 1) * cell_height - padding)
                    x1 = max(0, j * cell_width + padding)
                    x2 = min(width, (j + 1) * cell_width - padding)
                    
                    if y2 > y1 and x2 > x1:
                        cell = grid[y1:y2, x1:x2]
                    else:
                        cell = np.ones((20, 20), dtype=np.uint8) * 255
                    row.append(cell)
                cells.append(row)
            return cells
        
        # Sort line positions
        h_positions = sorted([line['center'] for line in h_lines])
        v_positions = sorted([line['center'] for line in v_lines])
        
        # Ensure we have boundaries - add edges if needed
        if h_positions[0] > 5:
            h_positions.insert(0, 0)
        if h_positions[-1] < height - 5:
            h_positions.append(height - 1)
        if v_positions[0] > 5:
            v_positions.insert(0, 0)  
        if v_positions[-1] < width - 5:
            v_positions.append(width - 1)
        
        # Extract cells using detected line positions
        cells = []
        for i in range(9):
            row = []
            for j in range(9):
                # Calculate cell boundaries based on detected lines
                if i < len(h_positions) - 1 and j < len(v_positions) - 1:
                    y1 = h_positions[i] + line_thickness // 2 + 2
                    y2 = h_positions[i + 1] - line_thickness // 2 - 2
                    x1 = v_positions[j] + line_thickness // 2 + 2  
                    x2 = v_positions[j + 1] - line_thickness // 2 - 2
                    
                    if y2 > y1 and x2 > x1:
                        cell = grid[y1:y2, x1:x2]
                    else:
                        cell = np.ones((20, 20), dtype=np.uint8) * 255
                else:
                    cell = np.ones((20, 20), dtype=np.uint8) * 255
                    
                row.append(cell)
            cells.append(row)
            
        return cells
    
    def extract_cells(self, grid: np.ndarray) -> List[List[np.ndarray]]:
        """
        Extract individual cell images using center-based geometric positioning
        """
        height, width = grid.shape
        cell_height = height // 9
        cell_width = width // 9
        
        cells = []
        for i in range(9):
            row = []
            for j in range(9):
                # Calculate the center of each cell, accounting for grid line thickness
                # Grid lines are approximately 1-2 pixels, so adjust slightly inward
                center_y = i * cell_height + cell_height // 2
                center_x = j * cell_width + cell_width // 2
                
                # For cells near borders, shift center away from grid lines
                # Apply adjustments more broadly to avoid grid line interference
                if j <= 1:  # First two columns - shift right to avoid left grid lines
                    center_x += 6
                elif j >= 7:  # Last two columns - shift left to avoid right grid lines  
                    center_x -= 6
                    
                if i <= 1:  # First two rows - shift down to avoid top grid lines
                    center_y += 6
                elif i >= 7:  # Last two rows - shift up to avoid bottom grid lines
                    center_y -= 6
                
                # Extract a centered region around the digit  
                # Use 80% of cell size to capture full digit while avoiding grid lines
                extract_height = int(cell_height * 0.8)
                extract_width = int(cell_width * 0.8)
                
                # Calculate boundaries centered on the digit location
                y1 = max(0, center_y - extract_height // 2)
                y2 = min(height, center_y + extract_height // 2)
                x1 = max(0, center_x - extract_width // 2)
                x2 = min(width, center_x + extract_width // 2)
                
                # Ensure we have a valid cell region
                if y2 <= y1 or x2 <= x1:
                    cell = np.ones((20, 20), dtype=np.uint8) * 255
                else:
                    cell = grid[y1:y2, x1:x2]
                
                # Apply preprocessing
                cell = self.preprocess_cell(cell)
                row.append(cell)
            cells.append(row)
        
        return cells
    
    def preprocess_cell(self, cell: np.ndarray) -> np.ndarray:
        """
        Minimal preprocessing for geometrically extracted clean cells
        """
        if cell.size == 0:
            return cell
        
        # Ensure grayscale
        if len(cell.shape) == 3:
            cell = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
        
        # Resize to standard size for OCR
        cell = cv2.resize(cell, (100, 100), interpolation=cv2.INTER_CUBIC)
        
        # Simple thresholding - no adaptive since cells are clean
        _, cell = cv2.threshold(cell, 127, 255, cv2.THRESH_BINARY)
        
        # Ensure digits are black on white background
        black_pixels = np.sum(cell < 127)
        white_pixels = np.sum(cell >= 127)
        
        if black_pixels > white_pixels:
            cell = cv2.bitwise_not(cell)
        
        return cell
    
    def remove_grid_lines(self, cell: np.ndarray) -> np.ndarray:
        """
        MINIMAL grid line removal - only clean obvious border artifacts
        Rely primarily on better padding to avoid grid lines entirely
        """
        if cell.size == 0:
            return cell
        
        # Work on a copy and ensure grayscale
        if len(cell.shape) == 3:
            cleaned = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
        else:
            cleaned = cell.copy()
        
        h, w = cleaned.shape
        if h < 10 or w < 10:
            return cleaned
        
        # ONLY clean 1-2 pixel borders if they appear to be solid dark lines
        # This is very conservative to avoid damaging digits
        
        # Check and clean top border only if it's a solid dark line
        if h > 8:
            top_strip = cleaned[0:1, :]
            if np.mean(top_strip) < 100 and np.std(top_strip) < 50:  # Solid dark line
                cleaned[0:1, :] = 255
        
        # Check and clean bottom border only if it's a solid dark line  
        if h > 8:
            bottom_strip = cleaned[h-1:h, :]
            if np.mean(bottom_strip) < 100 and np.std(bottom_strip) < 50:  # Solid dark line
                cleaned[h-1:h, :] = 255
        
        # Check and clean left border only if it's a solid dark line
        if w > 8:
            left_strip = cleaned[:, 0:1]
            if np.mean(left_strip) < 100 and np.std(left_strip) < 50:  # Solid dark line
                cleaned[:, 0:1] = 255
        
        # Check and clean right border only if it's a solid dark line
        if w > 8:
            right_strip = cleaned[:, w-1:w]
            if np.mean(right_strip) < 100 and np.std(right_strip) < 50:  # Solid dark line
                cleaned[:, w-1:w] = 255
        
        return cleaned
    

    def recognize_digit_easyocr(self, cell: np.ndarray) -> Tuple[int, float]:
        """
        Use EasyOCR to recognize digits in a cell
        """
        if cell.size == 0:
            return 0, 0.0
        
        try:
            # Try multiple preprocessing approaches for EasyOCR
            # Approach 1: Larger size (cell is already 100x100 after preprocessing)
            cell_large = cv2.resize(cell, (120, 120), interpolation=cv2.INTER_CUBIC)
            
            # EasyOCR expects RGB image
            if len(cell_large.shape) == 2:
                cell_rgb = cv2.cvtColor(cell_large, cv2.COLOR_GRAY2RGB)
            else:
                cell_rgb = cell_large
            
            results = self.easyocr_reader.readtext(
                cell_rgb,
                allowlist='123456789',
                width_ths=0.005,  # More sensitive to smaller text
                height_ths=0.005,  # More sensitive to smaller text
                paragraph=False,
                detail=1,
                low_text=0.3,  # Lower threshold for text detection
                text_threshold=0.5  # Lower confidence threshold
            )
            
            if not results:
                # Try fallback approach with less aggressive preprocessing
                cell_fallback = cv2.resize(cell, (100, 100), interpolation=cv2.INTER_CUBIC)
                # Apply lighter preprocessing
                cell_fallback = cv2.GaussianBlur(cell_fallback, (1, 1), 0)
                
                if len(cell_fallback.shape) == 2:
                    cell_rgb_fallback = cv2.cvtColor(cell_fallback, cv2.COLOR_GRAY2RGB)
                else:
                    cell_rgb_fallback = cell_fallback
                
                results = self.easyocr_reader.readtext(
                    cell_rgb_fallback,
                    allowlist='123456789',
                    width_ths=0.1,
                    height_ths=0.1,
                    paragraph=False,
                    detail=1
                )
                
                if not results:
                    return 0, 0.0
            
            # Get the result with highest confidence
            best_result = max(results, key=lambda x: x[2])
            text, confidence = best_result[1], best_result[2]
            
            # Validate digit
            if text.isdigit() and 1 <= int(text) <= 9:
                return int(text), float(confidence)
            else:
                return 0, 0.0
                
        except Exception as e:
            logger.warning(f"EasyOCR recognition failed: {e}")
            return 0, 0.0

    def recognize_digit_template(self, cell: np.ndarray) -> Tuple[int, float]:
        """
        Use template matching to recognize digits
        """
        if cell.size == 0:
            return 0, 0.0
        
        try:
            # Resize cell to match template size (cell is now 100x100 after preprocessing)
            cell_resized = cv2.resize(cell, (30, 40), interpolation=cv2.INTER_CUBIC)
            
            # Invert if needed (templates are inverted)
            if np.mean(cell_resized) > 127:
                cell_resized = 255 - cell_resized
            
            best_match = 0
            best_confidence = 0.0
            
            for digit, template in self.digit_templates.items():
                # Template matching
                result = cv2.matchTemplate(cell_resized, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                
                if max_val > best_confidence:
                    best_confidence = max_val
                    best_match = digit
            
            # Higher confidence threshold to reduce false positives
            if best_confidence > 0.5:
                return best_match, float(best_confidence)
            else:
                return 0, 0.0
                
        except Exception as e:
            logger.warning(f"Template matching failed: {e}")
            return 0, 0.0
    
    def is_cell_empty(self, cell: np.ndarray, threshold: int = 50) -> bool:
        """
        Determine if a cell is empty based on pixel analysis
        """
        if cell.size == 0:
            return True
        
        # For binary images after preprocessing, count black pixels (digits)
        # Since preprocess_cell ensures black digits on white background
        black_pixels = np.sum(cell < 127)
        total_pixels = cell.size
        
        # Calculate the percentage of black pixels
        black_ratio = black_pixels / total_pixels
        
        # If less than 0.5% of pixels are black, consider empty (even less aggressive)
        return black_ratio < 0.005
    
    def enhanced_digit_recovery(self, cell: np.ndarray) -> Tuple[int, float]:
        """Enhanced digit recovery using histogram equalization"""
        if cell.size == 0:
            return 0, 0.0
        
        try:
            # Histogram equalization enhancement
            equalized = cv2.equalizeHist(cell)
            _, thresh = cv2.threshold(equalized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            enhanced = cv2.resize(thresh, (100, 100), interpolation=cv2.INTER_CUBIC)
            
            # Ensure black digits on white background
            if np.mean(enhanced) > 127:
                enhanced = cv2.bitwise_not(enhanced)
            
            # Test with EasyOCR
            easy_digit, easy_conf = self.recognize_digit_easyocr(enhanced)
            if easy_digit > 0 and easy_conf > 0.3:
                return easy_digit, easy_conf
            
            # Test with template matching
            template_digit, template_conf = self.recognize_digit_template(enhanced)
            if template_digit > 0 and template_conf > 0.3:
                return template_digit, template_conf
                
        except Exception:
            pass
        
        return 0, 0.0
    
    def ensemble_recognition(self, cell: np.ndarray) -> Tuple[int, float, List[str]]:
        """
        Use ensemble of recognition methods to achieve higher accuracy
        """
        if self.is_cell_empty(cell):
            return 0, 1.0, ["empty_detection"]
        
        # Try recognition methods (disable PaddleOCR temporarily for speed)
        easy_digit, easy_conf = self.recognize_digit_easyocr(cell)
        template_digit, template_conf = self.recognize_digit_template(cell)
        
        # Collect results
        results = []
        if easy_digit > 0:
            results.append(('easyocr', easy_digit, easy_conf))
        if template_digit > 0:
            results.append(('template', template_digit, template_conf))
        
        if not results:
            # Try enhanced recovery for cells with content
            black_ratio = np.sum(cell < 127) / cell.size if cell.size > 0 else 0
            if black_ratio > 0.005:  # Has significant content
                enhanced_digit, enhanced_conf = self.enhanced_digit_recovery(cell)
                if enhanced_digit > 0:
                    return enhanced_digit, enhanced_conf, ["enhanced_recovery"]
            
            return 0, 0.0, ["no_detection"]
        
        # Ensemble decision making
        digit_votes = {}
        confidence_sum = {}
        sources_by_digit = {}
        
        for source, digit, conf in results:
            if digit not in digit_votes:
                digit_votes[digit] = 0
                confidence_sum[digit] = 0.0
                sources_by_digit[digit] = []
            
            digit_votes[digit] += 1
            confidence_sum[digit] += conf
            sources_by_digit[digit].append(source)
        
        # Prioritize EasyOCR results if available
        easyocr_results = [r for r in results if r[0] == 'easyocr']
        if easyocr_results and easyocr_results[0][2] > 0.6:  # High confidence EasyOCR
            best_digit = easyocr_results[0][1]
            ensemble_confidence = min(0.99, easyocr_results[0][2] * 1.1)
            sources = ['easyocr']
        else:
            # Find the digit with most votes
            best_digit = max(digit_votes.items(), key=lambda x: (x[1], confidence_sum[x[0]]))[0]
            
            # Calculate ensemble confidence
            vote_count = digit_votes[best_digit]
            avg_confidence = confidence_sum[best_digit] / vote_count
            
            # Boost confidence if multiple methods agree
            if vote_count >= 2:
                ensemble_confidence = min(0.99, avg_confidence * 1.2)
            else:
                ensemble_confidence = avg_confidence * 0.9  # Slight penalty for single method
            
            sources = sources_by_digit[best_digit]
        
        return best_digit, ensemble_confidence, sources

    def process_cells(self, cells: List[List[np.ndarray]]) -> List[List[CellDetection]]:
        """
        Process all cells using ensemble recognition with validation
        """
        results = []
        
        # First pass: Initial OCR recognition
        for i, row in enumerate(cells):
            result_row = []
            for j, cell in enumerate(row):
                digit, confidence, sources = self.ensemble_recognition(cell)
                detection = CellDetection(digit, confidence, sources, (i, j))
                result_row.append(detection)
            results.append(result_row)
        
        # Second pass: Validate against Sudoku rules and reassess low-confidence conflicts
        validated_results, validation_conflicts = self.validate_and_reassess(results, cells)
        
        # Store validation conflicts for reporting
        self.validation_conflicts = validation_conflicts
        
        return validated_results
    
    def validate_and_reassess(self, detections: List[List[CellDetection]], cells: List[List[np.ndarray]]) -> Tuple[List[List[CellDetection]], List[Dict]]:
        """
        Validate OCR results against Sudoku rules and reassess conflicting low-confidence digits
        """
        # Convert detections to grid format for validation
        current_grid = [[det.digit for det in row] for row in detections]
        
        # Find all conflicts
        conflicts = self.find_sudoku_conflicts(current_grid)
        original_conflicts = [conflict.copy() for conflict in conflicts]  # Store for reporting
        
        # Process each conflict
        for conflict in conflicts:
            row, col, digit = conflict['row'], conflict['col'], conflict['value']
            detection = detections[row][col]
            
            # Only reassess if confidence is below threshold (uncertain digits)
            if detection.confidence < 0.8:  # Configurable threshold
                logger.info(f"Reassessing low-confidence digit {digit} at ({row}, {col}) due to Sudoku rule violation")
                
                # Try enhanced recovery methods
                cell = cells[row][col]
                new_digit, new_confidence, new_sources = self.reassess_conflicted_digit(
                    cell, current_grid, row, col, detection
                )
                
                if new_digit != digit:
                    logger.info(f"Reassessment changed digit from {digit} to {new_digit} at ({row}, {col})")
                    # Update the detection
                    detections[row][col] = CellDetection(
                        new_digit, new_confidence, new_sources, (row, col)
                    )
                    # Update current grid for subsequent validations
                    current_grid[row][col] = new_digit
        
        return detections, original_conflicts
    
    def find_sudoku_conflicts(self, grid: List[List[int]]) -> List[Dict]:
        """
        Find all cells that violate Sudoku rules
        """
        conflicts = []
        
        for row in range(9):
            for col in range(9):
                digit = grid[row][col]
                if digit != 0 and not self.is_valid_placement(grid, row, col, digit):
                    conflicts.append({
                        'row': row,
                        'col': col,
                        'value': digit,
                        'conflict_type': self.get_conflict_type(grid, row, col, digit)
                    })
        
        return conflicts
    
    def is_valid_placement(self, grid: List[List[int]], row: int, col: int, digit: int) -> bool:
        """
        Check if placing digit at (row, col) violates Sudoku rules
        """
        # Temporarily clear the cell for validation
        original = grid[row][col]
        grid[row][col] = 0
        
        # Check row
        for j in range(9):
            if grid[row][j] == digit:
                grid[row][col] = original
                return False
        
        # Check column
        for i in range(9):
            if grid[i][col] == digit:
                grid[row][col] = original
                return False
        
        # Check 3x3 box
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(box_row, box_row + 3):
            for j in range(box_col, box_col + 3):
                if grid[i][j] == digit:
                    grid[row][col] = original
                    return False
        
        grid[row][col] = original
        return True
    
    def get_conflict_type(self, grid: List[List[int]], row: int, col: int, digit: int) -> str:
        """
        Determine the type of Sudoku rule violation
        """
        original = grid[row][col]
        grid[row][col] = 0
        
        # Check row conflict
        for j in range(9):
            if grid[row][j] == digit:
                grid[row][col] = original
                return 'row'
        
        # Check column conflict
        for i in range(9):
            if grid[i][col] == digit:
                grid[row][col] = original
                return 'column'
        
        # Check box conflict
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(box_row, box_row + 3):
            for j in range(box_col, box_col + 3):
                if grid[i][j] == digit:
                    grid[row][col] = original
                    return 'box'
        
        grid[row][col] = original
        return 'unknown'
    
    def reassess_conflicted_digit(self, cell: np.ndarray, current_grid: List[List[int]], 
                                row: int, col: int, original_detection: CellDetection) -> Tuple[int, float, List[str]]:
        """
        Reassess a conflicted digit using enhanced methods and rule-based filtering
        """
        # Try enhanced recovery first
        enhanced_digit, enhanced_conf = self.enhanced_digit_recovery(cell)
        
        # Get all possible digits from different OCR methods
        candidates = []
        
        # EasyOCR
        easy_digit, easy_conf = self.recognize_digit_easyocr(cell)
        if easy_digit != 0:
            candidates.append((easy_digit, easy_conf, 'easyocr'))
        
        # Template matching
        template_digit, template_conf = self.recognize_digit_template(cell)
        if template_digit != 0:
            candidates.append((template_digit, template_conf, 'template'))
        
        # Enhanced recovery
        if enhanced_digit != 0:
            candidates.append((enhanced_digit, enhanced_conf, 'enhanced_recovery'))
        
        # Filter candidates by Sudoku rules
        valid_candidates = []
        for digit, conf, source in candidates:
            if self.is_valid_placement(current_grid, row, col, digit):
                valid_candidates.append((digit, conf, source))
        
        if valid_candidates:
            # Choose the highest confidence valid candidate
            best_digit, best_conf, best_source = max(valid_candidates, key=lambda x: x[1])
            logger.info(f"Found valid alternative: {best_digit} (confidence: {best_conf:.3f}) from {best_source}")
            return best_digit, best_conf, [best_source]
        else:
            # If no valid candidates, mark as empty (let solver handle it)
            logger.info(f"No valid alternatives found, marking cell as empty")
            return 0, 0.0, ['rule_validation']
    
    def process_image(self, image_path_or_array) -> Dict[str, Any]:
        """
        Main processing pipeline
        """
        start_time = time.time()
        
        # Load image
        if isinstance(image_path_or_array, str):
            image = cv2.imread(image_path_or_array)
        elif isinstance(image_path_or_array, Image.Image):
            image = cv2.cvtColor(np.array(image_path_or_array), cv2.COLOR_RGB2BGR)
        else:
            image = image_path_or_array
        
        if image is None:
            raise ValueError("Could not load image")
        
        logger.info(f"Processing image of size: {image.shape}")
        
        # Preprocessing
        processed = self.preprocess_image(image)
        
        # Grid detection
        grid, grid_found = self.detect_grid(processed)
        
        # Cell extraction
        cells = self.extract_cells(grid)
        
        # OCR processing
        detections = self.process_cells(cells)
        
        # Build result grid and metadata
        original_grid = []
        confidence_scores = []
        recognition_sources = []
        given_positions = []
        uncertain_cells = []
        
        total_confidence = 0
        digit_count = 0
        
        for i, row in enumerate(detections):
            grid_row = []
            conf_row = []
            sources_row = []
            
            for j, detection in enumerate(row):
                grid_row.append(detection.digit)
                conf_row.append(detection.confidence)
                sources_row.append(detection.sources)
                
                if detection.digit > 0:
                    given_positions.append((i, j))
                    total_confidence += detection.confidence
                    digit_count += 1
                    
                    # Flag uncertain cells (low confidence)
                    if detection.confidence < 0.7:
                        uncertain_cells.append((i, j))
            
            original_grid.append(grid_row)
            confidence_scores.append(conf_row)
            recognition_sources.append(sources_row)
        
        # Calculate overall accuracy estimate
        accuracy_estimate = total_confidence / digit_count if digit_count > 0 else 0.0
        
        processing_time = time.time() - start_time
        
        result = {
            "original_grid": original_grid,
            "solved_grid": None,  # Will be filled by solver
            "given_positions": given_positions,
            "confidence_scores": confidence_scores,
            "recognition_sources": recognition_sources,
            "uncertain_cells": uncertain_cells,
            "validation_conflicts": getattr(self, 'validation_conflicts', []),
            "processing_time": processing_time,
            "valid_puzzle": len(given_positions) >= 17,  # Minimum clues for valid Sudoku
            "unique_solution": False,  # Will be determined by solver
            "accuracy_estimate": accuracy_estimate,
            "grid_detected": grid_found
        }
        
        logger.info(f"OCR processing completed in {processing_time:.2f}s")
        logger.info(f"Detected {len(given_positions)} digits with {accuracy_estimate:.2%} average confidence")
        
        return result