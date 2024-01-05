"""Testing stubs for the curd package"""
import json
import networkx

from model import Catalog, Course, CourseId, Limits, Objective, Program, ProgramId
from serialize import CatalogEncoder, catalog_hook


def main():
    """Stubs for testing"""
    cs1400 = Course(CourseId("CS", "1400"), "Fundamentals of Programming", 3)
    cs1400_id = cs1400.c_id
    basics = Objective("basic programming")
    cs1410 = Course(CourseId("CS", "1410"), "Object-Oriented Programming", 3)
    cs1410_id = cs1410.c_id
    oop = Objective("OOP")
    cs_cs = Program(ProgramId("CS"), {cs1400_id, cs1410_id})
    cs_id = cs_cs.p_id
    catalog = Catalog(
        {basics, oop},
        {oop: {basics}},
        {cs1400_id: cs1400, cs1410_id: cs1410},
        {basics: cs1400_id, oop: cs1410_id},
        {cs_id: cs_cs},
        Limits(120, 18, 8),
    )

    graph = catalog.courses_graph()
    networkx.nx_pydot.write_dot(graph, "deps.dot")

    with open("deps.json", "w", encoding="utf-8") as json_file:
        json.dump(catalog, json_file, indent=4, sort_keys=True, cls=CatalogEncoder)
        json_file.write("\n")

    with open("deps.json", "r", encoding="utf-8") as json_file:
        result = json.load(json_file, object_hook=catalog_hook)

    print(f"Successfully read JSON back:\n\n{result}")


if __name__ == "__main__":
    main()
