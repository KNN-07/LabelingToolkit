import sys
import os
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QListWidget, QLineEdit, QMessageBox, QComboBox
)

class LabelEntry:
    def __init__(self, person_id, label, start, end):
        self.person_id = person_id
        self.label = label
        self.start = int(start)
        self.end = int(end)
    def __str__(self):
        return f"{self.label}: {self.start} - {self.end}"

class LabelMerger(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Label File Merger Tool")
        self.label_files = []
        self.labels_by_file = []  # List of {person_id: [LabelEntry, ...]}
        self.id_ranges = []  # List of (start_id, end_id) for each file
        self.merged_labels = {}  # {person_id: [LabelEntry, ...]}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.file_list = QListWidget()
        layout.addWidget(QLabel("Loaded Label Files:"))
        layout.addWidget(self.file_list)
        file_btn_layout = QHBoxLayout()
        self.add_file_btn = QPushButton("Add Label File")
        self.remove_file_btn = QPushButton("Remove Selected File")
        file_btn_layout.addWidget(self.add_file_btn)
        file_btn_layout.addWidget(self.remove_file_btn)
        layout.addLayout(file_btn_layout)

        self.range_list = QListWidget()
        layout.addWidget(QLabel("ID Ranges for Each File (e.g. 1-16):"))
        layout.addWidget(self.range_list)
        range_btn_layout = QHBoxLayout()
        self.range_edit = QLineEdit()
        self.range_edit.setPlaceholderText("e.g. 1-16")
        self.set_range_btn = QPushButton("Set Range for Selected File")
        range_btn_layout.addWidget(self.range_edit)
        range_btn_layout.addWidget(self.set_range_btn)
        layout.addLayout(range_btn_layout)

        self.merge_btn = QPushButton("Merge Files")
        layout.addWidget(self.merge_btn)
        self.merged_list = QListWidget()
        layout.addWidget(QLabel("Merged Labels Preview:"))
        layout.addWidget(self.merged_list)
        self.save_btn = QPushButton("Save Merged Labels")
        layout.addWidget(self.save_btn)
        self.setLayout(layout)

        self.add_file_btn.clicked.connect(self.add_label_file)
        self.remove_file_btn.clicked.connect(self.remove_selected_file)
        self.set_range_btn.clicked.connect(self.set_id_range)
        self.merge_btn.clicked.connect(self.merge_files)
        self.save_btn.clicked.connect(self.save_merged_labels)

    def add_label_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Label File", filter="Text Files (*.txt)")
        if file:
            self.label_files.append(file)
            self.file_list.addItem(file)
            labels = self.parse_label_file(file)
            self.labels_by_file.append(labels)
            self.id_ranges.append((None, None))
            self.range_list.addItem("Not set")

    def remove_selected_file(self):
        idx = self.file_list.currentRow()
        if idx >= 0:
            self.file_list.takeItem(idx)
            self.range_list.takeItem(idx)
            del self.label_files[idx]
            del self.labels_by_file[idx]
            del self.id_ranges[idx]

    def set_id_range(self):
        idx = self.file_list.currentRow()
        if idx < 0:
            return
        text = self.range_edit.text().strip()
        m = re.match(r"(\d+)-(\d+)", text)
        if not m:
            QMessageBox.warning(self, "Invalid Range", "Please enter a valid range like 1-16.")
            return
        start_id, end_id = int(m.group(1)), int(m.group(2))
        self.id_ranges[idx] = (start_id, end_id)
        self.range_list.item(idx).setText(f"{start_id}-{end_id}")

    def parse_label_file(self, path):
        labels_by_id = {}
        current_id = None
        with open(path, 'r') as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
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

    def merge_files(self):
        self.merged_labels = {}
        for file_idx, labels_by_id in enumerate(self.labels_by_file):
            start_id, end_id = self.id_ranges[file_idx]
            if start_id is None or end_id is None:
                QMessageBox.warning(self, "Range Not Set", f"Set ID range for file {self.label_files[file_idx]}")
                return
            for person_id, entries in labels_by_id.items():
                pid_int = int(person_id)
                if start_id <= pid_int <= end_id:
                    if person_id not in self.merged_labels:
                        self.merged_labels[person_id] = []
                    self.merged_labels[person_id].extend(entries)
        self.update_merged_list()
        QMessageBox.information(self, "Merge Complete", "Files merged by ID range.")

    def update_merged_list(self):
        self.merged_list.clear()
        for person_id in sorted(self.merged_labels.keys(), key=int):
            self.merged_list.addItem(f"{person_id}: student, appearance")
            for l in self.merged_labels[person_id]:
                self.merged_list.addItem(f"  {l.label}: {l.start} - {l.end}")

    def save_merged_labels(self):
        if not self.merged_labels:
            QMessageBox.warning(self, "No Data", "No merged labels to save.")
            return
        file, _ = QFileDialog.getSaveFileName(self, "Save Merged Label File", filter="Text Files (*.txt)")
        if not file:
            return
        with open(file, 'w') as f:
            for person_id in sorted(self.merged_labels.keys(), key=int):
                f.write(f"{person_id}: student, appearance\n")
                for l in self.merged_labels[person_id]:
                    f.write(f"{l.label}: {l.start} - {l.end}\n")
        QMessageBox.information(self, "Saved", "Merged labels saved successfully.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LabelMerger()
    window.resize(600, 500)
    window.show()
    sys.exit(app.exec_())
