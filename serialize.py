"""Serialization and deserialization for the classes in the data model"""

import json
import sys

from model import Catalog, Course, CourseId, Limits, Requirement, Program, ProgramId


class CatalogEncoder(json.JSONEncoder):
    "A JSON encoder for Catalog objects"

    def default(self, o):
        if isinstance(o, Catalog):
            return {
                "__Catalog__": True,
                "requirements": [req.name for req in o.requirements],
                "req_deps": {
                    from_req.name: [to_req.name for to_req in to_reqs]
                    for (from_req, to_reqs) in o.requirement_deps.items()
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
                "course_reqs": {
                    req.name: [
                        (course.dept, course.course_number) for course in courses
                    ]
                    for (req, courses) in o.course_requirements.items()
                },
                "programs": [
                    (
                        program.p_id.name,
                        [requirement.name for requirement in program.requirements],
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
            requirements = {Requirement(req) for req in dct["requirements"]}
            req_deps = {
                Requirement(post_name): {
                    Requirement(pre_name) for pre_name in pre_names
                }
                for (post_name, pre_names) in dct["req_deps"].items()
            }
            courses = {}
            for dept, number, title, creds in dct["courses"]:
                c_id = CourseId(dept, number)
                courses[c_id] = Course(c_id, title, creds)
            course_reqs = {
                Requirement(req_name): {
                    CourseId(dept, number) for (dept, number) in courses
                }
                for (req_name, courses) in dct["course_reqs"].items()
            }
            programs = {}
            for name, requirements in dct["programs"]:
                p_id = ProgramId(name)
                programs[p_id] = Program(
                    p_id, {Requirement(name) for name in requirements}
                )
            limits = Limits(
                dct["program_credit_limit"], dct["term_credit_limit"], dct["term_limit"]
            )
            return Catalog(
                requirements, req_deps, courses, course_reqs, programs, limits
            )
        except IndexError as index_error:
            sys.stderr.print(f"Unable to read a Catalog from json: {index_error}")
    return dct
