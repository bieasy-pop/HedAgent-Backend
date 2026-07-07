# # Add this endpoint to app/routers/admin.py

# @router.delete("/user/{user_id}", summary="Delete a user and all related data")
# def delete_user(
#     user_id: str,
#     db: Session = Depends(get_db),
#     current_user: dict = Depends(require_role("admin")),
# ):
#     from app.models.student import Student
#     from app.models.educator import Educator
#     from app.models.ai_classification import AIClassification
#     from app.models.course import StudentCourse, EducatorCourse
#     from app.models.relationship import EducatorStudent
#     from app.models.reminder import Reminder
#     from app.models.intervention import Intervention
#     from app.models.notification_log import NotificationLog
#     from app.models.educator_approval import EducatorApproval
#     from firebase_admin import auth as fa

#     user = db.query(User).filter(User.id == user_id).first()
#     if not user:
#         raise HTTPException(
#             status_code=404,
#             detail={"success": False, "message": "User not found.", "code": "NOT_FOUND"}
#         )

#     # Prevent self-deletion
#     if user_id == current_user["uid"]:
#         raise HTTPException(
#             status_code=400,
#             detail={"success": False, "message": "You cannot delete your own account.", "code": "SELF_DELETE"}
#         )

#     student = db.query(Student).filter(Student.user_id == user_id).first()
#     educator = db.query(Educator).filter(Educator.user_id == user_id).first()

#     if student:
#         db.query(AIClassification).filter(AIClassification.student_id == student.id).delete()
#         db.query(StudentCourse).filter(StudentCourse.student_id == student.id).delete()
#         db.query(EducatorStudent).filter(EducatorStudent.student_id == student.id).delete()
#         db.query(Reminder).filter(Reminder.student_id == student.id).delete()
#         db.query(Intervention).filter(Intervention.student_id == student.id).delete()
#         db.query(Student).filter(Student.id == student.id).delete()

#     if educator:
#         db.query(EducatorCourse).filter(EducatorCourse.educator_id == educator.id).delete()
#         db.query(EducatorStudent).filter(EducatorStudent.educator_id == educator.id).delete()
#         db.query(EducatorApproval).filter(EducatorApproval.educator_user_id == user_id).delete()
#         db.query(Educator).filter(Educator.id == educator.id).delete()

#     db.query(NotificationLog).filter(NotificationLog.recipient_id == user_id).delete()
#     db.query(User).filter(User.id == user_id).delete()
#     db.commit()

#     # Also delete from Firebase
#     try:
#         fa.delete_user(user_id)
#     except Exception:
#         pass  # non-fatal — DB record is already gone

#     return {
#         "success": True,
#         "message": f"User {user_id} and all related data deleted successfully.",
#     }