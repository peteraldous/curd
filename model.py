"""Data structures for curriculum design"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple
from networkx import chordless_cycles, transitive_closure, transitive_reduction, DiGraph


@dataclass(order=True, frozen=True)
class Requirement:
    "An requirement of a course"

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
    requirements: Set[Requirement]

    def fits(self, limits: "Limits"):
        """Determine if the program fits within the specified credit and term
        limits."""
        # TODO
        return self is not None and limits is not None


@dataclass(order=True, frozen=True)
class Limits:
    "The limits on credits and terms for a Catalog"
    program_credit_limit: int = 120
    term_credit_limit: int = 18
    terms: int = 8


@dataclass
class CycleException(ValueError):
    cycles: List[List[CourseId]]


@dataclass
class Catalog:
    "A course catalog"
    requirements: Set[Requirement]
    requirement_deps: Dict[Requirement, Set[Requirement]]
    courses: Dict[CourseId, Course]
    course_requirements: Dict[Requirement, Set[CourseId]]
    programs: Dict[ProgramId, Program]
    limits: Limits

    @staticmethod
    def _check(d: DiGraph) -> List[List[CourseId]]:
        return sorted(list(chordless_cycles(d)))

    def reqs_graph(self) -> DiGraph:
        """Create a `networkx.DiGraph` object to show the relationships between
        requirements."""
        result: DiGraph = DiGraph()
        for post, pres in self.requirement_deps.items():
            for pre in pres:
                result.add_edge(pre, post)
        return Catalog.reduce_graph(result)

    def build_courses_graph(self) -> DiGraph:
        """Induce a `networkx.DiGraph` object over classes from the dependencies.
        If the resulting graph is cyclic, return the cycles as a list of lists
        of course IDs.

        If a requirement can be satisfied by multiple courses, pick one
        arbitrarily. (Consider making a meta-node with the name of the
                      requirement instead.)"""
        result: DiGraph = DiGraph()
        for requirement, deps in self.requirement_deps.items():
            post_course = next(iter(self.course_requirements[requirement]))
            for dep in deps:
                pre_course = next(iter(self.course_requirements[dep]))
                if post_course != pre_course:
                    result.add_edge(post_course, pre_course)
        return result

    @staticmethod
    def reduce_graph(graph: DiGraph) -> DiGraph:
        """Check for cycles in `graph`. If it is cyclic, return the cycles.
        Otherwise, return its transitive reduction."""
        cycles = Catalog._check(graph)
        if cycles:
            raise CycleException(cycles)
        return transitive_reduction(graph)  # type: ignore

    @staticmethod
    def close_graph(graph: DiGraph) -> DiGraph:
        """Check for cycles in `graph`. If it is cyclic, return the cycles.
        Otherwise, return its transitive closure."""
        cycles = Catalog._check(graph)
        if cycles:
            raise CycleException(cycles)
        return transitive_closure(graph)  # type: ignore

    def add_course(self, dept: str, course_number: str, title: str, creds: int):
        """Add a course to the catalog. If another course by the same
        department and course number exists, replace it."""
        c_id = CourseId(dept, course_number)
        self.courses[c_id] = Course(c_id, title, creds)

    @staticmethod
    def _get_requirement(req: str | Requirement) -> Requirement:
        match req:
            case str():
                return Requirement(req)
            case Requirement():
                return req
            case _:
                raise TypeError(f"Cannot make an Requirement from {req}")

    @staticmethod
    def _get_program(program: str | ProgramId) -> ProgramId:
        match program:
            case str():
                return ProgramId(program)
            case ProgramId():
                return program
            case _:
                raise TypeError(f"Cannot make a ProgramId from {program}")

    @staticmethod
    def _get_course(course: str | Tuple[str, str] | CourseId) -> CourseId:
        match course:
            case str(name):
                values = name.split()
                assert len(values) == 2
                (dept, course_number) = values
                return CourseId(dept, course_number)
            case (str(dept), str(course_number)):
                return CourseId(dept, course_number)
            case CourseId():
                return course
            case _:
                raise TypeError(f"Cannot make a CourseId from {course}")

    def add_requirement(
        self,
        req: str | Requirement,
        courses: Iterable[str | Tuple[str, str] | CourseId],
    ):
        """Add a requirement to the catalog, which can be satisfied by any
        course in `courses`."""
        course_ids = set(map(Catalog._get_course, courses))
        req = Catalog._get_requirement(req)
        self.requirements.add(req)
        assert req not in self.course_requirements
        self.course_requirements[req] = set(course_ids)

    def req_depends(self, pre_req: str | Requirement, post_req: str | Requirement):
        """Add a dependency between two requirements. Both requirements must
        already be in the catalog.

        All prerequisites must be satisfied before enrolling in a course. If
        students can choose between courses, create a requirement that can be
        satisfied by any of them."""
        pre_req = Catalog._get_requirement(pre_req)
        post_req = Catalog._get_requirement(post_req)
        assert pre_req in self.requirements and post_req in self.requirements
        self.requirement_deps.setdefault(post_req, set()).add(pre_req)

    def add_program(
        self,
        name: str | ProgramId,
        requirements: Optional[Iterable[str | Requirement]] = None,
    ):
        """Add a program to the catalog. Requirements may optionally be
        specified that pertain to the program."""
        reqs: Set[Requirement] = set()
        if requirements is not None:
            reqs = set(map(Catalog._get_requirement, requirements))
        p_id = Catalog._get_program(name)
        self.programs[p_id] = Program(p_id, reqs)

    def add_requirement_to_program(
        self, name: str | ProgramId, requirement: str | Requirement
    ):
        """Add a requirement to the specified program. If no such requirement
        exists in the catalog, create it."""
        p_id = Catalog._get_program(name)
        req = Catalog._get_requirement(requirement)
        self.programs.setdefault(p_id, Program(p_id, set())).requirements.add(req)
