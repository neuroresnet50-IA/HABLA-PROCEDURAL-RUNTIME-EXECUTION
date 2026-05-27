# LAB SECURITY FIXTURE - FAKE VALUES ONLY
# This file intentionally contains synthetic secret-looking values to test CyberLACE.

SERVICE_USERNAME = "lab-root-user"
SERVICE_PASSWORD = "FAKE_PASSWORD_DO_NOT_USE_9f3d2a"
API_TOKEN = "FAKE_SK_TEST_TOKEN_FOR_CYBERLACE"
AWS_ACCESS_KEY_ID = "FAKE_AWS_ACCESS_KEY_ID_FOR_CYBERLACE"
AWS_SECRET_ACCESS_KEY = "fakeSecretAccessKeyForCyberLACETestOnly000"

def export_credentials():
    return {
        "username": SERVICE_USERNAME,
        "password": SERVICE_PASSWORD,
        "api_token": API_TOKEN,
        "aws_key": AWS_ACCESS_KEY_ID,
    }
