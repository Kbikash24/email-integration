# Configuration Files Setup

This directory contains sensitive credential files that are not tracked in Git.

## Required Files

You need to create the following files by copying the `.template` files and filling in your actual credentials:

1. `firebase_dev.json` - Firebase service account credentials
2. `service_account_dev.json` - Service account credentials
3. `bigquery-prod.json` - BigQuery production credentials
4. `client_secret.json` - Google OAuth client credentials

## Setup Instructions

1. Copy each `.template` file and remove the `.template` extension:
   ```bash
   cp firebase_dev.json.template firebase_dev.json
   cp service_account_dev.json.template service_account_dev.json
   cp bigquery-prod.json.template bigquery-prod.json
   cp client_secret.json.template client_secret.json
   ```

2. Fill in the actual values in each file with your Google Cloud credentials

3. **NEVER commit these files to Git** - they are already in .gitignore

## Security Note

⚠️ These files contain sensitive credentials. Keep them secure and never share them publicly.
