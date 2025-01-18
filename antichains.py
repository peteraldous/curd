from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple
import math
import os
import pydot
import sys

from z3 import (
    Const,
    Datatype,
    ExprRef,
    Implies,
    IntSort,
    IntVal,
    Solver,
    StringSort,
    z3types,
)

Z = IntSort()
S = StringSort()


@dataclass
class CourseData:
    term: Const
    credits: Const


CourseType = Datatype("CourseType")
CourseType.declare("Course", ("term", Z), ("credits", Z))
CourseType = CourseType.create()


class Op(Enum):
    LT = 1
    LE = 2
    GT = 3
    GE = 4
    EQ = 5
    NE = 6
    PAR = 7


@dataclass(order=True, frozen=True)
class Constraint:
    l_course: str
    op: Op
    r_course: str | int


@dataclass
class Schedule:
    schedule: list[Tuple[int, set[str]]]

    def __str__(self):
        result = ""
        for index, (total, classes) in enumerate(self.schedule):
            term = index + 1
            result += f"Term {term} ({total} credits):" + os.linesep
            for c in sorted(classes):
                result += f"\t{c}" + os.linesep
        return result


class Scheduler:
    def __init__(
        self,
        courses: Iterable[Tuple[str, int]],
        prereqs: Iterable[Tuple[str, str]],
        term_count: int,
        term_credit_max: int,
        terms_past: int,
        constraints: Optional[Iterable[Tuple[str, Op, str | int]]] = None,
    ):
        self.solver = Solver()
        self.solver.set("timeout", 600)
        self.prereqs = prereqs
        self.term_count = term_count
        self.term_credit_max = term_credit_max
        self.max_credits = Const("max_credits", Z)
        self.terms_past = terms_past
        self.credits_past = 0
        courses = sorted(courses)
        self.total_required = sum(map(lambda p: p[1], courses))

        if constraints is None:
            constraints = []
        else:
            constraints = list(constraints)

        past_courses: set[str] = set()

        for lhs, op, rhs in constraints:
            if isinstance(rhs, int) and rhs <= terms_past:
                past_courses.add(lhs)

        self.course_lookup = {
            name: self.make_course_data(
                name, credits, 0 if name in past_courses else terms_past
            )
            for (name, credits) in sorted(courses)
        }
        self.counter = 0

        for lhs, op, rhs in constraints:
            self.add_constraint(lhs, op, rhs)

    def make_course_data(
        self, name: str, credits: int, term_infimum: int
    ) -> CourseData:
        term = Const(name + "_term", Z)
        credit_var = Const(name + "_credits", Z)
        if term_infimum < self.terms_past:
            self.credits_past += credits
        self.solver.add(term > term_infimum, term <= self.term_count)
        self.solver.add(
            credit_var == IntVal(credits),
            credit_var > 0,
            credit_var <= self.max_credits,
        )
        return CourseData(term, credit_var)

    def to_const(self, datum: ExprRef | str | int) -> ExprRef:
        if isinstance(datum, ExprRef):
            return datum
        elif isinstance(datum, str):
            course = self.course_lookup.get(datum)
            if course:
                return course.term
            raise ValueError("No such course: %s" % datum)
        else:
            if datum < 1:
                datum += self.term_count
            return IntVal(datum)

    def make_term_total_variable(self, term: int):
        old_counter = self.counter
        self.counter += 1
        return Const(f"total_{term}_{old_counter}", Z)

    def generate_schedule(self) -> Schedule:

        self.solver.add(self.max_credits <= IntVal(self.term_credit_max))
        self.solver.add(
            self.max_credits
            >= IntVal(
                math.ceil(
                    (self.total_required - self.credits_past)
                    / (self.term_count - self.terms_past)
                )
            )
        )

        def prerequisite(before: ExprRef | str | int, after: ExprRef | str | int):
            self.add_constraint(before, Op.LT, after)

        for before, after in self.prereqs:
            prerequisite(before, after)

        self.totals: list[ExprRef] = [
            self.make_term_total_variable(index + 1) for index in range(self.term_count)
        ]
        for total in self.totals:
            self.solver.add(total == IntVal(0))
        for course, data in self.course_lookup.items():
            for index, prev_total in enumerate(self.totals):
                term = index + 1
                next_total = self.make_term_total_variable(term)
                term_val = IntVal(term)
                self.solver.add(
                    Implies(
                        data.term == term_val, next_total == prev_total + data.credits
                    )
                )
                self.solver.add(
                    Implies(data.term != term_val, next_total == prev_total)
                )
                self.totals[index] = next_total

        for index, total in enumerate(self.totals):
            if index < self.terms_past:
                continue
            self.solver.add(total <= self.max_credits)

        return self.update()

    def add_constraint(
        self, l_course: ExprRef | str | int, op: Op, r_course: ExprRef | str | int
    ):
        l_const = self.to_const(l_course)
        r_const = self.to_const(r_course)
        # if l_const is None or r_const is None:
        # return
        match op:
            case Op.LT:
                self.solver.add(l_const < r_const)
            case Op.LE:
                self.solver.add(l_const <= r_const)
            case Op.GT:
                self.solver.add(l_const > r_const)
            case Op.GE:
                self.solver.add(l_const >= r_const)
            case Op.EQ:
                self.solver.add(l_const == r_const)
            case Op.NE:
                self.solver.add(l_const != r_const)
            case Op.PAR:
                self.solver.add((l_const % IntVal(2)) == (r_const % IntVal(2)))
            case _:
                raise ValueError("%s is not an Op!" % (op,))

    def update(self) -> Schedule:
        self.solver.check()
        model = self.solver.model()
        term_credit_max = self.term_credit_max

        attempt_solver = self.solver.__copy__()
        attempt_solver.set("timeout", 600)
        # attempt to find a solution with a tighter bound to even the semesters out
        while True:
            term_credit_max -= 1
            attempt_solver.add(self.max_credits <= IntVal(term_credit_max))
            try:
                attempt_solver.check()
                model = attempt_solver.model()
            except z3types.Z3Exception:
                # when the solver fails, continue with the last functional model
                break

        schedule: list[Tuple[int, set[str]]] = []
        terms: list[set[str]] = [set() for _ in range(self.term_count)]
        for name, c in self.course_lookup.items():
            terms[model[c.term].as_long() - 1].add(name)

        for index, classes in enumerate(terms):
            total = model[self.totals[index]]
            schedule.append((total, classes))

        self.schedule = Schedule(schedule)

        return self.schedule


if __name__ == "__main__":
    courses = [
        # general education
        ("engl_1010", 3),
        ("engl_2010", 3),
        ("math_1210", 4),
        ("hist_1700", 3),
        ("phil_2050", 3),
        ("hlth_1100", 2),
        ("comm_1020", 3),
        ("comm_2110", 3),
        ("fa_dist", 3),
        ("bio_dist", 3),
        ("phys_dist", 3),
        ("biol_1610", 4),
        ("biol_1615", 1),
        # core
        ("cs_1400", 3),
        ("cs_1410", 3),
        ("cs_2300", 3),
        ("cs_2370", 3),
        ("cs_2420", 3),
        ("cs_2450", 3),
        ("cs_2550", 3),
        ("cs_2600", 3),
        ("cs_2810", 3),
        ("cs_305g", 3),
        ("cs_3060", 3),
        ("cs_3100", 3),
        ("cs_3240", 3),
        ("cs_3520", 3),
        ("stat_2050", 4),
        # emphasis
        ("cs_3370", 3),
        ("cs_3310", 3),
        ("cs_3450", 3),
        ("cs_4380", 3),
        ("cs_4450", 3),
        ("cs_4470", 3),
        ("cs_4490", 3),
        # electives
        ("cs_3410", 3),
        ("cs_3320", 3),
        ("cs_3530", 3),
        ("cs_3660", 3),
        ("cs_3720", 3),
    ]

    prereqs = [
        ("engl_1010", "engl_2010"),
        ("cs_1400", "cs_1410"),
        ("cs_1410", "cs_2300"),
        ("cs_1410", "cs_2370"),
        ("cs_1410", "cs_2420"),
        ("cs_2300", "cs_2450"),
        ("cs_2420", "cs_2450"),
        ("cs_1410", "cs_2550"),
        ("cs_2810", "cs_2600"),
        ("cs_1400", "cs_2810"),
        ("cs_1400", "cs_305g"),
        ("engl_2010", "cs_305g"),
        ("cs_2370", "cs_3060"),
        ("cs_2420", "cs_3060"),
        ("cs_2450", "cs_3060"),
        ("cs_2810", "cs_3060"),
        ("cs_2420", "cs_3100"),
        ("cs_2450", "cs_3100"),
        ("cs_2300", "cs_3240"),
        ("cs_2420", "cs_3240"),
        ("cs_2810", "cs_3240"),
        ("cs_2450", "cs_3310"),
        ("math_1210", "cs_3320"),
        ("cs_2370", "cs_3370"),
        ("cs_2450", "cs_3370"),
        ("cs_2810", "cs_3370"),
        ("cs_2450", "cs_3410"),
        ("cs_3370", "cs_3450"),
        ("cs_2450", "cs_3520"),
        ("cs_3520", "cs_3530"),
        ("cs_2420", "cs_3660"),
        ("cs_2450", "cs_3660"),
        ("cs_2550", "cs_3660"),
        ("cs_3520", "cs_3720"),
        ("cs_2450", "cs_4380"),
        ("cs_3060", "cs_4380"),
        ("cs_2450", "cs_4450"),
        ("cs_3240", "cs_4450"),
        ("cs_3370", "cs_4450"),
        ("cs_2420", "cs_4470"),
        ("cs_2450", "cs_4470"),
        ("cs_3370", "cs_4470"),
        ("cs_3450", "cs_4490"),
        ("cs_4380", "cs_4490"),
        ("cs_4450", "cs_4490"),
    ]

    scheduler = Scheduler(
        courses,
        prereqs,
        8,
        18,
        [
            ("cs_4470", Op.NE, "cs_4490"),
            ("biol_1610", Op.EQ, "biol_1615"),
        ],
    )
    schedule = scheduler.generate_schedule()

    print(schedule)

    scheduler.add_constraint("cs_4490", Op.EQ, 8)
    scheduler.add_constraint("fa_dist", Op.EQ, 7)

    schedule = scheduler.update()

    print()
    print(schedule)
