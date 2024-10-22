from collections import namedtuple
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
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
import math

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


@dataclass
class Constraint:
    l_course: str
    op: Op
    r_course: str | int


class Scheduler:
    def __init__(self, courses, prereqs, term_count, term_credit_max):
        self.solver = Solver()
        self.courses = courses
        self.prereqs = prereqs
        self.term_count = term_count
        self.term_credit_max = term_credit_max

    def to_const(self, datum: str | ExprRef | int) -> ExprRef:
        if isinstance(datum, ExprRef):
            return datum
        elif isinstance(datum, str):
            return self.course_lookup[datum].term
        else:
            return IntVal(datum)

    def generate_schedule(
        self,
        additional_constraints: Optional[List[Constraint]] = None,
    ):
        counter = 0

        self.course_lookup: Dict[str, CourseData] = {}
        total_required = sum(map(lambda p: p[1], self.courses))

        self.max_credits = Const("max_credits", Z)
        self.solver.add(self.max_credits <= IntVal(self.term_credit_max))
        self.solver.add(
            self.max_credits >= IntVal(math.ceil(total_required / self.term_count))
        )

        def add_course(name: str, credits: int) -> CourseData:
            term = Const(name + "_term", Z)
            credit_var = Const(name + "_credits", Z)
            self.solver.add(term > 0, term <= self.term_count)
            self.solver.add(
                credit_var == IntVal(credits),
                credit_var > 0,
                credit_var <= self.max_credits,
            )
            return CourseData(term, credit_var)

        def prerequisite(before: ExprRef | str | int, after: ExprRef | str | int):
            self.add_constraint(before, Op.LT, after)

        def make_term_total_variable(term: int):
            nonlocal counter
            old_counter = counter
            counter += 1
            return Const(f"total_{term}_{old_counter}", Z)

        for name, credits in self.courses:
            self.course_lookup[name] = add_course(name, credits)

        if additional_constraints:
            for constraint in additional_constraints:
                self.add_constraint(
                    constraint.l_course,
                    Op.LT,
                    constraint.r_course,
                )

        for before, after in prereqs:
            prerequisite(before, after)

        self.totals: List[ExprRef] = [
            make_term_total_variable(index + 1) for index in range(self.term_count)
        ]
        for total in self.totals:
            self.solver.add(total == IntVal(0))
        for course, data in self.course_lookup.items():
            for index, prev_total in enumerate(self.totals):
                term = index + 1
                next_total = make_term_total_variable(term)
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

        for total in self.totals:
            self.solver.add(total <= self.max_credits)

        self.update()

    def add_constraint(
        self, l_course: ExprRef | str | int, op: Op, r_course: ExprRef | str | int
    ):
        l_const = self.to_const(l_course)
        r_const = self.to_const(r_course)
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
            case _:
                raise ValueError("%s is not an Op!" % (op,))

    def update(self):
        self.schedule: List[Tuple[int, Set[str]]] = []
        self.solver.check()
        model = self.solver.model()
        term_credit_max = self.term_credit_max

        attempt_solver = self.solver.__copy__()
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

        terms: List[Set[str]] = [set() for _ in range(self.term_count)]
        for name, c in self.course_lookup.items():
            terms[model[c.term].as_long() - 1].add(name)

        for index, classes in enumerate(terms):
            total = model[self.totals[index]]
            self.schedule.append((total, classes))

    def print_schedule(self):
        for index, (total, classes) in enumerate(self.schedule):
            term = index + 1
            print(f"Term {term} ({total} credits):")
            for c in sorted(classes):
                print(f"\t{c}")


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

    scheduler = Scheduler(courses, prereqs, 8, 18)
    scheduler.generate_schedule(
        [
            Constraint("cs_4470", Op.NE, "cs_4490"),
            Constraint("biol_1610", Op.EQ, "biol_1615"),
        ],
    )

    scheduler.print_schedule()

    scheduler.add_constraint("cs_4490", Op.EQ, 8)
    scheduler.add_constraint("fa_dist", Op.EQ, 7)

    scheduler.update()

    print()
    scheduler.print_schedule()
