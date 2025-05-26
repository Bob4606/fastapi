students = []

class StudentNotFound(Exception):
    def __init__(self, student_id: int):
        self.student_id = student_id
