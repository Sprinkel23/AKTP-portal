import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app


def login(client: TestClient, identifier: str, password: str, portal_role: str) -> dict:
    resp = client.post("/api/auth/login", json={"identifier": identifier, "password": password, "portal_role": portal_role})
    assert resp.status_code == 200, f"Login failed for {identifier}: {resp.text}"
    return resp.json()


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def run_verification():
    with TestClient(app) as client:
        # 1. Public Homepage & Contact
        pub = client.get("/api/public/home")
        assert pub.status_code == 200
        pub_data = pub.json()
        assert len(pub_data["classes"]) >= 10
        assert len(pub_data["announcements"]) >= 1

        contact = client.post("/api/public/contact", json={
            "name": "Test Parent",
            "phone": "+919999888877",
            "student_class": "Class 10",
            "message": "Admission inquiry",
        })
        assert contact.status_code == 200

        # 2. All 4 Portal Logins & Cross-Portal Isolation
        admin_auth = login(client, "admin", "Admin@123", "admin")
        teacher_auth = login(client, "teacher1", "Teacher@123", "teacher")
        student_auth = login(client, "AK001", "Student@123", "student")
        parent_auth = login(client, "parent1", "Parent@123", "parent")
        parent_phone_auth = login(client, "9811111001", "Parent@123", "parent")
        assert parent_phone_auth["user"]["username"] == "parent1"

        # 2a. Parent Registered Phone-Only Login
        p_only = client.post("/api/auth/parent/phone-login", json={"phone": "9811111001"})
        assert p_only.status_code == 200 and p_only.json()["user"]["role"] == "parent", p_only.text

        # 2b. Teacher Mobile + OTP Login
        otp_req = client.post("/api/auth/teacher/request-otp", json={"phone": "9876500001"})
        assert otp_req.status_code == 200 and otp_req.json().get("demo_otp"), otp_req.text
        otp_verify = client.post("/api/auth/teacher/verify-otp", json={"phone": "9876500001", "otp_code": otp_req.json()["demo_otp"]})
        assert otp_verify.status_code == 200 and otp_verify.json()["user"]["role"] == "teacher"

        # Cross-portal login blocked
        bad_portal = client.post("/api/auth/login", json={"identifier": "AK001", "password": "Student@123", "portal_role": "admin"})
        assert bad_portal.status_code == 403

        # Student cannot access Admin endpoint
        assert client.get("/api/admin/dashboard", headers=auth_header(student_auth["access_token"])).status_code == 403
        # Teacher cannot access Admin fees
        assert client.get("/api/admin/fees", headers=auth_header(teacher_auth["access_token"])).status_code == 403
        # Parent1 cannot access Parent2's child (student id 2 = AK002)
        assert client.get("/api/parent/dashboard?student_id=2", headers=auth_header(parent_auth["access_token"])).status_code == 403

        # 3. Admin Dashboard & Auto Student ID (AK005+)
        dash = client.get("/api/admin/dashboard", headers=auth_header(admin_auth["access_token"]))
        assert dash.status_code == 200
        assert dash.json()["cards"]["total_students"] >= 4

        classes = client.get("/api/admin/classes", headers=auth_header(admin_auth["access_token"])).json()
        class10 = next(c for c in classes if c["grade_level"] == 10)

        new_st = client.post(
            "/api/admin/students",
            headers=auth_header(admin_auth["access_token"]),
            json={
                "student_name": "Kiran Hegde",
                "gender": "Male",
                "class_id": class10["id"],
                "section": "A",
                "parent_name": "Mrs. Kavitha Hegde",
                "parent_phone": "+919822223344",
            },
        )
        assert new_st.status_code == 200, new_st.text
        st_created = new_st.json()
        assert st_created["student_code"].startswith("AK")
        new_sid = st_created["id"]
        creds = st_created["generated_credentials"]
        assert creds["student_password"].startswith("AK@")
        # Verify newly generated unique student password logs in
        login(client, creds["student_username"], creds["student_password"], "student")
        if creds["parent_is_new"]:
            login(client, creds["parent_phone"], creds["parent_password"], "parent")
        # Verify Admin Reset Credentials endpoint generates a new unique password
        reset_res = client.post(f"/api/admin/students/{new_sid}/reset-credentials", headers=auth_header(admin_auth["access_token"]))
        assert reset_res.status_code == 200
        reset_creds = reset_res.json()
        assert reset_creds["student_password"] != creds["student_password"]
        login(client, reset_creds["student_username"], reset_creds["student_password"], "student")

        # 4. Fee Payment & Duplicate Reference Prevention & Receipt PDF
        ref = f"TESTREF-{date.today().isoformat()}-{new_sid}"
        pay1 = client.post(
            "/api/admin/payments",
            headers=auth_header(admin_auth["access_token"]),
            json={"student_id": new_sid, "amount": 5000, "payment_mode": "UPI", "reference_number": ref},
        )
        assert pay1.status_code == 200, pay1.text
        pay_id = pay1.json()["id"]

        dup_pay = client.post(
            "/api/admin/payments",
            headers=auth_header(admin_auth["access_token"]),
            json={"student_id": new_sid, "amount": 1000, "payment_mode": "UPI", "reference_number": ref},
        )
        assert dup_pay.status_code == 409

        rec_pdf = client.get(f"/api/admin/payments/{pay_id}/receipt-pdf", headers=auth_header(admin_auth["access_token"]))
        assert rec_pdf.status_code == 200 and rec_pdf.content.startswith(b"%PDF")

        # 5. Teacher Attendance & Absent Details Check
        today_str = date.today().isoformat()
        att_res = client.post(
            "/api/teacher/attendance",
            headers=auth_header(teacher_auth["access_token"]),
            json={
                "class_id": class10["id"],
                "attendance_date": today_str,
                "entries": [{"student_id": student_auth["user"]["student_id"], "status": "ABSENT", "remarks": "Fever"}],
            },
        )
        assert att_res.status_code == 200

        st_att = client.get("/api/student/attendance", headers=auth_header(student_auth["access_token"])).json()
        assert st_att["absent_days"] >= 1
        assert all(set(item.keys()) == {"absent_date", "attendance_status"} for item in st_att["absent_details"])

        # 6. Teacher Marks Entry -> PENDING -> Admin Approval -> PUBLISHED -> Marks Card PDF
        subjects_list = client.get("/api/admin/subjects", headers=auth_header(admin_auth["access_token"])).json()
        math_subj = next(s for s in subjects_list if s["code"] == "MATH")
        temp_exam = client.post(
            "/api/admin/examinations",
            headers=auth_header(admin_auth["access_token"]),
            json={
                "name": "E2E Verification Exam",
                "class_id": class10["id"],
                "exam_type": "UNIT_TEST",
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=2)).isoformat(),
                "subjects": [
                    {
                        "subject_id": math_subj["id"],
                        "exam_date": date.today().isoformat(),
                        "start_time": "10:00 AM",
                        "duration_minutes": 60,
                        "max_marks": 50,
                        "passing_marks": 18,
                    }
                ],
            },
        )
        assert temp_exam.status_code == 200, temp_exam.text
        temp_exam_id = temp_exam.json()["id"]

        teacher_exams = client.get("/api/teacher/examinations", headers=auth_header(teacher_auth["access_token"])).json()
        target_ex = next(ex for ex in teacher_exams if ex["id"] == temp_exam_id)
        target_es = target_ex["subjects"][0]
        # Validate marks > max_marks rejected
        over_marks = client.post(
            "/api/teacher/marks",
            headers=auth_header(teacher_auth["access_token"]),
            json={
                "examination_id": target_ex["id"],
                "examination_subject_id": target_es["examination_subject_id"],
                "submit_for_approval": True,
                "entries": [{"student_id": student_auth["user"]["student_id"], "marks_obtained": 999}],
            },
        )
        assert over_marks.status_code == 400, over_marks.text

        # Submit valid marks -> status becomes PENDING
        sub_marks = client.post(
            "/api/teacher/marks",
            headers=auth_header(teacher_auth["access_token"]),
            json={
                "examination_id": target_ex["id"],
                "examination_subject_id": target_es["examination_subject_id"],
                "submit_for_approval": True,
                "entries": [{"student_id": student_auth["user"]["student_id"], "marks_obtained": 46}],
            },
        )
        assert sub_marks.status_code == 200 and sub_marks.json()["status"] == "PENDING", sub_marks.text

        # Student cannot see pending exam before approval
        st_results_before = client.get("/api/student/results", headers=auth_header(student_auth["access_token"])).json()
        assert target_ex["id"] not in {r["examination_id"] for r in st_results_before}

        # Admin approves pending submission
        approvals = client.get("/api/admin/result-approvals?status_filter=PENDING", headers=auth_header(admin_auth["access_token"])).json()
        target_ap = next(a for a in approvals if a["examination_subject_id"] == target_es["examination_subject_id"])
        rev = client.post(
            f"/api/admin/result-approvals/{target_ap['id']}/review",
            headers=auth_header(admin_auth["access_token"]),
            json={"action": "APPROVE", "send_notifications": True},
        )
        assert rev.status_code == 200 and rev.json()["status"] == "PUBLISHED"

        # Now Student & Parent see published exam and can download Official Marks Card PDF
        st_results_after = client.get("/api/student/results", headers=auth_header(student_auth["access_token"])).json()
        assert target_ex["id"] in {r["examination_id"] for r in st_results_after}

        exam_id = st_results_after[0]["examination_id"]
        mc_pdf = client.get(f"/api/student/results/{exam_id}/marks-card-pdf", headers=auth_header(student_auth["access_token"]))
        assert mc_pdf.status_code == 200 and mc_pdf.content.startswith(b"%PDF")

        parent_mc = client.get(
            f"/api/parent/children/{student_auth['user']['student_id']}/results/{exam_id}/marks-card-pdf",
            headers=auth_header(parent_auth["access_token"]),
        )
        assert parent_mc.status_code == 200 and parent_mc.content.startswith(b"%PDF")

        # 6b. Teacher Question Paper (including total marks validation & PDF)
        bad_qp = client.post(
            "/api/teacher/question-papers",
            headers=auth_header(teacher_auth["access_token"]),
            json={
                "title": "Mismatch Paper",
                "class_id": class10["id"],
                "subject_id": target_es["subject_id"],
                "duration_minutes": 30,
                "total_marks": 10,
                "questions": [{"question_type": "ONE_MARK", "question_text": "Q1", "marks": 1}],
            },
        )
        assert bad_qp.status_code == 400

        good_qp = client.post(
            "/api/teacher/question-papers",
            headers=auth_header(teacher_auth["access_token"]),
            json={
                "title": "Verified Practice Paper",
                "class_id": class10["id"],
                "subject_id": target_es["subject_id"],
                "duration_minutes": 30,
                "total_marks": 5,
                "questions": [
                    {"question_type": "ONE_MARK", "question_text": "Define Newton's 1st law.", "marks": 1},
                    {"question_type": "FOUR_MARK", "question_text": "Derive quadratic formula.", "marks": 4},
                ],
            },
        )
        assert good_qp.status_code == 200, good_qp.text
        qp_pdf = client.get(f"/api/teacher/question-papers/{good_qp.json()['id']}/pdf", headers=auth_header(teacher_auth["access_token"]))
        assert qp_pdf.status_code == 200 and qp_pdf.content.startswith(b"%PDF")

        # 6c. Teacher Adds Student (any class) + Unified All-Class Attendance + Absence Alert + Student Self-Signup + QR Verify
        class1 = next(c for c in classes if c["grade_level"] == 1)
        t_st = client.post(
            "/api/teacher/students",
            headers=auth_header(teacher_auth["access_token"]),
            json={
                "student_name": "Meera Nair",
                "class_id": class1["id"],
                "section": "A",
                "student_phone": "+919844445566",
            },
        )
        assert t_st.status_code == 200, t_st.text
        t_st_id = t_st.json()["id"]
        t_creds = t_st.json()["generated_credentials"]
        login(client, t_creds["student_username"], t_creds["student_password"], "student")

        # Unified all-class attendance -> absent triggers real-time absence alerts
        all_att_sheet = client.get(f"/api/teacher/attendance?attendance_date={today_str}", headers=auth_header(teacher_auth["access_token"]))
        assert all_att_sheet.status_code == 200 and len(all_att_sheet.json()["students"]) >= 5
        all_att_save = client.post(
            "/api/teacher/attendance",
            headers=auth_header(teacher_auth["access_token"]),
            json={
                "attendance_date": today_str,
                "entries": [{"student_id": t_st_id, "status": "ABSENT", "remarks": "Family trip"}],
            },
        )
        assert all_att_save.status_code == 200
        assert len(all_att_save.json().get("absent_alerts", [])) >= 1
        assert all_att_save.json()["absent_alerts"][0]["whatsapp_url"].startswith("https://wa.me/")

        # Student self-signup by mobile number -> auto-generated login credentials
        signup = client.post(
            "/api/auth/student/signup",
            json={"student_name": "Vikram SelfSignup", "class_id": class1["id"], "student_phone": "9855556677"},
        )
        assert signup.status_code == 200, signup.text
        signup_creds = signup.json()["generated_credentials"]
        signup_sid = signup.json()["user"]["student_id"]
        login(client, signup_creds["student_username"], signup_creds["student_password"], "student")
        client.delete(f"/api/admin/students/{signup_sid}?hard_delete=true", headers=auth_header(admin_auth["access_token"]))

        # QR Verification endpoint + Public VTU Captcha + AI Assistant
        qr_ver = client.get(f"/api/public/verify-markscard?code={student_auth['user']['student_code']}&exam={exam_id}")
        assert qr_ver.status_code == 200 and qr_ver.json()["verified"] is True

        cap = client.get("/api/public/result-captcha")
        assert cap.status_code == 200 and "<svg" in cap.json()["svg"]
        bad_lookup = client.post("/api/public/results/lookup", json={
            "mode": "register_no",
            "register_no": "AK001A",
            "captcha_token": cap.json()["captcha_token"],
            "captcha_answer": "ZZZZZ",
        })
        assert bad_lookup.status_code == 400

        ai = client.post("/api/public/ai-assistant", json={"message": "How do I check my PUC marks card result?"})
        assert ai.status_code == 200 and len(ai.json().get("reply", "")) > 10

        # Submit draft/pending marks for another exam subject -> Admin Publish All at once
        sci_subj = next(s for s in subjects_list if s["code"] == "SCI")
        bulk_exam = client.post(
            "/api/admin/examinations",
            headers=auth_header(admin_auth["access_token"]),
            json={
                "name": "Bulk Publish Test Exam",
                "class_id": class10["id"],
                "exam_type": "UNIT_TEST",
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=1)).isoformat(),
                "subjects": [{
                    "subject_id": sci_subj["id"],
                    "exam_date": date.today().isoformat(),
                    "max_marks": 50,
                    "passing_marks": 18,
                }],
            },
        ).json()
        bulk_ex_list = client.get("/api/teacher/examinations", headers=auth_header(teacher_auth["access_token"])).json()
        bulk_ex_item = next(e for e in bulk_ex_list if e["id"] == bulk_exam["id"])
        bulk_es = bulk_ex_item["subjects"][0]["examination_subject_id"]
        client.post(
            "/api/teacher/marks",
            headers=auth_header(teacher_auth["access_token"]),
            json={
                "examination_id": bulk_exam["id"],
                "examination_subject_id": bulk_es,
                "submit_for_approval": True,
                "entries": [{"student_id": student_auth["user"]["student_id"], "marks_obtained": 48}],
            },
        )
        pub_all = client.post(
            "/api/admin/result-approvals/publish-all",
            headers=auth_header(admin_auth["access_token"]),
            json={"examination_id": bulk_exam["id"], "send_notifications": True},
        )
        assert pub_all.status_code == 200 and pub_all.json()["approved_count"] >= 1 and len(pub_all.json()["dispatches"]) >= 1

        t_res_pdf = client.get("/api/teacher/results-pdf", headers=auth_header(teacher_auth["access_token"]))
        assert t_res_pdf.status_code == 200 and t_res_pdf.content.startswith(b"%PDF")
        assert st_results_after[0].get("class_rank") is not None
        assert "dispatches" in rev.json() and len(rev.json()["dispatches"]) >= 1
        client.delete(f"/api/admin/students/{t_st_id}?hard_delete=true", headers=auth_header(admin_auth["access_token"]))

        # 7. Online Practice Test (No Answer Leak Before Submission)
        tests_list = client.get("/api/student/tests", headers=auth_header(student_auth["access_token"])).json()
        assert len(tests_list) >= 1
        started = client.post(f"/api/student/tests/{tests_list[0]['id']}/start", headers=auth_header(student_auth["access_token"])).json()
        for q in started["questions"]:
            assert "correct_answer" not in q
            for o in q.get("options", []):
                assert "is_correct" not in o

        # 8. All 13 Admin Reports (PDF & Excel)
        report_types = [
            "overall_students",
            "class_wise_students",
            "student_attendance",
            "absent_students",
            "overall_attendance_percentage",
            "examination_timetable",
            "examination_results",
            "class_wise_performance",
            "fee_collection",
            "pending_fees",
            "student_payment_history",
            "teacher_report",
        ]
        for rt in report_types:
            r_pdf = client.get(f"/api/admin/reports/{rt}?format=pdf", headers=auth_header(admin_auth["access_token"]))
            assert r_pdf.status_code == 200 and r_pdf.content.startswith(b"%PDF"), f"PDF failed for {rt}"
            r_xls = client.get(f"/api/admin/reports/{rt}?format=xlsx", headers=auth_header(admin_auth["access_token"]))
            assert r_xls.status_code == 200 and r_xls.content.startswith(b"PK"), f"XLSX failed for {rt}"

        r_card = client.get(
            f"/api/admin/reports/individual_marks_card?format=pdf&student_id={student_auth['user']['student_id']}&examination_id={exam_id}",
            headers=auth_header(admin_auth["access_token"]),
        )
        assert r_card.status_code == 200 and r_card.content.startswith(b"%PDF")

        # 9. Photo in News/Announcement, Teacher Direct Re-Exam Marks, Watermark QP PDF, 15-day Result Expiry & Webhook Setting
        tiny_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc```\xf8\x0f\x00\x01\x04\x01\x00\x1c\x83\xdc=\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        photo_up = client.post(
            "/api/admin/announcements/upload-photo",
            headers=auth_header(admin_auth["access_token"]),
            files={"file": ("news_student.png", tiny_png, "image/png")},
        )
        assert photo_up.status_code == 200 and photo_up.json()["image_path"].startswith("data:image/png;base64,")
        ann_photo = client.post(
            "/api/admin/announcements",
            headers=auth_header(admin_auth["access_token"]),
            json={
                "title": "Topper Photo News",
                "category": "NEWS",
                "content": "Congratulations to AK Tuition topper!",
                "image_path": photo_up.json()["image_path"],
            },
        )
        assert ann_photo.status_code == 200
        pub_home_after = client.get("/api/public/home").json()
        assert any(a["title"] == "Topper Photo News" and (a.get("image_path") or "").startswith("data:image/") for a in pub_home_after["announcements"])
        client.delete(f"/api/admin/announcements/{ann_photo.json()['id']}", headers=auth_header(admin_auth["access_token"]))

        re_direct = client.post(
            "/api/teacher/marks/direct",
            headers=auth_header(teacher_auth["access_token"]),
            json={
                "exam_name": "Special Re-Exam Verification",
                "exam_type": "RE_EXAMINATION",
                "class_id": class10["id"],
                "subject_id": sci_subj["id"],
                "max_marks": 100,
                "submit_for_approval": True,
                "entries": [{"student_id": student_auth["user"]["student_id"], "marks_obtained": 89}],
            },
        )
        assert re_direct.status_code == 200, re_direct.text
        re_ex_id = re_direct.json()["examination_id"]
        re_pub = client.post(
            "/api/admin/result-approvals/publish-all",
            headers=auth_header(admin_auth["access_token"]),
            json={"examination_id": re_ex_id, "send_notifications": True},
        )
        assert re_pub.status_code == 200
        ann_res = client.get("/api/public/results/announcements").json()
        re_item = next(x for x in ann_res["declared_exams"] if x["id"] == re_ex_id)
        assert re_item["days_remaining"] == 15 and re_item["is_expired"] is False

        from app.database import SessionLocal
        from app.models import Examination
        db_s = SessionLocal()
        try:
            ex_row = db_s.query(Examination).filter(Examination.id == re_ex_id).first()
            ex_row.results_declared_at = datetime.utcnow() - timedelta(days=16)
            db_s.commit()
        finally:
            db_s.close()

        expired_qr = client.get(f"/api/public/verify-markscard?code={student_auth['user']['student_code']}&exam={re_ex_id}")
        assert expired_qr.status_code == 410
        redec = client.post(f"/api/admin/examinations/{re_ex_id}/redeclare", headers=auth_header(admin_auth["access_token"]))
        assert redec.status_code == 200
        active_qr = client.get(f"/api/public/verify-markscard?code={student_auth['user']['student_code']}&exam={re_ex_id}")
        assert active_qr.status_code == 200 and active_qr.json()["verified"] is True

        wm_qp = client.post(
            "/api/teacher/question-papers",
            headers=auth_header(teacher_auth["access_token"]),
            json={
                "title": "Watermarked Auto Paper",
                "class_id": class10["id"],
                "subject_id": sci_subj["id"],
                "duration_minutes": 45,
                "total_marks": 5,
                "watermark_text": "AK TUITION RE-EXAM",
                "questions": [{
                    "question_type": "FIVE_MARK",
                    "question_text": "Derive Ohm law with circuit diagram.",
                    "marks": 5,
                }],
            },
        )
        assert wm_qp.status_code == 200
        wm_pdf = client.get(f"/api/teacher/question-papers/{wm_qp.json()['id']}/pdf", headers=auth_header(teacher_auth["access_token"]))
        assert wm_pdf.status_code == 200 and wm_pdf.content.startswith(b"%PDF")

        st_get = client.get("/api/admin/settings", headers=auth_header(admin_auth["access_token"])).json()
        assert "whatsapp_webhook_url" in st_get

        # Cleanup test student so seeded state stays tidy
        client.delete(f"/api/admin/students/{new_sid}?hard_delete=true", headers=auth_header(admin_auth["access_token"]))
        print("ALL_END_TO_END_PORTAL_TESTS_PASSED")


if __name__ == "__main__":
    run_verification()
