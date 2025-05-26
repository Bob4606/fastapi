# # from fastapi import FastAPI, Depends, HTTPException
# # from pydantic import BaseModel
# # from starlette.responses import JSONResponse
# #
# # app = FastAPI()
# #
# # students = []
# #
# # class Student(BaseModel):
# #     name: str
# #     age: int
# #     grade: str
# #
# # @app.get("/")
# # def read_root():
# #     return {"message": "Welcome to FastAPI!"}
# #
# # @app.get("/students")
# # def get_students():
# #     return students
# #
# # @app.head("/students")
# # def head_student():
# #     return {"X-Total-Students": len(students)}
# #
# # @app.options("/students")
# # def option_student():
# #     return {
# #         "allowed_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
# #     }
# #
# # @app.post("/students")
# # def create_student(student: Student):
# #     students.append(student.dict())
# #     return {"message": "Student added", "data": student}
# #
# # @app.get("/students/{student_id}")
# # def get_student(student_id: int):
# #     if (0 <= student_id <
# #             len(students)):
# #         return students[student_id]
# #     raise HTTPException(status_code=404, detail="Student not found")
# #
# # @app.put("/students/{student_id}")
# # def update_student(student_id: int, student: Student):
# #     if 0 <= student_id < len(students):
# #         students[student_id] = student.dict()
# #         return {"message": "Student updated", "data": student}
# #     raise HTTPException(status_code=404, detail="Student not found")
# #
# # @app.patch("/students/{student_id}")
# # def partial_update_student(student_id: int, student: Student):
# #     if 0 <= student_id < len(students):
# #         current_data = students[student_id]
# #         update_data = student.dict(exclude_unset=True)
# #         current_data.update(update_data)
# #         students[student_id] = current_data
# #         return {"message": "Student partially updated", "data": current_data}
# #     raise HTTPException(status_code=404, detail="Student not found")
# #
# # @app.delete("/students/{student_id}")
# # def delete_student(student_id: int):
# #     if 0 <= student_id < len(students):
# #         removed = students.pop(student_id)
# #         return {"message": "Student deleted", "data": removed}
# #     raise HTTPException(status_code=404, detail="Student not found")
# #
# # @app.get("/search")
# # def search_student(name: str = None):
# #     if name:
# #         results = [s for s in students if s["name"].lower() == name.lower()]
# #         return {"results": results}
# #     return {"message": "No name provided"}
# #
# # def common_dependency():
# #     return {"note": "Common dependency injected"}
# #
# # @app.get("/check")
# # def check(dep=Depends(common_dependency)):
# #     return dep
# #
# from django.contrib.sessions.models import Session
# from fastapi import FastAPI, HTTPException
# from sqlmodel import session, select
# from models import Student
# from database import engine, create_db_and_tables
#
# app = FastAPI()
#
# @app.on_event("startup")
# def on_startup():
#     create_db_and_tables()
#
# @app.post("/students/")
# def add_student(student: Student):
#     with Session(engine) as session:
#         session.add(student)
#         session.commit()
#         session.refresh(student)
#         return student
#
# @app.get("/students/")
# def get_students():
#     with Session(engine) as session:
#         statement = select(Student)
#         results = session.exec(statement).all()
#         return results
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Field, SQLModel, Session, create_engine, select
from cachetools import TTLCache
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI()


class Student(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    age: int
    grade: str


sqlite_file_name = "students.db"
engine = create_engine(f"sqlite:///{sqlite_file_name}", echo=False)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


cache = TTLCache(maxsize=100, ttl=30)


@app.get("/students")
async def get_students(version: str = Header(default="v1")):
    logging.info("Fetching students list")

    if 'students' in cache:
        logging.info("Serving from cache")
        return cache['students']

    with Session(engine) as session:
        statement = select(Student)
        results = session.execute(statement).all()

        students_with_links = []
        for student in results:
            students_with_links.append({
                "id": student.id,
                "name": student.name,
                "age": student.age,
                "grade": student.grade,
                "links": [
                    {"rel": "self", "href": f"/students/{student.id}"},
                    {"rel": "updte", "href": f"/students/{student.id}"},
                    {"rel": "delete", "href": f"/students/{student.id}"},
                ]
            })
    cache['students'] = students_with_links
    return students_with_links


@app.post("/students")
def add_student(student: Student):
    with Session(engine) as session:
        existing = session.exec(select(Student).where(Student.id == student.id)).first()
        if existing:
            raise HTTPException(status_code=409, detail="Student with this ID already exists")

        session.add(student)
        session.commit()
        session.refresh(student)
        return student


@app.post("/webhook")
def webhook_receiver(data: dict):
    logging.info("f" Webhook received: {data}")
    return {"status": "received", "data": data}


@app.get("/v1/students")
def v1_students():
    return {"version": "v1", "message": "Using v1 structure"}


@app.get("/v2/students")
def v2_students():
    return {"version": "v2", "message": "Using v2 structure with new features"}


@app.get("/students-deprecated")
def deprecated_students():
    return JSONResponse(
        content={"message": "This endpoint is deprecated. Please use /students"},
        headers={"Deprecation": "true"}
    )


@app.get("/students/{student_id}")
def get_student(student_id: int):
    with Session(engine) as session:
        student = session.get(Student, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        return student


@app.put("/students/{student_id}")
def update_student(student_id: int, updated_data: Student):
    with Session(engine) as session:
        student = session.get(Student, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        student.name = updated_data.name
        student.age = updated_data.age
        student.grade = updated_data.grade
        session.add(student)
        session.commit()
        session.refresh(student)
        return student


@app.delete("/students/{student_id}")
def delete_student(student_id: int):
    with Session(engine) as session:
        student = session.get(Student, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        session.delete(student)
        session.commit()
        return {"message": f"Student {student.id} deleted"}
