import sys
from datetime import date, timedelta
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

        # 6c. Teacher Adds Student + Parent Phone & Prints Overall Student Result PDF + Class Rank check
        t_st = client.post(
            "/api/teacher/students",
            headers=auth_header(teacher_auth["access_token"]),
            json={
                "student_name": "Meera Nair",
                "class_id": class10["id"],
                "section": "A",
                "parent_name": "Mr. Suresh Nair",
                "parent_phone": "+919844445566",
            },
        )
        assert t_st.status_code == 200, t_st.text
        t_st_id = t_st.json()["id"]
        t_creds = t_st.json()["generated_credentials"]
        login(client, t_creds["student_username"], t_creds["student_password"], "student")
        t_res_pdf = client.get("/api/teacher/results-pdf", headers=auth_header(teacher_auth["access_token"]))
        assert t_res_pdf.status_code == 200 and t_res_pdf.content.startswith(b"%PDF")
        assert st_results_after[0].get("class_rank") is not None
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

        # Cleanup test student so seeded state stays tidy
        client.delete(f"/api/admin/students/{new_sid}?hard_delete=true", headers=auth_header(admin_auth["access_token"]))
        print("ALL_END_TO_END_PORTAL_TESTS_PASSED")


if __name__ == "__main__":
    run_verification()
