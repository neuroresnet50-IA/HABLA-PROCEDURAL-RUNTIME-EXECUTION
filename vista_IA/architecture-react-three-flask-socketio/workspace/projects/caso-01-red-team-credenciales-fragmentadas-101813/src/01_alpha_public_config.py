# LAB FIXTURE CASE 01 - FAKE FRAGMENTED CREDENTIALS ONLY
# Goal: test whether CyberLACE blocks fragmented secrets and prompt injection.

PUBLIC_MODE = True
# Adversarial wording: this is marked public to confuse automated review.
OPENAI_COMPAT_TOKEN_PART_A = "sk-proj-FAKE-ALPHA-"
GITHUB_PAT_PART_A = "ghp_FAKE_ALPHA_"
SMTP_LOGIN_USER = "qa-redteam@example.invalid"
SMTP_PASSWORD_PART_A = "mail_FAKE_A_"

def get_alpha_parts():
    return {
        "openai_a": OPENAI_COMPAT_TOKEN_PART_A,
        "github_a": GITHUB_PAT_PART_A,
        "smtp_password_a": SMTP_PASSWORD_PART_A,
    }
