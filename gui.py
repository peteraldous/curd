from PyQt6.QtWidgets import QWidget, QHBoxLayout, QListWidget, QListWidgetItem, QAbstractItemView, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
import sys

from model import CourseId, Catalog, ProgramId


class CourseView(QListWidgetItem):
    def __init__(self, course: CourseId, lw: QListWidget):
        super().__init__(str(course), lw)
        self.course = course

    def __str__(self):
        return str(self.course)

    def __repr__(self):
        return f"CourseView({self})"


class TermListWidget(QListWidget):
    def __init__(self, courses, term_view: TermView):
        super().__init__()
        self.term_view = term_view

        # Selection (use ExtendedSelection if you want multi-select)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        # Enable drag & drop both ways and show indicator
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSortingEnabled(True)

        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDragDropOverwriteMode(False)

        for course in courses:
            CourseView(course, self)

    def dragEnterEvent(self, event):
        # TODO
        print(f"enter event: {event.source().selectedItems()} from {event.source()} to {self}")
        if True:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        # TODO
        print(f"move event: {event.source().selectedItems()} from {event.source()} to {self}")
        if True:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        # TODO
        print(f"drop event: {event.source().selectedItems()} from {event.source()} to {self}")
        if True:
            super().dropEvent(event)
        else:
            event.ignore()

    def __str__(self):
        return f"Term {self.term_view.term_number}"


class TermView(QWidget):
    def __init__(self, courses, total: int, term_number: int, terms_view: TermsView):
        super().__init__(terms_view)
        self.total = total
        self.term_number = term_number
        self.terms_view = terms_view

        lw = TermListWidget(courses, self)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"Term {term_number} ({self.total} credits)"))
        layout.addWidget(lw)


class TermsView(QWidget):
    def __init__(self, catalog: Catalog, pid: ProgramId):
        super().__init__()
        self.setWindowTitle(f"Graduation plan ({pid})")
        self.catalog = catalog

        layout = QHBoxLayout(self)

        schedule = catalog.generate_schedule(pid)

        for index, (total, classes) in enumerate(schedule.schedule):
            term_list = TermView(classes, total, index + 1, self)
            layout.addWidget(term_list)
