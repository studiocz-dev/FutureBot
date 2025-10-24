# Bot Logs

This directory contains daily log files for the trading bot.

## 📁 Log Files

- **Format**: `bot_YYYYMMDD.log` (e.g., `bot_20251024.log`)
- **Rotation**: New file created each day automatically
- **Format**: JSON (one JSON object per line for easy parsing)
- **Encoding**: UTF-8

## 📊 Log Structure

Each log entry contains:
```json
{
  "timestamp": "2025-10-24T12:34:56.789Z",
  "level": "INFO",
  "logger": "src.bot.main",
  "message": "Signal generated for BTCUSDT",
  "symbol": "BTCUSDT",
  "timeframe": "15m",
  "signal_type": "LONG",
  "confidence": 0.723
}
```

## 🔍 Useful Commands

### View today's logs
```bash
# Windows PowerShell
Get-Content logs/bot_$(Get-Date -Format 'yyyyMMdd').log -Tail 50

# Linux/Mac
tail -f logs/bot_$(date +%Y%m%d).log
```

### Search for errors
```bash
# Windows PowerShell
Select-String -Path "logs/*.log" -Pattern "ERROR"

# Linux/Mac
grep ERROR logs/*.log
```

### Count signals by type
```bash
# Windows PowerShell
Get-Content logs/bot_*.log | Select-String "LONG|SHORT" | Measure-Object

# Linux/Mac
grep -o '"signal_type":"LONG"' logs/*.log | wc -l
grep -o '"signal_type":"SHORT"' logs/*.log | wc -l
```

### Parse JSON logs (Python)
```python
import json
from pathlib import Path
from datetime import datetime

# Read today's log
today = datetime.now().strftime('%Y%m%d')
log_file = Path(f'logs/bot_{today}.log')

signals = []
errors = []

with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        entry = json.loads(line)
        
        if entry.get('signal_type'):
            signals.append(entry)
        
        if entry['level'] == 'ERROR':
            errors.append(entry)

print(f"Total signals: {len(signals)}")
print(f"Total errors: {len(errors)}")
```

## 🧹 Maintenance

### Clean old logs (keep last 30 days)
```bash
# Windows PowerShell
Get-ChildItem logs/*.log | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item

# Linux/Mac
find logs/ -name "*.log" -mtime +30 -delete
```

### Compress old logs
```bash
# Windows PowerShell
Get-ChildItem logs/*.log | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | ForEach-Object { Compress-Archive -Path $_ -DestinationPath "$($_.FullName).zip"; Remove-Item $_ }

# Linux/Mac
find logs/ -name "*.log" -mtime +7 -exec gzip {} \;
```

## 📈 Log Analysis Tips

### 1. Track Signal Performance
Look for patterns in signals that led to profitable trades:
- Confidence levels that worked best
- Symbols with highest success rate
- Time patterns (certain hours/days)

### 2. Debug Issues
When something goes wrong:
- Check timestamp of last successful operation
- Look for ERROR/WARNING messages around that time
- Check if WebSocket disconnections occurred
- Verify database operations completed

### 3. Monitor Bot Health
Regular checks:
- Are signals being generated consistently?
- Are there repeated errors?
- Is WebSocket reconnecting too often?
- Are API rate limits being hit?

## 🚨 Important Events to Monitor

| Event | Log Level | What to Look For |
|-------|-----------|------------------|
| Signal Generated | INFO | `"signal_type": "LONG"` or `"SHORT"` |
| WebSocket Error | ERROR | `"logger": "src.ingest.binance_ws"` |
| Database Error | ERROR | `"logger": "src.storage.supabase_client"` |
| Bot Started | INFO | `"message": "Bot started successfully"` |
| Bot Shutdown | INFO | `"message": "Shutting down"` |

## 💡 Troubleshooting

### No logs being written?
- Check if `logs/` directory exists (created automatically)
- Check file permissions
- Check disk space

### Log files too large?
- Implement log rotation (already daily)
- Compress old logs
- Delete logs older than needed

### Can't read log files?
- Ensure UTF-8 encoding
- Each line is a separate JSON object
- Use `json.loads()` per line, not `json.load()`

---

**Note**: Log files are ignored by Git (`.gitignore`) and are NOT deployed to the server. Each environment (local/server) maintains its own logs.
