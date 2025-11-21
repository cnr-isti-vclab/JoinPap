import sys
import os
import glob
import h5py
import numpy as np
import pandas as pd
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QLabel, QAbstractItemView, QSpacerItem, QSizePolicy, QLineEdit, QCheckBox, QGraphicsEllipseItem
)
from PyQt5.QtCore import Qt, pyqtSlot, QSettings
from PyQt5.QtGui import QFont, QBrush, QPen

class QtFragmentMatchingWidget(QWidget):
    """
    A PyQt5 widget to browse and analyze merged fragment matching results
    from HDF5 files, based on the provided mocap.
    """
    def __init__(self, viewerplus, parent=None):
        super().__init__(parent)
        self.viewerplus = viewerplus
        self.project = viewerplus.project
        
        # --- Data Storage ---
        # Stores data from HDF5 files (one dict per row)
        self.pair_data = [] 
        # Stores the current sorted index for the positioning arrows (one per row)
        self.current_position_indices = {}
        self.current_solo_checked = {}
        self.current_flip_checked = {}

        # List for containing matching points drawn on the screen
        self.matching_points = []

        # --- Memorize initial fragment positions ---
        self.initial_fragment_positions = {}
        for frag in self.project.fragments:
            self.initial_fragment_positions[Path(frag.filename).stem] = frag.getBoundingBox()[:2]

        # --- Initialize UI ---
        self._init_ui()

        # --- Load initial results ---
        self.settings = QSettings("VCLAB-AIMH", "PIUI")
        folder_path = self.settings.value("matching-fragments-path", defaultValue="ai_data_dgx")
        self._load_results(folder_path=folder_path)

    def _init_ui(self):
        """Initializes all UI components."""
        self.setWindowTitle("Matching Fragments")
        main_layout = QVBoxLayout(self)

        # --- Top Button ---
        self.load_button = QPushButton("Pick Folder")
        self.load_button.setFixedWidth(120)
        self.load_button.clicked.connect(self._load_results)

        # --- Checkbox for showing points ---
        show_matching_points = QCheckBox("Show Matching Points")
        show_matching_points.setChecked(True)
        show_matching_points.stateChanged[int].connect(self.change_matching_points_visibility)
        
        top_bar_layout = QHBoxLayout()
        top_bar_layout.addWidget(self.load_button)
        top_bar_layout.addWidget(show_matching_points)
        top_bar_layout.addStretch(1)
        main_layout.addLayout(top_bar_layout)

        # --- Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Pairs", "Glob score", "Positioning", "Solo", "Flip A<->B", "Apply"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents) # Solo
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents) # Flip
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents) # Apply
        
        self.table.setMinimumSize(1000, 300)
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

    @pyqtSlot(int)
    def change_matching_points_visibility(self, visible):
        """
        Changes the visibility of the points provided in items_list.
        
        Args:
            items_list (list): List of QGraphicsItem objects.
            visible (bool): True to make visible, False to hide.
        """
        if not self.matching_points:
            return

        for item in self.matching_points:
            item.setVisible(visible)

    @pyqtSlot()
    def _load_results(self, folder_path=None):
        """
        Opens a dialog to select the 'merged' results folder and populates
        the table with data from all HDF5 files found.
        """
        hdf5_files_found = folder_path and (Path(folder_path) / "merged").is_dir()
        while not hdf5_files_found:
            folder_path = QFileDialog.getExistingDirectory(self, "Select Results Folder")
            if folder_path == "":
                self.close()
                return

            print(f"Loading results from: {folder_path}")
            
            hdf5_files = glob.glob(os.path.join(folder_path, "merged", "*.hdf5"))
            print(f"Found {len(hdf5_files)} HDF5 files.")
            hdf5_files_found = len(hdf5_files) > 0

        QApplication.setOverrideCursor(Qt.WaitCursor)
        hdf5_files = glob.glob(os.path.join(folder_path, "merged", "*.hdf5"))
        # Set this folder to be used from this point on in successive sessions
        self.settings.setValue("matching-fragments-path", folder_path)

        # Clear existing data
        self.table.setRowCount(0)
        self.pair_data = []

        loaded_fragments_names = [Path(f.filename).stem for f in self.project.fragments]
        loaded_data = []

        for file_path in hdf5_files:
            try:
                with h5py.File(file_path, 'r') as f:
                    # 1. Read fragment names
                    frag_a = Path(f.attrs['fragment_a_recto']).stem
                    frag_b = Path(f.attrs['fragment_b_recto']).stem

                    if frag_a not in loaded_fragments_names or frag_b not in loaded_fragments_names:
                        print(f"Skipping {file_path} (fragments not loaded in viewer)")
                        continue
                    
                    pair_name = f"{frag_a} ↔ {frag_b}"

                    # 2. Read and process sum_scores_grid
                    sum_scores_grid = f['sum_scores_grid'][:]
                    grid_to_tid = f['grid_to_translation_id_recto'][:] # Use this for grouping
                    if sum_scores_grid.size == 0:
                        print(f"Skipping {file_path} (empty sum_scores_grid)")
                        continue
                        
                    glob_score = np.max(sum_scores_grid)
                    
                    # 3. Get sorted indices and scores (as per logic)
                    df_agg = pd.DataFrame({
                        'score': sum_scores_grid.ravel(),
                        'translation_id': grid_to_tid.ravel()
                    })
                    
                    # Group by T_ID and calculate the max score for all grid points
                    # mapped to that T_ID.
                    aggregated_scores = df_agg.groupby('translation_id')['score'].max()
                    
                    # Sort the unique T_IDs based on their aggregated mean score
                    sorted_agg_t_ids = aggregated_scores.sort_values(ascending=False).index.to_numpy()
                    sorted_agg_scores = aggregated_scores.sort_values(ascending=False).to_numpy()
                    
                    # 4. Store all data needed for interaction
                    data_dict = {
                        "pair": (frag_a, frag_b),
                        "file_path": file_path,
                        "pair_name": pair_name,
                        "glob_score": glob_score,
                        "sorted_agg_t_ids": sorted_agg_t_ids,
                        "sorted_agg_scores": sorted_agg_scores,
                        "grid": f['grid'][:],
                        "grid_to_translation_id_recto": f['grid_to_translation_id_recto'][:],
                        "translation_ids_recto": f['translation_ids_recto'][:],
                        "a_coords_recto": f['a_coords_recto'][:],
                        "b_coords_recto": f['b_coords_recto'][:],
                        "t_relatives_recto": f['t_relatives_recto'][:],
                        "scores_recto": f['scores_recto'][:]
                    }
                    loaded_data.append(data_dict)
                    
            except Exception as e:
                print(f"Error loading {file_path}: {e}")

        self.pair_data = sorted(loaded_data, key=lambda x: x['glob_score'], reverse=True)
        
        # Now that all data is loaded, populate the table
        self._populate_table()

        # Restore cursor
        QApplication.restoreOverrideCursor()

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
            self.current_solo_checked[row_index] = False # Default solo unchecked
            self.current_flip_checked[row_index] = False # Default flip unchecked

            initial_score = data['sorted_agg_scores'][0]
            
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
            
            # --- Cell 3: Solo (Checkbox) ---
            solo_checkbox = QCheckBox()
            solo_widget = QWidget()
            solo_layout = QHBoxLayout(solo_widget)
            solo_layout.addWidget(solo_checkbox, 0, Qt.AlignCenter)
            solo_layout.setContentsMargins(0, 0, 0, 0)
            solo_widget.setLayout(solo_layout)
            solo_checkbox.stateChanged.connect(lambda state, r=row_index: self._on_solo_changed(r, state))
            self.table.setCellWidget(row_index, 3, solo_widget)

            # --- Cell 4: Flip A<->B (Checkbox) ---
            flip_checkbox = QCheckBox()
            flip_widget = QWidget()
            flip_layout = QHBoxLayout(flip_widget)
            flip_layout.addWidget(flip_checkbox, 0, Qt.AlignCenter)
            flip_layout.setContentsMargins(0, 0, 0, 0)
            flip_widget.setLayout(flip_layout)
            flip_checkbox.stateChanged.connect(lambda state, r=row_index: self._on_flip_changed(r, state))
            self.table.setCellWidget(row_index, 4, flip_widget)
            
            # --- Cell 5: Apply (Button) ---
            apply_button = QPushButton("Apply")
            apply_button.clicked.connect(lambda _, r=row_index: self._on_apply_clicked(r))
            self.table.setCellWidget(row_index, 5, apply_button)

    @pyqtSlot(int, int)
    def _on_position_change(self, row, direction):
        """
        Handles clicks on the left/right positioning arrows for a given row.
        
        Args:
            row (int): The table row that was clicked.
            direction (int): +1 for next (left arrow), -1 for previous (right arrow).
        """

        # First, reset all fragments to initial positions
        self._on_reset_all(reset_interface=False)
        self._remove_matching_points()

        # select this row of the table, in case not already selected
        self.table.blockSignals(True)
        self.table.selectRow(row)
        self.table.blockSignals(False)

        # Re-enable apply button
        if direction != 0:
            apply_button = self.table.cellWidget(row, 5)
            apply_button.setEnabled(True)

        data = self.pair_data[row]
        current_pos_idx = self.current_position_indices[row]
        
        # Calculate and clamp new index
        max_idx = len(data['sorted_agg_scores']) - 1
        new_pos_idx = max(0, min(current_pos_idx + direction, max_idx))

        if new_pos_idx == current_pos_idx and (direction == -1 and new_pos_idx == 0 or direction == 1 and new_pos_idx == max_idx):
             print(f"Row {row}: Reached end of scores.")
             return # No change

        self.current_position_indices[row] = new_pos_idx
        
        # --- Update UI ---
        new_score = data['sorted_agg_scores'][new_pos_idx]
        container = self.table.cellWidget(row, 2)
        score_label = container.layout().itemAt(1).widget()
        score_label.setText(f"{new_score:.3f}")

        # --- Execute Core Logic ---
        
        # Find the original translation_id using the reverse map
        translation_id = data['sorted_agg_t_ids'][new_pos_idx]
        
        # Find all original data for that translation_id
        mask = (data['translation_ids_recto'] == translation_id)
        
        fine_scores = data['scores_recto'][mask]
        fine_a_coords = data['a_coords_recto'][mask]
        fine_b_coords = data['b_coords_recto'][mask]
        precise_relative_position = data['t_relatives_recto'][mask][0]

        if self.current_flip_checked[row]:
            pair = data['pair'][::-1]
            rel_pos = -precise_relative_position
            fine_coords = fine_b_coords
        else:
            pair = data['pair']
            rel_pos = precise_relative_position
            fine_coords = fine_a_coords
        self._preview_fragment_movement(row, pair, rel_pos)
        self._draw_matching_points(pair, fine_scores, fine_coords)

    def _draw_matching_points(self, pair, fine_scores, fine_a_coords):
        """
        Draws points on the qgraphicview based on coordinates and scores.
        
        Args:
            qgraphicview (QGraphicsView): The view containing the scene to draw on.
            fine_scores (array-like): Shape [N], scores determining color.
            fine_a_coords (array-like): Shape [N, 2], (x, y) coordinates.
            
        Returns:
            list: A list of QGraphicsItem objects that were added to the scene.
        """
        scene = self.viewerplus.scene
        self.matching_points = []
        
        # Point radius
        radius = 30
        diameter = radius * 2

        # Iterate through scores and coords simultaneously
        for score, (y, x) in zip(fine_scores, fine_a_coords):
            
            # Determine color based on score thresholds
            if score > 0.7:
                color = Qt.yellow
            elif score > 0.4:
                color = Qt.cyan
            else:
                color = Qt.black

            # Compute scene coordinates
            frag_a_name, _ = pair
            frag_a = next((f for f in self.project.fragments if Path(f.filename).stem == frag_a_name), None)
            y_frag, x_frag = frag_a.getBoundingBox()[:2]

            x = x + x_frag
            y = y + y_frag

            # Create the point (Ellipse)
            # x and y are usually center points, so we offset by radius to center the circle
            point_item = QGraphicsEllipseItem(x - radius, y - radius, diameter, diameter)
            
            # Set the fill color (Brush)
            point_item.setBrush(QBrush(color))
            
            # Set the border (Pen). 
            # Using NoPen makes them look like solid dots. 
            # If you want a border, use QPen(Qt.black, 1)
            point_item.setPen(QPen(Qt.NoPen))

            # Set Z-value to ensure points are drawn on top of other elements
            point_item.setZValue(100)
            
            # Add to scene and tracking list
            scene.addItem(point_item)
            self.matching_points.append(point_item)
        

    def _remove_matching_points(self):
        """
        Removes the specific points provided in items_list from the view's scene.
        """
        scene = self.viewerplus.scene
        if scene is None or not self.matching_points:
            return

        for item in self.matching_points:
            # Check if the item is actually in the scene before trying to remove
            if item.scene() == scene:
                scene.removeItem(item)
        
        # Clear the python list reference
        self.matching_points = []
        
    @pyqtSlot()
    def _on_row_selected(self):
        """Placeholder: Called when a table row is selected."""
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            selected_row_index = selected_rows[0].row()
            # get direction 
            self._on_position_change(selected_row_index, 0)  # 0 means no change, just to trigger any needed updates

    @pyqtSlot(int)
    def _on_apply_clicked(self, row):
        """Placeholder: Called when the 'Apply' button for a row is clicked."""
        
        # overwrite the initial positions to the current one for the frag a and b pair
        data = self.pair_data[row]
        pair = data['pair']
        frag_a_name, frag_b_name = pair
        frag_a = next((f for f in self.project.fragments if Path(f.filename).stem == frag_a_name), None)
        frag_b = next((f for f in self.project.fragments if Path(f.filename).stem == frag_b_name), None)
        if not frag_a or not frag_b:
            print(f"Fragments {frag_a_name} or {frag_b_name} not found in project.")
            return
        # Store current positions as new initial positions
        self.initial_fragment_positions[frag_a_name] = frag_a.getBoundingBox()[:2]
        self.initial_fragment_positions[frag_b_name] = frag_b.getBoundingBox()[:2]

        # disable apply button
        apply_button = self.table.cellWidget(row, 5)
        self.table.blockSignals(True)   # disable table signals to avoid triggering position change again
        apply_button.setEnabled(False)  
        self.table.clearSelection()
        self.table.blockSignals(False)

    def _update_frag_visibility(self, row):
        pair = self.pair_data[row]['pair']
        is_checked = self.current_solo_checked[row]
        if is_checked:
            # Hide all fragments except the ones in the pair
            for frag in self.project.fragments:
                frag_name = Path(frag.filename).stem
                if frag_name not in pair:
                    frag.setVisible(False)
                    frag.setVisible(False, back=True)
                else:
                    frag.setVisible(True)
                    frag.setVisible(True, back=True)
        else:
            # Show all fragments
            for frag in self.project.fragments:
                frag.setVisible(True)
                frag.setVisible(True, back=True)

    @pyqtSlot(int, int)
    def _on_solo_changed(self, row, state):
        """Placeholder: Called when the 'Solo' checkbox is changed."""
        is_checked = state == Qt.Checked
        self.current_solo_checked[row] = is_checked

        # select this row of the table
        self.table.blockSignals(True)
        self.table.selectRow(row)
        self.table.blockSignals(False)

        # deselect all the others
        for r in range(len(self.current_solo_checked)):
            if r != row:
                self.current_solo_checked[r] = False
                solo_widget = self.table.cellWidget(r, 3)
                solo_checkbox = solo_widget.layout().itemAt(0).widget()
                solo_checkbox.blockSignals(True)
                solo_checkbox.setChecked(False)
                solo_checkbox.blockSignals(False)

        self._update_frag_visibility(row)

    @pyqtSlot(int, int)
    def _on_flip_changed(self, row, state):
        """Placeholder: Called when the 'Flip A<->B' checkbox is changed."""
        is_checked = state == Qt.Checked
        self.current_flip_checked[row] = is_checked

        # select this row of the table
        self.table.blockSignals(True)
        self.table.selectRow(row)
        self.table.blockSignals(False)

        self._on_position_change(row, 0)  # Refresh position to apply solo logic if needed

    @pyqtSlot()
    def _on_reset_all(self, reset_interface=True):
        """Resets all fragments to their initial positions."""
        for frag in self.project.fragments:
            frag_name = Path(frag.filename).stem
            if frag_name in self.initial_fragment_positions:
                init_y, init_x = self.initial_fragment_positions[frag_name]
                frag.setPosition(init_x, init_y)
                self.viewerplus.drawFragment(frag)
        
        self.viewerplus.fragmentPositionChanged()

        if reset_interface:
            # also reset all solo and flip checkboxes
            for row in range(len(self.current_solo_checked)):
                self.current_solo_checked[row] = False
                solo_widget = self.table.cellWidget(row, 3)
                solo_checkbox = solo_widget.layout().itemAt(0).widget()
                solo_checkbox.blockSignals(True)
                solo_checkbox.setChecked(False)
                solo_checkbox.blockSignals(False)

                self.current_flip_checked[row] = False
                flip_widget = self.table.cellWidget(row, 4)
                flip_checkbox = flip_widget.layout().itemAt(0).widget()
                flip_checkbox.blockSignals(True)
                flip_checkbox.setChecked(False)
                flip_checkbox.blockSignals(False)

    @pyqtSlot()
    def _on_ok_clicked(self):
        """Placeholder: Called when 'Ok' button is clicked."""
        self.close()

    def _preview_fragment_movement(self, row, pair, position_coords):
        """
        Previews the movement of fragments based on the selected position.
        
        Args:
            pair (tuple): Tuple of fragment names (frag_a, frag_b).
            position_coords (array-like): The (y, x) coordinates for positioning.
        """
        frag_a_name, frag_b_name = pair
        frag_a = next((f for f in self.project.fragments if Path(f.filename).stem == frag_a_name), None)
        frag_b = next((f for f in self.project.fragments if Path(f.filename).stem == frag_b_name), None)

        if not frag_a or not frag_b:
            print(f"Fragments {frag_a_name} or {frag_b_name} not found in project.")
            return

        # Apply new displacement based on position_coords
        dy, dx = position_coords

        y, x = frag_a.getBoundingBox()[:2]
        print(f"Frag A positioning (yx): ({y}, {x})")
        final_y, final_x = [y+dy, x+dx]
        frag_b.setPosition(final_x, final_y)
        self.viewerplus.drawFragment(frag_b)
        self.viewerplus.fragmentPositionChanged()

        self._update_frag_visibility(row)

    def closeEvent(self, event):
        """Handles the widget close event."""
        # re-enable visibility on all fragments
        for frag in self.project.fragments:
            frag.setVisible(True)
            frag.setVisible(True, back=True)
        if event.spontaneous():
            # if click on close icon, reset all positions before closing
            self._on_reset_all()
        self._remove_matching_points()
        event.accept()
        