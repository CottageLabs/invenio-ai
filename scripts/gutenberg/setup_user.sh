#!/bin/bash
# Setup InvenioRDM user and API token for Gutenberg uploads

set -e

USER_EMAIL="gutenberg@example.org"
USER_PASSWORD="GutenbergUploader2025!"
TOKEN_NAME="gutenberg-upload"
TOKEN_FILE="scripts/gutenberg/.api_token"

echo "============================================"
echo "Setting up Gutenberg uploader user..."
echo "============================================"
echo ""

# Create user (will fail if already exists, which is fine)
echo "Creating user: $USER_EMAIL"
pipenv run invenio users create \
  "$USER_EMAIL" \
  --password "$USER_PASSWORD" \
  --active \
  --confirm 2>&1 || echo "User may already exist, continuing..."

echo ""
echo "Creating API token..."

# Create token and save it
TOKEN=$(pipenv run invenio tokens create -n "$TOKEN_NAME" -u "$USER_EMAIL" 2>&1 | grep -oP '(?<=Token: ).*' || true)

if [ -z "$TOKEN" ]; then
    echo "Error: Failed to create token"
    echo "You may need to create it manually with:"
    echo "  pipenv run invenio tokens create -n $TOKEN_NAME -u $USER_EMAIL"
    exit 1
fi

# Save token to file
echo "$TOKEN" > "$TOKEN_FILE"
chmod 600 "$TOKEN_FILE"

echo ""
echo "============================================"
echo "Setup complete!"
echo "============================================"
echo ""
echo "User credentials:"
echo "  Email: $USER_EMAIL"
echo "  Password: $USER_PASSWORD"
echo ""
echo "API Token saved to: $TOKEN_FILE"
echo "Token: $TOKEN"
echo ""
echo "You can now run the upload script with:"
echo "  python3 scripts/gutenberg/upload_to_invenio.py"
echo ""
