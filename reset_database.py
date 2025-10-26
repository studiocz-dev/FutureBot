"""
Complete database reset utility.

WARNING: This will DELETE ALL candles and signals from the database!
Use only if you want to start completely fresh.

The bot will re-download all historical data on next startup.

Usage:
    python reset_database.py --help
    python reset_database.py --dry-run        # Preview
    python reset_database.py --confirm        # Actually delete everything
"""

import asyncio
import argparse
from src.bot.config import Config
from src.storage.supabase_client import SupabaseClient
from src.bot.logger import get_logger

logger = get_logger(__name__)


async def reset_database(dry_run: bool = True):
    """
    Reset the entire database by deleting all candles and signals.
    
    Args:
        dry_run: If True, only show what would be deleted
    """
    # Load configuration
    config = Config()
    
    # Initialize Supabase client
    logger.info("Connecting to database...")
    supabase = SupabaseClient(config.supabase.url, config.supabase.key)
    await supabase.initialize()
    
    # Get counts
    logger.info("\n" + "="*80)
    logger.info("CURRENT DATABASE STATE")
    logger.info("="*80)
    
    candles_response = supabase.client.table("candles").select("id", count="exact").execute()
    total_candles = candles_response.count if candles_response.count else 0
    
    signals_response = supabase.client.table("signals").select("id", count="exact").execute()
    total_signals = signals_response.count if signals_response.count else 0
    
    logger.info(f"Total Candles: {total_candles:,}")
    logger.info(f"Total Signals: {total_signals:,}")
    logger.info("="*80 + "\n")
    
    if dry_run:
        logger.warning("[DRY RUN MODE]")
        logger.warning(f"Would delete ALL {total_candles:,} candles")
        logger.warning(f"Would delete ALL {total_signals:,} signals")
        logger.warning("\nRun with --confirm to actually delete")
        return
    
    # Confirm deletion
    logger.error("\n" + "🚨 " * 20)
    logger.error("DANGER: YOU ARE ABOUT TO DELETE EVERYTHING!")
    logger.error("🚨 " * 20 + "\n")
    logger.error(f"This will permanently delete:")
    logger.error(f"  • {total_candles:,} candles")
    logger.error(f"  • {total_signals:,} signals")
    logger.error("\nThe bot will re-download all data on next startup.")
    logger.error("This operation CANNOT be undone!\n")
    
    confirm1 = input("Type 'DELETE EVERYTHING' to confirm: ")
    if confirm1 != "DELETE EVERYTHING":
        logger.info("❌ Reset cancelled")
        return
    
    confirm2 = input("Are you absolutely sure? (yes/no): ")
    if confirm2.lower() != "yes":
        logger.info("❌ Reset cancelled")
        return
    
    # Delete all candles
    logger.info("\n🗑️  Deleting all candles...")
    batch_size = 500
    total_deleted_candles = 0
    
    while True:
        # Fetch IDs
        fetch_response = supabase.client.table("candles")\
            .select("id")\
            .limit(batch_size)\
            .execute()
        
        if not fetch_response.data:
            break
        
        ids_to_delete = [row["id"] for row in fetch_response.data]
        
        # Delete batch
        supabase.client.table("candles").delete().in_("id", ids_to_delete).execute()
        
        total_deleted_candles += len(ids_to_delete)
        logger.info(f"  Deleted {total_deleted_candles:,} / {total_candles:,} candles...")
        
        await asyncio.sleep(0.3)
    
    logger.info(f"✅ Deleted {total_deleted_candles:,} candles")
    
    # Delete all signals
    logger.info("\n🗑️  Deleting all signals...")
    batch_size = 100
    total_deleted_signals = 0
    
    while True:
        # Fetch IDs
        fetch_response = supabase.client.table("signals")\
            .select("id")\
            .limit(batch_size)\
            .execute()
        
        if not fetch_response.data:
            break
        
        ids_to_delete = [row["id"] for row in fetch_response.data]
        
        # Delete batch
        supabase.client.table("signals").delete().in_("id", ids_to_delete).execute()
        
        total_deleted_signals += len(ids_to_delete)
        logger.info(f"  Deleted {total_deleted_signals:,} / {total_signals:,} signals...")
        
        await asyncio.sleep(0.3)
    
    logger.info(f"✅ Deleted {total_deleted_signals:,} signals")
    
    # Final verification
    logger.info("\n" + "="*80)
    logger.info("RESET COMPLETE - FINAL STATE")
    logger.info("="*80)
    
    candles_response = supabase.client.table("candles").select("id", count="exact").execute()
    remaining_candles = candles_response.count if candles_response.count else 0
    
    signals_response = supabase.client.table("signals").select("id", count="exact").execute()
    remaining_signals = signals_response.count if signals_response.count else 0
    
    logger.info(f"Remaining Candles: {remaining_candles:,}")
    logger.info(f"Remaining Signals: {remaining_signals:,}")
    logger.info("="*80 + "\n")
    
    if remaining_candles == 0 and remaining_signals == 0:
        logger.info("✅ Database successfully reset!")
        logger.info("\n📊 Next steps:")
        logger.info("  1. Restart the bot")
        logger.info("  2. It will automatically download fresh historical data")
        logger.info("  3. This will take 60-90 seconds on startup")
    else:
        logger.warning(f"⚠️  Warning: {remaining_candles} candles and {remaining_signals} signals still remain")


async def main():
    parser = argparse.ArgumentParser(
        description="Complete database reset - DELETE EVERYTHING",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
⚠️  WARNING: This is a destructive operation!

Examples:
  # Preview what would be deleted
  python reset_database.py --dry-run
  
  # Actually delete everything (CAREFUL!)
  python reset_database.py --confirm
        """
    )
    
    parser.add_argument("--dry-run", action="store_true", help="Preview deletion without actually deleting")
    parser.add_argument("--confirm", action="store_true", help="Confirm you want to delete everything")
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.confirm:
        logger.error("❌ You must specify either --dry-run or --confirm")
        logger.info("Use --help for more information")
        return
    
    await reset_database(dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
