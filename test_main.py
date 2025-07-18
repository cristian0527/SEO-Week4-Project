import unittest
from datetime import datetime, timedelta
from main import (
    ddmmyyyy_filter,
    ddmmyyyy_time_filter,
    parse_time_blocks,
    detect_start_date_from_description,
    convert_to_datetime_with_future_dates,
    add_task_to_google_calendar,
    app,
)
from unittest.mock import patch, MagicMock
import pytz

class TestAppFunctions(unittest.TestCase):

    def test_ddmmyyyy_filter(self):
        date_obj = datetime(2025, 7, 18)
        result = ddmmyyyy_filter(date_obj)
        self.assertEqual(result, '18/07/2025')

    def test_ddmmyyyy_time_filter(self):
        dt = datetime(2025, 7, 18, 15, 30)
        result = ddmmyyyy_time_filter(dt)
        self.assertEqual(result, '18/07/2025 15:30')

    def test_parse_time_blocks(self):
        plan = """
        ## 📅 Your Study Schedule

        **TIME BLOCK 1**
        ⏰ **Time:** 10:00 AM - 11:30 AM
        📝 **Task:** Study Calculus
        ⏱️ **Duration:** 1 hour 30 minutes
        📋 **Details:** Work on limits and derivatives.

        **TIME BLOCK 2**
        ⏰ **Time:** 12:00 PM - 1:00 PM
        📝 **Task:** Take a Break
        ⏱️ **Duration:** 1 hour
        📋 **Details:** Relax or grab lunch.
        """
        blocks = parse_time_blocks(plan)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]['task'], 'Study Calculus')
        self.assertEqual(blocks[1]['task'], 'Take a Break')

    def test_detect_start_date_from_description(self):
        now = datetime(2025, 7, 18)  
        start_date = detect_start_date_from_description("I want to start Saturday", now)
        self.assertEqual(start_date, datetime(2025, 7, 19).date())

    def test_convert_to_datetime_with_future_dates(self):
        now = datetime(2025, 7, 18, 15, 0)  
        deadline = now + timedelta(days=2)
        dt = convert_to_datetime_with_future_dates("10:00 AM", now.date(), now, deadline)
        self.assertEqual(dt.date(), datetime(2025, 7, 19, 10, 0) .date())
        self.assertEqual(dt.time().hour, 10)

        now = datetime(2025, 7, 20, 0, 0)  
        deadline = now + timedelta(days=1)
        dt = convert_to_datetime_with_future_dates("03:00 PM", now.date(), now, deadline)
        self.assertEqual(dt.date(), datetime(2025, 7, 20, 10, 0) .date())
        self.assertEqual(dt.time().hour, 15)

    @patch("main.create_task_event")
    @patch("main.load_credentials")
    @patch("main.update_task_schedule")
    def test_add_task_to_google_calendar(self, mock_update, mock_load, mock_create_event):
        mock_creds = MagicMock()
        mock_load.return_value = mock_creds
        mock_create_event.return_value = "mock-event-id"

        user_id = 1
        task_id = 42
        title = "Test Task"
        description = "Do something important"
        due = datetime(2025, 7, 20, 14, 0)

        success, event_id = add_task_to_google_calendar(user_id, task_id, title, description, due)
        self.assertTrue(success)
        self.assertEqual(event_id, "mock-event-id")
        mock_update.assert_called_once()

    def test_landing_route(self):
        tester = app.test_client(self)
        response = tester.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome', response.data)  

if __name__ == '__main__':
    unittest.main()