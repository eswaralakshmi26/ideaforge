import sys
from unittest.mock import MagicMock
import google.auth

# Mock google.auth.default to return dummy credentials and project
google.auth.default = MagicMock(return_value=(MagicMock(), "mock-project"))

# Initialize Vertex AI with mock project and location
import vertexai
vertexai.init(project="mock-project", location="us-east1")
