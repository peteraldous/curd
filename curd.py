"""Testing stubs for the curd package"""

import json
import networkx
import sys

from model import Catalog, Course, CourseId, Limits, Requirement, Program, ProgramId
from serialize import CatalogEncoder, catalog_hook


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
        Limits(120, 18, 8),
    )

    graph = catalog.courses_graph()
    networkx.nx_pydot.write_dot(graph, "small.dot")

    with open("small.json", "w", encoding="utf-8") as json_file:
        json.dump(catalog, json_file, indent=4, sort_keys=True, cls=CatalogEncoder)
        json_file.write("\n")


def test_input():
    """Read a file and generate a graph from it"""
    with open("deps.json", "r", encoding="utf-8") as json_file:
        catalog = json.load(json_file, object_hook=catalog_hook)

    print(f"Successfully read JSON back:\n\n{catalog}")

    graph = catalog.courses_graph()
    networkx.nx_pydot.write_dot(graph, "deps.dot")


def make_reqs(filename: str):
    with open(filename, "r", encoding="utf-8") as json_file:
        catalog = json.load(json_file, object_hook=catalog_hook)

    graph = catalog.reqs_graph()
    networkx.nx_pydot.write_dot(graph, "output.dot")


def main():
    """Stubs for testing"""

    test_output()
    test_input()

    if len(sys.argv) > 1:
        make_reqs(sys.argv[1])


if __name__ == "__main__":
    main()
