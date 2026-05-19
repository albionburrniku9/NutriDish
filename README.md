# NutriDish

NutriDish is a Flask-based AI recipe assistant for users with dietary restrictions. Users can create an account, log in, generate recipe ideas from ingredients they already have, save recipes, manage their profile, and upgrade to a Pro-style membership flow.

## Features

- User signup and login with Flask-Login sessions
- Auto-login after successful signup
- Password hashing with Werkzeug
- Forgot password and reset password token flow
- Saved recipes
- Multilingual UI support
- Dietary restriction checks
- AI/API-powered recipe recommendations
- Profile and subscription management UI
- Vercel-ready production configuration
- Hosted database support through `DATABASE_URL`

## Tech Stack

- Python / Flask
- Flask-SQLAlchemy
- Flask-Login
- PostgreSQL in production, for example Supabase or Neon
- SQLite fallback for local development
- Stripe checkout placeholder flow
- Vercel Python runtime

## Local Setup

1. Clone the repository.

```bash
git clone https://github.com/albionburrniku9/NutriDish.git
cd NutriDish
```

2. Create and activate a virtual environment.

```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Install dependencies.

```bash
pip install -r requirements.txt
```

4. Create local database tables.

```bash
python -c "from app import app; from models import db; app.app_context().push(); db.create_all(); print('tables created')"
```

5. Run the app.

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Environment Variables

Required in production:

```env
DATABASE_URL=your_hosted_postgres_connection_string
SECRET_KEY=your_long_random_secret
```

Optional for local development:

```env
LOCAL_DATABASE_URL=sqlite:///nutridish_v2.db
FLASK_DEBUG=1
```

Temporary for first production table creation only:

```env
AUTO_CREATE_TABLES=1
```

Use `AUTO_CREATE_TABLES=1` only once to create tables, then remove it and redeploy.

Optional Stripe variables:

```env
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
```

Password reset email is not fully connected to an email provider yet. The backend token logic exists, but SMTP/provider setup still needs to be configured.

## Supabase / PostgreSQL Setup

For Vercel, use a hosted production database instead of local SQL Server or local SQLite.

Recommended Supabase connection type:

```text
Transaction pooler
```

Use the URI format from Supabase:

```text
postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-region.pooler.supabase.com:6543/postgres
```

Make sure to replace `PROJECT_REF`, `PASSWORD`, and `region` with real Supabase values.

## Vercel Deployment

1. Push the latest code to GitHub.
2. Import the project into Vercel.
3. Add production environment variables:

```env
DATABASE_URL=your_real_supabase_or_neon_url
SECRET_KEY=your_long_random_secret
```

4. Add temporarily:

```env
AUTO_CREATE_TABLES=1
```

5. Redeploy.
6. Visit:

```text
https://your-domain.vercel.app/api/health/db
```

7. Confirm:

```json
{
  "database_connected": true,
  "missing_tables": [],
  "success": true
}
```

8. Remove `AUTO_CREATE_TABLES` and redeploy again.

## Database Health Check

The app includes:

```text
/api/health/db
```

This checks database connectivity and required tables:

- `users`
- `saved_recipes`
- `dietary_profiles`
- `password_reset_tokens`

## Auth Flow

- `/signup` creates a user.
- `/api/auth/signup` validates input, hashes the password, stores the user, and logs them in automatically.
- `/login` displays the login page.
- `/api/auth/login` validates credentials and starts a remembered session.
- `/logout` ends the session.
- `/forgot_password` creates a secure password reset token.
- `/reset_password/<token>` lets users set a new hashed password.

Sessions use Flask-Login with remembered login support and a 14-day duration.

## Testing Checklist

Local:

```bash
python -m compileall app.py models.py translations.py ai_engine.py
python app.py
```

Manual checks:

- Open `/`
- Sign up for a new account
- Confirm auto-login works
- Refresh and confirm the session persists
- Log out
- Log in again
- Request a password reset
- Visit `/api/health/db`
- Generate recipe recommendations
- Save a recipe
- Open saved recipe details
- Check mobile navigation

Production:

- Confirm Vercel env vars are set
- Confirm `/api/health/db` returns success
- Test signup and login on the production domain
- Remove `AUTO_CREATE_TABLES` after table creation

## Notes

- Do not hardcode database credentials or secrets.
- Do not use local SQL Server or SQLite for production.
- Keep `SECRET_KEY` stable in production. Changing it logs users out.
- Configure a real email provider before relying on password reset emails in production.
