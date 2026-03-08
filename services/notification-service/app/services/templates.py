from jinja2 import Environment

jinja = Environment(autoescape=True)

TEMPLATES = {
    "welcome": {
        "subject": "Welcome to SaaS Platform, {{ full_name }}! 🎉",
        "body": """
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h1 style="color: #4F46E5;">Welcome aboard, {{ full_name }}! 🎉</h1>
  <p>Your account has been created successfully.</p>
  <p>You're on the <strong>Free plan</strong>. Upgrade anytime to unlock more features.</p>
  <a href="https://yourapp.com/dashboard"
     style="background: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin-top: 16px;">
    Go to Dashboard
  </a>
  <p style="margin-top: 32px; color: #666; font-size: 12px;">
    You received this because you signed up at yourapp.com
  </p>
</body>
</html>
""",
    },
    "password_reset": {
        "subject": "Reset your password",
        "body": """
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h1 style="color: #4F46E5;">Reset Your Password</h1>
  <p>Click the button below to reset your password. This link expires in 1 hour.</p>
  <a href="https://yourapp.com/reset-password?token={{ reset_token }}"
     style="background: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin-top: 16px;">
    Reset Password
  </a>
  <p style="margin-top: 16px; color: #666;">If you didn't request this, ignore this email.</p>
</body>
</html>
""",
    },
    "file_uploaded": {
        "subject": "Your file '{{ filename }}' has been processed",
        "body": """
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h1 style="color: #4F46E5;">File Processed ✅</h1>
  <p>Your file <strong>{{ filename }}</strong> has been uploaded and processed successfully.</p>
  <p>Size: {{ file_size }}</p>
  <a href="https://yourapp.com/files"
     style="background: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin-top: 16px;">
    View Files
  </a>
</body>
</html>
""",
    },
}


def render_template(template_name: str, context: dict) -> tuple[str, str]:
    """Returns (subject, html_body) for a given template and context"""
    template_data = TEMPLATES.get(template_name)
    if not template_data:
        raise ValueError(f"Template '{template_name}' not found")

    subject = jinja.from_string(template_data["subject"]).render(**context)
    body = jinja.from_string(template_data["body"]).render(**context)
    return subject, body
