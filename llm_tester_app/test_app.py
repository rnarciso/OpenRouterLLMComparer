# llm_tester_app/test_app.py
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open

# Add the project root directory (parent of 'llm_tester_app') to sys.path
# This allows imports like 'from llm_tester_app.app import ...'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now, attempt to import the modules and functions from the app
# These imports MUST succeed for the tests to target the actual code.
try:
    from llm_tester_app.app import query_openrouter_model, setup_database
    import llm_tester_app.app as app_module  # Used for patching attributes of the app module
except ImportError as e:
    print(f"CRITICAL IMPORT ERROR: Failed to import from llm_tester_app.app: {e}")
    print("Ensure llm_tester_app/__init__.py exists and is empty.")
    print("Ensure app.py is not broken.")
    # Define placeholder functions if import fails, so tests can at least be discovered,
    # but this indicates a fundamental problem.
    def query_openrouter_model(prompt, model_name): return None
    def setup_database(conn): pass
    class MockSt:
        secrets = {}
    class MockAppModule:
        st = MockSt()
        requests = MagicMock()
        sqlite3 = MagicMock()
        psycopg2 = MagicMock()

    app_module = MockAppModule()


class TestQueryOpenRouterModel(unittest.TestCase):

    @patch.object(app_module, 'requests')
    @patch.dict(app_module.st.secrets, {'OPENROUTER_API_KEY': 'test_api_key'}, clear=True)
    def test_successful_api_call(self, mock_requests):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'choices': [{'message': {'content': 'Test response'}}]}
        mock_requests.post.return_value = mock_response

        result = query_openrouter_model("test prompt", "test_model")
        
        mock_requests.post.assert_called_once_with(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": "Bearer test_api_key",
                "Content-Type": "application/json"
            },
            json={
                "model": "test_model",
                "messages": [{"role": "user", "content": "test prompt"}]
            }
        )
        self.assertEqual(result, "Test response")

    @patch.object(app_module, 'requests')
    @patch.dict(app_module.st.secrets, {'OPENROUTER_API_KEY': 'test_api_key'}, clear=True)
    def test_api_request_exception(self, mock_requests):
        mock_requests.post.side_effect = app_module.requests.exceptions.RequestException("API error")
        
        result = query_openrouter_model("test prompt", "test_model")
        self.assertTrue("Erro na API: API error" in result)


    @patch.object(app_module, 'requests')
    @patch.dict(app_module.st.secrets, {'OPENROUTER_API_KEY': 'test_api_key'}, clear=True)
    def test_malformed_json_keyerror(self, mock_requests):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'unexpected_structure': True} # Missing 'choices'
        mock_response.text = "{'unexpected_structure': True}"
        mock_requests.post.return_value = mock_response

        result = query_openrouter_model("test prompt", "test_model")
        self.assertTrue("Erro ao processar a resposta da API" in result)
        self.assertTrue("KeyError" in result or "'choices'" in result) # Check for indication of KeyError

    @patch.object(app_module, 'requests')
    @patch.dict(app_module.st.secrets, {'OPENROUTER_API_KEY': 'test_api_key'}, clear=True)
    def test_malformed_json_indexerror(self, mock_requests):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'choices': []} # Empty 'choices' list
        mock_response.text = "{'choices': []}"
        mock_requests.post.return_value = mock_response

        result = query_openrouter_model("test prompt", "test_model")
        self.assertTrue("Erro ao processar a resposta da API" in result)
        self.assertTrue("IndexError" in result or "list index out of range" in result)


class TestSetupDatabase(unittest.TestCase):

    def test_table_creation_sqlite(self):
        # This test uses the actual sqlite3 module, not a mock from app_module
        import sqlite3
        conn = sqlite3.connect(':memory:')
        try:
            # Call the actual setup_database function
            setup_database(conn)
            
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='llm_evaluations'")
                self.assertIsNotNone(cursor.fetchone(), "Table 'llm_evaluations' was not created.")
                
                cursor.execute("PRAGMA table_info(llm_evaluations)")
                columns_info = cursor.fetchall()
                columns = {row[1] for row in columns_info}
                expected_columns = {'id', 'prompt', 'model_name', 'response', 'rating', 'created_at'}
                self.assertEqual(columns, expected_columns, f"Table columns do not match. Got: {columns}")

                # Check if 'id' is primary key (simplified check for SQLite)
                id_column_info = next((col for col in columns_info if col[1] == 'id'), None)
                self.assertIsNotNone(id_column_info, "'id' column not found")
                self.assertEqual(id_column_info[5], 1, "'id' column is not the primary key.") # pk field in PRAGMA table_info

            finally:
                cursor.close()
        finally:
            conn.close()

if __name__ == '__main__':
    unittest.main()