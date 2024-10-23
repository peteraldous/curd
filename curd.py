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
        {basics: (1, {cs1400_id}), oop: (1, {cs1410_id})},
        {cs_id: cs_cs},
        Limits(120, 18, 8),
    )

    graph = Catalog.reduce_graph(catalog.build_courses_graph())
    networkx.nx_pydot.write_dot(graph, "small.dot")

    with open("small.json", "w", encoding="utf-8") as json_file:
        json.dump(catalog, json_file, indent=4, sort_keys=True, cls=CatalogEncoder)
        json_file.write("\n")


def test_input():
    """Read a file and generate a graph from it"""
    with open("concepts.json", "r", encoding="utf-8") as json_file:
        catalog = json.load(json_file, object_hook=catalog_hook)

    print(f"Successfully read JSON back:\n\n{catalog}")

    graph = catalog.build_courses_graph()
    networkx.nx_pydot.write_dot(Catalog.reduce_graph(graph), "concepts.dot")

    with open("order.txt", "w", encoding="utf-8") as order:
        for post, pre in Catalog.close_graph(graph).edges:
            print(f"{pre}\t{post}", file=order)


def make_reqs(filename: str):
    with open(filename, "r", encoding="utf-8") as json_file:
        catalog = json.load(json_file, object_hook=catalog_hook)

    graph = catalog.reqs_graph()
    name_graph: networkx.DiGraph = networkx.DiGraph()
    for pre, post in graph.edges:
        name_graph.add_edge(pre.name, post.name)
    networkx.nx_pydot.write_dot(name_graph, "output.dot")

    for course, topics in catalog.exam_topics().items():
        print(f"{course.dept} {course.course_number}")
        for topic in topics:
            print(f"\t{topic.name}")


def main():
    """Stubs for testing"""

    test_output()
    test_input()

    if len(sys.argv) > 1:
        make_reqs(sys.argv[1])


if __name__ == "__main__":
    main()
