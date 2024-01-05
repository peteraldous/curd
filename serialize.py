"""Serialization and deserialization for the classes in the data model"""
import json
import sys

from model import Catalog, Course, CourseId, Limits, Objective, Program, ProgramId


class CatalogEncoder(json.JSONEncoder):
    "A JSON encoder for Catalog objects"

    def default(self, o):
        if isinstance(o, Catalog):
            return {
                "__Catalog__": True,
                "objectives": [obj.name for obj in o.objectives],
                "obj_deps": {
                    from_obj.name: [to_obj.name for to_obj in to_objs]
                    for (from_obj, to_objs) in o.objective_deps.items()
                },
                "courses": [
                    (
                        course.c_id.dept,
                        course.c_id.course_number,
                        course.title,
                        course.creds,
                    )
                    for course in o.courses.values()
                ],
                "course_objs": {
                    obj.name: (course.dept, course.course_number)
                    for (obj, course) in o.course_objectives.items()
                },
                "programs": [
                    (
                        program.p_id.name,
                        [
                            (course.dept, course.course_number)
                            for course in program.courses
                        ],
                    )
                    for program in o.programs.values()
                ],
                "program_credit_limit": o.limits.program_credit_limit,
                "term_credit_limit": o.limits.term_credit_limit,
                "term_limit": o.limits.terms,
            }
        return json.JSONEncoder.default(self, o)


def catalog_hook(dct):
    "Attempt to read a Catalog from JSON"

    if "__Catalog__" in dct:
        try:
            objectives = {Objective(obj) for obj in dct["objectives"]}
            obj_deps = {
                Objective(from_name): {Objective(to_name) for to_name in to_names}
                for (from_name, to_names) in dct["obj_deps"].items()
            }
            courses = {}
            for (dept, number, title, creds) in dct["courses"]:
                c_id = CourseId(dept, number)
                courses[c_id] = Course(c_id, title, creds)
            course_objs = {
                Objective(obj_name): CourseId(dept, number)
                for (obj_name, (dept, number)) in dct["course_objs"].items()
            }
            programs = {}
            for (name, courses) in dct["programs"]:
                p_id = ProgramId(name)
                programs[p_id] = Program(
                    p_id, {CourseId(dept, number) for (dept, number) in courses}
                )
            limits = Limits(
                dct["program_credit_limit"], dct["term_credit_limit"], dct["term_limit"]
            )
            return Catalog(objectives, obj_deps, courses, course_objs, programs, limits)
        except IndexError as index_error:
            sys.stderr.print(f"Unable to read a Catalog from json: {index_error}")
    return dct
