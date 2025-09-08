def sync_teachers(remote_url, api_key):
    """Sync teacher data to remote server"""
    try:
        from .models import Teacher
        teachers = Teacher.objects.all()
        
        teachers_data = []
        for teacher in teachers:
            teachers_data.append({
                'id': teacher.id,
                'teacher_fname': teacher.teacher_fname,
                'teacher_lname': teacher.teacher_lname,
                'teacher_contact': teacher.teacher_contact,
                'teacher_email': teacher.teacher_email,
                'teacher_address': teacher.teacher_address,
                'teacher_qualification': teacher.teacher_qualification,
                'teacher_experience': teacher.teacher_experience,
                'teacher_salary': float(teacher.teacher_salary) if teacher.teacher_salary else 0,
                'is_active': getattr(teacher, 'is_active', True)
            })
        
        import requests
        payload = {'teachers': teachers_data}
        
        response = requests.post(
            f"{remote_url}/api/sync/teachers/",
            json=payload,
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=30
        )
        
        if response.status_code == 200:
            return {'status': 'success', 'count': len(teachers_data)}
        else:
            return {'status': 'error', 'message': response.text}
            
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def sync_exams(remote_url, api_key):
    """Sync exam/test data to remote server"""
    try:
        from .models import Subject, TestSession, Test
        
        # Sync subjects first
        subjects = Subject.objects.all()
        subjects_data = []
        for subject in subjects:
            subjects_data.append({
                'id': subject.id,
                'subject_name': subject.subject_name,
                'class_name_id': subject.class_name.id if subject.class_name else None
            })
        
        # Sync test sessions
        test_sessions = TestSession.objects.all()
        sessions_data = []
        for session in test_sessions:
            sessions_data.append({
                'id': session.id,
                'name': session.name,
                'class_name_id': session.class_name.id if session.class_name else None,
                'section_id': session.section.id if session.section else None,
                'month': session.month,
                'session_type': getattr(session, 'session_type', 'monthly'),
                'is_active': session.is_active
            })
        
        # Sync tests
        tests = Test.objects.all()
        tests_data = []
        for test in tests:
            tests_data.append({
                'id': test.id,
                'test_session_id': test.test_session.id if test.test_session else None,
                'subject_id': test.subject.id if test.subject else None,
                'test_name': getattr(test, 'test_name', ''),
                'total_marks': test.total_marks,
                'test_date': test.test_date.isoformat() if test.test_date else None
            })
        
        import requests
        payload = {
            'subjects': subjects_data,
            'test_sessions': sessions_data,
            'tests': tests_data
        }
        
        response = requests.post(
            f"{remote_url}/api/sync/exams/",
            json=payload,
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=30
        )
        
        if response.status_code == 200:
            return {'status': 'success', 'count': len(subjects_data) + len(sessions_data) + len(tests_data)}
        else:
            return {'status': 'error', 'message': response.text}
            
    except Exception as e:
        return {'status': 'error', 'message': str(e)}