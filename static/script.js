// AI Sudoku Solver - Frontend JavaScript
class SudokuSolver {
    constructor() {
        this.currentFile = null;
        this.currentResult = null;
        this.correctionMode = false;
        this.correctedGrid = null;
        this.currentEditCell = null;
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // File upload
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        
        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
        uploadArea.addEventListener('dragleave', this.handleDragLeave.bind(this));
        uploadArea.addEventListener('drop', this.handleDrop.bind(this));
        
        fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        
        // Buttons
        document.getElementById('processBtn').addEventListener('click', this.processImage.bind(this));
        document.getElementById('clearBtn').addEventListener('click', this.clearImage.bind(this));
        document.getElementById('newPuzzleBtn').addEventListener('click', this.resetApp.bind(this));
        document.getElementById('correctBtn').addEventListener('click', this.enterCorrectionMode.bind(this));
        document.getElementById('applyCorrectionBtn').addEventListener('click', this.applyCorrections.bind(this));
        document.getElementById('cancelCorrectionBtn').addEventListener('click', this.cancelCorrections.bind(this));
        document.getElementById('downloadBtn').addEventListener('click', this.downloadSolution.bind(this));
        document.getElementById('shareBtn').addEventListener('click', this.shareResult.bind(this));
        
        // Modal
        document.getElementById('closeModal').addEventListener('click', this.closeModal.bind(this));
        document.getElementById('cancelEdit').addEventListener('click', this.closeModal.bind(this));
        document.getElementById('saveEdit').addEventListener('click', this.saveCellEdit.bind(this));
        
        // Close modal when clicking outside
        document.getElementById('cellModal').addEventListener('click', (e) => {
            if (e.target.id === 'cellModal') {
                this.closeModal();
            }
        });
    }

    // Drag and drop handlers
    handleDragOver(e) {
        e.preventDefault();
        document.getElementById('uploadArea').classList.add('dragover');
    }

    handleDragLeave(e) {
        e.preventDefault();
        document.getElementById('uploadArea').classList.remove('dragover');
    }

    handleDrop(e) {
        e.preventDefault();
        document.getElementById('uploadArea').classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.handleFile(files[0]);
        }
    }

    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.handleFile(file);
        }
    }

    handleFile(file) {
        if (!file.type.startsWith('image/')) {
            this.showError('Please select an image file (PNG, JPG, JPEG)');
            return;
        }

        this.currentFile = file;
        this.previewImage(file);
    }

    previewImage(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const previewImg = document.getElementById('previewImg');
            previewImg.src = e.target.result;
            document.getElementById('imagePreview').style.display = 'block';
            this.hideResults();
        };
        reader.readAsDataURL(file);
    }

    clearImage() {
        this.currentFile = null;
        document.getElementById('fileInput').value = '';
        document.getElementById('imagePreview').style.display = 'none';
        this.hideResults();
        this.hideMessages();
    }

    async processImage() {
        if (!this.currentFile) {
            this.showError('Please select an image first');
            return;
        }

        this.showLoading();
        this.hideMessages();

        try {
            const formData = new FormData();
            formData.append('file', this.currentFile);

            const response = await fetch('/solve', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Server error');
            }

            const result = await response.json();
            this.currentResult = result;
            this.displayResults(result);
            this.showSuccess('Puzzle processed successfully!');

        } catch (error) {
            console.error('Error processing image:', error);
            this.showError(`Error processing image: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }

    displayResults(result) {
        // Update stats
        document.getElementById('accuracyStat').textContent = 
            `${(result.accuracy_estimate * 100).toFixed(1)}%`;
        document.getElementById('digitsStat').textContent = result.given_positions.length;
        document.getElementById('timeStat').textContent = `${result.processing_time.toFixed(2)}s`;
        document.getElementById('statusStat').textContent = 
            result.unique_solution ? '✓ Solved' : '⚠ Issues';

        // Display grids
        this.displayGrid('detectedGrid', result.original_grid, result, 'detected');
        if (result.solved_grid) {
            this.displayGrid('solutionGrid', result.solved_grid, result, 'solution');
        } else {
            document.getElementById('solutionGrid').innerHTML = 
                '<div style="text-align: center; color: #999; padding: 40px;">No solution available</div>';
        }

        // Show results section
        document.getElementById('results').style.display = 'block';
        
        // Scroll to results
        document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
    }

    displayGrid(containerId, grid, result, type) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';

        for (let i = 0; i < 9; i++) {
            for (let j = 0; j < 9; j++) {
                const cell = document.createElement('div');
                cell.className = 'sudoku-cell';
                cell.textContent = grid[i][j] || '';
                
                // Add cell classes based on type and data
                if (type === 'detected') {
                    if (grid[i][j] !== 0) {
                        cell.classList.add('given');
                        
                        // Check if this is an uncertain cell
                        if (result.uncertain_cells.some(pos => pos[0] === i && pos[1] === j)) {
                            cell.classList.add('uncertain');
                        }
                        
                        // Check if this is an enhanced recovery
                        const sources = result.recognition_sources[i][j];
                        if (sources && sources.includes('enhanced_recovery')) {
                            cell.classList.add('enhanced');
                        }
                    }
                    
                    // Add click handler for correction mode
                    cell.addEventListener('click', () => this.handleCellClick(i, j, cell));
                    
                } else if (type === 'solution') {
                    if (result.original_grid[i][j] !== 0) {
                        cell.classList.add('given');
                    } else {
                        cell.classList.add('solved');
                    }
                }

                container.appendChild(cell);
            }
        }
    }

    handleCellClick(row, col, cellElement) {
        if (!this.correctionMode) return;

        this.currentEditCell = { row, col, element: cellElement };
        this.openCellEditModal(row, col);
    }

    openCellEditModal(row, col) {
        const currentGrid = this.correctedGrid || this.currentResult.original_grid;
        const currentValue = currentGrid[row][col];
        
        document.getElementById('cellPosition').textContent = `(${row + 1}, ${col + 1})`;
        document.getElementById('currentValue').textContent = currentValue || 'Empty';
        document.getElementById('newValue').value = currentValue;
        document.getElementById('cellModal').style.display = 'block';
        
        // Focus and select the input
        setTimeout(() => {
            const input = document.getElementById('newValue');
            input.focus();
            input.select();
        }, 100);
    }

    closeModal() {
        document.getElementById('cellModal').style.display = 'none';
        this.currentEditCell = null;
    }

    saveCellEdit() {
        if (!this.currentEditCell) return;

        const newValue = parseInt(document.getElementById('newValue').value) || 0;
        const { row, col, element } = this.currentEditCell;

        // Initialize corrected grid if not exists
        if (!this.correctedGrid) {
            this.correctedGrid = this.currentResult.original_grid.map(row => [...row]);
        }

        // Update the corrected grid
        this.correctedGrid[row][col] = newValue;

        // Update the display
        element.textContent = newValue || '';
        if (newValue !== 0) {
            element.classList.add('given');
            element.style.backgroundColor = '#e3f2fd'; // Light blue for edited cells
        } else {
            element.classList.remove('given');
            element.style.backgroundColor = '';
        }

        this.closeModal();
    }

    enterCorrectionMode() {
        this.correctionMode = true;
        document.getElementById('correctionMode').style.display = 'block';
        document.getElementById('correctBtn').style.display = 'none';
        
        // Highlight correctable cells
        const cells = document.querySelectorAll('#detectedGrid .sudoku-cell');
        cells.forEach(cell => {
            cell.style.cursor = 'pointer';
            cell.style.border = '2px solid #007bff';
        });
    }

    async applyCorrections() {
        if (!this.correctedGrid) {
            this.showError('No corrections made');
            return;
        }

        this.showLoading();
        
        try {
            // Create a mock result with corrected grid
            const correctedResult = {
                ...this.currentResult,
                original_grid: this.correctedGrid,
                given_positions: []
            };

            // Count non-zero positions
            for (let i = 0; i < 9; i++) {
                for (let j = 0; j < 9; j++) {
                    if (this.correctedGrid[i][j] !== 0) {
                        correctedResult.given_positions.push([i, j]);
                    }
                }
            }

            // Try to solve the corrected puzzle
            const response = await this.solveCorrectedPuzzle(this.correctedGrid);
            if (response) {
                correctedResult.solved_grid = response.solved_grid;
                correctedResult.valid_puzzle = response.valid_puzzle;
                correctedResult.unique_solution = response.unique_solution;
            }

            this.currentResult = correctedResult;
            this.displayResults(correctedResult);
            this.exitCorrectionMode();
            this.showSuccess('Corrections applied and puzzle re-solved!');

        } catch (error) {
            this.showError(`Error applying corrections: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }

    async solveCorrectedPuzzle(grid) {
        // In a real implementation, you would send the corrected grid to a solve endpoint
        // For now, we'll use a simple client-side validation and solving attempt
        
        try {
            const solver = new ClientSudokuSolver();
            const solution = solver.solve(grid.map(row => [...row]));
            
            return {
                solved_grid: solution,
                valid_puzzle: solution !== null,
                unique_solution: solution !== null
            };
        } catch (error) {
            console.error('Client-side solving failed:', error);
            return null;
        }
    }

    cancelCorrections() {
        this.correctedGrid = null;
        this.exitCorrectionMode();
        // Refresh the original display
        this.displayResults(this.currentResult);
    }

    exitCorrectionMode() {
        this.correctionMode = false;
        document.getElementById('correctionMode').style.display = 'none';
        document.getElementById('correctBtn').style.display = 'inline-flex';
        
        // Remove correction mode styling
        const cells = document.querySelectorAll('#detectedGrid .sudoku-cell');
        cells.forEach(cell => {
            cell.style.cursor = '';
            cell.style.border = '1px solid #ddd';
        });
    }

    downloadSolution() {
        if (!this.currentResult || !this.currentResult.solved_grid) {
            this.showError('No solution available to download');
            return;
        }

        const solution = this.currentResult.solved_grid;
        let content = 'AI Sudoku Solver - Solution\\n\\n';
        
        content += 'Original Grid:\\n';
        content += this.gridToString(this.currentResult.original_grid) + '\\n\\n';
        
        content += 'Complete Solution:\\n';
        content += this.gridToString(solution) + '\\n\\n';
        
        content += `Processing Time: ${this.currentResult.processing_time.toFixed(2)}s\\n`;
        content += `OCR Accuracy: ${(this.currentResult.accuracy_estimate * 100).toFixed(1)}%\\n`;
        content += `Digits Detected: ${this.currentResult.given_positions.length}\\n`;

        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `sudoku_solution_${new Date().getTime()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    shareResult() {
        if (!this.currentResult) {
            this.showError('No result to share');
            return;
        }

        const text = `I solved a Sudoku puzzle using AI! 🤖\\n` +
                    `OCR Accuracy: ${(this.currentResult.accuracy_estimate * 100).toFixed(1)}%\\n` +
                    `Processing Time: ${this.currentResult.processing_time.toFixed(2)}s\\n` +
                    `Digits Found: ${this.currentResult.given_positions.length}`;

        if (navigator.share) {
            navigator.share({
                title: 'AI Sudoku Solver Result',
                text: text
            });
        } else {
            // Fallback: copy to clipboard
            navigator.clipboard.writeText(text).then(() => {
                this.showSuccess('Result copied to clipboard!');
            }).catch(() => {
                this.showError('Could not copy to clipboard');
            });
        }
    }

    gridToString(grid) {
        let result = '';
        for (let i = 0; i < 9; i++) {
            for (let j = 0; j < 9; j++) {
                result += (grid[i][j] || '.') + ' ';
                if (j === 2 || j === 5) result += '| ';
            }
            result += '\\n';
            if (i === 2 || i === 5) {
                result += '------+-------+------\\n';
            }
        }
        return result;
    }

    resetApp() {
        this.currentFile = null;
        this.currentResult = null;
        this.correctionMode = false;
        this.correctedGrid = null;
        
        document.getElementById('fileInput').value = '';
        document.getElementById('imagePreview').style.display = 'none';
        this.hideResults();
        this.hideMessages();
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    showLoading() {
        document.getElementById('loading').style.display = 'block';
    }

    hideLoading() {
        document.getElementById('loading').style.display = 'none';
    }

    showResults() {
        document.getElementById('results').style.display = 'block';
    }

    hideResults() {
        document.getElementById('results').style.display = 'none';
    }

    showError(message) {
        const errorDiv = document.getElementById('errorMessage');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }

    showSuccess(message) {
        const successDiv = document.getElementById('successMessage');
        successDiv.textContent = message;
        successDiv.style.display = 'block';
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            successDiv.style.display = 'none';
        }, 3000);
    }

    hideMessages() {
        document.getElementById('errorMessage').style.display = 'none';
        document.getElementById('successMessage').style.display = 'none';
    }
}

// Simple client-side Sudoku solver for corrections
class ClientSudokuSolver {
    solve(grid) {
        const solution = this.deepCopy(grid);
        
        if (this.solveSudoku(solution)) {
            return solution;
        }
        
        return null; // No solution found
    }

    solveSudoku(grid) {
        for (let row = 0; row < 9; row++) {
            for (let col = 0; col < 9; col++) {
                if (grid[row][col] === 0) {
                    for (let num = 1; num <= 9; num++) {
                        if (this.isValid(grid, row, col, num)) {
                            grid[row][col] = num;
                            
                            if (this.solveSudoku(grid)) {
                                return true;
                            }
                            
                            grid[row][col] = 0; // Backtrack
                        }
                    }
                    return false;
                }
            }
        }
        return true;
    }

    isValid(grid, row, col, num) {
        // Check row
        for (let j = 0; j < 9; j++) {
            if (grid[row][j] === num) return false;
        }

        // Check column
        for (let i = 0; i < 9; i++) {
            if (grid[i][col] === num) return false;
        }

        // Check 3x3 box
        const boxRow = Math.floor(row / 3) * 3;
        const boxCol = Math.floor(col / 3) * 3;
        
        for (let i = boxRow; i < boxRow + 3; i++) {
            for (let j = boxCol; j < boxCol + 3; j++) {
                if (grid[i][j] === num) return false;
            }
        }

        return true;
    }

    deepCopy(grid) {
        return grid.map(row => [...row]);
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new SudokuSolver();
});