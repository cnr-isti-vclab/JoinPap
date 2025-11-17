import sys
import os
import glob
import h5py
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QLabel, QAbstractItemView, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QFont

class QtFragmentMatchingWidget(QWidget):
    """
    A PyQt5 widget to browse and analyze merged fragment matching results
    from HDF5 files, based on the provided mocap.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # --- Data Storage ---
        # Stores data from HDF5 files (one dict per row)
        self.pair_data = [] 
        # Stores the current sorted index for the positioning arrows (one per row)
        self.current_position_indices = {}

        self._init_ui()

    def _init_ui(self):
        """Initializes all UI components."""
        self.setWindowTitle("Matching Fragments")
        main_layout = QVBoxLayout(self)

        # --- Top Button ---
        self.load_button = QPushButton("Load results")
        self.load_button.setFixedWidth(120)
        self.load_button.clicked.connect(self._load_results)
        
        top_bar_layout = QHBoxLayout()
        top_bar_layout.addWidget(self.load_button)
        top_bar_layout.addStretch(1)
        main_layout.addLayout(top_bar_layout)

        # --- Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Pairs", "Glob score", "Positioning", "Apply"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        # Set columns 1-3 to Interactive to allow dragging
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.table.setMinimumSize(600, 300)
        self.table.verticalHeader().setVisible(False)
        
        # Connect table selection event
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        
        main_layout.addWidget(self.table)

        # --- Bottom Buttons ---
        self.reset_button = QPushButton("Reset all")
        self.ok_button = QPushButton("Ok")
        
        bottom_button_layout = QHBoxLayout()
        bottom_button_layout.addStretch(1)
        bottom_button_layout.addWidget(self.reset_button)
        bottom_button_layout.addWidget(self.ok_button)
        
        main_layout.addLayout(bottom_button_layout)
        
        # Connect bottom button events
        self.reset_button.clicked.connect(self._on_reset_all)
        self.ok_button.clicked.connect(self._on_ok_clicked)

    @pyqtSlot()
    def _load_results(self):
        """
        Opens a dialog to select the 'merged' results folder and populates
        the table with data from all HDF5 files found.
        """
        folder_path = QFileDialog.getExistingDirectory(self, "Select Merged Results Folder")
        if not folder_path:
            return

        print(f"Loading results from: {folder_path}")
        
        # Clear existing data
        self.table.setRowCount(0)
        self.pair_data = []
        self.current_position_indices = {}
        
        hdf5_files = glob.glob(os.path.join(folder_path, "*.hdf5"))
        print(f"Found {len(hdf5_files)} HDF5 files.")

        for file_path in hdf5_files:
            try:
                with h5py.File(file_path, 'r') as f:
                    # 1. Read fragment names
                    frag_a = Path(f.attrs['fragment_a_recto']).stem
                    frag_b = Path(f.attrs['fragment_b_recto']).stem
                    pair_name = f"{frag_a} ↔ {frag_b}"

                    # 2. Read and process sum_scores_grid
                    sum_scores_grid = f['sum_scores_grid'][:]
                    if sum_scores_grid.size == 0:
                        print(f"Skipping {file_path} (empty sum_scores_grid)")
                        continue
                        
                    glob_score = np.max(sum_scores_grid)
                    
                    # 3. Get sorted indices and scores (as per logic)
                    sorted_indices_desc = np.argsort(sum_scores_grid.ravel())[::-1]
                    sorted_scores_desc = sum_scores_grid.ravel()[sorted_indices_desc]
                    
                    # 4. Store all data needed for interaction
                    data_dict = {
                        "file_path": file_path,
                        "pair_name": pair_name,
                        "glob_score": glob_score,
                        "sorted_indices_desc": sorted_indices_desc,
                        "sorted_scores_desc": sorted_scores_desc,
                        "grid": f['grid'][:],
                        "grid_to_translation_id_recto": f['grid_to_translation_id_recto'][:],
                        "translation_ids_recto": f['translation_ids_recto'][:],
                        "a_coords_recto": f['a_coords_recto'][:],
                        "b_coords_recto": f['b_coords_recto'][:],
                        "scores_recto": f['scores_recto'][:]
                    }
                    self.pair_data.append(data_dict)
                    
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
        
        # Now that all data is loaded, populate the table
        self._populate_table()

    def _populate_table(self):
        """Fills the QTableWidget with data loaded into self.pair_data."""
        self.table.setRowCount(len(self.pair_data))
        
        for row_index, data in enumerate(self.pair_data):
            # --- Cell 0: Pairs ---
            pair_item = QTableWidgetItem(data['pair_name'])
            pair_item.setFlags(pair_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row_index, 0, pair_item)

            # --- Cell 1: Glob score ---
            score_item = QTableWidgetItem(f"{data['glob_score']:.3f}")
            score_item.setFlags(score_item.flags() & ~Qt.ItemIsEditable)
            score_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_index, 1, score_item)

            # --- Cell 2: Positioning (Widget) ---
            self.current_position_indices[row_index] = 0 # Default to top score
            initial_score = data['sorted_scores_desc'][0]
            
            pos_widget = QWidget()
            pos_layout = QHBoxLayout(pos_widget)
            pos_layout.setContentsMargins(5, 0, 5, 0) # Add some spacing
            pos_layout.setSpacing(10)

            left_arrow = QPushButton("<")
            right_arrow = QPushButton(">")
            score_label = QLabel(f"{initial_score:.3f}")
            
            # Set fixed widths for consistent look
            left_arrow.setFixedWidth(30)
            right_arrow.setFixedWidth(30)
            score_label.setFixedWidth(50)
            score_label.setAlignment(Qt.AlignCenter)

            # Connect signals using lambda to pass row and direction
            # Per user request: Left arrow = next (+1), Right arrow = previous (-1)
            left_arrow.clicked.connect(lambda _, r=row_index: self._on_position_change(r, +1))
            right_arrow.clicked.connect(lambda _, r=row_index: self._on_position_change(r, -1))

            pos_layout.addWidget(left_arrow)
            pos_layout.addWidget(score_label)
            pos_layout.addWidget(right_arrow)
            
            self.table.setCellWidget(row_index, 2, pos_widget)
            
            # --- Cell 3: Apply (Button) ---
            apply_button = QPushButton("Apply")
            apply_button.clicked.connect(lambda _, r=row_index: self._on_apply_clicked(r))
            self.table.setCellWidget(row_index, 3, apply_button)

    @pyqtSlot(int, int)
    def _on_position_change(self, row, direction):
        """
        Handles clicks on the left/right positioning arrows for a given row.
        
        Args:
            row (int): The table row that was clicked.
            direction (int): +1 for next (left arrow), -1 for previous (right arrow).
        """
        data = self.pair_data[row]
        current_pos_idx = self.current_position_indices[row]
        
        # Calculate and clamp new index
        max_idx = len(data['sorted_scores_desc']) - 1
        new_pos_idx = max(0, min(current_pos_idx + direction, max_idx))

        if new_pos_idx == current_pos_idx and (direction == -1 and new_pos_idx == 0 or direction == 1 and new_pos_idx == max_idx):
             print(f"Row {row}: Reached end of scores.")
             return # No change

        self.current_position_indices[row] = new_pos_idx
        
        # --- Update UI ---
        new_score = data['sorted_scores_desc'][new_pos_idx]
        container = self.table.cellWidget(row, 2)
        score_label = container.layout().itemAt(1).widget()
        score_label.setText(f"{new_score:.3f}")

        # --- Execute Core Logic ---
        # 1. Get the index from the sorted list
        sorted_grid_index = data['sorted_indices_desc'][new_pos_idx]
        
        # 2. Find the coordinates from the grid
        position_coords = data['grid'][sorted_grid_index]
        
        # 3. Find the original translation_id using the reverse map
        translation_id = data['grid_to_translation_id_recto'][sorted_grid_index]
        
        # 4. Find all original data for that translation_id
        mask = (data['translation_ids_recto'] == translation_id)
        
        fine_scores = data['scores_recto'][mask]
        fine_a_coords = data['a_coords_recto'][mask]
        fine_b_coords = data['b_coords_recto'][mask]
        
        # --- Placeholder for "do other stuff" ---
        print("-" * 30)
        print(f"Row {row} | Position {new_pos_idx+1} / {max_idx+1}")
        print(f"  > Grid Score: {new_score:.4f}")
        print(f"  > Position (y,x): {position_coords}")
        print(f"  > Mapped Translation ID: {translation_id}")
        print(f"  > Found {len(fine_scores)} fine-grained patches for this T_ID.")
        # print(f"  > Fine Scores: {fine_scores}")
        # print(f"  > Fine A Coords: {fine_a_coords}")
        # print(f"  > Fine B Coords: {fine_b_coords}")
        print("-" * 30)
        
    @pyqtSlot()
    def _on_row_selected(self):
        """Placeholder: Called when a table row is selected."""
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            selected_row_index = selected_rows[0].row()
            print(f"Row {selected_row_index} selected.")
            # You can access data via: self.pair_data[selected_row_index]

    @pyqtSlot(int)
    def _on_apply_clicked(self, row):
        """Placeholder: Called when the 'Apply' button for a row is clicked."""
        current_pos_idx = self.current_position_indices[row]
        print(f"Apply button clicked for row {row} at position index {current_pos_idx}.")
        # You can access all data for this state similar to _on_position_change

    @pyqtSlot()
    def _on_reset_all(self):
        """Placeholder: Called when 'Reset all' button is clicked."""
        print("Reset all clicked.")

    @pyqtSlot()
    def _on_ok_clicked(self):
        """Placeholder: Called when 'Ok' button is clicked."""
        print("Ok clicked.")
        # self.close() # Example: close the widget