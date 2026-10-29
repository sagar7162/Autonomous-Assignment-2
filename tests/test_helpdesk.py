import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import helpdesk


class HelpdeskTests(unittest.TestCase):
    def test_out_of_scope_logs_and_refuses(self):
        with patch.object(helpdesk, 'route', return_value='OUT'), patch.object(helpdesk, 'log_unknown') as log:
            self.assertEqual(helpdesk.answer('Where can I eat?'), helpdesk.UNKNOWN)
            log.assert_called_once()

    def test_missing_course_never_invents_schedule(self):
        with patch.object(helpdesk, 'route', return_value='SCHEDULE'), patch.object(helpdesk, 'lookup', return_value=[]), patch.object(helpdesk, 'log_unknown') as log:
            self.assertIn("I don't know", helpdesk.answer('Slot for CSL7570?'))
            log.assert_called_once()

    def test_policy_citation_maps_to_real_evidence(self):
        evidence = [('a', '12 credits', {'title': 'Curriculum', 'page': '8', 'url': 'https://example.edu/source'}, 0.1)]
        with patch.object(helpdesk, 'route', return_value='POLICY'), patch.object(helpdesk, 'retrieve', return_value=evidence), patch.object(helpdesk, 'chat', return_value='12 credits [1]'):
            result = helpdesk.answer('How many credits?')
            self.assertIn('Curriculum, page 8: https://example.edu/source', result)

    def test_uncited_policy_answer_is_refused(self):
        evidence = [('a', 'text', {'title': 'Source', 'page': '1', 'url': 'https://example.edu'}, 0.1)]
        with patch.object(helpdesk, 'route', return_value='POLICY'), patch.object(helpdesk, 'retrieve', return_value=evidence), patch.object(helpdesk, 'chat', return_value='A fabricated fact.'), patch.object(helpdesk, 'log_unknown'):
            self.assertEqual(helpdesk.answer('Question'), helpdesk.UNKNOWN)

    def test_mixed_answer_and_unknown_is_not_returned_without_citations(self):
        evidence = [('a', 'text', {'title': 'Source', 'page': '1', 'url': 'https://example.edu'}, 0.1)]
        with patch.object(helpdesk, 'route', return_value='POLICY'), patch.object(helpdesk, 'retrieve', return_value=evidence), patch.object(helpdesk, 'chat', return_value='A fact [1]. ' + helpdesk.UNKNOWN), patch.object(helpdesk, 'log_unknown'):
            self.assertEqual(helpdesk.answer('Question'), helpdesk.UNKNOWN)

    def test_broad_open_elective_query_asks_for_context(self):
        with patch.object(helpdesk, 'route', return_value='POLICY'), patch.object(helpdesk, 'log_unknown'):
            self.assertIn('programme and admission year', helpdesk.answer('How many open elective credits do I need for B.Tech?'))

    def test_historical_instructor_is_not_used_for_unspecified_semester(self):
        self.assertEqual(helpdesk.lookup('Who teaches CSL7570?', 'instructors.csv'), [])
        result = helpdesk.lookup('Who taught CSL7570 in May 2022?', 'instructors.csv')
        self.assertEqual(result[0]['instructor'], 'Sumit Kalra')
        self.assertTrue(result[0]['source_url'].startswith('https://'))

    def test_missing_leave_dates_are_marked_for_review(self):
        with patch.object(helpdesk, 'route', return_value='EMAIL'), patch.object(helpdesk, 'lookup', return_value=[]), patch.object(helpdesk, 'chat', return_value='Dear Instructor, please grant two days leave. Sincerely, [Name]'), patch.object(helpdesk, 'log_unknown'):
            result = helpdesk.answer('Write a sick leave email for CSL7570 for two days')
            self.assertIn('[start date]', result)
            self.assertIn('CSL7570', result)

    def test_unmentioned_attachment_is_removed_from_draft(self):
        draft = 'Dear Instructor. Please find attached my medical documentation. Thank you.'
        with patch.object(helpdesk, 'route', return_value='EMAIL'), patch.object(helpdesk, 'lookup', return_value=[]), patch.object(helpdesk, 'chat', return_value=draft), patch.object(helpdesk, 'log_unknown'):
            result = helpdesk.answer('Draft a sick leave email')
            self.assertNotIn('attached', result)
            self.assertIn('Thank you', result)

    def test_historical_timetable_uses_specified_semester(self):
        self.assertEqual(helpdesk.lookup('Slot for CSL1010?', 'timetable.csv'), [])
        row = helpdesk.lookup('Slot for CSL1010 2023-24 Semester-I?', 'timetable.csv')[0]
        self.assertIn('Group A1', row['slot'])

    def test_single_agent_uses_shared_retrieval_and_citations(self):
        evidence = [('a', '12 credits', {'title': 'Curriculum', 'page': '8', 'url': 'https://example.edu/source'}, 0.1)]
        with patch.object(helpdesk, 'route', return_value='POLICY') as route, patch.object(helpdesk, 'retrieve', return_value=evidence), patch.object(helpdesk, 'chat', return_value='12 credits [1]'):
            result = helpdesk.answer('How many credits?', mode='single')
            route.assert_called_once_with('How many credits?', helpdesk.CHAT, 'single')
            self.assertIn('Curriculum, page 8', result)

    def test_trace_shows_actual_policy_delegation_and_retrieval(self):
        evidence = [('a', '12 credits', {'title': 'Curriculum', 'page': '8', 'url': 'https://example.edu/source'}, 0.1)]
        events = []
        with patch.object(helpdesk, 'route', return_value='POLICY'), patch.object(helpdesk, 'retrieve', return_value=evidence) as retrieve, patch.object(helpdesk, 'chat', return_value='12 credits [1]'):
            result = helpdesk.answer('How many credits?', trace=lambda role, message: events.append((role, message)))
        retrieve.assert_called_once()
        self.assertIn('12 credits', result)
        self.assertTrue(any(role == 'Orchestrator' and 'Delegating' in message for role, message in events))
        self.assertTrue(any(role == 'Policy agent' and 'Retrieved 1' in message for role, message in events))

    def test_trace_identifies_clarification_without_claiming_a_delegation(self):
        events = []
        with patch.object(helpdesk, 'route') as route, patch.object(helpdesk, 'log_unknown'):
            helpdesk.answer('What is the attendance requirement for the exam?', trace=lambda role, message: events.append((role, message)))
        route.assert_not_called()
        self.assertTrue(any('rule identified' in message for _, message in events))
        self.assertFalse(any('Delegating' in message for _, message in events))

    def test_single_mode_trace_uses_single_agent_label(self):
        events = []
        with patch.object(helpdesk, 'route', return_value='SCHEDULE'), patch.object(helpdesk, 'lookup', return_value=[]), patch.object(helpdesk, 'log_unknown'):
            helpdesk.answer('Slot for CSL7570?', mode='single', trace=lambda role, message: events.append((role, message)))
        self.assertTrue(events)
        self.assertEqual({role for role, _ in events}, {'Helpdesk'})

    def test_scanned_attendance_policy_has_page_level_ocr(self):
        path = helpdesk.ROOT / 'documents' / 'attendance-amendment-2024.pdf'
        pages = helpdesk.pdf_pages(path, 'attendance-amendment-2024')
        self.assertEqual(pages[0][0], '1')
        self.assertTrue(pages[0][2])
        self.assertIn('Revised Policy', pages[0][1])
        self.assertIn('without sanctioned leave for more than two weeks', pages[0][1])

    def test_attendance_deregistration_requires_condition_and_page_two(self):
        evidence = [('a', 'text', {'title': 'Attendance amendment', 'page': '1', 'source_id': 'attendance-amendment-2024', 'url': 'https://example.edu/policy'}, 0.1)]
        with patch.object(helpdesk, 'route', return_value='POLICY'), patch.object(helpdesk, 'retrieve', return_value=evidence), patch.object(helpdesk, 'chat', return_value='Below 75%, instructors may recommend deregistration [1].'), patch.object(helpdesk, 'log_unknown'):
            result = helpdesk.answer('What happens under the 2024 attendance policy?')
            self.assertIn("I don't know", result)

    def test_attendance_fallback_uses_relevant_page_two_extract(self):
        evidence = [
            ('a', 'text', {'title': 'Attendance amendment', 'page': '1', 'source_id': 'attendance-amendment-2024', 'url': 'https://example.edu/policy'}, 0.1),
            ('b', "If a student's attendance falls below 75% without any valid reason, the instructor can recommend de-registration from the course to the SUGC/SPGC.", {'title': 'Attendance amendment', 'page': '2', 'source_id': 'attendance-amendment-2024', 'url': 'https://example.edu/policy'}, 0.2),
        ]
        with patch.object(helpdesk, 'route', return_value='POLICY'), patch.object(helpdesk, 'retrieve', return_value=evidence), patch.object(helpdesk, 'chat', return_value='Below 75%, instructors may recommend deregistration [1].'):
            result = helpdesk.answer('What happens below 75% attendance under the 2024 policy?')
            self.assertIn('without any valid reason', result)
            self.assertIn('page 2', result)

    def test_count_requires_certified_complete_listing(self):
        with tempfile.TemporaryDirectory(dir=helpdesk.ROOT) as temp:
            root = Path(temp)
            (root / 'data').mkdir()
            (root / 'data' / 'offerings_coverage.json').write_text('[{"semester":"Semester I 2026-27","department":"Humanities","complete":true,"source_url":"https://example.edu/list"}]', encoding='utf-8')
            (root / 'data' / 'timetable.csv').write_text('course_code,semester,department,level,category\nHUL401,Semester I 2026-27,Humanities,400,Open Elective\nHUL401,Semester I 2026-27,Humanities,400,Open Elective\nHUL402,Semester I 2026-27,Humanities,400,Elective\n', encoding='utf-8')
            with patch.object(helpdesk, 'ROOT', root):
                self.assertIsNone(helpdesk.count_offerings('How many 400-level Humanities electives this semester?'))
                self.assertIn('2 distinct', helpdesk.count_offerings('How many 400-level Humanities electives in Semester I 2026-27?'))


if __name__ == '__main__':
    unittest.main()
