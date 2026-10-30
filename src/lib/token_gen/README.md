# token_gen

Generates a Synamedia silent-login token for a household in two calls: (1) OAuth client-credentials at `auth.synamedia.com/oauth/token`, (2) `silent-login/create-token` with the returned bearer.

## Credentials

Put them in a gitignored `.env` at the repo root (never commit them), or export them in the shell; real environment variables win over the file.

```
SYNAMEDIA_CLIENT_ID=<client id>
SYNAMEDIA_CLIENT_SECRET=<client secret>
```

## Usage

```
python -m src.lib.token_gen.cli <householdID> [--expires-in 3600] [--env-file .env]
```

Prints the create-token JSON response; exits 1 with a message on stderr for missing credentials, HTTP errors or a response without `access_token`. Uses only the standard library (`urllib`).
