"""Data structures for curriculum design"""

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Set, Tuple
from networkx import (
    chordless_cycles,
    immediate_dominators,
    transitive_closure,
    transitive_reduction,
    DiGraph,
)

import pydot
import random

import antichains


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
        return f"{self.dept}_{self.course_number}"

    def to_tuple(self) -> Tuple[str, str]:
        """Produce a tuple; useful for serialization."""
        return (self.dept, self.course_number)

    @staticmethod
    def from_tuple(t: Tuple[str, str]) -> "CourseId":
        """Produce a CourseId from a tuple; useful for deserialization."""
        return CourseId(t[0], t[1])

    def is_elective(self) -> bool:
        """Determine if this course can be used as an elective.

        For now, this is hard-coded for UVU's requirements. Consider creating a
        more general way to express this.
        """
        return (
            self.dept == "CS"
            and len(self.course_number) > 0
            and (int(self.course_number[0]) >= 3 or self.course_number == "2700")
        )


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
    cycles: list[list[CourseId]]


@dataclass
class Catalog:
    "A course catalog"
    requirements: Set[Requirement]
    requirement_deps: Dict[Requirement, Set[Requirement]]
    courses: Dict[CourseId, Course]
    course_requirements: Dict[Requirement, Set[CourseId]]
    programs: Dict[ProgramId, Program]
    limits: Limits
    selections: Set[CourseId]
    constraints: Set[Tuple[str, antichains.Op, str | int]]

    @staticmethod
    def _check(d: DiGraph) -> list[list[CourseId]]:
        return sorted(list(chordless_cycles(d)))

    @staticmethod
    def bottlenecks(d: DiGraph):
        flow = d.copy()
        flow.add_node("source")
        for node in d.nodes:
            if d.in_degree(node) == 0:
                flow.add_edge("source", node)
            if d.out_degree(node) == 0:
                flow.add_edge(node, "sink")
        dom_tree = immediate_dominators(flow, "source")
        bottlenecks = {dom_tree["sink"]}
        print(bottlenecks)
        frontier = set(bottlenecks)
        while frontier:
            node = frontier.pop()
            dom = dom_tree[node]
            if dom == "source" or dom in bottlenecks:
                continue
            bottlenecks.add(node)
            frontier.add(node)
        return bottlenecks

    def reqs_graph(self) -> DiGraph:
        """Create a `networkx.DiGraph` object to show the relationships between
        requirements."""
        result: DiGraph = DiGraph()
        for post, pres in self.requirement_deps.items():
            for pre in pres:
                result.add_edge(pre, post)
        return Catalog.reduce_graph(result)

    def select_courses(
        self, p_id: str | ProgramId
    ) -> Tuple[set[CourseId], set[CourseId]]:
        """
        Select courses sufficient to match every requirement. When there are
        multiple options, choose randomly between them."""
        if isinstance(p_id, str):
            p_id = ProgramId(p_id)
        program = self.programs[p_id]

        pre_select = set(self.selections)
        required: set[CourseId] = set()

        requirements = program.requirements
        gens = ProgramId("generals")
        if gens in self.programs:
            requirements |= self.programs[gens].requirements

        for requirement in program.requirements:
            courses = self.course_requirements[requirement]
            pre = pre_select & courses
            if pre:
                choice = pre.pop()
                pre_select.remove(choice)
                required.add(choice)
                continue
            if required & courses:
                continue
            required.add(random.choice(list(courses)))
        total_required = sum(map(lambda c: self.courses[c].creds, required))

        electives: set[CourseId] = pre_select
        total_elective = sum(
            map(
                lambda c: self.courses[c].creds,
                filter(lambda c: c.is_elective(), pre_select),
            )
        )
        elective_options = list(
            filter(
                lambda cid: cid.is_elective(),
                set(self.courses) - (required | electives),
            )
        )
        random.shuffle(elective_options)
        while total_elective < self.limits.program_credit_limit - total_required:
            if not elective_options:
                print("Warning: insufficient electives to complete the program")
                break
            selection = elective_options.pop()
            electives.add(selection)
            total_elective += self.courses[selection].creds

        total = total_required + total_elective

        if total > self.limits.program_credit_limit:
            print(
                f"Warning: the courses selected total {total} credits but the "
                "specified credit limit for a program is "
                f"{self.limits.program_credit_limit}."
            )

        return (required, electives)

    def build_courses_graph(self, courses: set[CourseId]) -> DiGraph:
        """Induce a `networkx.DiGraph` representing the prerequisite
        dependencies between the specified courses. The resulting graph is the
        transitive _reduction_ of the relationships between classes. If the
        resulting graph is cyclic, raise a `CycleException` containing the
        courses that create the cycle."""
        result: DiGraph = DiGraph()
        for requirement, deps in self.requirement_deps.items():
            for post_course in self.course_requirements[requirement]:
                for dep in deps:
                    for pre_course in self.course_requirements[dep]:
                        if post_course != pre_course:
                            result.add_edge(pre_course, post_course)
        return Catalog.reduce_graph(Catalog.close_graph(result).subgraph(courses))  # type: ignore

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

    def generate_schedule(self, p_id: str | ProgramId) -> antichains.Schedule:
        """Choose classes that satisfy the program's requirements (using
        `Catalog.select_courses()`) and put them in a schedule with the
        appropriate number of terms."""
        required, electives = self.select_courses(p_id)
        courses = required | electives
        prereqs = [
            (str(before_id), str(after_id))
            for (before_id, after_id) in self.build_courses_graph(courses).edges()
        ]

        def course_value(c_id: CourseId) -> Tuple[str, int]:
            c = self.courses[c_id]
            return str(c_id), c.creds

        scheduler = antichains.Scheduler(
            map(course_value, courses),
            prereqs,
            self.limits.terms,
            self.limits.term_credit_limit,
            self.constraints,
        )
        return self.dot(scheduler.generate_schedule(), prereqs)

    def dot(
        self, schedule: antichains.Schedule, prereqs: list[Tuple[str, str]]
    ) -> pydot.Graph:
        graph = pydot.Dot("schedule", graph_type="digraph")
        # graph.set("ordering", "out")
        graph.set("compound", "true")
        graph.set("rankdir", "LR")
        graph.set("ranksep", "1.0 equally")
        nodes: dict[str, pydot.Node] = {}
        last: Optional[pydot.Subgraph] = None
        for index, (total, classes) in enumerate(schedule.schedule):
            term = index + 1
            subgraph = pydot.Subgraph(f"cluster_term_{term}", label=f"Term {term}")
            for c in sorted(classes):
                nodes[c] = pydot.Node(c, shape="box")
                subgraph.add_node(nodes[c])
            graph.add_subgraph(subgraph)
            if last:
                graph.add_edge(
                    pydot.Edge(
                        last.get_nodes()[0],
                        subgraph.get_nodes()[0],
                        ltail=last.get_name(),
                        lhead=subgraph.get_name(),
                        style="invis",
                    )
                )
            last = subgraph
        for before, after in prereqs:
            graph.add_edge(
                pydot.Edge(
                    nodes[before],
                    nodes[after],
                    splines="ortho",
                    constraint="false",
                )
            )
        return graph
