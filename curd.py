"""Testing stubs for the curd package"""

import json
import networkx
import os
import sys

from gui import TermsView

from argparse import ArgumentParser
from model import Catalog, Course, CourseId, Limits, Requirement, Program, ProgramId
from PyQt6.QtWidgets import QApplication
from serialize import CatalogEncoder, catalog_hook
from typing import Optional


def test_output():
    """Generate content by hand and print it as JSON"""
    cs1400 = Course(CourseId("CS", "1400"), "Fundamentals of Programming", 3)
    cs1400_id = cs1400.c_id
    basics = Requirement("basic programming")
    cs1410 = Course(CourseId("CS", "1410"), "Object-Oriented Programming", 3)
    cs1410_id = cs1410.c_id
    oop = Requirement("OOP")
    cs_cs = Program(ProgramId("CS"), {basics, oop})
    cs_id = cs_cs.p_id
    catalog = Catalog(
        {basics, oop},
        {oop: {basics}},
        {cs1400_id: cs1400, cs1410_id: cs1410},
        {basics: {cs1400_id}, oop: {cs1410_id}},
        {cs_id: cs_cs},
        Limits(6, 3, 2),
        set(),
        set(),
    )

    required, electives = catalog.select_courses("CS")
    courses = required | electives
    graph = Catalog.reduce_graph(catalog.build_courses_graph(courses))
    networkx.nx_pydot.write_dot(graph, "small.dot")

    with open("small.json", "w", encoding="utf-8") as json_file:
        json.dump(catalog, json_file, indent=4, sort_keys=True, cls=CatalogEncoder)
        json_file.write("\n")


def read_catalog(filename):
    """Read a catalog from `filename` and return it as a `Catalog` object."""
    with open(filename, "r", encoding="utf-8") as json_file:
        return json.load(json_file, object_hook=catalog_hook)


def test_input(filename: str, program: Optional[str]):
    """Read a file and generate a graph from it"""
    catalog = read_catalog(filename)

    if program is None:
        program = "CS_BS"

    required, electives = catalog.select_courses(program)
    courses = required | electives
    graph = catalog.build_courses_graph(courses)
    networkx.nx_pydot.write_dot(graph, "concepts.dot")

    if False:
        req_graph = catalog.build_courses_graph(required)
        print("bottlenecks:")
        for b in Catalog.bottlenecks(req_graph):
            print(f"\t{b}")
        print()

    with open("order.txt", "w", encoding="utf-8") as order:
        for post, pre in Catalog.close_graph(graph).edges:
            print(f"{pre}\t{post}", file=order)

    schedule = catalog.generate_graph(program)

    dotfile = os.path.splitext(os.path.basename(filename))[0] + ".dot"
    with open(dotfile, "w", encoding="utf8") as plan:
        print(schedule, file=plan)

    pid = ProgramId(program)

    app = QApplication(sys.argv)
    tv = TermsView(catalog, pid)
    tv.show()
    sys.exit(app.exec())


def make_reqs(filename: str):
    with open(filename, "r", encoding="utf-8") as json_file:
        catalog = json.load(json_file, object_hook=catalog_hook)

    graph = catalog.reqs_graph()
    name_graph: networkx.DiGraph = networkx.DiGraph()
    for pre, post in graph.edges:
        name_graph.add_edge(pre.name, post.name)
    networkx.nx_pydot.write_dot(name_graph, "output.dot")


def main():
    """Stubs for testing"""
    parser = ArgumentParser()
    parser.add_argument("-f", "--filename", type=str, default="cs.json")
    parser.add_argument("-p", "--program", type=str, default=None)
    args = parser.parse_args()

    # test_output()
    test_input(args.filename, args.program)


if __name__ == "__main__":
    main()
