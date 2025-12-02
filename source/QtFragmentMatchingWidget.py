import sys
import os
import glob
import numpy as np
import pandas as pd
import h5py
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QComboBox,
    QLabel, QAbstractItemView, QCheckBox, QGraphicsEllipseItem, QGraphicsView
)
from PyQt5.QtCore import Qt, pyqtSlot, QSettings
from PyQt5.QtGui import QBrush, QPen

class QtFragmentMatchingWidget(QWidget):
    """
    A PyQt5 widget to browse and analyze merged fragment matching results
    from HDF5 files.
    """
    
    # Define Column Indices for clarity
    COL_RANK = 0
    COL_PAIRS = 1
    COL_GLOB_SCORE = 2
    COL_RECTO_SCORE = 3
    COL_VERSO_SCORE = 4
    COL_POSITIONING = 5
    COL_SOLO = 6
    COL_FLIP = 7
    COL_APPLY = 8

    def __init__(self, viewerplus, viewerplus_back, on_close_callback=None, parent=None):
        super().__init__(parent)
        self.viewerplus = viewerplus
        self.viewerplus_back = viewerplus_back
        self.project = viewerplus.project
        self.on_close_callback = on_close_callback
        
        # --- Data Storage ---
        self.pair_data = [] 
        self.current_position_indices = {}
        self.current_solo_checked = {}
        self.current_flip_checked = {}
        self.matching_points_recto = []
        self.matching_points_verso = []
        self.current_side = "Both" # Tracks current selection in dropdown
        self.settings = QSettings("VCLAB-AIMH", "PapyrLab")

        # --- Memorize initial fragment positions ---
        self.initial_fragment_positions = {}
        for frag in self.project.fragments:
            self.initial_fragment_positions[Path(frag.filename).stem] = frag.getBoundingBox()[:2]

        # --- Initialize UI ---
        self._init_ui()

        # --- Load initial results ---
        folder_path = self.settings.value("matching-fragments-path", defaultValue="ai_data_dgx")
        self._load_results(folder_path=folder_path)

    def _init_ui(self):
        """Initializes all UI components."""
        self.setWindowTitle("Matching Fragments")
        main_layout = QVBoxLayout(self)

        # Current loaded folder
        self.current_folder_label = QLabel("Current folder: {}".format(self.settings.value("matching-fragments-path")))
        main_layout.addWidget(self.current_folder_label)

        # --- Top Bar Controls ---
        self.load_button = QPushButton("Pick Folder")
        self.load_button.setFixedWidth(120)
        self.load_button.clicked.connect(self._load_results_dialog)

        self.show_matching_points = QCheckBox("Show Matching Points")
        self.show_matching_points.setChecked(True)
        self.show_matching_points.stateChanged[int].connect(self._change_matching_points_visibility)

        side_dropdown_label = QLabel("Sort by Side:")
        self.side_dropdown = QComboBox()
        self.side_dropdown.addItems(["Both", "Recto", "Verso"])
        self.side_dropdown.setCurrentText("Both")
        self.side_dropdown.currentTextChanged.connect(self._on_side_changed)
        
        top_bar_layout = QHBoxLayout()
        top_bar_layout.addWidget(self.load_button)
        top_bar_layout.addWidget(self.show_matching_points)
        top_bar_layout.addStretch(1)
        top_bar_layout.addWidget(side_dropdown_label)
        top_bar_layout.addWidget(self.side_dropdown)
        main_layout.addLayout(top_bar_layout)

        # --- Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(9) 
        self.table.setHorizontalHeaderLabels([
            "Rank", "Pairs", "Glob score", "Recto score", "Verso score", 
            "Positioning", "Solo", "Flip A<->B", "Apply"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        
        # Column Resizing setup
        self.table.horizontalHeader().setSectionResizeMode(self.COL_RANK, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(self.COL_PAIRS, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(self.COL_GLOB_SCORE, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(self.COL_RECTO_SCORE, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(self.COL_VERSO_SCORE, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(self.COL_POSITIONING, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(self.COL_SOLO, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(self.COL_FLIP, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(self.COL_APPLY, QHeaderView.Interactive)
        
        self.table.setMinimumSize(1000, 300)
        self.table.verticalHeader().setVisible(False)
        
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
        
        self.reset_button.clicked.connect(self._on_reset_all)
        self.ok_button.clicked.connect(self._on_ok_clicked)

    @pyqtSlot()
    def _load_results_dialog(self):
        """Wrapper to open file dialog and load results."""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Results Folder")
        if folder_path:
            self._load_results(folder_path=folder_path)

    @pyqtSlot(int)
    def _change_matching_points_visibility(self, visible):
        """Changes the visibility of the matching points."""
        self._update_matching_points_visibility()

    def _update_matching_points_visibility(self):
        """Iterates through and updates visibility of drawn points."""
        if not self.matching_points_recto and not self.matching_points_verso:
            return

        visible = self.show_matching_points.isChecked()
        
        for item in self.matching_points_recto:
            item.setVisible(visible)
            
        for item in self.matching_points_verso:
            item.setVisible(visible)

    @pyqtSlot(str)
    def _on_side_changed(self, value):
        """
        Handler for side dropdown. Re-sorts the pair_data 
        and updates the table display and positioning logic.
        """
        self.current_side = value
        print(f"Side selected for sorting and positioning: {value}")
        
        # 1. Determine the key for sorting
        if value == "Both":
            sort_key = 'glob_score'
        elif value == "Recto":
            sort_key = 'max_recto_score'
        elif value == "Verso":
            sort_key = 'max_verso_score'
        
        # 2. Re-sort the internal data structure
        self.pair_data = sorted(self.pair_data, key=lambda x: x.get(sort_key, 0.0), reverse=True)
        
        # 3. Re-populate the table based on the new order
        self._populate_table()
        
        # 4. Reset positioning index for the selected row to 0 (best score in new order)
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            row_index = selected_rows[0].row()
            self._on_position_change(row_index, 0) # Refresh the selected row to show the top score

    @pyqtSlot()
    def _load_results(self, folder_path=None):
        """
        Loads merged HDF5 files from the specified folder.
        """
        import h5py # Dependency guard
        
        # Check if folder exists and contains merged/
        resolved_path = Path(folder_path) if folder_path else Path("")
        merged_path = resolved_path / "merged"
        
        hdf5_files_found = merged_path.is_dir() and len(glob.glob(str(merged_path / "*.hdf5"))) > 0
        
        # Loop until a valid folder is selected or cancelled
        while not hdf5_files_found:
            folder_path = QFileDialog.getExistingDirectory(self, "Select Results Folder (Containing 'merged' subdir)")            
            if not folder_path:
                QApplication.restoreOverrideCursor()
                self.close()
                return

            resolved_path = Path(folder_path)
            merged_path = resolved_path / "merged"
            hdf5_files_found = merged_path.is_dir() and len(glob.glob(str(merged_path / "*.hdf5"))) > 0
            
            if not hdf5_files_found:
                print(f"Folder '{folder_path}' does not contain a 'merged' subdirectory with HDF5 files.")

        QApplication.setOverrideCursor(Qt.WaitCursor)
        hdf5_files = glob.glob(str(merged_path / "*.hdf5"))
        self.settings.setValue("matching-fragments-path", str(resolved_path))
        self.current_folder_label.setText("Current folder: {}".format(str(resolved_path)))

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

                    # 2. Read all score grids and T_ID mapping
                    sum_scores_grid = f['sum_scores_grid'][:]
                    scores_grid = f['scores_grid'][:]
                    scores_grid_back = f['scores_grid_back'][:]
                    grid_to_tid = f['grid_to_translation_id_recto'][:] 
                    
                    if sum_scores_grid.size == 0:
                        print(f"Skipping {file_path} (empty sum_scores_grid)")
                        continue
                        
                    # Global (Both) scores
                    glob_score = np.max(sum_scores_grid)
                    
                    # Recto/Verso Max scores for display and sorting
                    max_recto_score = np.max(scores_grid)
                    max_verso_score = np.max(scores_grid_back)

                    # --- Aggregation Logic (Now for Both, Recto, and Verso) ---
                    
                    def aggregate_scores(scores_flat, grid_t_id):
                        df_agg = pd.DataFrame({'score': scores_flat.ravel(), 'translation_id': grid_t_id.ravel()})
                        agg_scores = df_agg.groupby('translation_id')['score'].max() # Use max for positioning
                        
                        sorted_agg_t_ids = agg_scores.sort_values(ascending=False).index.to_numpy()
                        sorted_agg_scores = agg_scores.sort_values(ascending=False).to_numpy()
                        return sorted_agg_t_ids, sorted_agg_scores
                        
                    # Both (Sum)
                    both_t_ids, both_scores = aggregate_scores(sum_scores_grid, grid_to_tid)
                    
                    # Recto
                    recto_t_ids, recto_scores = aggregate_scores(scores_grid, grid_to_tid)
                    
                    # Verso
                    verso_t_ids, verso_scores = aggregate_scores(scores_grid_back, grid_to_tid)
                    
                    # 4. Store all data needed for interaction
                    data_dict = {
                        "pair": (frag_a, frag_b),
                        "file_path": file_path,
                        "pair_name": pair_name,
                        
                        # Display Scores
                        "glob_score": glob_score,
                        "max_recto_score": max_recto_score,
                        "max_verso_score": max_verso_score,
                        
                        # Positioning/Sorting Data (Grouped by Side)
                        "agg_data": {
                            "Both": {"t_ids": both_t_ids, "scores": both_scores},
                            "Recto": {"t_ids": recto_t_ids, "scores": recto_scores},
                            "Verso": {"t_ids": verso_t_ids, "scores": verso_scores},
                        },
                        
                        # Raw data needed for lookup (Recto)
                        "translation_ids_recto": f['translation_ids_recto'][:],
                        "a_coords_recto": f['a_coords_recto'][:],
                        "b_coords_recto": f['b_coords_recto'][:],
                        "t_relatives_recto": f['t_relatives_recto'][:],
                        "scores_recto": f['scores_recto'][:],
                        
                        # Raw data needed for lookup (Verso)
                        "translation_ids_verso": f['translation_ids_verso'][:],
                        "a_coords_verso": f['a_coords_verso'][:],
                        "b_coords_verso": f['b_coords_verso'][:],
                        "t_relatives_verso": f['t_relatives_verso'][:],
                        "scores_verso": f['scores_verso'][:],
                    }
                    loaded_data.append(data_dict)
                    
            except Exception as e:
                print(f"Error loading {file_path}: {e}")

        # Initial sort by global score ("Both")
        self.pair_data = sorted(loaded_data, key=lambda x: x['glob_score'], reverse=True)
        
        self._populate_table()
        QApplication.restoreOverrideCursor()

    def _populate_table(self):
        """Fills the QTableWidget with data loaded into self.pair_data."""
        self.table.setRowCount(len(self.pair_data))
        
        for row_index, data in enumerate(self.pair_data):
            # --- Cell 0: Rank ---
            row_index_item = QTableWidgetItem(str(row_index+1))
            row_index_item.setFlags(row_index_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row_index, self.COL_RANK, row_index_item)

            # --- Cell 1: Pairs ---
            pair_item = QTableWidgetItem(data['pair_name'])
            pair_item.setFlags(pair_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row_index, self.COL_PAIRS, pair_item)

            # --- Cell 2: Glob score ---
            score_item = QTableWidgetItem(f"{data['glob_score']:.3f}")
            score_item.setFlags(score_item.flags() & ~Qt.ItemIsEditable)
            score_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_index, self.COL_GLOB_SCORE, score_item)
            
            # --- Cell 3: Recto Score ---
            recto_score_item = QTableWidgetItem(f"{data['max_recto_score']:.3f}")
            recto_score_item.setFlags(recto_score_item.flags() & ~Qt.ItemIsEditable)
            recto_score_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_index, self.COL_RECTO_SCORE, recto_score_item)
            
            # --- Cell 4: Verso Score ---
            verso_score_item = QTableWidgetItem(f"{data['max_verso_score']:.3f}")
            verso_score_item.setFlags(verso_score_item.flags() & ~Qt.ItemIsEditable)
            verso_score_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_index, self.COL_VERSO_SCORE, verso_score_item)

            # --- Cell 5: Positioning (Widget) ---
            self.current_position_indices[row_index] = 0
            self.current_solo_checked[row_index] = False
            self.current_flip_checked[row_index] = False
            
            initial_score = data['agg_data'][self.current_side]['scores'][0]
            
            pos_widget = QWidget()
            pos_layout = QHBoxLayout(pos_widget)
            pos_layout.setContentsMargins(5, 0, 5, 0)
            pos_layout.setSpacing(10)

            left_arrow = QPushButton("<")
            right_arrow = QPushButton(">")
            score_label = QLabel(f"{initial_score:.3f}")
            
            left_arrow.setFixedWidth(30)
            right_arrow.setFixedWidth(30)
            score_label.setFixedWidth(50)
            score_label.setAlignment(Qt.AlignCenter)

            left_arrow.clicked.connect(lambda _, r=row_index: self._on_position_change(r, +1))
            right_arrow.clicked.connect(lambda _, r=row_index: self._on_position_change(r, -1))

            pos_layout.addWidget(left_arrow)
            pos_layout.addWidget(score_label)
            pos_layout.addWidget(right_arrow)
            
            self.table.setCellWidget(row_index, self.COL_POSITIONING, pos_widget)
            
            # --- Cell 6: Solo (Checkbox) ---
            solo_checkbox = QCheckBox()
            solo_widget = QWidget()
            solo_layout = QHBoxLayout(solo_widget)
            solo_layout.addWidget(solo_checkbox, 0, Qt.AlignCenter)
            solo_layout.setContentsMargins(0, 0, 0, 0)
            solo_widget.setLayout(solo_layout)
            solo_checkbox.stateChanged.connect(lambda state, r=row_index: self._on_solo_changed(r, state))
            self.table.setCellWidget(row_index, self.COL_SOLO, solo_widget)

            # --- Cell 7: Flip A<->B (Checkbox) ---
            flip_checkbox = QCheckBox()
            flip_widget = QWidget()
            flip_layout = QHBoxLayout(flip_widget)
            flip_layout.addWidget(flip_checkbox, 0, Qt.AlignCenter)
            flip_layout.setContentsMargins(0, 0, 0, 0)
            flip_widget.setLayout(flip_layout)
            flip_checkbox.stateChanged.connect(lambda state, r=row_index: self._on_flip_changed(r, state))
            self.table.setCellWidget(row_index, self.COL_FLIP, flip_widget)
            
            # --- Cell 8: Apply (Button) ---
            apply_button = QPushButton("Apply")
            apply_button.clicked.connect(lambda _, r=row_index: self._on_apply_clicked(r))
            self.table.setCellWidget(row_index, self.COL_APPLY, apply_button)

        # Set initial reasonable widths for interactive columns
        self.table.resizeColumnToContents(self.COL_RANK)
        self.table.resizeColumnToContents(self.COL_GLOB_SCORE)
        self.table.setColumnWidth(self.COL_RECTO_SCORE, 90)
        self.table.setColumnWidth(self.COL_VERSO_SCORE, 90)
        self.table.setColumnWidth(self.COL_POSITIONING, 120)
        self.table.setColumnWidth(self.COL_SOLO, 40)
        self.table.setColumnWidth(self.COL_FLIP, 70)
        self.table.resizeColumnToContents(self.COL_APPLY)

    @pyqtSlot(int, int)
    def _on_position_change(self, row, direction):
        """
        Handles clicks on the left/right positioning arrows for a given row.
        Navigates through unique translation IDs sorted by the current side's score.
        """
        # First, reset and remove points
        self._on_reset_all(reset_interface=False)
        self._remove_matching_points()

        # Select this row of the table
        self.table.blockSignals(True)
        self.table.selectRow(row)
        self.table.blockSignals(False)

        # Re-enable apply button
        if direction != 0:
            apply_button = self.table.cellWidget(row, self.COL_APPLY)
            apply_button.setEnabled(True)

        data = self.pair_data[row]
        current_pos_idx = self.current_position_indices.get(row, 0)
        
        # Get the positioning data based on the current side selected in the dropdown
        # TODO: (see comment below) - as of now this makes sense only for Both, unless we find a way to draw recto and verso separately
        agg_data = data['agg_data']["Both"]
        sorted_agg_t_ids = agg_data['t_ids']
        sorted_agg_scores = agg_data['scores']
        
        # Calculate and clamp new index
        max_idx = len(sorted_agg_scores) - 1
        new_pos_idx = max(0, min(current_pos_idx + direction, max_idx))

        self.current_position_indices[row] = new_pos_idx
        
        # --- Update UI ---
        new_score = sorted_agg_scores[new_pos_idx]
        container = self.table.cellWidget(row, self.COL_POSITIONING)
        score_label = container.layout().itemAt(1).widget()
        score_label.setText(f"{new_score:.3f}")

        # --- Execute Core Logic ---
        
        # 1. Get the unique translation ID associated with this aggregated score
        translation_id = sorted_agg_t_ids[new_pos_idx]
        
        # 2. Find all original data for that translation_id
        mask_recto = (data['translation_ids_recto'] == translation_id)
        mask_verso = (data['translation_ids_verso'] == translation_id) # Using same T_ID for verso lookup
        
        # Recto data
        fine_scores_r = data['scores_recto'][mask_recto]
        fine_a_coords_r = data['a_coords_recto'][mask_recto]
        fine_b_coords_r = data['b_coords_recto'][mask_recto]
        precise_relative_position = data['t_relatives_recto'][mask_recto][0]

        # Verso data
        fine_scores_v = data['scores_verso'][mask_verso]
        fine_a_coords_v = data['a_coords_verso'][mask_verso]
        fine_b_coords_v = data['b_coords_verso'][mask_verso]


        # 3. Apply fragment movement
        if self.current_flip_checked.get(row, False):
            pair = data['pair'][::-1]
            rel_pos = -precise_relative_position
            fine_coords_r = fine_b_coords_r # Drawing B coords on Frag A
            fine_coords_v = fine_b_coords_v
        else:
            pair = data['pair']
            rel_pos = precise_relative_position
            fine_coords_r = fine_a_coords_r # Drawing A coords on Frag A
            fine_coords_v = fine_a_coords_v
            
        self._preview_fragment_movement(row, pair, rel_pos)

        # 4. Draw points
        self._draw_matching_points(
            viewer=self.viewerplus, 
            pair=pair, 
            fine_scores=fine_scores_r, 
            fine_coords=fine_coords_r, 
            point_list=self.matching_points_recto
        )
        # TODO: as of now, the above call visualizes matchings for recto or verso on the recto view, depending on the item selected on the dropdown.
        # Instead, the recto view should visualize only recto matchings and verso only verso ones. 
        # To do this, I should find the verso translation nearer to the recto one.
        # self._draw_matching_points(
        #     viewer=self.viewerplus_back, 
        #     pair=pair, 
        #     fine_scores=fine_scores_v, 
        #     fine_coords=fine_coords_v, 
        #     point_list=self.matching_points_verso
        # )

    def _draw_matching_points(self, viewer: QGraphicsView, pair, fine_scores, fine_coords, point_list: list):
        """
        Draws points on the scene based on coordinates and scores for a specific viewer.
        
        Args:
            viewer (QGraphicsView): The viewer containing the scene to draw on.
            pair (tuple): The (FragA, FragB) pair names.
            fine_scores (array-like): Scores determining color.
            fine_coords (array-like): (x, y) coordinates relative to FragA.
            point_list (list): List to store the created QGraphicsItem objects.
        """
        scene = viewer.scene
        # Clear existing points from the tracking list
        point_list.clear() 
        
        radius = 30
        diameter = radius * 2

        frag_a_name, _ = pair
        frag_a = next((f for f in self.project.fragments if Path(f.filename).stem == frag_a_name), None)
        
        if not frag_a or fine_scores.size == 0: return

        # Get frag_a's current scene position to convert local coordinates to scene coordinates
        # NOTE: Position is stored as (y, x) in bounding box
        y_frag_scene, x_frag_scene = frag_a.getBoundingBox()[:2] 

        for score, (y_local, x_local) in zip(fine_scores, fine_coords):
            
            # Determine color based on score thresholds
            if score > 0.7:
                color = Qt.yellow
            elif score > 0.4:
                color = Qt.cyan
            else:
                color = Qt.black

            # Convert local fragment coordinates to scene coordinates
            x_scene = x_local + x_frag_scene
            y_scene = y_local + y_frag_scene

            point_item = QGraphicsEllipseItem(x_scene - radius, y_scene - radius, diameter, diameter)
            
            point_item.setBrush(QBrush(color))
            point_item.setPen(QPen(Qt.NoPen))
            point_item.setZValue(100)
            
            scene.addItem(point_item)
            point_list.append(point_item)

        self._update_matching_points_visibility()
        

    def _remove_matching_points(self):
        """
        Removes all tracking points from both the recto and verso scenes.
        """
        
        def remove_from_scene(point_list, scene):
            if scene is None or not point_list:
                return
            for item in point_list:
                if item.scene() == scene:
                    scene.removeItem(item)
            point_list.clear()

        # Remove points from both viewers
        remove_from_scene(self.matching_points_recto, self.viewerplus.scene)
        remove_from_scene(self.matching_points_verso, self.viewerplus_back.scene)
        
    @pyqtSlot()
    def _on_row_selected(self):
        """Handles table row selection by calling position change with direction=0 (refresh)."""
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            selected_row_index = selected_rows[0].row()
            self._on_position_change(selected_row_index, 0) 

    @pyqtSlot(int)
    def _on_apply_clicked(self, row):
        """Overwrites the initial fragment positions to the current alignment."""
        
        data = self.pair_data[row]
        frag_a_name, frag_b_name = data['pair']
        frag_a = next((f for f in self.project.fragments if Path(f.filename).stem == frag_a_name), None)
        frag_b = next((f for f in self.project.fragments if Path(f.filename).stem == frag_b_name), None)
        
        if not frag_a or not frag_b:
            print(f"Fragments {frag_a_name} or {frag_b_name} not found in project.")
            return

        # Use current scene positions as the new 'initial' positions
        self.initial_fragment_positions[frag_a_name] = frag_a.getBoundingBox()[:2]
        self.initial_fragment_positions[frag_b_name] = frag_b.getBoundingBox()[:2]

        # disable apply button
        apply_button = self.table.cellWidget(row, self.COL_APPLY)
        self.table.blockSignals(True)
        apply_button.setEnabled(False)
        self.table.clearSelection()
        self.table.blockSignals(False)

    def _update_frag_visibility(self, row):
        """Manages visibility based on the 'Solo' checkbox state."""
        pair = self.pair_data[row]['pair']
        is_checked = self.current_solo_checked.get(row, False)
        
        if is_checked:
            for frag in self.project.fragments:
                frag_name = Path(frag.filename).stem
                is_in_pair = frag_name in pair
                
                frag.setVisible(is_in_pair)
                frag.setVisible(is_in_pair, back=True)
                frag.enableIds(self.viewerplus.ids_enabled and is_in_pair)
        else:
            for frag in self.project.fragments:
                frag.setVisible(True)
                frag.setVisible(True, back=True)
                frag.enableIds(self.viewerplus.ids_enabled)

    @pyqtSlot(int, int)
    def _on_solo_changed(self, row, state):
        """Handles 'Solo' checkbox change."""
        is_checked = state == Qt.Checked
        self.current_solo_checked[row] = is_checked

        self.table.blockSignals(True)
        self.table.selectRow(row)

        # Deselect all other solo checkboxes
        for r in range(len(self.current_solo_checked)):
            if r != row and self.current_solo_checked.get(r, False):
                self.current_solo_checked[r] = False
                solo_widget = self.table.cellWidget(r, self.COL_SOLO)
                if solo_widget:
                    solo_checkbox = solo_widget.layout().itemAt(0).widget()
                    solo_checkbox.blockSignals(True)
                    solo_checkbox.setChecked(False)
                    solo_checkbox.blockSignals(False)
        
        self.table.blockSignals(False)
        self._update_frag_visibility(row)

    @pyqtSlot(int, int)
    def _on_flip_changed(self, row, state):
        """Handles 'Flip A<->B' checkbox change."""
        is_checked = state == Qt.Checked
        self.current_flip_checked[row] = is_checked

        self.table.blockSignals(True)
        self.table.selectRow(row)
        self.table.blockSignals(False)

        # Refresh position to apply flip logic
        self._on_position_change(row, 0)

    @pyqtSlot()
    def _on_reset_all(self, reset_interface=True):
        """Resets all fragments to their initial positions and optionally resets the interface state."""
        for frag in self.project.fragments:
            frag_name = Path(frag.filename).stem
            if frag_name in self.initial_fragment_positions:
                init_y, init_x = self.initial_fragment_positions[frag_name]
                frag.setPosition(init_x, init_y)
                self.viewerplus.drawFragment(frag)
        
        self.viewerplus.fragmentPositionChanged()

        if reset_interface:
            # Also reset all solo and flip checkboxes
            for row in range(len(self.pair_data)):
                self.current_solo_checked[row] = False
                solo_widget = self.table.cellWidget(row, self.COL_SOLO)
                if solo_widget:
                    solo_checkbox = solo_widget.layout().itemAt(0).widget()
                    solo_checkbox.blockSignals(True)
                    solo_checkbox.setChecked(False)
                    solo_checkbox.blockSignals(False)

                self.current_flip_checked[row] = False
                flip_widget = self.table.cellWidget(row, self.COL_FLIP)
                if flip_widget:
                    flip_checkbox = flip_widget.layout().itemAt(0).widget()
                    flip_checkbox.blockSignals(True)
                    flip_checkbox.setChecked(False)
                    flip_checkbox.blockSignals(False)
            
            self._remove_matching_points()
            
    @pyqtSlot()
    def _on_ok_clicked(self):
        """Placeholder: Called when 'Ok' button is clicked."""
        self.close()

    def _preview_fragment_movement(self, row, pair, position_coords):
        """
        Previews the movement of fragments based on the selected position.
        """
        frag_a_name, frag_b_name = pair
        frag_a = next((f for f in self.project.fragments if Path(f.filename).stem == frag_a_name), None)
        frag_b = next((f for f in self.project.fragments if Path(f.filename).stem == frag_b_name), None)

        if not frag_a or not frag_b:
            print(f"Fragments {frag_a_name} or {frag_b_name} not found in project.")
            return

        # Apply new displacement based on position_coords (dy, dx)
        dy, dx = position_coords

        # Frag B moves relative to Frag A's current position
        y_a, x_a = frag_a.getBoundingBox()[:2]
        
        final_y_b = y_a + dy
        final_x_b = x_a + dx
        
        frag_b.setPosition(final_x_b, final_y_b)
        self.viewerplus.drawFragment(frag_b)
        self.viewerplus.fragmentPositionChanged()
        
        # Center view on Frag A's center
        self.viewerplus.centerOn(frag_a.center[0], frag_a.center[1])

        self._update_frag_visibility(row)

    def closeEvent(self, event):
        """Handles the widget close event."""
        for frag in self.project.fragments:
            frag.setVisible(True)
            frag.setVisible(True, back=True)
            frag.enableIds(self.viewerplus.ids_enabled)
        if event.spontaneous():
            self._on_reset_all()
        self._remove_matching_points()
        if self.on_close_callback:
            self.on_close_callback()
        event.accept()