"""Foydalanuvchi turi. Panel bitta egaga mo'ljallangan: ma'lumotlarda ``user`` ustuni yo'q,
shuning uchun o'quvchi panelga kirsa hammasini ko'radi — uni ``StudentGateMiddleware`` to'sadi."""


def is_student(user) -> bool:
    return hasattr(user, "student")
