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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Action Labeling Tool")
        self.frame_folder = None
        self.label_file = None
        self.labels = []
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
        self.labels = self.parse_label_file(self.label_file)
        print(f"Loaded label file: {self.label_file}")
        print(f"Number of labels loaded: {len(self.labels)}")
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
        labels = []
        with open(path, 'r') as f:
            lines = f.readlines()
        if not lines:
            return labels
        person_id = lines[0].split(':')[0].strip()
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            # Split on last colon
            if ':' in line:
                label_part, frame_part = line.rsplit(':', 1)
                frame_match = re.match(r"\s*(\d+)\s*-\s*(\d+)", frame_part.strip())
                if frame_match:
                    start, end = frame_match.groups()
                    labels.append(LabelEntry(person_id, label_part.strip(), start, end))
        return labels

    def update_label_list(self):
        self.label_list.clear()
        frame_num = self.get_current_frame_number()
        # print(f"[DEBUG] Current frame number: {frame_num}")
        # for label in self.labels:
        #     print(f"[DEBUG] Label: '{label.label}' Range: {label.start}-{label.end}")
        matches = [label for label in self.labels if label.start <= frame_num <= label.end]
        # print(f"[DEBUG] Matching labels for frame {frame_num}: {[str(label) for label in matches]}")
        for label in matches:
            self.label_list.addItem(str(label))
        # Only fill edit fields if a label is selected
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
        person_id = self.labels[0].person_id if self.labels else "1"
        new_label = LabelEntry(person_id, label, start, end)
        selected = self.label_list.currentItem()
        if selected:
            label_str = selected.text()
            for i, l in enumerate(self.labels):
                if str(l) == label_str:
                    self.labels[i] = new_label
                    break
            else:
                self.labels.append(new_label)
        else:
            self.labels.append(new_label)
        self.update_label_list()

    def delete_label(self):
        selected = self.label_list.currentItem()
        if not selected:
            return
        label_str = selected.text()
        for i, l in enumerate(self.labels):
            if str(l) == label_str:
                del self.labels[i]
                break
        self.update_label_list()

    def label_selected(self, item):
        label_str = item.text()
        for l in self.labels:
            if str(l) == label_str:
                self.label_edit.setText(l.label)
                self.start_edit.setText(str(l.start))
                self.end_edit.setText(str(l.end))
                break

    def save_labels(self):
        if not self.label_file:
            return
        person_id = self.labels[0].person_id if self.labels else "1"
        with open(self.label_file, 'w') as f:
            f.write(f"{person_id}: student, appearance\n")
            for l in self.labels:
                f.write(f"{l.label}: {l.start} - {l.end}\n")
        QMessageBox.information(self, "Saved", "Labels saved successfully.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoLabeler()
    window.resize(600, 500)
    window.show()
    sys.exit(app.exec_())
