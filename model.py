"""Data structures for curriculum design"""
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple
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

    def add_course(self, dept: str, course_number: str, title: str, creds: int):
        """Add a course to the catalog. If another course by the same
        department and course number exists, replace it."""
        c_id = CourseId(dept, course_number)
        self.courses[c_id] = Course(c_id, title, creds)

    @staticmethod
    def _get_objective(obj: str | Objective) -> Objective:
        match obj:
            case str():
                return Objective(obj)
            case Objective():
                return obj
            case _:
                raise TypeError(f"Cannot make an Objective from {obj}")

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

    def add_objective(
        self, obj: str | Objective, course: str | Tuple[str, str] | CourseId
    ):
        """Add an objective to the catalog and associate it with `course`.
        If the objective is already in the catalog, update it to belong to
        `course`."""
        course_id = Catalog._get_course(course)
        obj = Catalog._get_objective(obj)
        self.objectives.add(obj)
        self.course_objectives[obj] = course_id

    def obj_depends(self, from_obj: str | Objective, to_obj: str | Objective):
        """Add a dependency between two objectives. Both objectives must
        already be in the catalog."""
        from_obj = Catalog._get_objective(from_obj)
        to_obj = Catalog._get_objective(to_obj)
        assert from_obj in self.objectives and to_obj in self.objectives
        self.objective_deps.setdefault(from_obj, set()).add(to_obj)

    def add_program(
        self,
        name: str | ProgramId,
        courses: Optional[Iterable[str | Tuple[str, str] | CourseId]] = None,
    ):
        """Add a program to the catalog. Courses may optionally be specified
        that pertain to the program."""
        c_ids: Set[CourseId] = set()
        if courses is not None:
            c_ids = set(map(Catalog._get_course, courses))
        p_id = Catalog._get_program(name)
        self.programs[p_id] = Program(p_id, c_ids)

    def add_course_to_program(
        self, name: str | ProgramId, course: str | Tuple[str, str] | CourseId
    ):
        """Add a course to the specified program. If no such program exists in
        the catalog, create it."""
        p_id = Catalog._get_program(name)
        c_id = Catalog._get_course(course)
        self.programs.setdefault(p_id, Program(p_id, set())).courses.add(c_id)
