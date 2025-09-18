import sys
import os
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QListWidget, QLineEdit, QMessageBox, QSlider
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer

class LabelEntry:
    def __init__(self, person_id, label, start, end):
        self.person_id = person_id
        self.label = label
        self.start = int(start)
        self.end = int(end)
    def __str__(self):
        return f"{self.label}: {self.start} - {self.end}"

class VideoLabeler(QWidget):
    def replace_label_in_frame_range(self, person_id, start_frame, end_frame, new_label):
        """
        For the given person_id, replace the label of all LabelEntry objects whose range overlaps
        with [start_frame, end_frame] (inclusive) with new_label. Do not merge ranges, just change the label.
        """
        if person_id not in self.labels_by_id:
            return
        labels = self.labels_by_id[person_id]
        for entry in labels:
            # Check if entry overlaps with the given frame range
            if entry.end >= start_frame and entry.start <= end_frame:
                entry.label = new_label
        self.update_label_list()
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Action Labeling Tool")
        self.frame_folder = None
        self.label_file = None
        self.labels_by_id = {}  # {person_id: [LabelEntry, ...]}
        self.person_ids = []
        self.selected_person_id = None
        self.frames = []
        self.current_frame_idx = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        # Add current frame indicator
        self.frame_num_label = QLabel("Frame: N/A")
        self.frame_num_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.frame_num_label)

        btn_layout = QHBoxLayout()
        self.select_folder_btn = QPushButton("Select Frame Folder")
        self.load_frames_btn = QPushButton("Load Frames")
        self.select_label_btn = QPushButton("Select Label File")
        self.load_labels_btn = QPushButton("Load Labels")
        btn_layout.addWidget(self.select_folder_btn, 1)
        btn_layout.addWidget(self.load_frames_btn, 1)
        btn_layout.addWidget(self.select_label_btn, 1)
        btn_layout.addWidget(self.load_labels_btn, 1)
        layout.addLayout(btn_layout)

        self.image_label = QLabel("No frame loaded")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(320, 240)
        layout.addWidget(self.image_label, stretch=4)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.valueChanged.connect(self.slider_changed)
        layout.addWidget(self.slider)

        control_layout = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.pause_btn = QPushButton("Pause")
        control_layout.addWidget(self.play_btn, 1)
        control_layout.addWidget(self.pause_btn, 1)
        layout.addLayout(control_layout)

        # Dropdown for person ID selection
        from PyQt5.QtWidgets import QComboBox
        self.id_dropdown = QComboBox()
        self.id_dropdown.currentIndexChanged.connect(self.person_id_changed)
        layout.addWidget(QLabel("Select Person ID:"))
        layout.addWidget(self.id_dropdown)

        self.label_list = QListWidget()
        self.label_list.setMinimumHeight(80)
        layout.addWidget(self.label_list, stretch=1)

        edit_layout = QHBoxLayout()
        self.label_edit = QLineEdit()
        self.start_edit = QLineEdit()
        self.end_edit = QLineEdit()
        self.add_label_btn = QPushButton("Add/Edit Label")
        self.delete_label_btn = QPushButton("Delete Label")
        edit_layout.addWidget(QLabel("Label:"))
        edit_layout.addWidget(self.label_edit, 2)
        edit_layout.addWidget(QLabel("Start:"))
        edit_layout.addWidget(self.start_edit, 1)
        edit_layout.addWidget(QLabel("End:"))
        edit_layout.addWidget(self.end_edit, 1)
        edit_layout.addWidget(self.add_label_btn, 1)
        edit_layout.addWidget(self.delete_label_btn, 1)
        layout.addLayout(edit_layout)

        # UI for batch label replacement
        batch_layout = QHBoxLayout()
        self.batch_start_edit = QLineEdit()
        self.batch_start_edit.setPlaceholderText("Start Frame")
        self.batch_end_edit = QLineEdit()
        self.batch_end_edit.setPlaceholderText("End Frame")
        self.batch_label_edit = QLineEdit()
        self.batch_label_edit.setPlaceholderText("New Label Action")
        self.batch_replace_btn = QPushButton("Replace Label in Range")
        batch_layout.addWidget(QLabel("Batch Replace:"))
        batch_layout.addWidget(self.batch_start_edit, 1)
        batch_layout.addWidget(self.batch_end_edit, 1)
        batch_layout.addWidget(self.batch_label_edit, 2)
        batch_layout.addWidget(self.batch_replace_btn, 1)
        layout.addLayout(batch_layout)

        self.save_btn = QPushButton("Save Labels")
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

        self.select_folder_btn.clicked.connect(self.select_folder)
        self.load_frames_btn.clicked.connect(self.load_frames)
        self.select_label_btn.clicked.connect(self.select_label_file)
        self.load_labels_btn.clicked.connect(self.load_labels)
        self.play_btn.clicked.connect(self.play)
        self.pause_btn.clicked.connect(self.pause)
        self.add_label_btn.clicked.connect(self.add_edit_label)
        self.delete_label_btn.clicked.connect(self.delete_label)
        self.save_btn.clicked.connect(self.save_labels)
        self.label_list.itemClicked.connect(self.label_selected)

        self.batch_replace_btn.clicked.connect(self.batch_replace_label_action)
    def batch_replace_label_action(self):
        start_text = self.batch_start_edit.text().strip()
        end_text = self.batch_end_edit.text().strip()
        label_text = self.batch_label_edit.text().strip()
        if not start_text.isdigit() or not end_text.isdigit() or not label_text:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid start/end frame and label action.")
            return
        start_frame = int(start_text)
        end_frame = int(end_text)
        if start_frame > end_frame:
            QMessageBox.warning(self, "Invalid Range", "Start frame must be less than or equal to end frame.")
            return
        person_id = self.selected_person_id or (self.person_ids[0] if self.person_ids else None)
        if not person_id:
            QMessageBox.warning(self, "No Person Selected", "Please select a person ID.")
            return
        self.replace_label_in_frame_range(person_id, start_frame, end_frame, label_text)
        QMessageBox.information(self, "Batch Replace", "Labels updated for selected person in given frame range.")

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Frame Folder")
        if folder:
            self.frame_folder = folder

    def select_label_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Label File", filter="Text Files (*.txt)")
        if file:
            self.label_file = file

    def load_frames(self):
        if not self.frame_folder:
            QMessageBox.warning(self, "Missing Input", "Please select a frame folder.")
            return
        self.frames = sorted([f for f in os.listdir(self.frame_folder) if re.match(r"frame_\d{6}\.jpg", f)])
        print(f"Loaded frame folder: {self.frame_folder}")
        print(f"Number of frames found: {len(self.frames)}")
        if self.frames:
            print(f"First frame: {self.frames[0]}")
            print(f"Last frame: {self.frames[-1]}")
            self.slider.setMaximum(len(self.frames) - 1)
            self.current_frame_idx = 0
            self.load_frame()
        else:
            QMessageBox.warning(self, "No Frames Found", "No frames matching 'frame_000000.jpg' to 'frame_999999.jpg' (six digits) found in the selected folder.")
            self.image_label.setText("No frames found.")
            self.slider.setMaximum(0)
            self.current_frame_idx = 0
            self.frames = []
            self.update_label_list()

    def load_labels(self):
        if not self.label_file:
            QMessageBox.warning(self, "Missing Input", "Please select a label file.")
            return
        self.labels_by_id = self.parse_label_file(self.label_file)
        self.person_ids = list(self.labels_by_id.keys())
        self.id_dropdown.clear()
        self.id_dropdown.addItems(self.person_ids)
        self.selected_person_id = self.person_ids[0] if self.person_ids else None
        print(f"Loaded label file: {self.label_file}")
        print(f"Person IDs found: {self.person_ids}")
        self.update_label_list()

    def load_frame(self):
        if not self.frame_folder or not self.frames:
            self.image_label.setText("No frames found.")
            return
        frame_path = os.path.join(self.frame_folder, self.frames[self.current_frame_idx])
        pixmap = QPixmap(frame_path)
        self.image_label.setPixmap(pixmap.scaled(640, 480, Qt.KeepAspectRatio))
        self.slider.setValue(self.current_frame_idx)
        frame_num = self.get_current_frame_number()
        self.frame_num_label.setText(f"Frame: {frame_num}")
        self.update_label_list()

    def next_frame(self):
        if self.current_frame_idx < len(self.frames) - 1:
            self.current_frame_idx += 1
            self.load_frame()
        else:
            self.timer.stop()

    def play(self):
        self.timer.start(100)

    def pause(self):
        self.timer.stop()

    def slider_changed(self, value):
        self.current_frame_idx = value
        self.load_frame()

    def parse_label_file(self, path):
        labels_by_id = {}
        current_id = None
        with open(path, 'r') as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Only treat as person id if left side before ':' is a number
            m = re.match(r"(\d+):", line)
            if m:
                current_id = m.group(1)
                if current_id not in labels_by_id:
                    labels_by_id[current_id] = []
                continue
            if current_id and ':' in line:
                label_part, frame_part = line.rsplit(':', 1)
                frame_match = re.match(r"\s*(\d+)\s*-\s*(\d+)", frame_part.strip())
                if frame_match:
                    start, end = frame_match.groups()
                    labels_by_id[current_id].append(LabelEntry(current_id, label_part.strip(), start, end))
        return labels_by_id

    def update_label_list(self):
        self.label_list.clear()
        frame_num = self.get_current_frame_number()
        labels = self.labels_by_id.get(self.selected_person_id, [])
        matches = [label for label in labels if label.start <= frame_num <= label.end]
        for label in matches:
            self.label_list.addItem(f"{label.person_id} - {label}")
        if matches:
            self.label_list.setCurrentRow(0)
            selected_label = matches[0]
            self.label_edit.setText(selected_label.label)
            self.start_edit.setText(str(selected_label.start))
            self.end_edit.setText(str(selected_label.end))
        else:
            self.label_edit.clear()
            self.start_edit.clear()
            self.end_edit.clear()

    def get_current_frame_number(self):
        if not self.frames:
            return 0
        fname = self.frames[self.current_frame_idx]
        m = re.match(r"frame_(\d{6})\.jpg", fname)
        if m:
            return int(m.group(1))
        return 0

    def add_edit_label(self):
        label = self.label_edit.text().strip()
        start = self.start_edit.text().strip()
        end = self.end_edit.text().strip()
        if not label or not start.isdigit() or not end.isdigit():
            QMessageBox.warning(self, "Invalid Input", "Please enter valid label, start, and end.")
            return
        person_id = self.selected_person_id or (self.person_ids[0] if self.person_ids else "1")
        new_label = LabelEntry(person_id, label, start, end)
        labels = self.labels_by_id.setdefault(person_id, [])
        selected = self.label_list.currentItem()
        if selected:
            label_str = selected.text()
            # Remove ID prefix for comparison
            label_str = label_str.split(' - ', 1)[-1]
            for i, l in enumerate(labels):
                if str(l) == label_str:
                    labels[i] = new_label
                    break
            else:
                labels.append(new_label)
        else:
            labels.append(new_label)
        self.update_label_list()

    def delete_label(self):
        selected = self.label_list.currentItem()
        if not selected:
            return
        label_str = selected.text()
        label_str = label_str.split(' - ', 1)[-1]
        labels = self.labels_by_id.get(self.selected_person_id, [])
        for i, l in enumerate(labels):
            if str(l) == label_str:
                del labels[i]
                break
        self.update_label_list()

    def label_selected(self, item):
        label_str = item.text()
        label_str = label_str.split(' - ', 1)[-1]
        labels = self.labels_by_id.get(self.selected_person_id, [])
        for l in labels:
            if str(l) == label_str:
                self.label_edit.setText(l.label)
                self.start_edit.setText(str(l.start))
                self.end_edit.setText(str(l.end))
                break

    def save_labels(self):
        if not self.label_file:
            return
        with open(self.label_file, 'w') as f:
            for person_id in self.person_ids:
                f.write(f"{person_id}: student, appearance\n")
                for l in self.labels_by_id.get(person_id, []):
                    f.write(f"{l.label}: {l.start} - {l.end}\n")
        QMessageBox.information(self, "Saved", "Labels saved successfully.")

    def person_id_changed(self, idx):
        if idx < 0 or idx >= len(self.person_ids):
            return
        self.selected_person_id = self.person_ids[idx]
        self.update_label_list()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoLabeler()
    window.resize(600, 500)
    window.show()
    sys.exit(app.exec_())
