# Secret Safety Protocol

## Absolute Prohibitions
- NEVER run `cat .env`, `echo $SECRET`, or display full API keys/passwords
- NEVER commit .env, credentials.json, or files containing secrets
- NEVER display full secret values in output — show first 10 chars max with `***`

## Safe Alternatives
- Check existence: `test -f .env && echo "exists"` or `grep -c "KEY_NAME" .env`
- Show masked: `grep "KEY_NAME" .env | cut -c1-10` followed by `***`
- Use Infisical CLI: `infisical secrets get SECRET_NAME --plain | head -c 10`

## Accidental Exposure Response
1. STOP immediately
2. Inform user: "A secret was exposed in output"
3. Recommend immediate rotation
4. GitHub auto-revokes detected keys — rotation is urgent
