# Security Considerations

This document outlines security best practices, threat modeling, and responsible disclosure procedures for the Wyckoff-Elliott Trading Signals Bot.

---

## 🔒 Security Principles

1. **Defense in Depth**: Multiple layers of security controls
2. **Least Privilege**: Bot has minimal required permissions
3. **Secure by Default**: Trading disabled unless explicitly enabled
4. **Secrets Management**: All credentials via environment variables
5. **Input Validation**: Sanitize all user inputs
6. **Audit Logging**: Track all critical operations

---

## 🛡️ Threat Model

### Assets to Protect

1. **Binance API Keys** (if trading enabled)
   - Risk: Unauthorized trading, fund theft
   - Impact: **CRITICAL**

2. **Discord Bot Token**
   - Risk: Bot impersonation, spam, server takeover
   - Impact: **HIGH**

3. **Supabase Service Key**
   - Risk: Unauthorized database access/modification
   - Impact: **HIGH**

4. **Trading Algorithm Logic**
   - Risk: Reverse engineering, exploitation
   - Impact: **MEDIUM**

5. **Historical Signal Data**
   - Risk: Intellectual property theft
   - Impact: **LOW**

### Attack Vectors

| Vector | Likelihood | Impact | Mitigation |
|--------|-----------|--------|------------|
| API Key Compromise | Medium | Critical | Environment variables, never commit |
| SQL Injection | Low | High | Parameterized queries, RLS policies |
| Command Injection | Low | Medium | Input validation on Discord commands |
| Denial of Service | Medium | Medium | Rate limiting, error handling |
| Dependency Vulnerabilities | High | Varies | Regular updates, security scanning |
| Insider Threat | Low | Critical | Minimize access, audit logs |

---

## 🔐 Secrets Management

### Environment Variables Only

**✅ DO:**
```env
# .env file (NEVER commit to Git)
DISCORD_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4.GhJ4Kl.Mn0PqRsTuVwXyZ
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
BINANCE_API_SECRET=abcdef1234567890
```

**❌ DON'T:**
```python
# Hardcoded secrets (NEVER do this!)
DISCORD_TOKEN = "MTIzNDU2Nzg5MDEyMzQ1Njc4.GhJ4Kl.Mn0PqRsTuVwXyZ"
```

### .gitignore Protection

Ensure `.gitignore` includes:
```gitignore
.env
*.env
.env.*
!.env.example
```

Verify with:
```powershell
git status  # .env should NOT appear
```

### Token Rotation

**Best Practice:** Rotate secrets every 90 days.

**Discord Token:**
1. Discord Developer Portal → Bot → Reset Token
2. Update `.env` immediately
3. Restart bot

**Supabase Keys:**
1. Supabase Dashboard → Settings → API → Regenerate
2. Update `.env` immediately
3. Restart bot

**Binance API Keys:**
1. Binance → API Management → Delete old key
2. Create new key with same restrictions
3. Update `.env` immediately
4. Test on testnet first!

---

## 🚨 Trading Safety

### Default Configuration (SAFE)

```env
ENABLE_TRADING=false  # Trading DISABLED
```

Bot only sends Discord alerts. **No actual trades executed.**

### Enabling Trading (DANGER ZONE)

#### ⚠️ WARNING ⚠️

**Trading cryptocurrencies carries significant financial risk. You could lose your entire investment. This bot is for educational purposes only.**

#### Step 1: Use Testnet FIRST

**NEVER enable trading with real funds without extensive testnet testing.**

```env
ENABLE_TRADING=true
BINANCE_API_KEY=testnet-api-key
BINANCE_API_SECRET=testnet-api-secret
BINANCE_TESTNET=true  # ← CRITICAL: Use testnet
```

**Testnet URLs:**
- Spot: [https://testnet.binance.vision](https://testnet.binance.vision)
- Futures: [https://testnet.binancefuture.com](https://testnet.binancefuture.com)

**Testnet Duration:** Run for at least 2 weeks, monitoring every signal.

#### Step 2: Create Restricted API Keys

When creating Binance API keys:

✅ **Enable:**
- Enable Reading
- Enable Spot & Margin Trading (if trading spot)
- Enable Futures (if trading futures)

❌ **NEVER Enable:**
- Enable Withdrawals ← **THIS IS CRITICAL**
- Enable Internal Transfer

**Additional Restrictions:**
- Restrict to specific IP addresses (if static IP available)
- Set daily withdrawal limit to 0 (if option available)

#### Step 3: Start with Minimum Position Size

```env
POSITION_SIZE_USDT=10.0  # Start with $10 per trade
MAX_OPEN_POSITIONS=1     # Only 1 position at a time
LEVERAGE=1               # No leverage initially
```

**Gradually increase** only after proven success.

#### Step 4: Enable 2FA on Exchange

- **Binance**: Enable Google Authenticator + SMS
- **Never** share 2FA codes with anyone
- Store backup codes securely (offline)

#### Step 5: Monitor Continuously

- Check positions daily
- Set up exchange alerts for large losses
- Have manual override plan (kill bot, close positions manually)

---

## 🔑 Authentication & Authorization

### Discord Bot Permissions

**Minimum Required Permissions:**
- Send Messages
- Embed Links
- Use Slash Commands

**Optional Permissions:**
- Read Message History (for command history)
- Add Reactions (for interactive commands)

**NEVER grant:**
- Administrator
- Manage Server
- Manage Roles
- Manage Channels

### Supabase Row Level Security (RLS)

#### Current Configuration

**Service Role (Bot):**
- Full access to all tables
- Bypasses RLS policies

**Anon Key (Public):**
- Read-only access to signals (if exposed via API)
- No write access

#### Future: User-Specific Access

For multi-tenant deployment, implement RLS:

```sql
-- Example: Users can only see their own subscriptions
CREATE POLICY user_subscriptions_policy ON user_subscriptions
  FOR SELECT
  USING (auth.uid() = user_id);
```

---

## 🛡️ Input Validation

### Discord Command Validation

All user inputs sanitized:

```python
# Example: /lastsignal command
@app_commands.command(name="lastsignal")
async def lastsignal(
    interaction: discord.Interaction,
    symbol: str,
    timeframe: str
):
    # Validate symbol format (alphanumeric only)
    if not symbol.isalnum():
        await interaction.response.send_message("Invalid symbol", ephemeral=True)
        return
    
    # Validate timeframe against whitelist
    valid_timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
    if timeframe not in valid_timeframes:
        await interaction.response.send_message("Invalid timeframe", ephemeral=True)
        return
    
    # Safe to query database
    signals = await supabase_client.get_recent_signals(symbol.upper(), timeframe, 1)
```

### SQL Injection Prevention

**✅ Use parameterized queries:**
```python
# Safe
supabase.table("signals").select("*").eq("symbol", user_input).execute()
```

**❌ NEVER concatenate SQL:**
```python
# DANGEROUS - DO NOT USE
query = f"SELECT * FROM signals WHERE symbol = '{user_input}'"
```

Supabase Python SDK automatically parameterizes queries.

---

## 🚦 Rate Limiting

### Binance API Rate Limits

**Public API:**
- 1200 requests per minute
- 20 requests per second

**Bot Implementation:**
- Token bucket algorithm in `binance_rest.py`
- Refills at 20 tokens/second
- Max burst: 100 tokens

**If Exceeded:**
- Bot sleeps until tokens available
- Logs warning: "Rate limit approaching"

### Discord API Rate Limits

**Global Limit:**
- 50 requests per second

**Per-Channel:**
- 5 messages per 5 seconds

**Bot Implementation:**
- 1-second delay between messages in `notifier.py`
- Prevents rate limit errors

**If Exceeded:**
- Discord returns 429 error
- Bot automatically retries after delay

---

## 📊 Audit Logging

### What Gets Logged

**INFO Level:**
- Bot startup/shutdown
- Configuration loaded
- Signals generated (with confidence, rationale)
- WebSocket connections/disconnections
- Discord messages sent

**WARNING Level:**
- Rate limit approaching
- Missing data
- Unexpected responses

**ERROR Level:**
- Database errors
- API failures
- WebSocket errors (before reconnect)

**CRITICAL Level:**
- Fatal errors requiring manual intervention

### Log Format

**JSON (Recommended):**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "message": "Signal generated",
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "direction": "LONG",
  "confidence": 0.85,
  "entry": 50000.00
}
```

**Text (Development):**
```
2024-01-15 10:30:00 - INFO - Signal generated: BTCUSDT 1h LONG @ 50000.00 (confidence: 0.85)
```

### Log Storage

**Local Development:**
- Console output only

**Production:**
- File: `/var/log/wyeli-bot.log`
- Rotate daily, keep 30 days
- Use `logrotate` on Linux

**Cloud (Optional):**
- Ship to CloudWatch, Datadog, or similar
- Enables centralized monitoring and alerting

### Log Access Control

- Logs may contain sensitive information (API errors with partial keys)
- Restrict read access to administrators only
- Never commit logs to Git

---

## 🔍 Dependency Security

### Scanning for Vulnerabilities

**Automated Scanning (GitHub Actions):**

CI pipeline includes:
```yaml
- name: Check for known vulnerabilities
  run: |
    pip install safety
    safety check --json
  continue-on-error: true

- name: Security linting
  run: |
    pip install bandit
    bandit -r src/ -f json -o bandit-report.json
```

**Manual Scanning:**
```powershell
# Check dependencies
pip install safety
safety check

# Scan code for security issues
pip install bandit
bandit -r src/
```

### Keeping Dependencies Updated

**Monthly Updates:**
```powershell
pip list --outdated
pip install --upgrade <package>
pip freeze > requirements.txt
```

**Test After Updates:**
```powershell
pytest tests/
python -m src.bot.main  # Run briefly to verify
```

### Pinning Versions

`requirements.txt` includes version pins:
```
discord.py==2.3.2
supabase==2.3.0
```

**Trade-offs:**
- ✅ Reproducible builds
- ❌ May miss security patches

**Compromise:** Pin major/minor, allow patch updates:
```
discord.py>=2.3,<2.4
```

---

## 🌐 Network Security

### Firewall Configuration

**Outbound (Required):**
- `fapi.binance.com:443` (Binance REST API)
- `fstream.binance.com:443` (Binance WebSocket)
- `discord.com:443` (Discord API)
- `*.supabase.co:443` (Supabase)

**Inbound:**
- None required (bot is client-only)

### HTTPS Only

All external connections use TLS:
- `https://` for REST APIs
- `wss://` for WebSocket

**Verify:**
```python
# Enforced in code
self.ws_url = "wss://fstream.binance.com/ws"  # Not ws://
```

### VPN (Optional)

If running on VPS, consider VPN for additional privacy:
- Hides bot IP from exchanges
- May reduce targeted attacks
- Can add latency (test impact on WebSocket)

---

## 🚨 Incident Response

### Security Incident Classification

**P0 - Critical:**
- API keys compromised
- Unauthorized trades executed
- Database breach

**P1 - High:**
- Bot token leaked
- Service disruption >1 hour

**P2 - Medium:**
- Suspicious activity detected
- Dependency vulnerability (with exploit)

**P3 - Low:**
- Dependency vulnerability (no known exploit)
- Configuration issue

### Response Procedures

#### P0 - API Keys Compromised

1. **Immediate Actions (within 5 minutes):**
   - Disable Binance API keys in exchange settings
   - Stop bot process: `sudo systemctl stop wyeli-bot`
   - Close all open positions manually (if trading enabled)

2. **Investigation (within 1 hour):**
   - Review Binance API logs for unauthorized activity
   - Check Git history for accidental commits of `.env`
   - Review system access logs

3. **Remediation (within 24 hours):**
   - Generate new API keys with same restrictions
   - Update all systems with new keys
   - Implement additional monitoring

4. **Post-Mortem:**
   - Document how compromise occurred
   - Implement preventive measures
   - Share lessons learned (without sensitive details)

#### P1 - Discord Token Leaked

1. **Immediate Actions (within 15 minutes):**
   - Regenerate bot token in Discord Developer Portal
   - Update `.env` with new token
   - Restart bot: `sudo systemctl restart wyeli-bot`

2. **Investigation:**
   - Check Discord server audit logs
   - Review recent messages sent by bot
   - Verify no unauthorized servers added

3. **Remediation:**
   - Kick bot from unauthorized servers
   - Review bot permissions in all servers
   - Document incident

---

## 🕵️ Responsible Disclosure

### Reporting Security Vulnerabilities

If you discover a security vulnerability, please:

1. **DO NOT** create a public GitHub issue
2. **Email:** security@yourdomain.com (replace with actual email)
3. **Include:**
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (optional)

### Response Timeline

- **Initial Response:** Within 48 hours
- **Assessment:** Within 1 week
- **Fix (Critical):** Within 2 weeks
- **Fix (Non-Critical):** Next release cycle

### Disclosure Policy

- **Embargo Period:** 90 days after fix released
- **Public Disclosure:** After embargo, we'll publish advisory
- **Credit:** Security researchers credited (unless requested otherwise)

---

## ✅ Security Checklist

Before deploying to production:

### Configuration
- [ ] All secrets in environment variables (not hardcoded)
- [ ] `.env` file in `.gitignore`
- [ ] `ENABLE_TRADING=false` (unless explicitly needed)
- [ ] If trading enabled, `BINANCE_TESTNET=true` for testing
- [ ] API keys have minimum required permissions
- [ ] 2FA enabled on all exchange accounts

### Network
- [ ] Firewall configured (outbound only)
- [ ] HTTPS/WSS enforced for all connections
- [ ] IP restrictions on API keys (if static IP available)

### Monitoring
- [ ] Structured logging enabled (`LOG_FORMAT=json`)
- [ ] Log rotation configured
- [ ] Error alerts configured (email, Slack, etc.)
- [ ] Database backups enabled (Supabase paid plan)

### Code
- [ ] Dependencies scanned with `safety check`
- [ ] Code scanned with `bandit`
- [ ] Unit tests passing
- [ ] No secrets in Git history

### Access Control
- [ ] Bot has minimum Discord permissions
- [ ] Supabase RLS policies reviewed
- [ ] Server access restricted to admins only

### Documentation
- [ ] README updated with security notes
- [ ] RUNBOOK includes emergency procedures
- [ ] Security contact information current

---

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Binance API Security Best Practices](https://www.binance.com/en/support/faq/360002502072)
- [Discord Bot Security](https://discord.com/developers/docs/topics/oauth2#bot-vs-user-accounts)
- [Supabase Security](https://supabase.com/docs/guides/auth/row-level-security)

---

## 📞 Security Contact

For security issues, contact:
- **Email:** security@yourdomain.com
- **PGP Key:** [Link to public key]
- **Response Time:** 48 hours

For general issues, use GitHub Issues.

---

**Remember:** Security is a continuous process, not a one-time task. Stay vigilant, keep systems updated, and always assume compromise is possible.

🔒 **Stay Safe. Trade Responsibly.**
