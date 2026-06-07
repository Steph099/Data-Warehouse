"""Spark aggregation job.

Reads `data`, keeps the latest version per (asset, source, business_date) and drops
tombstones (honoring the temporal model), aggregates `close` per business year, and
writes summaries to `totals`. Runs inside the Spark container (PySpark + stdlib only);
see README / docker-compose for the spark-submit command.
"""
import os

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def main() -> None:
    keyspace = os.environ.get("CASSANDRA_KEYSPACE", "acme_dwh")
    spark = SparkSession.builder.appName("acme-dwh-aggregation").getOrCreate()

    data = (
        spark.read.format("org.apache.spark.sql.cassandra")
        .options(table="data", keyspace=keyspace)
        .load()
    )

    # latest version per business date, tombstones excluded
    latest_per_day = Window.partitionBy(
        "asset_id", "data_source_id", "business_date"
    ).orderBy(F.col("system_time").desc())
    latest = (
        data.withColumn("_rn", F.row_number().over(latest_per_day))
        .filter(F.col("_rn") == 1)
        .filter(~F.coalesce(F.col("deleted"), F.lit(False)))
        .withColumn("close", F.col("values_double")["close"])
        .filter(F.col("close").isNotNull())
    )

    totals = latest.groupBy("asset_id", "data_source_id", "business_date_year").agg(
        F.count(F.lit(1)).cast("long").alias("cnt"),
        F.min("close").alias("min_close"),
        F.max("close").alias("max_close"),
        F.avg("close").alias("avg_close"),
    )

    (
        totals.write.format("org.apache.spark.sql.cassandra")
        .options(table="totals", keyspace=keyspace)
        .mode("append")
        .save()
    )

    print(f"[aggregation] wrote {totals.count()} (asset, source, year) summary rows to totals")
    totals.orderBy("asset_id", "business_date_year").show(50, truncate=False)
    spark.stop()


if __name__ == "__main__":
    main()
