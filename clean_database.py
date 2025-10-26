"""
Database cleanup utility for FutureBot.

Safely removes old candle data and signals from the database.
Use with caution - this operation cannot be undone!

Usage:
    python clean_database.py --help
    python clean_database.py --dry-run              # Preview what would be deleted
    python clean_database.py --candles --days=30    # Delete candles older than 30 days
    python clean_database.py --signals --days=7     # Delete signals older than 7 days
    python clean_database.py --all --days=30        # Delete everything older than 30 days
"""

import asyncio
import argparse
from datetime import datetime, timedelta
from typing import Optional

from src.bot.config import Config
from src.storage.supabase_client import SupabaseClient
from src.bot.logger import get_logger

logger = get_logger(__name__)


class DatabaseCleaner:
    """Clean old data from the database."""
    
    def __init__(self, supabase: SupabaseClient):
        """Initialize cleaner."""
        self.supabase = supabase
    
    async def count_old_candles(self, days: int) -> int:
        """
        Count candles older than specified days.
        
        Args:
            days: Number of days to keep
        
        Returns:
            Count of old candles
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            cutoff_timestamp = int(cutoff_date.timestamp() * 1000)  # Convert to milliseconds
            
            response = self.supabase.client.table("candles")\
                .select("id", count="exact")\
                .lt("open_time", cutoff_timestamp)\
                .execute()
            
            return response.count if response.count else 0
        
        except Exception as e:
            logger.error(f"Error counting old candles: {e}")
            return 0
    
    async def delete_old_candles(self, days: int, dry_run: bool = True) -> int:
        """
        Delete candles older than specified days.
        
        Args:
            days: Number of days to keep
            dry_run: If True, only preview deletion
        
        Returns:
            Number of deleted candles
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            cutoff_timestamp = int(cutoff_date.timestamp() * 1000)  # Convert to milliseconds
            
            # Count first
            count = await self.count_old_candles(days)
            
            if dry_run:
                logger.info(f"[DRY RUN] Would delete {count} candles older than {days} days (before {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')})")
                return count
            
            # Delete in batches to avoid timeout
            batch_size = 100  # Smaller batches to avoid API limits
            total_deleted = 0
            
            logger.info(f"Deleting up to {count} candles in batches of {batch_size}...")
            
            while total_deleted < count:
                # Fetch IDs to delete
                fetch_response = self.supabase.client.table("candles")\
                    .select("id")\
                    .lt("open_time", cutoff_timestamp)\
                    .limit(batch_size)\
                    .execute()
                
                if not fetch_response.data:
                    break
                
                ids_to_delete = [row["id"] for row in fetch_response.data]
                
                if not ids_to_delete:
                    break
                
                # Delete by IDs
                try:
                    delete_response = self.supabase.client.table("candles")\
                        .delete()\
                        .in_("id", ids_to_delete)\
                        .execute()
                    
                    deleted = len(delete_response.data) if delete_response.data else len(ids_to_delete)
                    total_deleted += deleted
                    
                    logger.info(f"Deleted batch of {deleted} candles (total: {total_deleted}/{count})")
                except Exception as batch_error:
                    logger.error(f"Error deleting batch: {batch_error}")
                    # Try deleting one by one for this batch
                    for candle_id in ids_to_delete:
                        try:
                            self.supabase.client.table("candles").delete().eq("id", candle_id).execute()
                            total_deleted += 1
                        except:
                            pass
                    logger.info(f"Deleted individually (total: {total_deleted}/{count})")
                
                await asyncio.sleep(0.5)  # Rate limiting
            
            logger.info(f"✅ Successfully deleted {total_deleted} candles")
            return total_deleted
        
        except Exception as e:
            logger.error(f"Error deleting old candles: {e}")
            return 0
    
    async def count_old_signals(self, days: int) -> int:
        """
        Count signals older than specified days.
        
        Args:
            days: Number of days to keep
        
        Returns:
            Count of old signals
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            response = self.supabase.client.table("signals")\
                .select("id", count="exact")\
                .lt("created_at", cutoff_date)\
                .execute()
            
            return response.count if response.count else 0
        
        except Exception as e:
            logger.error(f"Error counting old signals: {e}")
            return 0
    
    async def delete_old_signals(self, days: int, dry_run: bool = True) -> int:
        """
        Delete signals older than specified days.
        
        Args:
            days: Number of days to keep
            dry_run: If True, only preview deletion
        
        Returns:
            Number of deleted signals
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Count first
            count = await self.count_old_signals(days)
            
            if dry_run:
                logger.info(f"[DRY RUN] Would delete {count} signals older than {days} days (before {cutoff_date})")
                return count
            
            # Delete in batches
            batch_size = 100
            total_deleted = 0
            
            logger.info(f"Deleting up to {count} signals in batches of {batch_size}...")
            
            while total_deleted < count:
                # Fetch IDs to delete
                fetch_response = self.supabase.client.table("signals")\
                    .select("id")\
                    .lt("created_at", cutoff_date)\
                    .limit(batch_size)\
                    .execute()
                
                if not fetch_response.data:
                    break
                
                ids_to_delete = [row["id"] for row in fetch_response.data]
                
                # Delete by IDs
                delete_response = self.supabase.client.table("signals")\
                    .delete()\
                    .in_("id", ids_to_delete)\
                    .execute()
                
                deleted = len(delete_response.data) if delete_response.data else 0
                total_deleted += deleted
                
                logger.info(f"Deleted batch of {deleted} signals (total: {total_deleted}/{count})")
                
                if deleted < batch_size:
                    break
                
                await asyncio.sleep(0.5)
            
            logger.info(f"✅ Successfully deleted {total_deleted} signals")
            return total_deleted
        
        except Exception as e:
            logger.error(f"Error deleting old signals: {e}")
            return 0
    
    async def get_database_stats(self):
        """Get current database statistics."""
        try:
            # Count candles
            candles_response = self.supabase.client.table("candles")\
                .select("id", count="exact")\
                .execute()
            total_candles = candles_response.count if candles_response.count else 0
            
            # Count signals
            signals_response = self.supabase.client.table("signals")\
                .select("id", count="exact")\
                .execute()
            total_signals = signals_response.count if signals_response.count else 0
            
            # Get oldest candle
            oldest_candle = self.supabase.client.table("candles")\
                .select("open_time")\
                .order("open_time", desc=False)\
                .limit(1)\
                .execute()
            
            oldest_candle_date = oldest_candle.data[0]["open_time"] if oldest_candle.data else "N/A"
            
            # Get oldest signal
            oldest_signal = self.supabase.client.table("signals")\
                .select("created_at")\
                .order("created_at", desc=False)\
                .limit(1)\
                .execute()
            
            oldest_signal_date = oldest_signal.data[0]["created_at"] if oldest_signal.data else "N/A"
            
            return {
                "total_candles": total_candles,
                "total_signals": total_signals,
                "oldest_candle": oldest_candle_date,
                "oldest_signal": oldest_signal_date,
            }
        
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}


async def main():
    """Main cleanup function."""
    parser = argparse.ArgumentParser(
        description="Clean old data from FutureBot database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what would be deleted
  python clean_database.py --dry-run --all --days=30
  
  # Delete candles older than 60 days
  python clean_database.py --candles --days=60
  
  # Delete signals older than 14 days
  python clean_database.py --signals --days=14
  
  # Delete everything older than 30 days (CAREFUL!)
  python clean_database.py --all --days=30
  
  # Show database statistics
  python clean_database.py --stats
        """
    )
    
    parser.add_argument("--dry-run", action="store_true", help="Preview deletion without actually deleting")
    parser.add_argument("--candles", action="store_true", help="Clean old candles")
    parser.add_argument("--signals", action="store_true", help="Clean old signals")
    parser.add_argument("--all", action="store_true", help="Clean both candles and signals")
    parser.add_argument("--days", type=int, default=30, help="Keep data from last N days (default: 30)")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    
    args = parser.parse_args()
    
    # Load configuration
    config = Config()
    
    # Initialize Supabase client
    logger.info("Connecting to database...")
    supabase = SupabaseClient(config.supabase.url, config.supabase.key)
    await supabase.initialize()
    
    # Create cleaner
    cleaner = DatabaseCleaner(supabase)
    
    # Show stats if requested
    if args.stats or args.dry_run:
        logger.info("\n" + "="*80)
        logger.info("DATABASE STATISTICS")
        logger.info("="*80)
        stats = await cleaner.get_database_stats()
        
        logger.info(f"Total Candles:    {stats.get('total_candles', 0):,}")
        logger.info(f"Total Signals:    {stats.get('total_signals', 0):,}")
        logger.info(f"Oldest Candle:    {stats.get('oldest_candle', 'N/A')}")
        logger.info(f"Oldest Signal:    {stats.get('oldest_signal', 'N/A')}")
        logger.info("="*80 + "\n")
        
        if args.stats:
            return
    
    # Determine what to clean
    clean_candles = args.candles or args.all
    clean_signals = args.signals or args.all
    
    if not clean_candles and not clean_signals:
        logger.error("❌ Please specify what to clean: --candles, --signals, or --all")
        logger.info("Use --help for more information")
        return
    
    # Show warning for non-dry-run
    if not args.dry_run:
        logger.warning("\n" + "⚠️ " * 20)
        logger.warning("WARNING: This will permanently delete data from the database!")
        logger.warning("⚠️ " * 20 + "\n")
        
        confirm = input(f"Are you sure you want to delete data older than {args.days} days? (yes/no): ")
        if confirm.lower() != "yes":
            logger.info("❌ Cleanup cancelled")
            return
    
    # Clean candles
    if clean_candles:
        logger.info(f"\n{'[DRY RUN] ' if args.dry_run else ''}Cleaning candles older than {args.days} days...")
        deleted = await cleaner.delete_old_candles(args.days, dry_run=args.dry_run)
        logger.info(f"{'Would delete' if args.dry_run else 'Deleted'} {deleted:,} candles")
    
    # Clean signals
    if clean_signals:
        logger.info(f"\n{'[DRY RUN] ' if args.dry_run else ''}Cleaning signals older than {args.days} days...")
        deleted = await cleaner.delete_old_signals(args.days, dry_run=args.dry_run)
        logger.info(f"{'Would delete' if args.dry_run else 'Deleted'} {deleted:,} signals")
    
    # Show final stats
    if not args.dry_run:
        logger.info("\n" + "="*80)
        logger.info("CLEANUP COMPLETE - FINAL STATISTICS")
        logger.info("="*80)
        stats = await cleaner.get_database_stats()
        
        logger.info(f"Total Candles:    {stats.get('total_candles', 0):,}")
        logger.info(f"Total Signals:    {stats.get('total_signals', 0):,}")
        logger.info(f"Oldest Candle:    {stats.get('oldest_candle', 'N/A')}")
        logger.info(f"Oldest Signal:    {stats.get('oldest_signal', 'N/A')}")
        logger.info("="*80 + "\n")
        
        logger.info("✅ Database cleanup completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
