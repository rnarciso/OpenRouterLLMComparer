import unittest
import sqlite3
from unittest.mock import patch, MagicMock
import sys
import os

# Adjust sys.path to allow importing from llm_tester_app
# This assumes the test script is run from the repository root or a context where /app is accessible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now try to import the app module and its functions
# We need to ensure that the app.py file uses the restored get_db_connection
# that does not force SQLite, and does not have the minimal test app content.
# For the purpose of this test, we will assume app.py is in its correct state.
try:
    from llm_tester_app.app import query_openrouter_model, setup_database
    import llm_tester_app.app as app_module # For patching st.secrets
except ImportError as e:
    print(f"Failed to import app modules: {e}")
    print("Ensure llm_tester_app/app.py exists and is in the correct state (not minimal test version).")
    print("Current sys.path:", sys.path)
    # As a fallback for the agent's environment, if direct import fails,
    # try to define dummy functions so the test structure can at least be created.
    # This is not ideal but helps in restricted execution environments.
    def query_openrouter_model(prompt, model_name):
        pass
    def setup_database(conn):
        pass
    class st_secrets_mock: # Mock for app_module.st.secrets
        def get(self, key):
            return None
    
    class st_mock:
        secrets = st_secrets_mock()

    class app_module_mock:
        st = st_mock()
        # Define requests within the mock if it's patched there
        class requests_mock:
            class exceptions:
                RequestException = Exception # Define a generic exception
            def post(self, *args, **kwargs):
                pass
        requests = requests_mock()


    app_module = app_module_mock()


# Mock requests.exceptions.RequestException if requests could not be imported via app_module
# This is a bit of a workaround for environments where the full app structure isn't perfectly mirrored.
if not hasattr(app_module.requests, 'exceptions'):
    class RequestsExceptionsMock:
        RequestException = type('RequestException', (Exception,), {})
    app_module.requests.exceptions = RequestsExceptionsMock()


class TestQueryOpenRouterModel(unittest.TestCase):

    @patch.object(app_module, 'st', MagicMock(secrets={'OPENROUTER_API_KEY': 'test_api_key'}))
    @patch.object(app_module.requests, 'post')
    def test_successful_api_call(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'choices': [{'message': {'content': 'Test response'}}]}
        mock_post.return_value = mock_response

        result = query_openrouter_model("test prompt", "test_model")
        self.assertEqual(result, "Test response")
        mock_post.assert_called_once()

    @patch.object(app_module, 'st', MagicMock(secrets={'OPENROUTER_API_KEY': 'test_api_key'}))
    @patch.object(app_module.requests, 'post')
    def test_api_request_exception(self, mock_post):
        mock_post.side_effect = app_module.requests.exceptions.RequestException("API error")

        result = query_openrouter_model("test prompt", "test_model")
        self.assertEqual(result, "Erro na API: API error")
        mock_post.assert_called_once()

    @patch.object(app_module, 'st', MagicMock(secrets={'OPENROUTER_API_KEY': 'test_api_key'}))
    @patch.object(app_module.requests, 'post')
    def test_malformed_json_keyerror(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'unexpected_structure': True} # Missing 'choices'
        mock_post.return_value = mock_response

        result = query_openrouter_model("test prompt", "test_model")
        # Depending on how deep the access is, the error message might change.
        # If it tries to access data['choices'][0] directly.
        self.assertTrue("Erro ao processar a resposta da API" in result)
        self.assertTrue("choices" in result or "KeyError" in result) # Check for general indications
        mock_post.assert_called_once()

    @patch.object(app_module, 'st', MagicMock(secrets={'OPENROUTER_API_KEY': 'test_api_key'}))
    @patch.object(app_module.requests, 'post')
    def test_malformed_json_indexerror(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'choices': []} # Empty list for choices
        mock_post.return_value = mock_response

        result = query_openrouter_model("test prompt", "test_model")
        self.assertTrue("Erro ao processar a resposta da API" in result)
        # Check for general indications of list index out of range
        self.assertTrue("list index out of range" in result or "IndexError" in result)
        mock_post.assert_called_once()


class TestSetupDatabase(unittest.TestCase):

    def test_table_creation_sqlite(self):
        conn = sqlite3.connect(':memory:')
        try:
            setup_database(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='llm_evaluations'")
            self.assertIsNotNone(cursor.fetchone(), "Table 'llm_evaluations' was not created.")

            # Verify table columns
            cursor.execute("PRAGMA table_info(llm_evaluations)")
            columns_info = cursor.fetchall()
            columns = {row[1] for row in columns_info}
            expected_columns = {'id', 'prompt', 'model_name', 'response', 'rating', 'created_at'}
            self.assertEqual(columns, expected_columns, "Table columns do not match expected schema.")

            # Check primary key and auto-increment behavior for 'id' if possible (more complex for PRAGMA)
            # For SQLite, SERIAL PRIMARY KEY from PostgreSQL becomes INTEGER PRIMARY KEY AUTOINCREMENT
            id_column_info = next((col for col in columns_info if col[1] == 'id'), None)
            self.assertIsNotNone(id_column_info, "'id' column not found.")
            # col[2] is type, col[5] is pk flag
            self.assertEqual(id_column_info[2].upper(), 'INTEGER', "'id' column type is not INTEGER.")
            self.assertEqual(id_column_info[5], 1, "'id' column is not a primary key.")
            # AUTOINCREMENT is not directly checkable via PRAGMA table_info in a simple way,
            # but INTEGER PRIMARY KEY on its own implies auto-increment behavior for SQLite in most cases.
            # The DDL "id SERIAL PRIMARY KEY" is compatible enough for SQLite to make it auto-incrementing.

        finally:
            conn.close()

if __name__ == '__main__':
    # This is to ensure that the app.py used by tests is the full version, not the minimal one.
    # This part of the code is for the agent to verify/restore app.py if needed.
    # In a real CI/CD, app.py would be checked out from version control.
    
    # For now, we assume app.py is correct for the test execution.
    # If imports failed, the dummy functions are used, and tests might not be meaningful.
    if 'app_module_mock' in globals():
        print("\nWARNING: Running tests with MOCKED app functions due to import errors. "
              "Actual app logic is NOT being tested.\n")

    unittest.main()
