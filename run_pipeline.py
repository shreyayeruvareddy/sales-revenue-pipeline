# ============================================================
# run_pipeline.py — Sales & Revenue Analytics Pipeline
# Usage: py -3.11 run_pipeline.py
# ============================================================

import time, logging, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_pipeline():
    start  = time.time()
    run_id = __import__("datetime").datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    logger.info("=" * 60)
    logger.info(f"🛒 SALES PIPELINE STARTED  |  run_id: {run_id}")
    logger.info("=" * 60)

    # STAGE 1 — DATA GENERATION
    logger.info("\n📦 STAGE 1: Sales Data Generation")
    logger.info("-" * 40)
    t = time.time()
    try:
        from src.data_generator import run_data_generation
        transactions, customers, products, ts = run_data_generation()
        logger.info(f"✅ Stage 1 complete in {round(time.time()-t,2)}s | {len(transactions):,} transactions")
    except Exception as e:
        logger.error(f"❌ Stage 1 FAILED: {e}"); return False

    # STAGE 2 — ETL TRANSFORMATION
    logger.info("\n🔄 STAGE 2: ETL Transformation & KPI Analytics")
    logger.info("-" * 40)
    t = time.time()
    try:
        from src.transformation import run_transformation
        dfs = run_transformation(transactions, ts)
        logger.info(f"✅ Stage 2 complete in {round(time.time()-t,2)}s")
        logger.info(f"   Total Revenue: ${dfs['transactions']['net_revenue'].sum():,.2f}")
    except Exception as e:
        logger.error(f"❌ Stage 2 FAILED: {e}"); return False

    # STAGE 3 — DATABASE LOAD
    logger.info("\n🗄️  STAGE 3: Star Schema Database Load")
    logger.info("-" * 40)
    t = time.time()
    try:
        from src.db_loader import run_db_load
        dfs["customers_raw"] = customers
        dfs["products_raw"]  = products
        run_db_load(dfs)
        logger.info(f"✅ Stage 3 complete in {round(time.time()-t,2)}s")
    except Exception as e:
        logger.error(f"❌ Stage 3 FAILED: {e}"); return False

    # STAGE 4 — VALIDATION
    logger.info("\n✅ STAGE 4: Validation Summary")
    logger.info("-" * 40)
    try:
        from src.db_loader import query_summary
        summary = query_summary()
        print("\n" + summary.to_string())

        # Print key insights
        regional = dfs["regional"]
        underperforming = regional[regional["vs_avg_pct"] < -5]
        logger.info(f"\n📊 KEY INSIGHTS:")
        logger.info(f"   Total Annual Revenue:  ${dfs['transactions']['net_revenue'].sum():,.2f}")
        logger.info(f"   Total Transactions:    {len(dfs['transactions']):,}")
        logger.info(f"   Top Region:            {regional.iloc[0]['region']} (${regional.iloc[0]['total_revenue']:,.2f})")
        if len(underperforming):
            for _, row in underperforming.iterrows():
                logger.info(f"   Underperforming:       {row['region']} ({row['vs_avg_pct']}% vs avg)")
        logger.info(f"   Top Category:          {dfs['categories'].iloc[0]['category']} (${dfs['categories'].iloc[0]['total_revenue']:,.2f})")
        logger.info(f"   RFM Champions:         {(dfs['rfm']['rfm_segment']=='Champions').sum()} customers")

    except Exception as e:
        logger.warning(f"⚠️  Validation warning: {e}")

    total = round(time.time() - start, 2)
    logger.info("\n" + "=" * 60)
    logger.info(f"🎉 PIPELINE COMPLETE  |  Total time: {total}s")
    logger.info("=" * 60)
    return True


if __name__ == "__main__":
    run_pipeline()
