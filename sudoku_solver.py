#!/usr/bin/env python3
"""
Sudoku solver implementation for the complete solution
"""

import numpy as np
from typing import List, Tuple, Optional

class SudokuSolver:
    def __init__(self):
        """Initialize the Sudoku solver."""
        self.grid = None
    
    def is_valid(self, grid: List[List[int]], row: int, col: int, num: int) -> bool:
        """Check if placing num at (row, col) is valid"""
        
        # Check row
        for j in range(9):
            if grid[row][j] == num:
                return False
        
        # Check column
        for i in range(9):
            if grid[i][col] == num:
                return False
        
        # Check 3x3 box
        box_row = (row // 3) * 3
        box_col = (col // 3) * 3
        
        for i in range(box_row, box_row + 3):
            for j in range(box_col, box_col + 3):
                if grid[i][j] == num:
                    return False
        
        return True
    
    def solve(self, grid: List[List[int]]) -> bool:
        """Solve the Sudoku puzzle using backtracking"""
        
        # Find empty cell
        for i in range(9):
            for j in range(9):
                if grid[i][j] == 0:
                    # Try numbers 1-9
                    for num in range(1, 10):
                        if self.is_valid(grid, i, j, num):
                            grid[i][j] = num
                            
                            if self.solve(grid):
                                return True
                            
                            # Backtrack
                            grid[i][j] = 0
                    
                    return False
        
        return True
    
    def validate_puzzle(self, grid: List[List[int]]) -> Tuple[bool, List[str]]:
        """Validate if the puzzle has a valid setup (no conflicts)"""
        
        errors = []
        
        # Check each filled cell for conflicts
        for i in range(9):
            for j in range(9):
                if grid[i][j] != 0:
                    num = grid[i][j]
                    
                    # Temporarily remove the number to check validity
                    grid[i][j] = 0
                    
                    if not self.is_valid(grid, i, j, num):
                        errors.append(f"Conflict at ({i},{j}) with digit {num}")
                    
                    # Restore the number
                    grid[i][j] = num
        
        return len(errors) == 0, errors
    
    def get_candidates(self, grid: List[List[int]], row: int, col: int) -> List[int]:
        """Get possible candidates for a cell"""
        
        if grid[row][col] != 0:
            return []
        
        candidates = []
        for num in range(1, 10):
            if self.is_valid(grid, row, col, num):
                candidates.append(num)
        
        return candidates
    
    def solve_with_steps(self, grid: List[List[int]]) -> Tuple[bool, List[List[int]], int]:
        """Solve and return intermediate steps"""
        
        # Make a copy to work with
        working_grid = [row[:] for row in grid]
        steps = []
        iterations = 0
        
        def solve_recursive(current_grid):
            nonlocal iterations
            iterations += 1
            
            if iterations > 100000:  # Prevent infinite loops
                return False
            
            # Save current state
            steps.append([row[:] for row in current_grid])
            
            # Find empty cell
            for i in range(9):
                for j in range(9):
                    if current_grid[i][j] == 0:
                        # Try numbers 1-9
                        for num in range(1, 10):
                            if self.is_valid(current_grid, i, j, num):
                                current_grid[i][j] = num
                                
                                if solve_recursive(current_grid):
                                    return True
                                
                                # Backtrack
                                current_grid[i][j] = 0
                        
                        return False
            
            return True
        
        success = solve_recursive(working_grid)
        return success, steps, iterations

def create_sudoku_validator():
    """Create validation utilities for OCR results"""
    
    class SudokuValidator:
        def __init__(self):
            self.solver = SudokuSolver()
        
        def validate_ocr_result(self, detected_grid: List[List[int]]) -> dict:
            """Validate OCR detected grid and suggest corrections"""
            
            result = {
                'is_valid': False,
                'errors': [],
                'suggestions': [],
                'confidence': 0.0,
                'solvable': False
            }
            
            # Check basic validity
            is_valid, errors = self.solver.validate_puzzle(detected_grid)
            result['is_valid'] = is_valid
            result['errors'] = errors
            
            if not is_valid:
                result['suggestions'] = self.suggest_corrections(detected_grid, errors)
            
            # Check if solvable
            test_grid = [row[:] for row in detected_grid]
            result['solvable'] = self.solver.solve(test_grid)
            
            # Calculate confidence based on filled cells and validity
            filled_cells = sum(1 for row in detected_grid for cell in row if cell != 0)
            result['confidence'] = min(1.0, filled_cells / 17)  # Minimum 17 clues needed
            
            if is_valid and result['solvable']:
                result['confidence'] = 1.0
            
            return result
        
        def suggest_corrections(self, grid: List[List[int]], errors: List[str]) -> List[dict]:
            """Suggest corrections for invalid configurations"""
            
            suggestions = []
            
            for error in errors:
                # Parse error message to extract position and digit
                if "Conflict at" in error:
                    # Extract position and digit from error message
                    import re
                    match = re.search(r'\((\d+),(\d+)\).*digit (\d+)', error)
                    if match:
                        row, col, digit = int(match.group(1)), int(match.group(2)), int(match.group(3))
                        
                        # Get valid candidates for this position
                        test_grid = [r[:] for r in grid]
                        test_grid[row][col] = 0  # Remove conflicting digit
                        
                        candidates = self.solver.get_candidates(test_grid, row, col)
                        
                        suggestions.append({
                            'position': (row, col),
                            'current_digit': digit,
                            'suggested_digits': candidates,
                            'error': error
                        })
            
            return suggestions
        
        def get_solving_hints(self, grid: List[List[int]]) -> List[dict]:
            """Get hints for solving the puzzle"""
            
            hints = []
            
            for i in range(9):
                for j in range(9):
                    if grid[i][j] == 0:
                        candidates = self.solver.get_candidates(grid, i, j)
                        
                        if len(candidates) == 1:
                            hints.append({
                                'position': (i, j),
                                'digit': candidates[0],
                                'reason': 'Only possible candidate',
                                'difficulty': 'easy'
                            })
                        elif len(candidates) == 2:
                            hints.append({
                                'position': (i, j),
                                'candidates': candidates,
                                'reason': 'Two possible candidates',
                                'difficulty': 'medium'
                            })
            
            return sorted(hints, key=lambda x: len(x.get('candidates', [x['digit']])))
    
    return SudokuValidator()

def main():
    """Test the Sudoku solver with our enhanced OCR result"""
    
    print("🧩 SUDOKU SOLVER TEST")
    print("="*30)
    
    # Our enhanced OCR result (38/38 digits detected)
    detected_grid = [
        [3, 0, 5, 0, 0, 0, 1, 0, 8],
        [0, 9, 0, 0, 5, 1, 7, 2, 0],
        [0, 7, 0, 2, 3, 0, 6, 4, 5],
        [0, 0, 7, 0, 4, 2, 0, 8, 1],  # ← Recovered digit 7 at (3,2)
        [0, 8, 0, 0, 0, 0, 9, 0, 0],
        [1, 0, 9, 0, 0, 0, 0, 7, 0],
        [0, 3, 2, 4, 0, 8, 5, 1, 7],
        [0, 1, 0, 0, 0, 5, 4, 0, 0],
        [6, 0, 0, 0, 9, 0, 8, 0, 0]
    ]
    
    print("Detected Grid (38 digits):")
    for i, row in enumerate(detected_grid):
        print(f"Row {i}: {' '.join(str(x) if x != 0 else '.' for x in row)}")
    
    # Validate the puzzle
    validator = create_sudoku_validator()
    validation = validator.validate_ocr_result(detected_grid)
    
    print(f"\n📊 VALIDATION RESULTS:")
    print(f"Valid configuration: {validation['is_valid']}")
    print(f"Solvable: {validation['solvable']}")
    print(f"Confidence: {validation['confidence']:.2f}")
    
    if validation['errors']:
        print(f"Errors: {len(validation['errors'])}")
        for error in validation['errors'][:3]:
            print(f"  - {error}")
    
    # Try to solve
    if validation['solvable']:
        print(f"\n🎯 SOLVING PUZZLE...")
        
        solver = SudokuSolver()
        solution_grid = [row[:] for row in detected_grid]
        
        if solver.solve(solution_grid):
            print("✅ PUZZLE SOLVED!")
            print("\nComplete Solution:")
            for i, row in enumerate(solution_grid):
                print(f"Row {i}: {' '.join(str(x) for x in row)}")
        else:
            print("❌ Could not solve puzzle")
    else:
        print(f"\n❌ Puzzle is not solvable")
        
        if validation['suggestions']:
            print("Suggested corrections:")
            for suggestion in validation['suggestions'][:3]:
                pos = suggestion['position']
                print(f"  - Cell ({pos[0]},{pos[1]}): Try {suggestion['suggested_digits']}")

if __name__ == "__main__":
    main()