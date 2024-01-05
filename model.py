"""Data structures for curriculum design"""
from dataclasses import dataclass
from typing import Dict, List, Set
from networkx import chordless_cycles, transitive_reduction, DiGraph


@dataclass(order=True, frozen=True)
class Objective:
    "An objective of a course"

    name: str


@dataclass(order=True, frozen=True)
class CourseId:
    """An immutable object that contains just a course code. It is hashable and
    can be used in a `networkx.DiGraph` object."""

    dept: str
    course_number: str

    def __str__(self) -> str:
        return f"{self.dept} {self.course_number}"


@dataclass(order=True)
class Course:
    "A college course"

    c_id: CourseId
    title: str
    creds: int


@dataclass(order=True, frozen=True)
class ProgramId:
    """An immutable object that contains just a program name. It is hashable
    and can be used in a `networkx.DiGraph` object."""

    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(order=True)
class Program:
    "A degree or emphasis"

    p_id: ProgramId
    courses: Set[CourseId]


@dataclass(order=True)
class Limits:
    "The limits on credits and terms for a Catalog"
    program_credit_limit: int = 120
    term_credit_limit: int = 18
    terms: int = 8


@dataclass
class Catalog:
    "A course catalog"
    objectives: Set[Objective]
    objective_deps: Dict[Objective, Set[Objective]]
    courses: Dict[CourseId, Course]
    course_objectives: Dict[Objective, CourseId]
    programs: Dict[ProgramId, Program]
    limits: Limits

    def courses_graph(self) -> List[List[CourseId]] | DiGraph:
        """Induce a `networkx.DiGraph` object over classes from the dependencies.
        If the resulting graph is cyclic, return the cycles as a list of lists
        of course IDs."""
        result: DiGraph = DiGraph()
        for objective, deps in self.objective_deps.items():
            if objective in self.course_objectives:
                from_course = self.course_objectives[objective]
                to_courses = set()
                for dep in deps:
                    if dep in self.course_objectives:
                        to_courses.add(self.course_objectives[dep])
                result.add_edges_from(
                    [(from_course, to_course) for to_course in to_courses]
                )
        cycles = sorted(list(chordless_cycles(result)))
        if cycles:
            return cycles
        return transitive_reduction(result)
