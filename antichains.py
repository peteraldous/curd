from kanren import eq, run, membero, var, lall, lany, Relation, facts, reify, isvar

ordered = Relation()

facts(
    ordered,
    ("CS 1400", "CS 1410"),
    ("CS 1410", "CS 2420"),
    ("CS 1410", "CS 2300"),
    ("CS 1410", "CS 2370"),
    ("CS 1410", "CS 2420"),
    ("CS 2300", "CS 2450"),
    ("CS 2420", "CS 2450"),
    ("CS 1410", "CS 2550"),
    ("CS 2810", "CS 2600"),
    ("CS 1400", "CS 2810"),
    ("ENGL 2010", "CS 305G"),
    ("CS 1400", "CS 305G"),
    ("CS 2450", "CS 305G"),
    ("CS 2370", "CS 3060"),
    ("CS 2420", "CS 3060"),
    ("CS 2450", "CS 3060"),
    ("CS 3100", "CS 2420"),
    ("CS 2450", "CS 3100"),
    ("CS 2300", "CS 3240"),
    ("CS 2420", "CS 3240"),
    ("CS 2810", "CS 3240"),
    ("CS 2450", "CS 3240"),
    ("CS 2450", "CS 3310"),
    ("CS 2370", "CS 3370"),
    ("CS 2810", "CS 3370"),
    ("CS 2450", "CS 3370"),
    ("CS 3370", "CS 3450"),
    ("CS 2450", "CS 3520"),
    ("CS 3060", "CS 4380"),
    ("CS 3370", "CS 4380"),
    ("CS 2450", "CS 4380"),
    ("CS 3240", "CS 4450"),
    ("CS 3370", "CS 4450"),
    ("CS 2450", "CS 4450"),
    ("CS 3240", "CS 4470"),
    ("CS 3310", "CS 4470"),
    ("CS 3370", "CS 4470"),
    ("CS 2450", "CS 4470"),
    ("CS 3450", "CS 4490"),
    ("CS 4380", "CS 4490"),
    ("CS 2450", "CS 4490"),
    ("ENGL 1010", "ENGL 2010"),
    ("ENGL 1010", "BIOL 1610"),
    ("ENGL 1010", "PHIL 2050"),
    ("CS 3100", "CS 3110"),
    ("CS 2300", "CS 3110"),
    ("CS 2450", "CS 3110"),
    ("CS 3100", "CS 3120"),
    ("CS 2450", "CS 3120"),
    ("CS 2450", "CS 3410"),
    ("CS 2550", "CS 3410"),
    ("CS 2450", "CS 3540"),
    ("CS 3520", "CS 3530"),
    ("CS 2450", "CS 3530"),
)


def before(*args):
    def before_goal(S):
        nonlocal args
        args_rf = reify(args, S)

        x = 1
        for a in args_rf:
            S_new = S.copy()

            if isvar(a) or x > 3:
                S_new[a] = x

            z = yield S_new

            if not z:
                x += 1

        # if ordered(

    middle = var()
    return lany(ordered(x, y), lall(before(x, middle), ordered(middle, y)))


after = var()
run(0, after, before("CS 2450", after))
