class ClassSection:
    def __init__(self, name):
        self.name = name
        self.subject_teacher_map = {}


class ClassObj:
    def __init__(self, name, subject_teacher_map, room):
        self.name = name
        self.subject_teacher_map = subject_teacher_map
        self.room = room
